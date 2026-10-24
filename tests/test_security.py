import io
from models import AuditEvent, Document, DocumentGrant, User
from extensions import db
from audit import verify_audit_chain
from models import AuditHead


def upload(client, title="Private agreement"):
    return client.post("/documents/upload", data={
        "title": title, "category": "Legal", "description": "confidential",
        "file": (io.BytesIO(b"Confidential contract text"), "agreement.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)


def test_unauthenticated_cannot_view_documents(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.location


def test_user_cannot_read_or_download_another_users_document(app, client, login_as):
    login_as(client)
    upload(client)
    with app.app_context():
        doc_id = Document.query.one().id
    client.post("/logout", follow_redirects=True)
    login_as(client, "viewer2@trustvault.local", "Viewer2Pass!123")
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.get(f"/documents/{doc_id}/download").status_code == 404
    with app.app_context():
        actions = [e.action for e in AuditEvent.query.all()]
        assert "denied_read" in actions
        assert "denied_download" in actions


def test_grant_then_revoke_takes_effect_immediately(app, client, login_as):
    login_as(client)
    upload(client)
    with app.app_context():
        doc = Document.query.one()
        doc_id = doc.id
        grant_url = f"/documents/{doc_id}/grants"
    client.post(grant_url, data={"email": "viewer@trustvault.local", "permission": "read"})
    client.post("/logout", follow_redirects=True)
    login_as(client, "viewer@trustvault.local", "ViewerPass!123")
    assert client.get(f"/documents/{doc_id}").status_code == 200
    assert client.get(f"/documents/{doc_id}/download").status_code == 200
    client.post("/logout", follow_redirects=True)
    login_as(client)
    with app.app_context():
        grant = DocumentGrant.query.filter_by(document_id=doc_id).one()
        grant_id = grant.id
    client.post(f"/documents/{doc_id}/grants/{grant_id}/revoke")
    client.post("/logout", follow_redirects=True)
    login_as(client, "viewer@trustvault.local", "ViewerPass!123")
    assert client.get(f"/documents/{doc_id}").status_code == 404
    assert client.get(f"/documents/{doc_id}/download").status_code == 404


def test_read_grant_cannot_edit_or_delete(app, client, login_as):
    login_as(client)
    upload(client)
    with app.app_context():
        doc_id = Document.query.one().id
    client.post(f"/documents/{doc_id}/grants", data={"email": "viewer@trustvault.local", "permission": "read"})
    client.post("/logout", follow_redirects=True)
    login_as(client, "viewer@trustvault.local", "ViewerPass!123")
    assert client.get(f"/documents/{doc_id}/edit").status_code == 404
    assert client.post(f"/documents/{doc_id}/delete").status_code == 404
    assert client.post(f"/documents/{doc_id}/grants", data={"email": "viewer2@trustvault.local", "permission": "edit"}).status_code == 404


def test_admin_role_does_not_implicitly_grant_document_content_access(app, client, login_as):
    login_as(client)
    upload(client)
    with app.app_context():
        doc_id = Document.query.one().id
    client.post("/logout", follow_redirects=True)
    login_as(client, "admin@trustvault.local", "AdminPass!123")
    assert client.get("/admin/activity").status_code == 200
    assert client.get(f"/documents/{doc_id}").status_code == 404


def test_invalid_file_signature_is_rejected(client, login_as):
    login_as(client)
    response = client.post("/documents/upload", data={
        "title": "Fake PDF", "category": "Legal", "description": "",
        "file": (io.BytesIO(b"not really a pdf"), "fake.pdf"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert b"do not look like a PDF" in response.data


def test_viewer_cannot_upload(client, login_as):
    login_as(client, "viewer@trustvault.local", "ViewerPass!123")
    assert client.get("/documents/upload").status_code == 403


def test_audit_chain_detects_tampering(app, client, login_as):
    login_as(client)
    upload(client)
    with app.app_context():
        events = AuditEvent.query.order_by(AuditEvent.id.asc()).all()
        assert events
        assert verify_audit_chain(events)[0] is True
        events[0].details = '{"changed":true}'
        db.session.commit()
        assert verify_audit_chain(AuditEvent.query.order_by(AuditEvent.id.asc()).all())[0] is False


def test_only_admin_can_provision_owner_accounts(client, app, login_as):
    login_as(client, "viewer@trustvault.local", "ViewerPass!123")
    denied = client.post("/admin/users/new", data={
        "name": "New Owner", "email": "newowner@example.com", "role": "owner",
        "password": "A-strong-passphrase-123",
    })
    assert denied.status_code == 403
    client.post("/logout")
    login_as(client, "admin@trustvault.local", "AdminPass!123")
    allowed = client.post("/admin/users/new", data={
        "name": "New Owner", "email": "newowner@example.com", "role": "owner",
        "password": "A-strong-passphrase-123",
    }, follow_redirects=True)
    assert allowed.status_code == 200
    with app.app_context():
        from models import User
        owner = User.query.filter_by(email="newowner@example.com").one()
        assert owner.role == "owner"
        assert AuditEvent.query.filter_by(action="admin_user_created", target_user_id=owner.id).count() == 1


def test_admin_account_form_never_creates_admin_even_if_role_is_forged(client, app, login_as):
    login_as(client, "admin@trustvault.local", "AdminPass!123")
    response = client.post("/admin/users/new", data={
        "name": "Attempted Admin", "email": "newadmin@example.com", "role": "admin",
        "password": "A-strong-passphrase-123",
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        from models import User
        created = User.query.filter_by(email="newadmin@example.com").one()
        assert created.role == "owner"


def test_admin_can_upload_only_a_document_they_own(client, app, login_as):
    login_as(client, "admin@trustvault.local", "AdminPass!123")
    response = client.post("/documents/upload", data={
        "title": "Admin-owned policy", "category": "Security", "description": "Owned by admin",
        "file": (io.BytesIO(b"internal policy"), "policy.txt"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        doc = Document.query.filter_by(title="Admin-owned policy").one()
        assert doc.owner.email == "admin@trustvault.local"
    client.post("/logout")
    login_as(client, "owner@trustvault.local", "OwnerPass!123")
    assert client.get(f"/documents/{doc.id}").status_code == 404


def test_manage_access_page_is_owner_only(client, app, login_as):
    login_as(client)
    upload(client, "Access controlled file")
    with app.app_context():
        doc_id = Document.query.filter_by(title="Access controlled file").one().id
    assert client.get(f"/documents/{doc_id}/share").status_code == 200
    client.post("/logout")
    login_as(client, "viewer@trustvault.local", "ViewerPass!123")
    assert client.get(f"/documents/{doc_id}/share").status_code == 404


def test_private_pages_redirect_to_login_for_anonymous_users(client):
    # Workspace, upload, document detail/download and sharing pages must never
    # reveal the authenticated interface to a visitor without a session.
    for path in ["/", "/documents/upload", "/documents/1", "/documents/1/download", "/documents/1/share", "/admin/activity"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302, (path, response.status_code)
        assert "/login" in response.headers.get("Location", ""), path


def test_public_registration_never_creates_or_logs_in_an_admin(client, app):
    response = client.post("/register", data={
        "name": "Attempted Admin", "email": "attempted.admin@example.com",
        "password": "A-strong-passphrase-123", "confirm_password": "A-strong-passphrase-123",
        "role": "admin",
    }, follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers.get("Location", "")
    # Flash messages may create a session cookie, but it must not be an
    # authenticated session: protected workspace access still redirects to login.
    workspace = client.get("/", follow_redirects=False)
    assert workspace.status_code == 302
    assert "/login" in workspace.headers.get("Location", "")
    with app.app_context():
        user = User.query.filter_by(email="attempted.admin@example.com").one()
        assert user.role == "owner"


def test_audit_chain_detects_head_row_tampering(app, client, login_as):
    login_as(client)
    upload(client, "Audit head test")
    with app.app_context():
        events = AuditEvent.query.order_by(AuditEvent.id.asc()).all()
        head = db.session.get(AuditHead, 1)
        assert verify_audit_chain(events)[0] is True
        original = head.last_hash
        head.last_hash = "f" * 64 if original != "f" * 64 else "e" * 64
        db.session.commit()
        valid, reason = verify_audit_chain(AuditEvent.query.order_by(AuditEvent.id.asc()).all())
        assert valid is False
        assert "head" in reason.lower()


def test_login_is_rate_limited(client):
    # Ten invalid POST attempts are allowed per minute from the same client;
    # the next attempt is rejected before password verification.
    for _ in range(10):
        response = client.post("/login", data={"email": "unknown@example.com", "password": "wrong"})
        assert response.status_code in {200, 302}
    response = client.post("/login", data={"email": "unknown@example.com", "password": "wrong"})
    assert response.status_code == 429


def test_security_headers_are_set(client):
    response = client.get("/login")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "frame-ancestors 'none'" in response.headers.get("Content-Security-Policy", "")
    assert response.headers.get("Cache-Control") == "no-store"


def test_csrf_rejects_login_post_without_token(tmp_path):
    from app import create_app
    csrf_app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'csrf.db'}",
        "SECRET_KEY": "csrf-test-secret-key-that-is-long-enough",
        "SESSION_COOKIE_SECURE": False,
        "RATELIMIT_ENABLED": False,
    })
    response = csrf_app.test_client().post("/login", data={"email": "nobody@example.com", "password": "not-a-password"})
    assert response.status_code == 400


def test_edit_grant_allows_metadata_edit_but_not_delete_or_share(client, app, login_as):
    login_as(client)
    upload(client, "Editable shared document")
    with app.app_context():
        doc_id = Document.query.filter_by(title="Editable shared document").one().id
    client.post(f"/documents/{doc_id}/grants", data={
        "email": "viewer@trustvault.local", "permission": "edit"
    })
    client.post("/logout")
    login_as(client, "viewer@trustvault.local", "ViewerPass!123")
    assert client.get(f"/documents/{doc_id}/edit").status_code == 200
    changed = client.post(f"/documents/{doc_id}/edit", data={
        "title": "Edited by grantee", "category": "Engineering", "description": "Permitted metadata edit"
    }, follow_redirects=True)
    assert changed.status_code == 200
    assert b"Edited by grantee" in changed.data
    assert client.get(f"/documents/{doc_id}/share").status_code == 404
    assert client.post(f"/documents/{doc_id}/delete").status_code == 404
    assert client.post(f"/documents/{doc_id}/grants", data={
        "email": "viewer2@trustvault.local", "permission": "edit"
    }).status_code == 404


def test_login_next_parameter_cannot_redirect_off_site(client):
    for target in ["https://evil.example/", "//evil.example/", "/\\evil.example/path"]:
        response = client.post(f"/login?next={target.replace('/', '%2F')}", data={
            "email": "owner@trustvault.local", "password": "OwnerPass!123"
        }, follow_redirects=False)
        assert response.status_code == 302
        location = response.headers.get("Location", "")
        assert not location.startswith("https://evil.example")
        assert not location.startswith("//evil.example")
