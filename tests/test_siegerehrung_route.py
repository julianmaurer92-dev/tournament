"""Tests fuer Siegerehrung, Endplatzierung und Urkunden (mit Datenbank)."""
from app import db
from app.models import set_setting
from app.siegerehrung import platzierung_fuer
from tests.conftest import (
    finish_match, make_group, make_match, make_team, make_tournament,
)


def _turnier_mit_finale():
    """Vier Teams, Gruppenphase gespielt, Halbfinale, Finale, Platz 3."""
    t = make_tournament("Ehrung Cup")
    gr = make_group(t)
    alpha = make_team(t, "Alpha", gr)
    bravo = make_team(t, "Bravo", gr)
    charlie = make_team(t, "Charlie", gr)
    delta = make_team(t, "Delta", gr)

    # Gruppenphase: Alpha > Bravo > Charlie > Delta
    finish_match(make_match(t, alpha, delta, gr, 1), 3, 0)
    finish_match(make_match(t, bravo, charlie, gr, 2), 2, 1)
    finish_match(make_match(t, alpha, charlie, gr, 3), 2, 0)
    finish_match(make_match(t, bravo, delta, gr, 4), 1, 0)

    # Halbfinale, Finale, Spiel um Platz 3
    finish_match(make_match(t, alpha, delta, None, 5, is_final=True,
                            final_round=2, final_label="Halbfinale 1"), 1, 0)
    finish_match(make_match(t, bravo, charlie, None, 6, is_final=True,
                            final_round=2, final_label="Halbfinale 2"), 0, 2)
    finish_match(make_match(t, alpha, charlie, None, 7, is_final=True,
                            final_round=1, final_label="Finale"), 2, 1)
    finish_match(make_match(t, delta, bravo, None, 8, is_final=True,
                            final_round=1, final_label="Spiel um Platz 3",
                            is_loser_match=True), 1, 0)
    return t


def test_platzierung_aus_der_datenbank(app):
    t = _turnier_mit_finale()
    platzierung = platzierung_fuer(t.id)
    assert [(e["platz"], e["team_name"]) for e in platzierung] == [
        (1, "Alpha"), (2, "Charlie"), (3, "Delta"), (4, "Bravo"),
    ]
    assert platzierung[0]["quelle"] == "Finale"
    assert platzierung[2]["quelle"] == "Spiel um Platz 3"


def test_platzierung_ohne_finalrunde(app):
    t = make_tournament("Nur Gruppe Cup")
    gr = make_group(t)
    a = make_team(t, "Alpha", gr)
    b = make_team(t, "Bravo", gr)
    finish_match(make_match(t, a, b, gr, 1), 3, 0)

    platzierung = platzierung_fuer(t.id)
    assert [e["team_name"] for e in platzierung] == ["Alpha", "Bravo"]
    assert all(e["quelle"] == "Gruppenphase" for e in platzierung)


def test_platzierung_ohne_teams(app):
    t = make_tournament("Leer Cup")
    assert platzierung_fuer(t.id) == []


def test_platzierung_trennt_turniere(app):
    t1 = _turnier_mit_finale()
    t2 = make_tournament("Anderes Cup")
    gr = make_group(t2)
    make_team(t2, "Fremd FC", gr)

    namen = {e["team_name"] for e in platzierung_fuer(t2.id)}
    assert namen == {"Fremd FC"}


# ──────────────────────────────────────
# Adminseiten
# ──────────────────────────────────────

