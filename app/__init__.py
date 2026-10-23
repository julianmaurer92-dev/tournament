import os
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
oauth = OAuth()


def create_app(config_overrides=None):
    """Create the Flask app.

    config_overrides: optional dict, applied after the environment config.
    Used by the test suite (e.g. a SQLite URI) – never set in production.
    """
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "postgresql://cupplan:cupplan_secret@localhost:5432/cupplan"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 3,       # 1 worker needs very few persistent connections
        "max_overflow": 5,    # burst up to 8 total – well within postgres max_connections=20
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "admin123")

    if config_overrides:
        app.config.update(config_overrides)

    # SQLite (Tests) kennt die Pool-Optionen von psycopg2 nicht
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}

    # Google OAuth
    app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    app.config["ADMIN_EMAILS"] = [
        e.strip().lower()
        for e in os.environ.get("ADMIN_EMAILS", "").split(",")
        if e.strip()
    ]

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "admin.login"
    socketio.init_app(app, cors_allowed_origins="*", async_mode="gevent")

    oauth.init_app(app)
    if app.config["GOOGLE_CLIENT_ID"]:
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    from app.models import Admin, SETTINGS_DEFAULTS

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Admin, int(user_id))

    # Inject settings into every template context
    @app.context_processor
    def inject_settings():
        from app.models import get_all_settings
        tournament = getattr(g, "tournament", None)
        if tournament:
            return {
                "site_settings": get_all_settings(tournament.id),
                "current_tournament": tournament,
            }
        return {
            "site_settings": dict(SETTINGS_DEFAULTS),
            "current_tournament": None,
        }

    from app.routes import main_bp
    from app.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    with app.app_context():
        db.create_all()
        _migrate_db()
        _ensure_admin(app)

    return app


def _migrate_db():
    """Add missing columns to existing tables (safe to run on every start).

    Nur additive Aenderungen mit Defaults – bestehende Daten bleiben erhalten.
    Die Anweisungen sind Postgres-spezifisch; unter SQLite (Tests) legt
    db.create_all() bereits das vollstaendige Schema an, deshalb uebersprungen.
    """
    if db.engine.dialect.name != "postgresql":
        return

    migrations = [
        "ALTER TABLE match ADD COLUMN IF NOT EXISTS field INTEGER DEFAULT 1",
        "ALTER TABLE match ADD COLUMN IF NOT EXISTS is_penalty BOOLEAN DEFAULT FALSE",
        "ALTER TABLE tournament ADD COLUMN IF NOT EXISTS event_time VARCHAR(5)",
        # Widen tournament_settings.value from VARCHAR(500) to TEXT
        "ALTER TABLE tournament_settings ALTER COLUMN value TYPE TEXT",
        # team_payment table is created by db.create_all(); no ALTER needed
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            conn.execute(db.text(sql))
        conn.commit()


def _ensure_admin(app):
    from app.models import Admin
    if not Admin.query.first():
        admin = Admin(username="admin", role="superadmin")
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
    else:
        # Migrate existing admin to superadmin if role not set
        existing = Admin.query.filter_by(role="editor").first()
        if existing and Admin.query.count() == 1:
            existing.role = "superadmin"
            db.session.commit()
