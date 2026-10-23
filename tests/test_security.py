"""Tests fuer Sicherheits-Konfiguration und Anmeldebremse."""
import pytest

from app import _als_bool, create_app
from app.security import Anmeldebremse, anmeldebremse, pruefe_konfiguration
from tests.conftest import ADMIN_PW


@pytest.fixture(autouse=True)
def bremse_leeren():
    """Jeder Test startet mit einer leeren Anmeldebremse."""
    anmeldebremse.zuruecksetzen()
    yield
    anmeldebremse.zuruecksetzen()


# ──────────────────────────────────────
# Konfigurationspruefung
# ──────────────────────────────────────

def test_warnt_bei_vorgabe_secret_key(app):
    app.config["SECRET_KEY"] = "change-me-in-production-please"
    warnungen = pruefe_konfiguration(app)
    assert any("SECRET_KEY" in w for w in warnungen)


def test_warnt_bei_vorgabe_admin_passwort(app):
    app.config["ADMIN_PASSWORD"] = "admin123"
    warnungen = pruefe_konfiguration(app)
    assert any("ADMIN_PASSWORD" in w for w in warnungen)


def test_keine_warnung_bei_guter_konfiguration(app):
    app.config["SECRET_KEY"] = "4f1c9a7e2b8d6350af1e9c4b7d2a5e80"
    app.config["ADMIN_PASSWORD"] = "ein-langes-eigenes-passwort"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["CUPPLAN_DEV_MODE"] = False
    assert pruefe_konfiguration(app) == []


def test_warnt_bei_unsicherem_cookie_ausserhalb_dev(app):
    app.config["SECRET_KEY"] = "4f1c9a7e2b8d6350af1e9c4b7d2a5e80"
    app.config["ADMIN_PASSWORD"] = "ein-langes-eigenes-passwort"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["CUPPLAN_DEV_MODE"] = False
    assert any("SESSION_COOKIE_SECURE" in w for w in pruefe_konfiguration(app))


def test_cookie_flags_gesetzt(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert app.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"


def test_cookie_secure_folgt_umgebung(monkeypatch):
    """In Produktion standardmaessig an, im Dev-Modus aus."""
    monkeypatch.setenv("CUPPLAN_ENV", "")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    prod = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert prod.config["SESSION_COOKIE_SECURE"] is True

    monkeypatch.setenv("CUPPLAN_ENV", "dev")
    dev = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert dev.config["SESSION_COOKIE_SECURE"] is False


def test_cookie_secure_per_umgebungsvariable_erzwingbar(monkeypatch):
    monkeypatch.setenv("CUPPLAN_ENV", "dev")
    monkeypatch.setenv("COOKIE_SECURE", "1")
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://"})
    assert app.config["SESSION_COOKIE_SECURE"] is True


@pytest.mark.parametrize("wert,erwartet", [
    ("1", True), ("true", True), ("JA", True), ("on", True), ("yes", True),
    ("0", False), ("false", False), ("nein", False), ("irgendwas", False),
])
def test_als_bool(wert, erwartet):
    assert _als_bool(wert) is erwartet


def test_als_bool_default():
    assert _als_bool(None, default=True) is True
    assert _als_bool("", default=True) is True
    assert _als_bool(None) is False


def test_warnbanner_nur_fuer_superadmin(app, admin_client, viewer_client):
    app.config["SICHERHEITSWARNUNGEN"] = ["Testwarnung XYZ"]

    resp = admin_client.get("/admin/")
    assert b"Testwarnung XYZ" in resp.data

    resp = viewer_client.get("/admin/")
    assert b"Testwarnung XYZ" not in resp.data


# ──────────────────────────────────────
# Anmeldebremse
# ──────────────────────────────────────

def test_bremse_sperrt_nach_zu_vielen_fehlversuchen():
    bremse = Anmeldebremse(max_versuche=3, sperre_sekunden=60)
    assert bremse.fehlversuch("a") == 0
    assert bremse.fehlversuch("a") == 0
    assert bremse.fehlversuch("a") == 60
    assert bremse.restsperre("a") > 0


def test_bremse_trennt_nach_schluessel():
    bremse = Anmeldebremse(max_versuche=2, sperre_sekunden=60)
    bremse.fehlversuch("a")
    bremse.fehlversuch("a")
    assert bremse.restsperre("a") > 0
    assert bremse.restsperre("b") == 0


def test_bremse_vergisst_nach_erfolg():
    bremse = Anmeldebremse(max_versuche=3, sperre_sekunden=60)
    bremse.fehlversuch("a")
    bremse.fehlversuch("a")
    bremse.erfolg("a")
    assert bremse.fehlversuch("a") == 0, "Zaehler muss zurueckgesetzt sein"


def test_bremse_loest_sich_nach_ablauf(monkeypatch):
    bremse = Anmeldebremse(max_versuche=2, sperre_sekunden=60)
    jetzt = [1000.0]
    monkeypatch.setattr(bremse, "_jetzt", lambda: jetzt[0])

    bremse.fehlversuch("a")
    bremse.fehlversuch("a")
    assert bremse.restsperre("a") > 0

    jetzt[0] += 61
    assert bremse.restsperre("a") == 0


def test_bremse_vergisst_alte_versuche_im_fenster(monkeypatch):
    """Verteilte Fehlversuche ueber Stunden duerfen nicht aufaddieren."""
    bremse = Anmeldebremse(max_versuche=3, sperre_sekunden=60,
                           fenster_sekunden=100)
    jetzt = [1000.0]
    monkeypatch.setattr(bremse, "_jetzt", lambda: jetzt[0])

    bremse.fehlversuch("a")
    bremse.fehlversuch("a")
    jetzt[0] += 200          # beide Versuche fallen aus dem Fenster
    assert bremse.fehlversuch("a") == 0
    assert bremse.restsperre("a") == 0


def test_login_wird_nach_vielen_fehlversuchen_gesperrt(client):
    for _ in range(8):
        client.post("/admin/login",
                    data={"username": "admin", "password": "falsch"})

    resp = client.post("/admin/login",
                       data={"username": "admin", "password": "falsch"})
    assert resp.status_code == 429
    assert "Zu viele Fehlversuche".encode() in resp.data


def test_gesperrter_benutzer_kommt_auch_mit_richtigem_passwort_nicht_rein(client):
    for _ in range(8):
        client.post("/admin/login",
                    data={"username": "admin", "password": "falsch"})
    resp = client.post("/admin/login",
                       data={"username": "admin", "password": ADMIN_PW})
    assert resp.status_code == 429


def test_erfolgreiche_anmeldung_loest_zaehler(client):
    for _ in range(4):
        client.post("/admin/login",
                    data={"username": "admin", "password": "falsch"})
    resp = client.post("/admin/login",
                       data={"username": "admin", "password": ADMIN_PW})
    assert resp.status_code == 302

    # Zaehler ist zurueckgesetzt: weitere 4 Fehlversuche sperren noch nicht
    client.get("/admin/logout")
    for _ in range(4):
        resp = client.post("/admin/login",
                           data={"username": "admin", "password": "falsch"})
    assert resp.status_code == 200
