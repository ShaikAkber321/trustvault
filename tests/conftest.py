import pytest
from app import create_app
from extensions import db
from models import User


@pytest.fixture()
def app(tmp_path):
    database = tmp_path / "test.db"
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
        "SECRET_KEY": "test-secret-key",
        "SESSION_COOKIE_SECURE": False,
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
        for name, email, role, password in [
            ("Admin", "admin@trustvault.local", "admin", "AdminPass!123"),
            ("Owner One", "owner@trustvault.local", "owner", "OwnerPass!123"),
            ("Viewer One", "viewer@trustvault.local", "viewer", "ViewerPass!123"),
            ("Viewer Two", "viewer2@trustvault.local", "viewer", "Viewer2Pass!123"),
        ]:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email="owner@trustvault.local", password="OwnerPass!123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


@pytest.fixture()
def login_as():
    return login
