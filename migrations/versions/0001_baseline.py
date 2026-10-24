"""Baseline TrustVault schema.

Revision ID: 0001_baseline
Revises: None

The challenge starter already used SQLAlchemy create_all. This baseline creates
any missing current tables and leaves existing tables intact. All future schema
changes must be represented by explicit Alembic revisions.
"""
from alembic import op
from extensions import db
import models  # noqa: F401 - registers tables on db.metadata

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    db.metadata.create_all(bind=op.get_bind(), checkfirst=True)

def downgrade():
    # The baseline contains user documents and audit history; destructive downgrade
    # is intentionally unsupported. Create a backup and perform a reviewed migration.
    raise RuntimeError("TrustVault baseline downgrade is intentionally disabled to protect stored documents and audit history.")
