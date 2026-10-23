"""Gemeinsame Test-Fixtures.

Die Tests laufen gegen eine SQLite-Datei im Temp-Verzeichnis – schnell und
voellig getrennt von jeder echten Datenbank. Die Postgres-spezifischen
Migrationen werden dabei uebersprungen (siehe app/__init__.py:_migrate_db).
"""
import os
import sys

import pytest
from flask import g

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import _ensure_admin, create_app, db as _db  # noqa: E402
from app.models import (  # noqa: E402
    Admin, Group, Match, MenuItem, Team, Tournament,
    ensure_default_settings, slugify,
)

ADMIN_PW = "test-admin-pw"


@pytest.fixture(scope="session")
def _application(tmp_path_factory):
    """App einmal pro Testlauf bauen.

    create_app() kostet auf dieser Maschine ueber eine Sekunde; pro Test waere
    das die Haelfte der Laufzeit. Die Isolation passiert stattdessen in der
    app-Fixture ueber drop_all/create_all.
    """
    db_file = tmp_path_factory.mktemp("db") / "test.sqlite"
    application = create_app({
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret",
        "ADMIN_PASSWORD": ADMIN_PW,
        # Billiges Hash-Verfahren: scrypt kostet pro Test mehrere Sekunden
        "PASSWORD_HASH_METHOD": "pbkdf2:sha256:10",
    })

    @application.before_request
    def _login_cache_leeren():
        """Flask-Login-Cache pro Anfrage verwerfen.

        Die app-Fixture haelt waehrend des Tests einen App-Kontext offen,
        damit Tests direkt auf die Modelle zugreifen koennen. Flask legt
        dann fuer Anfragen KEINEN neuen App-Kontext an – `g` wird also
        zwischen allen Anfragen eines Tests geteilt, inklusive des von
        Flask-Login dort abgelegten `_login_user`. Ohne dieses Leeren
        wuerde ein Test, der erst als Superadmin und dann als Viewer
        anfragt, beide Male den Superadmin sehen.
        """
        g.pop("_login_user", None)

    return application


@pytest.fixture()
def app(_application):
    """Frische, leere Datenbank pro Test – inklusive Standard-Superadmin.

    Die App selbst wird wiederverwendet (teuer), ihre Konfiguration aber vor
    jedem Test zurueckgesetzt. Sonst wirkt ein Test, der z. B. ADMIN_PASSWORD
    umstellt, in allen folgenden Tests weiter.
    """
    config_sicherung = dict(_application.config)
    with _application.app_context():
        _db.drop_all()
        _db.create_all()
        _ensure_admin(_application)
        yield _application
        _db.session.remove()
    _application.config.clear()
    _application.config.update(config_sicherung)


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_client(app):
    """Test-Client, der als Superadmin eingeloggt ist."""
    c = app.test_client()
    resp = c.post("/admin/login", data={
        "username": "admin", "password": ADMIN_PW,
    }, follow_redirects=False)
    assert resp.status_code == 302, (
        "Login als Superadmin fehlgeschlagen – vermutlich hat ein anderer "
        "Test ADMIN_PASSWORD veraendert."
    )
    return c


@pytest.fixture()
def editor_client(app):
    """Test-Client, der als Editor ohne Turnierzugang eingeloggt ist."""
    user = Admin(username="editor1", role="editor")
    user.set_password("pw")
    _db.session.add(user)
    _db.session.commit()
    c = app.test_client()
    c.post("/admin/login", data={"username": "editor1", "password": "pw"})
    return c


@pytest.fixture()
def viewer_client(app):
    """Test-Client, der als Viewer (nur lesen) eingeloggt ist."""
    user = Admin(username="viewer1", role="viewer")
    user.set_password("pw")
    _db.session.add(user)
    _db.session.commit()
    c = app.test_client()
    c.post("/admin/login", data={"username": "viewer1", "password": "pw"})
    return c


# ──────────────────────────────────────
# Datenaufbau-Helfer
# ──────────────────────────────────────

def make_tournament(name="Testturnier", **kwargs):
    t = Tournament(name=name, slug=slugify(name), **kwargs)
    _db.session.add(t)
    _db.session.commit()
    ensure_default_settings(t.id)
    return t


def make_group(tournament, name="Gruppe A", order=0):
    gr = Group(tournament_id=tournament.id, name=name, display_order=order)
    _db.session.add(gr)
    _db.session.commit()
    return gr


def make_team(tournament, name, group=None):
    tm = Team(
        tournament_id=tournament.id, name=name,
        group_id=group.id if group else None,
    )
    _db.session.add(tm)
    _db.session.commit()
    return tm


def make_match(tournament, team1, team2, group=None, order=0, **kwargs):
    m = Match(
        tournament_id=tournament.id,
        team1_id=team1.id if team1 else None,
        team2_id=team2.id if team2 else None,
        group_id=group.id if group else None,
        match_order=order,
        **kwargs,
    )
    _db.session.add(m)
    _db.session.commit()
    return m


def finish_match(match, s1, s2):
    match.score_team1 = s1
    match.score_team2 = s2
    match.status = "finished"
    _db.session.commit()
    return match


@pytest.fixture()
def simple_tournament(app):
    """Ein Turnier, eine Gruppe, vier Teams, alle Spiele gespielt.

    Endstand: Alpha 7, Bravo 4, Charlie 4, Delta 0 Punkte.
    """
    t = make_tournament("Simple Cup")
    gr = make_group(t, "Gruppe A")
    alpha = make_team(t, "Alpha", gr)
    bravo = make_team(t, "Bravo", gr)
    charlie = make_team(t, "Charlie", gr)
    delta = make_team(t, "Delta", gr)

    finish_match(make_match(t, alpha, bravo, gr, 1), 2, 0)
    finish_match(make_match(t, charlie, delta, gr, 2), 3, 1)
    finish_match(make_match(t, alpha, charlie, gr, 3), 1, 1)
    finish_match(make_match(t, bravo, delta, gr, 4), 4, 0)
    finish_match(make_match(t, alpha, delta, gr, 5), 5, 0)
    finish_match(make_match(t, bravo, charlie, gr, 6), 0, 2)

    return {
        "tournament": t, "group": gr,
        "teams": {"alpha": alpha, "bravo": bravo,
                  "charlie": charlie, "delta": delta},
    }


@pytest.fixture()
def menu_items(app):
    items = [
        MenuItem(name="Bratwurst", price="3,00", category="speise", display_order=1),
        MenuItem(name="Pommes", price="2,50", category="speise", display_order=2),
        MenuItem(name="Cola 0,33", price="2,00", category="getraenk", display_order=1),
    ]
    _db.session.add_all(items)
    _db.session.commit()
    return items
