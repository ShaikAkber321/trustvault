from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.session_protection = "strong"
login_manager.login_message_category = "warning"
csrf = CSRFProtect()
# In-memory storage is suitable for local/single-instance development. Configure
# RATELIMIT_STORAGE_URI with a shared Redis URI if running multiple instances.
limiter = Limiter(key_func=get_remote_address, default_limits=[], headers_enabled=True)
