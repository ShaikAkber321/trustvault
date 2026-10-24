import os
from urllib.parse import urlparse


def database_url():
    url = os.getenv("DATABASE_URL", "sqlite:///trustvault.db")
    # Render and some other hosts provide postgres://; SQLAlchemy expects postgresql://.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Config:
    IS_PRODUCTION = (
        os.getenv("RENDER", "").lower() == "true"
        or os.getenv("APP_ENV", "").lower() == "production"
        or os.getenv("COOKIE_SECURE", "").lower() == "true"
        or os.getenv("DATABASE_URL", "").startswith(("postgres://", "postgresql://", "postgresql+psycopg://"))
    )
    SECRET_KEY = os.getenv("SECRET_KEY") or ("" if IS_PRODUCTION else "dev-only-change-me-before-deploying")
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(5 * 1024 * 1024)))
    # Change the cookie name to invalidate sessions created by the earlier build,
    # which could otherwise make the upgraded app appear to skip the login screen.
    SESSION_COOKIE_NAME = "trustvault_session_v2"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true" if IS_PRODUCTION else "false").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = 3600
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME_SECONDS", "28800"))
    SESSION_REFRESH_EACH_REQUEST = False
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
