import re
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import AuditEvent, User
from audit import verify_audit_chain, record_event

bp = Blueprint("admin", __name__, url_prefix="/admin")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def admin_required():
    if current_user.role != "admin":
        record_event("denied_admin_view", details={"route": request.path})
        db.session.commit()
        abort(403)


@bp.get("/activity")
@login_required
def activity():
    admin_required()
    events = AuditEvent.query.order_by(AuditEvent.id.desc()).limit(300).all()
    valid, message = verify_audit_chain(AuditEvent.query.order_by(AuditEvent.id.asc()).all())
    users = User.query.order_by(User.name.asc()).all()
    return render_template("admin_activity.html", events=events, chain_valid=valid,
                           chain_message=message, users=users)


@bp.route("/users/new", methods=["GET", "POST"])
@login_required
def create_user():
    """Admins may provision normal owner accounts, but cannot create more admins here."""
    admin_required()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        # Account provisioning follows the normal-user model. Public/admin account
        # creation never exposes the privileged administrator role.
        role = "owner"
        password = request.form.get("password", "")
        if not name or len(name) > 120:
            flash("Enter a name between 1 and 120 characters.", "danger")
        elif not EMAIL_RE.fullmatch(email) or len(email) > 254:
            flash("Enter a valid email address.", "danger")
        elif len(password) < 12 or len(password) > 128:
            flash("Use a password between 12 and 128 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
        else:
            user = User(name=name, email=email, role=role, active=True)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.flush()
                record_event("admin_user_created", target_user_id=user.id,
                             details={"target_email": email, "new_role": role})
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("An account with that email already exists.", "warning")
            else:
                flash(f"{role.title()} account created for {email}.", "success")
                return redirect(url_for("admin.activity"))
    return render_template("admin_create_user.html")