def test_siegerehrung_seite(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.get(f"/admin/t/{t.slug}/siegerehrung")
    assert resp.status_code == 200
    assert b"Endplatzierung" in resp.data
    assert b"Alpha" in resp.data
    assert "Ablauf der Siegerehrung".encode() in resp.data


def test_siegerehrung_ablauf_steht_rueckwaerts(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.get(f"/admin/t/{t.slug}/siegerehrung")
    text = resp.data.decode()
    # Im Ablauf kommt der 4. Platz vor dem 1.
    ablauf = text[text.index("Ablauf der Siegerehrung"):]
    assert ablauf.index("4. Platz") < ablauf.index("1. Platz")


def test_urkunden_druckansicht(app, admin_client):
    t = _turnier_mit_finale()
    set_setting(t.id, "urkunde_veranstalter", "SV Winkel e. V.")
    set_setting(t.id, "urkunde_text", "Danke für das faire Spiel.")
    set_setting(t.id, "urkunde_ort", "Winkel")

    resp = admin_client.get(f"/admin/t/{t.slug}/urkunden")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "URKUNDE" in text
    assert "SV Winkel e. V." in text
    assert "Danke für das faire Spiel." in text
    assert "Winkel," in text
    # Vier Teams, vier Blätter
    assert text.count('class="urkunde"') == 4
    assert "A4 landscape" in text


def test_urkunden_nur_podium(app, admin_client):
    t = _turnier_mit_finale()
    set_setting(t.id, "urkunde_alle_teams", "0")
    resp = admin_client.get(f"/admin/t/{t.slug}/urkunden")
    assert resp.data.decode().count('class="urkunde"') == 3


def test_urkunden_einzelne_plaetze(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.get(f"/admin/t/{t.slug}/urkunden?nur=1")
    text = resp.data.decode()
    assert text.count('class="urkunde"') == 1
    assert "Alpha" in text
    assert "Bravo" not in text


def test_urkunden_mehrere_plaetze(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.get(f"/admin/t/{t.slug}/urkunden?nur=1,2")
    assert resp.data.decode().count('class="urkunde"') == 2


def test_urkunden_kaputter_filter_wird_ignoriert(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.get(f"/admin/t/{t.slug}/urkunden?nur=abc")
    assert resp.status_code == 200
    assert resp.data.decode().count('class="urkunde"') == 4


def test_urkunden_einstellungen_speichern(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.post(
        f"/admin/t/{t.slug}/siegerehrung/einstellungen",
        data={
            "urkunde_veranstalter": "TSV Beispiel",
            "urkunde_ort": "Beispielstadt",
            "urkunde_text": "Gut gespielt!",
            "urkunde_unterschrift": "Der Vorstand",
            "urkunde_alle_teams": "1",
        }, follow_redirects=True)
    assert resp.status_code == 200

    from app.models import get_all_settings
    s = get_all_settings(t.id)
    assert s["urkunde_veranstalter"] == "TSV Beispiel"
    assert s["urkunde_ort"] == "Beispielstadt"
    assert s["urkunde_text"] == "Gut gespielt!"
    assert s["urkunde_unterschrift"] == "Der Vorstand"
    assert s["urkunde_alle_teams"] == "1"


def test_urkunden_haekchen_abwaehlbar(app, admin_client):
    t = _turnier_mit_finale()
    admin_client.post(f"/admin/t/{t.slug}/siegerehrung/einstellungen", data={})
    from app.models import get_all_settings
    assert get_all_settings(t.id)["urkunde_alle_teams"] == "0"


def test_viewer_darf_urkunden_sehen_aber_nichts_speichern(app, viewer_client):
    from app.models import Admin, UserTournamentAccess
    t = _turnier_mit_finale()
    viewer = Admin.query.filter_by(username="viewer1").first()
    db.session.add(UserTournamentAccess(user_id=viewer.id, tournament_id=t.id))
    db.session.commit()

    assert viewer_client.get(f"/admin/t/{t.slug}/siegerehrung").status_code == 200
    assert viewer_client.get(f"/admin/t/{t.slug}/urkunden").status_code == 200
    assert viewer_client.post(
        f"/admin/t/{t.slug}/siegerehrung/einstellungen",
        data={}).status_code == 403


def test_platzierung_csv(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.get(f"/admin/t/{t.slug}/siegerehrung/platzierung.csv")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert text.startswith("﻿")
    assert "Platz;Mannschaft;geteilt;entschieden durch" in text
    assert "1;Alpha;nein;Finale" in text


# ──────────────────────────────────────
# Oeffentliche Ansicht
# ──────────────────────────────────────

def test_oeffentliche_platzierung(client, app):
    t = _turnier_mit_finale()
    resp = client.get(f"/t/{t.slug}/platzierung")
    assert resp.status_code == 200
    assert b"Alpha" in resp.data
    assert "Endplatzierung".encode() in resp.data


def test_oeffentliche_platzierung_respektiert_hide_results(client, app):
    t = _turnier_mit_finale()
    set_setting(t.id, "hide_results", "1")
    resp = client.get(f"/t/{t.slug}/platzierung")
    assert b"Alpha" not in resp.data
    assert "noch nicht öffentlich".encode() in resp.data

    assert client.get(f"/t/{t.slug}/api/platzierung").get_json() == {
        "verborgen": True}


def test_platzierung_api(client, app):
    t = _turnier_mit_finale()
    daten = client.get(f"/t/{t.slug}/api/platzierung").get_json()
    assert [e["team_name"] for e in daten["platzierung"]] == [
        "Alpha", "Charlie", "Delta", "Bravo"]


def test_platzierung_api_unbekanntes_turnier(client):
    assert client.get("/t/gibts-nicht/api/platzierung").status_code == 404


def test_platzierung_seite_unbekanntes_turnier(client):
    assert client.get("/t/gibts-nicht/platzierung").status_code == 404


def test_turnieradministration_verlinkt_siegerehrung(app, admin_client):
    t = _turnier_mit_finale()
    resp = admin_client.get(f"/admin/t/{t.slug}/administration")
    assert f"/admin/t/{t.slug}/siegerehrung".encode() in resp.data
