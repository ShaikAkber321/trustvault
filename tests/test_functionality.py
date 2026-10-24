import io
from models import Document, AuditEvent, User
from app import seed_demo_users
from extensions import db


def login_owner(client):
    return client.post("/login", data={"email": "owner@trustvault.local", "password": "OwnerPass!123"}, follow_redirects=True)


def test_upload_search_edit_download_and_delete(client, app):
    login_owner(client)
    response = client.post("/documents/upload", data={
        "title": "Policy document", "category": "Compliance", "description": "Annual policy",
        "file": (io.BytesIO(b"policy body"), "policy.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    assert b"Policy document" in response.data
    response = client.get("/?name=Policy&category=Compliance")
    assert b"Policy document" in response.data
    with app.app_context():
        doc_id = Document.query.one().id
    response = client.get(f"/documents/{doc_id}/download")
    assert response.status_code == 200
    assert response.data == b"policy body"
    response = client.post(f"/documents/{doc_id}/edit", data={"title": "Updated policy", "category": "HR", "description": "Revised"}, follow_redirects=True)
    assert b"Updated policy" in response.data
    response = client.post(f"/documents/{doc_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert Document.query.count() == 0
        actions = [event.action for event in AuditEvent.query.all()]
        assert "document_uploaded" in actions
        assert "document_downloaded" in actions
        assert "document_changed" in actions
        assert "document_deleted" in actions


def test_login_failure_is_audited(app, client):
    client.post("/login", data={"email": "owner@trustvault.local", "password": "wrong"}, follow_redirects=True)
    with app.app_context():
        assert AuditEvent.query.filter_by(action="login_failed").count() == 1


def test_public_registration_creates_normal_owner_account(client, app):
    response = client.post("/register", data={
        "name": "New Person", "email": "new.person@example.com",
        "password": "A-strong-passphrase-123", "confirm_password": "A-strong-passphrase-123",
        "role": "admin",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="new.person@example.com").one()
        assert user.role == "owner"
        assert user.check_password("A-strong-passphrase-123")
        assert AuditEvent.query.filter_by(action="user_registered", target_user_id=user.id).count() == 1
    # Registration does not silently authenticate: the private workspace remains
    # behind the explicit login form, even though the account has owner privileges.
    protected = client.get("/", follow_redirects=False)
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]
    login_response = client.post("/login", data={
        "email": "new.person@example.com", "password": "A-strong-passphrase-123"
    }, follow_redirects=True)
    assert login_response.status_code == 200
    # Registration's posted role field is ignored; the new account is an owner,
    # never an administrator, and can create its own private document after login.
    upload_response = client.post("/documents/upload", data={
        "title": "My first private file", "category": "General", "description": "",
        "file": (io.BytesIO(b"my private content"), "first.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert upload_response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="new.person@example.com").one()
        assert user.role == "owner"
        assert Document.query.filter_by(owner_id=user.id, title="My first private file").count() == 1


def test_registration_rejects_short_password(client, app):
    response = client.post("/register", data={
        "name": "New Person", "email": "short@example.com",
        "password": "short", "confirm_password": "short",
    }, follow_redirects=True)
    assert b"between 12 and 128 characters" in response.data
    with app.app_context():
        assert User.query.filter_by(email="short@example.com").count() == 0


def test_legacy_registered_viewer_is_migrated_to_owner_and_audited(app):
    with app.app_context():
        legacy = User(name="Legacy Member", email="legacy.member@example.com", role="viewer")
        legacy.set_password("A-strong-passphrase-123")
        db.session.add(legacy)
        db.session.commit()
        legacy_id = legacy.id
        seed_demo_users(app)
        migrated = db.session.get(User, legacy_id)
        assert migrated.role == "owner"
        event = AuditEvent.query.filter_by(action="account_role_migrated", target_user_id=legacy_id).one()
        assert '"from_role":"viewer"' in event.details
        assert '"to_role":"owner"' in event.details


def test_shared_with_me_shows_only_documents_shared_by_others(client, app, login_as):
    login_as(client)
    upload_response = client.post("/documents/upload", data={
        "title": "Owner shared policy", "category": "Legal", "description": "Shared by owner",
        "file": (io.BytesIO(b"shared body"), "shared.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert upload_response.status_code == 200
    with app.app_context():
        shared_doc = Document.query.filter_by(title="Owner shared policy").one()
        shared_id = shared_doc.id
        recipient = User(name="Shared Reader", email="shared.reader@example.com", role="owner")
        recipient.set_password("SharedReaderPass!123")
        db.session.add(recipient)
        db.session.commit()
    client.post(f"/documents/{shared_id}/grants", data={
        "email": "shared.reader@example.com", "permission": "read"
    })
    client.post("/logout")
    login_as(client, "shared.reader@example.com", "SharedReaderPass!123")
    own_upload = client.post("/documents/upload", data={
        "title": "Viewer own policy", "category": "General", "description": "Owned by viewer",
        "file": (io.BytesIO(b"own body"), "own.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert own_upload.status_code == 200
    response = client.get("/?scope=shared")
    assert response.status_code == 200
    assert b"Owner shared policy" in response.data
    assert b"Viewer own policy" not in response.data
