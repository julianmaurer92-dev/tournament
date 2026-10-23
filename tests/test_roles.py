"""Tests fuer Anmeldung, Rollen und Turnier-Zugang.

Sichert ab, dass ein Viewer nichts aendern kann, ein Editor keine Turniere
anlegen oder loeschen kann und niemand an fremde Turniere kommt.
"""
import pytest

from app import db
from app.models import Admin, UserTournamentAccess
from tests.conftest import ADMIN_PW, make_group, make_team, make_tournament


# ──────────────────────────────────────
# Anmeldung
# ──────────────────────────────────────

def test_login_mit_richtigem_passwort(client):
    resp = client.post("/admin/login", data={
        "username": "admin", "password": ADMIN_PW,
    })
    assert resp.status_code == 302
    assert "/admin/" in resp.headers["Location"]


def test_login_mit_falschem_passwort(client):
    resp = client.post("/admin/login", data={
        "username": "admin", "password": "falsch",
    })
    assert resp.status_code == 200
    assert b"Ungueltige Anmeldedaten" in resp.data


def test_login_mit_unbekanntem_benutzer(client):
    resp = client.post("/admin/login", data={
        "username": "gibtsnicht", "password": "x",
    })
    assert resp.status_code == 200
    assert b"Ungueltige Anmeldedaten" in resp.data


def test_benutzer_ohne_passwort_kann_sich_nicht_anmelden(app, client):
    """Google-OAuth-Benutzer haben keinen Passwort-Hash."""
    u = Admin(username="oauth-only", role="editor", password_hash=None)
    db.session.add(u)
    db.session.commit()
    resp = client.post("/admin/login", data={
        "username": "oauth-only", "password": "",
    })
    assert b"Ungueltige Anmeldedaten" in resp.data


def test_admin_bereich_ohne_login_leitet_um(client):
    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_logout(admin_client):
    assert admin_client.get("/admin/").status_code == 200
    admin_client.get("/admin/logout")
    assert admin_client.get("/admin/").status_code == 302


# ──────────────────────────────────────
# Rollenmodell
# ──────────────────────────────────────

def test_rollen_eigenschaften(app):
    sa = Admin(username="sa", role="superadmin")
    ed = Admin(username="ed", role="editor")
    vw = Admin(username="vw", role="viewer")

    assert sa.can_edit() and sa.can_delete()
    assert ed.can_edit() and not ed.can_delete()
    assert not vw.can_edit() and not vw.can_delete()


def test_superadmin_hat_zugang_zu_allen_turnieren(app):
    t = make_tournament("Fremdes Turnier")
    sa = Admin.query.filter_by(username="admin").first()
    assert sa.has_tournament_access(t.id)


def test_editor_hat_nur_zugang_zu_freigegebenen_turnieren(app):
    t1 = make_tournament("Turnier Eins")
    t2 = make_tournament("Turnier Zwei")
    ed = Admin(username="ed", role="editor")
    ed.set_password("pw")
    db.session.add(ed)
    db.session.commit()
    db.session.add(UserTournamentAccess(user_id=ed.id, tournament_id=t1.id))
    db.session.commit()

    assert ed.has_tournament_access(t1.id)
    assert not ed.has_tournament_access(t2.id)


# ──────────────────────────────────────
# Zugriffsschutz der Admin-Routen
# ──────────────────────────────────────

SUPERADMIN_ONLY_GLOBAL = [
    ("POST", "/admin/tournaments"),
    ("GET", "/admin/users"),
    ("POST", "/admin/users/create"),
    ("GET", "/admin/export-import"),
    ("GET", "/admin/api/export"),
    ("POST", "/admin/api/import"),
    ("POST", "/admin/speisekarte/add"),
    ("POST", "/admin/api/menu/reorder"),
]


@pytest.mark.parametrize("methode,pfad", SUPERADMIN_ONLY_GLOBAL)
def test_editor_kommt_nicht_an_superadmin_routen(editor_client, methode, pfad):
    resp = editor_client.open(pfad, method=methode)
    assert resp.status_code == 403, f"{methode} {pfad} erlaubt Editor-Zugriff!"


@pytest.mark.parametrize("methode,pfad", SUPERADMIN_ONLY_GLOBAL)
def test_viewer_kommt_nicht_an_superadmin_routen(viewer_client, methode, pfad):
    resp = viewer_client.open(pfad, method=methode)
    assert resp.status_code == 403, f"{methode} {pfad} erlaubt Viewer-Zugriff!"


def _mit_zugang(user_name, tournament):
    user = Admin.query.filter_by(username=user_name).first()
    db.session.add(UserTournamentAccess(
        user_id=user.id, tournament_id=tournament.id))
    db.session.commit()


def test_viewer_darf_lesen_aber_nicht_schreiben(app, viewer_client):
    t = make_tournament("Viewer Cup")
    _mit_zugang("viewer1", t)

    # lesen: erlaubt
    assert viewer_client.get(f"/admin/t/{t.slug}/").status_code == 200

    # schreiben: verboten
    assert viewer_client.post(
        f"/admin/t/{t.slug}/teams", data={"name": "Hack FC"}
    ).status_code == 403
    assert viewer_client.post(
        f"/admin/t/{t.slug}/groups", data={"name": "Gruppe X"}
    ).status_code == 403
    assert viewer_client.post(
        f"/admin/t/{t.slug}/api/announcement", json={"text": "x"}
    ).status_code == 403


def test_editor_darf_teams_anlegen_aber_nicht_loeschen(app, editor_client):
    t = make_tournament("Editor Cup")
    _mit_zugang("editor1", t)
    gr = make_group(t)

    resp = editor_client.post(f"/admin/t/{t.slug}/teams",
                              data={"name": "Neu FC", "group_id": gr.id})
    assert resp.status_code == 302
    team = make_team(t, "Weg FC", gr)

    # Loeschen ist Superadmin-Sache
    assert editor_client.post(
        f"/admin/t/{t.slug}/teams/{team.id}/delete"
    ).status_code == 403
    assert editor_client.post(
        f"/admin/t/{t.slug}/groups/{gr.id}/delete"
    ).status_code == 403


def test_editor_ohne_zugang_bekommt_403(app, editor_client):
    t = make_tournament("Geheimes Turnier")
    assert editor_client.get(f"/admin/t/{t.slug}/").status_code == 403
    assert editor_client.post(
        f"/admin/t/{t.slug}/teams", data={"name": "X"}
    ).status_code == 403


def test_turnierliste_zeigt_editor_nur_eigene_turniere(app, editor_client):
    eigen = make_tournament("Mein Turnier")
    fremd = make_tournament("Fremdes Turnier")
    _mit_zugang("editor1", eigen)

    resp = editor_client.get("/admin/")
    assert b"Mein Turnier" in resp.data
    assert b"Fremdes Turnier" not in resp.data


def test_unbekannter_slug_im_admin_gibt_404(admin_client):
    assert admin_client.get("/admin/t/gibt-es-nicht/").status_code == 404
