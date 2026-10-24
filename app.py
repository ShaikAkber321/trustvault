import os
from flask import Flask, render_template, jsonify, request
from sqlalchemy import text
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from extensions import db, login_manager, csrf, limiter
from models import User


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config.get("IS_PRODUCTION"):
        # Render terminates TLS at one trusted reverse proxy. Trust only the
        # forwarded client/protocol values; do not trust forwarded Host headers.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0)
        if not app.config.get("SECRET_KEY") or len(app.config["SECRET_KEY"]) < 32:
            raise RuntimeError("Set a random SECRET_KEY of at least 32 characters before starting TrustVault in production.")
        missing_seeds = [key for key in ("SEED_ADMIN_PASSWORD", "SEED_OWNER_PASSWORD", "SEED_VIEWER_PASSWORD")
                         if not os.getenv(key) or len(os.getenv(key, "")) < 12]
        if missing_seeds:
            raise RuntimeError("Set unique 12+ character Render environment secrets: " + ", ".join(missing_seeds))
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    Migrate(app, db, directory="migrations")

    @app.after_request
    def apply_security_headers(response):
        # These headers are applied to every response, including errors. Scripts
        # are same-origin static files; inline styles remain for visual effects.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; font-src 'self' https://fonts.gstatic.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "script-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        # Dynamic responses may contain private document metadata. Do not allow
        # shared browser/proxy caches to retain authenticated pages.
        if request.endpoint != "static":
            response.headers.setdefault("Cache-Control", "no-store")
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    from auth import bp as auth_bp
    from documents import bp as documents_bp
    from admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(admin_bp)

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ok"), 200
        except Exception:
            app.logger.exception("Health check failed")
            return jsonify(status="error"), 503

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("error.html", code=413, message="Upload is larger than the configured limit."), 413

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, message="You are not allowed to perform this action."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="The requested resource was not found or is not available to you."), 404

    @app.errorhandler(429)
    def rate_limited(_error):
        return render_template("error.html", code=429, message="Too many requests. Please wait a little before trying again."), 429

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template("error.html", code=500, message="Something went wrong. No internal details are shown here."), 500

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = db.session.get(User, int(user_id))
            return user if user and user.active else None
        except (ValueError, TypeError):
            return None

    # Database schema creation/migrations and demo seeding run explicitly through
    # init_db.py / Flask-Migrate before serving traffic. Doing this in every
    # Gunicorn worker can race during concurrent startup.
    return app


def seed_demo_users(app):
    production = bool(app.config.get("IS_PRODUCTION"))
    env_passwords = {
        "admin": os.getenv("SEED_ADMIN_PASSWORD"),
        "owner": os.getenv("SEED_OWNER_PASSWORD"),
        "viewer": os.getenv("SEED_VIEWER_PASSWORD"),
    }
    if production and any(not value or len(value) < 12 for value in env_passwords.values()):
        # Never seed known/default credentials into a public deployment.
        app.logger.error("Demo accounts were not seeded: set unique 12+ character SEED_*_PASSWORD values in the production environment.")
        return
    demo = [
        ("TrustVault Admin", "admin@trustvault.local", "admin", env_passwords["admin"] or "ChangeThisAdmin!2026"),
        ("Document Owner", "owner@trustvault.local", "owner", env_passwords["owner"] or "ChangeThisOwner!2026"),
        ("Viewer Account", "viewer@trustvault.local", "viewer", env_passwords["viewer"] or "ChangeThisViewer!2026"),
    ]
    for name, email, role, password in demo:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
        elif app.config.get("IS_PRODUCTION") and not user.check_password(password):
            # Rotate any legacy default demo password to the configured Render
            # secret so a prior unsafe seed cannot remain usable after upgrade.
            user.set_password(password)
            from audit import record_event
            record_event("demo_password_rotated", target_user_id=user.id,
                         details={"account": email, "reason": "configured production secret"})
    db.session.commit()

    # Upgrade existing public accounts created by the previous viewer-only sign-up
    # flow. Keep the dedicated demo viewer read-only for security demonstrations.
    # Role ownership only permits creating/managing one's own documents; it never
    # grants access to somebody else's documents.
    from audit import record_event
    legacy_viewers = User.query.filter(User.role == "viewer", User.email != "viewer@trustvault.local").all()
    for user in legacy_viewers:
        user.role = "owner"
        record_event("account_role_migrated", target_user_id=user.id,
                     details={"from_role": "viewer", "to_role": "owner", "reason": "self-service document ownership policy"})
    if legacy_viewers:
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
