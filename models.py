from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, default="owner", index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.active


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General", index=True)
    description = db.Column(db.String(1000), nullable=False, default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False, index=True)
    content = db.Column(db.LargeBinary, nullable=False)
    content_type = db.Column(db.String(120), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    owner = db.relationship("User", foreign_keys=[owner_id])
    grants = db.relationship("DocumentGrant", cascade="all, delete-orphan", backref="document", lazy=True)


class DocumentGrant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("document.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    permission = db.Column(db.String(10), nullable=False)  # read or edit
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    user = db.relationship("User", foreign_keys=[user_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    __table_args__ = (db.UniqueConstraint("document_id", "user_id", name="uq_document_grant_user"),)


class AuditHead(db.Model):
    # A single locked row serializes audit-chain appends on PostgreSQL.
    id = db.Column(db.Integer, primary_key=True)
    last_hash = db.Column(db.String(64), nullable=False, default="0" * 64)


class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_uuid = db.Column(db.String(36), nullable=False, unique=True, index=True)
    actor_id = db.Column(db.Integer, nullable=True, index=True)  # no FK: preserve history if user is removed
    actor_email = db.Column(db.String(254), nullable=False, default="anonymous")
    action = db.Column(db.String(80), nullable=False, index=True)
    document_id = db.Column(db.Integer, nullable=True, index=True)  # no FK: preserve history after deletion
    target_user_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=False, default="{}")
    ip_address = db.Column(db.String(64), nullable=False, default="")
    user_agent = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    previous_hash = db.Column(db.String(64), nullable=False)
    event_hash = db.Column(db.String(64), nullable=False, unique=True)
