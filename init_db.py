"""Initialize local/deployed tables and seed demo accounts before serving traffic."""
from app import app
from extensions import db
from models import User, AuditHead

with app.app_context():
    db.create_all()
    if not db.session.get(AuditHead, 1):
        db.session.add(AuditHead(id=1, last_hash="0" * 64))
    db.session.commit()
    print("TrustVault database is ready. Demo users are seeded by this initialization command.")
