import os
from datetime import timedelta
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()
oauth = OAuth()


def _als_bool(wert, default=False):
    """Umgebungsvariable als Wahrheitswert lesen ("1", "true", "ja", ...)."""
    if wert is None or wert == "":
        return default
    return str(wert).strip().lower() in ("1", "true", "yes", "ja", "on")


def _normalize_db_uri(uri):
    """Treiber in der Datenbank-URL festnageln.

    SQLAlchemy 2.1 hat den Standardtreiber fuer "postgresql://" von psycopg2
    auf psycopg (v3) umgestellt. Da im Image psycopg2-binary liegt, wuerde die
    App beim naechsten Image-Build nicht mehr starten. Deshalb schreiben wir
    den Treiber explizit in die URL – unabhaengig von der SQLAlchemy-Version.
    Ausserdem wird die alte Heroku-Form "postgres://" mituebersetzt.
    """
    if not uri:
        return uri
    for prefix in ("postgresql://", "postgres://"):
        if uri.startswith(prefix):
            return "postgresql+psycopg2://" + uri[len(prefix):]
    return uri


def create_app(config_overrides=None):
    """Create the Flask app.

    config_overrides: optional dict, applied after the environment config.
    Used by the test suite (e.g. a SQLite URI) – never set in production.
    """
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_db_uri(os.environ.get(
        "DATABASE_URL", "postgresql://cupplan:cupplan_secret@localhost:5432/cupplan"
    ))
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 3,       # 1 worker needs very few persistent connections
        "max_overflow": 5,    # burst up to 8 total – well within postgres max_connections=20
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "admin123")

    # Dev-/Test-Modus: lockert nur die HTTPS-Erwartung, nichts anderes
    umgebung = os.environ.get("CUPPLAN_ENV", "").lower()
    app.config["CUPPLAN_ENV"] = umgebung
    app.config["CUPPLAN_DEV_MODE"] = umgebung in ("dev", "test", "development")

    # Im Dev-Modus Vorlagen bei jeder Anfrage neu einlesen. Ohne das haelt
    # Jinja die kompilierte Vorlage im Speicher, und eine Aenderung an einer
    # .html-Datei wird erst nach einem Neustart sichtbar – gunicorn --reload
    # achtet nur auf .py-Dateien.
    if app.config["CUPPLAN_DEV_MODE"]:
        app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Sitzungs-Cookie absichern.
    # SameSite=Lax ist hier die wirksamste Einzelmassnahme: Browser senden das
    # Cookie dann nicht bei POST-Anfragen von fremden Seiten mit. Damit sind
    # die Admin-Formulare gegen Cross-Site-Request-Forgery geschuetzt, obwohl
    # die App (noch) keine CSRF-Token verwendet – siehe ARCHITEKTUR.md.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = _als_bool(
        os.environ.get("COOKIE_SECURE"), default=not app.config["CUPPLAN_DEV_MODE"]
    )
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_SECURE"] = app.config["SESSION_COOKIE_SECURE"]

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

    from app.security import pruefe_konfiguration
    app.config["SICHERHEITSWARNUNGEN"] = pruefe_konfiguration(app)

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

    @app.context_processor
    def inject_theme():
        """Theme, Schema und Vereinsfarbe fuer jede Vorlage.

        Eine Stelle statt zehn: Vorher setzte jede Vorlage data-theme
        selbst, der Adminbereich sogar fest auf "dark". Jetzt gilt die
        Turniereinstellung ueberall – Web, Handy, TV und Adminvorschau.
        """
        from app.farben import als_css, taugt_als_akzent
        from app.models import get_all_settings
        from app.themes import aufloesen

        tournament = getattr(g, "tournament", None)
        einstellungen = (get_all_settings(tournament.id) if tournament
                         else dict(SETTINGS_DEFAULTS))
        theme, schema = aufloesen(einstellungen.get("theme"))

        # Vereinsfarbe nur uebernehmen, wenn sie sich ueberhaupt abhebt.
        # Eine unsichtbare Farbe ist schlimmer als der Theme-Akzent.
        farbe = (einstellungen.get("color_primary") or "").strip()
        vereinsfarbe = ""
        if farbe and taugt_als_akzent(farbe,
                                      "#ffffff" if schema == "hell" else "#111827"):
            vereinsfarbe = als_css(farbe, schema)

        return {
            "cp_theme": theme,
            "cp_schema": schema,
            "cp_vereinsfarbe": vereinsfarbe,
            # Hat jemand bewusst ein Theme gewaehlt? Die Beamer-Ansicht
            # nimmt sonst "Anzeigetafel", weil sie aus zehn Metern
            # lesbar sein muss.
            "cp_theme_gesetzt": bool((einstellungen.get("theme") or "").strip()),
            "cp_themefarbe": None,
        }

    @app.context_processor
    def inject_navigation():
        """Navigationspunkte und Turnierliste fuer den Adminbereich.

        An einer Stelle statt in jeder Vorlage. Nur fuer angemeldete
        Benutzer und nur fuer Admin-Routen – die oeffentlichen Seiten
        brauchen das nicht und sollen keine zusaetzlichen Abfragen
        ausloesen.
        """
        from flask import request
        from flask_login import current_user
        from app.navigation import navigation, palette_eintraege, unten_punkte

        leer = {"cp_navigation": [], "cp_turniere": [], "cp_palette": [],
                "cp_unten": []}
        if not request.blueprint or not request.blueprint.startswith(
                ("admin", "anmeldung_admin", "ereignisse_admin",
                 "siegerehrung_admin", "schiedsrichter")):
            return leer
        if not current_user.is_authenticated:
            return leer

        from app.models import Tournament
        tournament = getattr(g, "tournament", None)

        if current_user.role == "superadmin":
            turniere = Tournament.query.order_by(
                Tournament.display_order, Tournament.name).all()
        else:
            ids = [a.tournament_id for a in current_user.tournament_access.all()]
            turniere = Tournament.query.filter(Tournament.id.in_(ids)).order_by(
                Tournament.display_order, Tournament.name).all() if ids else []

        # Fuer die Befehlspalette: Mannschaften, Spiele und Themes
        # des aktuellen Turniers. Zwei schlanke Abfragen – nur Namen
        # und Kennungen, keine Beziehungen.
        teams, spiele = (), ()
        if tournament is not None:
            from app.models import Team, Match
            teams = Team.query.filter_by(tournament_id=tournament.id).order_by(
                Team.name).all()
            spiele = Match.query.filter_by(tournament_id=tournament.id).order_by(
                Match.scheduled_time, Match.match_order).all()

        from app.themes import katalog
        themes = [(t["schluessel"], t["name"]) for t in katalog()]

        return {
            "cp_navigation": navigation(tournament),
            "cp_turniere": turniere,
            "cp_palette": palette_eintraege(tournament, teams, spiele, themes),
            "cp_unten": unten_punkte(tournament),
        }

    @app.context_processor
    def inject_sicherheitswarnungen():
        """Warnungen nur fuer angemeldete Superadmins einblenden."""
        from flask_login import current_user
        if current_user.is_authenticated and current_user.role == "superadmin":
            return {"sicherheitswarnungen": app.config["SICHERHEITSWARNUNGEN"]}
        return {"sicherheitswarnungen": []}

    from app.routes import main_bp
    from app.blueprints import admin_bp
    # Nur importieren, damit die Routen sich am admin_bp registrieren.
    # NICHT als "import app.admin" – das wuerde den Namen "app" in dieser
    # Funktion ueberschreiben (dort steht die Flask-App).
    from app import admin as _admin_routes      # noqa: F401
    from app import backup as _backup_routes    # noqa: F401
    from app.anmeldung import anmeldung_admin_bp, anmeldung_bp
    from app.ereignisse import ereignisse_admin_bp, ereignisse_bp
    from app.siegerehrung import siegerehrung_admin_bp, siegerehrung_bp
    from app.schiedsrichter_routes import schiedsrichter_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(anmeldung_bp)
    app.register_blueprint(anmeldung_admin_bp, url_prefix="/admin")
    app.register_blueprint(ereignisse_bp)
    app.register_blueprint(ereignisse_admin_bp, url_prefix="/admin")
    app.register_blueprint(siegerehrung_bp)
    app.register_blueprint(siegerehrung_admin_bp, url_prefix="/admin")
    app.register_blueprint(schiedsrichter_bp, url_prefix="/admin")

    # Design-Labor: nur in der Entwicklung, nur mit gesetzter Variable.
    # In einer normalen Installation existiert die Route nicht.
    if os.environ.get("CUPPLAN_DESIGN_LAB") == "1":
        from app.design_lab import design_lab_bp
        app.register_blueprint(design_lab_bp)

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
        # Nachtschicht 2026-10-24: Schiedsrichter je Spiel. Bewusst ohne
        # Fremdschluessel-Constraint – die Zuordnung wird von der ORM
        # gepflegt, und ein ALTER mit Constraint auf eine Tabelle mit
        # Altdaten ist riskanter als der Nutzen.
        "ALTER TABLE match ADD COLUMN IF NOT EXISTS referee_id INTEGER",
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
