import re
from urllib.parse import urlsplit
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from extensions import db
from models import User
from audit import record_event
from extensions import limiter

bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _valid_password(password):
    # A longer minimum makes newly created accounts harder to guess.
    return len(password) >= 12 and len(password) <= 128


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("documents.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.active and user.check_password(password):
            # Clear pre-authentication session values before establishing the
            # authenticated session to reduce session-fixation risk.
            session.clear()
            login_user(user, remember=False, fresh=True)
            # Bound the authenticated session to the configured lifetime.
            session.permanent = True
            record_event("login_success", details={"email": email})
            db.session.commit()
            next_url = request.args.get("next", "")
            # Prevent open redirects, including scheme-relative URLs and browser-
            # normalized backslash variants. Accept only a local absolute path.
            try:
                parsed_next = urlsplit(next_url)
            except ValueError:
                parsed_next = None
            if (parsed_next is not None and next_url.startswith("/")
                    and not next_url.startswith("//") and "\\" not in next_url
                    and not parsed_next.scheme and not parsed_next.netloc):
                return redirect(next_url)
            return redirect(url_for("documents.index"))
        record_event("login_failed", details={"email": email[:254]})
        db.session.commit()
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def register():
    """Public sign-up creates a normal document-owning account, never an admin."""
    if current_user.is_authenticated:
        return redirect(url_for("documents.index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or len(name) > 120:
            flash("Enter a name between 1 and 120 characters.", "danger")
        elif not EMAIL_RE.fullmatch(email) or len(email) > 254:
            flash("Enter a valid email address.", "danger")
        elif not _valid_password(password):
            flash("Use a password between 12 and 128 characters.", "danger")
        elif password != confirm:
            flash("The passwords do not match.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists. Try signing in.", "warning")
        else:
            user = User(name=name, email=email, role="owner", active=True)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.flush()
                record_event("user_registered", target_user_id=user.id,
                             details={"new_role": "owner"}, actor=user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("An account with that email already exists. Try signing in.", "warning")
                return render_template("register.html")
            # Do not silently sign the new account in. Registration ends on the
            # public sign-in page so the user explicitly authenticates before the
            # private workspace is displayed.
            flash("Your account was created successfully. Sign in to open your private workspace.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html")


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        record_event("logout")
        db.session.commit()
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
