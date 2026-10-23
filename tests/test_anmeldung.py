"""Tests fuer die Vereinsanmeldung (oeffentliches Formular + Freigabe)."""
from datetime import date

import pytest

from app import db
from app.anmeldung import anmeldestatus
from app.models import (
    ANMELDUNG_ABGELEHNT, ANMELDUNG_BESTAETIGT, ANMELDUNG_OFFEN,
    ANMELDUNG_WARTELISTE, Registration, Team, set_setting,
)
from app.security import formularbremse
from tests.conftest import make_group, make_team, make_tournament


GUT = {
    "club_name": "SV Winkel",
    "team_name": "SV Winkel I",
    "contact_name": "Maria Beispiel",
    "contact_email": "maria@sv-winkel.de",
    "contact_phone": "0171 1234567",
    "player_count": "12",
    "notes": "Wir kommen mit zwei Bussen.",
}


@pytest.fixture(autouse=True)
def bremse_leeren():
    formularbremse.zuruecksetzen()
    yield
    formularbremse.zuruecksetzen()


@pytest.fixture()
def offenes_turnier(app):
    t = make_tournament("Anmelde Cup")
    set_setting(t.id, "registration_open", "1")
    return t


# ──────────────────────────────────────
# anmeldestatus()
# ──────────────────────────────────────

def test_status_geschlossen_ist_standard(app):
    t = make_tournament("Zu Cup")
    offen, grund, _ = anmeldestatus(t.id)
    assert offen is False
    assert "nicht geöffnet" in grund


def test_status_offen_wenn_freigeschaltet(offenes_turnier):
    offen, grund, _ = anmeldestatus(offenes_turnier.id)
    assert offen is True
    assert grund is None


def test_status_frist_abgelaufen(offenes_turnier, monkeypatch):
    set_setting(offenes_turnier.id, "registration_deadline", "2026-01-31")
    monkeypatch.setattr("app.anmeldung._heute", lambda: date(2026, 2, 1))
    offen, grund, _ = anmeldestatus(offenes_turnier.id)
    assert offen is False
    assert "31.01.2026" in grund


def test_status_frist_heute_noch_offen(offenes_turnier, monkeypatch):
    set_setting(offenes_turnier.id, "registration_deadline", "2026-01-31")
    monkeypatch.setattr("app.anmeldung._heute", lambda: date(2026, 1, 31))
    offen, _, _ = anmeldestatus(offenes_turnier.id)
    assert offen is True


def test_status_kaputte_frist_wird_ignoriert(offenes_turnier):
    set_setting(offenes_turnier.id, "registration_deadline", "kein datum")
    offen, grund, infos = anmeldestatus(offenes_turnier.id)
    assert offen is True
    assert infos["deadline"] is None


def test_status_ausgebucht(offenes_turnier):
    set_setting(offenes_turnier.id, "registration_max_teams", "2")
    gr = make_group(offenes_turnier)
    make_team(offenes_turnier, "Team 1", gr)
    make_team(offenes_turnier, "Team 2", gr)

    offen, grund, infos = anmeldestatus(offenes_turnier.id)
    assert offen is False
    assert "ausgebucht" in grund
    assert infos["frei"] == 0


def test_status_freie_plaetze_werden_gezaehlt(offenes_turnier):
    set_setting(offenes_turnier.id, "registration_max_teams", "8")
    gr = make_group(offenes_turnier)
    make_team(offenes_turnier, "Team 1", gr)

    offen, _, infos = anmeldestatus(offenes_turnier.id)
    assert offen is True
    assert infos["max_teams"] == 8
    assert infos["frei"] == 7


# ──────────────────────────────────────
# Oeffentliches Formular
# ──────────────────────────────────────

def test_formular_wird_angezeigt(client, offenes_turnier):
    resp = client.get(f"/t/{offenes_turnier.slug}/anmeldung")
    assert resp.status_code == 200
    assert "Mannschaft anmelden".encode() in resp.data
    assert b"club_name" in resp.data


def test_formular_unbekanntes_turnier_404(client):
    assert client.get("/t/gibts-nicht/anmeldung").status_code == 404


def test_geschlossenes_turnier_zeigt_hinweis_ohne_formular(client, app):
    t = make_tournament("Zu Cup")
    resp = client.get(f"/t/{t.slug}/anmeldung")
    assert resp.status_code == 200
    assert "nicht geöffnet".encode() in resp.data
    assert b'name="club_name"' not in resp.data


def test_anmeldung_wird_gespeichert(client, offenes_turnier):
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    assert resp.status_code == 200
    assert "Anmeldung ist angekommen".encode() in resp.data

    a = Registration.query.filter_by(tournament_id=offenes_turnier.id).one()
    assert a.club_name == "SV Winkel"
    assert a.team_name == "SV Winkel I"
    assert a.contact_email == "maria@sv-winkel.de"
    assert a.player_count == 12
    assert a.status == ANMELDUNG_OFFEN
    assert a.token and len(a.token) > 10
    assert a.team_id is None, "Team entsteht erst beim Bestaetigen"


def test_anmeldung_erzeugt_noch_kein_team(client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    assert Team.query.filter_by(tournament_id=offenes_turnier.id).count() == 0


@pytest.mark.parametrize("feld", ["club_name", "contact_name", "contact_email"])
def test_pflichtfelder(client, offenes_turnier, feld):
    daten = dict(GUT)
    daten[feld] = ""
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=daten)
    assert resp.status_code == 400
    assert Registration.query.count() == 0


@pytest.mark.parametrize("email", ["keine-mail", "a@b", "a@b.", "@b.de", "a b@c.de"])
def test_email_wird_geprueft(client, offenes_turnier, email):
    daten = dict(GUT, contact_email=email)
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=daten)
    assert resp.status_code == 400
    assert "nicht richtig aus".encode() in resp.data


@pytest.mark.parametrize("anzahl", ["0", "100", "-3", "viele"])
def test_spieleranzahl_wird_geprueft(client, offenes_turnier, anzahl):
    daten = dict(GUT, player_count=anzahl)
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=daten)
    assert resp.status_code == 400


def test_spieleranzahl_darf_leer_sein(client, offenes_turnier):
    daten = dict(GUT, player_count="")
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=daten)
    assert resp.status_code == 200
    assert Registration.query.one().player_count is None


def test_teamname_faellt_auf_vereinsnamen_zurueck(client, offenes_turnier):
    daten = dict(GUT, team_name="")
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=daten)
    assert Registration.query.one().anzeige_teamname == "SV Winkel"


def test_doppelte_anmeldung_wird_abgelehnt(client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung",
                       data=dict(GUT, contact_email="anders@sv-winkel.de"))
    assert resp.status_code == 400
    assert "bereits eine Anmeldung".encode() in resp.data
    assert Registration.query.count() == 1


def test_doppelte_anmeldung_unabhaengig_von_gross_klein(client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung",
                       data=dict(GUT, club_name="sv winkel"))
    assert resp.status_code == 400


def test_nach_ablehnung_darf_verein_neu_anmelden(client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()
    a.status = ANMELDUNG_ABGELEHNT
    db.session.commit()

    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    assert resp.status_code == 200
    assert Registration.query.count() == 2


def test_gleicher_verein_in_anderem_turnier_ist_ok(client, app, offenes_turnier):
    t2 = make_tournament("Zweiter Cup")
    set_setting(t2.id, "registration_open", "1")

    assert client.post(f"/t/{offenes_turnier.slug}/anmeldung",
                       data=GUT).status_code == 200
    assert client.post(f"/t/{t2.slug}/anmeldung", data=GUT).status_code == 200
    assert Registration.query.count() == 2


def test_honeypot_verwirft_lautlos(client, offenes_turnier):
    daten = dict(GUT, website="http://spam.example")
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=daten)
    assert resp.status_code == 200
    assert "Anmeldung ist angekommen".encode() in resp.data
    assert Registration.query.count() == 0, "Bot-Eintrag darf nicht gespeichert werden"


def test_ausgebucht_landet_auf_warteliste(client, offenes_turnier):
    set_setting(offenes_turnier.id, "registration_max_teams", "1")
    gr = make_group(offenes_turnier)
    make_team(offenes_turnier, "Schon da FC", gr)

    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    assert resp.status_code == 200
    assert Registration.query.one().status == ANMELDUNG_WARTELISTE
    assert "Warteliste".encode() in resp.data


def test_geschlossene_anmeldung_nimmt_nichts_an(client, app):
    t = make_tournament("Zu Cup")
    resp = client.post(f"/t/{t.slug}/anmeldung", data=GUT)
    assert resp.status_code == 403
    assert Registration.query.count() == 0


def test_abgelaufene_frist_landet_auf_warteliste(client, offenes_turnier, monkeypatch):
    set_setting(offenes_turnier.id, "registration_deadline", "2026-01-01")
    monkeypatch.setattr("app.anmeldung._heute", lambda: date(2026, 6, 1))
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    assert resp.status_code == 200
    assert Registration.query.one().status == ANMELDUNG_WARTELISTE


def test_zu_lange_eingaben_werden_gekuerzt(client, offenes_turnier):
    daten = dict(GUT, club_name="X" * 400, notes="Y" * 5000)
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=daten)
    a = Registration.query.one()
    assert len(a.club_name) == 150
    assert len(a.notes) == 2000


def test_formularbremse_greift(client, offenes_turnier):
    for i in range(12):
        client.post(f"/t/{offenes_turnier.slug}/anmeldung",
                    data=dict(GUT, club_name=f"Verein {i}"))
    resp = client.post(f"/t/{offenes_turnier.slug}/anmeldung",
                       data=dict(GUT, club_name="Verein spaet"))
    assert resp.status_code == 429
    assert "Zu viele Anmeldungen".encode() in resp.data


# ──────────────────────────────────────
# Statusseite fuer den Verein
# ──────────────────────────────────────

def test_statusseite_mit_token(client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    token = Registration.query.one().token

    resp = client.get(f"/t/{offenes_turnier.slug}/anmeldung/status/{token}")
    assert resp.status_code == 200
    assert b"SV Winkel" in resp.data
    assert "Maria Beispiel".encode() in resp.data


def test_statusseite_mit_falschem_token_404(client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    resp = client.get(f"/t/{offenes_turnier.slug}/anmeldung/status/falsch")
    assert resp.status_code == 404


def test_statusseite_token_gilt_nur_fuer_sein_turnier(client, app, offenes_turnier):
    t2 = make_tournament("Zweiter Cup")
    set_setting(t2.id, "registration_open", "1")
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    token = Registration.query.one().token

    resp = client.get(f"/t/{t2.slug}/anmeldung/status/{token}")
    assert resp.status_code == 404


def test_verein_kann_zurueckziehen(client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    token = Registration.query.one().token

    resp = client.post(
        f"/t/{offenes_turnier.slug}/anmeldung/status/{token}/zurueckziehen",
        follow_redirects=True)
    assert resp.status_code == 200
    a = Registration.query.one()
    assert a.status == ANMELDUNG_ABGELEHNT
    assert "selbst zurückgezogen" in a.decision_note


def test_bestaetigte_anmeldung_kann_verein_nicht_zurueckziehen(
        client, admin_client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()
    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen")

    resp = client.post(
        f"/t/{offenes_turnier.slug}/anmeldung/status/{a.token}/zurueckziehen",
        follow_redirects=True)
    assert "an den Veranstalter".encode() in resp.data
    assert Registration.query.one().status == ANMELDUNG_BESTAETIGT


# ──────────────────────────────────────
# Adminbereich
# ──────────────────────────────────────

def test_adminliste_zeigt_anmeldungen(client, admin_client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    resp = admin_client.get(f"/admin/t/{offenes_turnier.slug}/anmeldungen")
    assert resp.status_code == 200
    assert b"SV Winkel" in resp.data
    assert b"maria@sv-winkel.de" in resp.data


def test_adminliste_filtert_nach_status(client, admin_client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    client.post(f"/t/{offenes_turnier.slug}/anmeldung",
                data=dict(GUT, club_name="TSV Anders",
                          contact_email="x@tsv.de"))
    a = Registration.query.filter_by(club_name="TSV Anders").one()
    a.status = ANMELDUNG_ABGELEHNT
    db.session.commit()

    resp = admin_client.get(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen?status=offen")
    assert b"SV Winkel" in resp.data
    assert b"TSV Anders" not in resp.data


def test_bestaetigen_erzeugt_team_mit_gruppe_und_gebuehr(
        client, admin_client, offenes_turnier):
    set_setting(offenes_turnier.id, "registration_fee", "25,00")
    gr = make_group(offenes_turnier, "Gruppe A")
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()

    resp = admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen",
        data={"team_name": "SV Winkel I", "group_id": gr.id},
        follow_redirects=True)
    assert resp.status_code == 200

    a = Registration.query.one()
    assert a.status == ANMELDUNG_BESTAETIGT
    assert a.team_id is not None
    assert a.decided_at is not None
    assert a.decided_by is not None

    team = Team.query.filter_by(tournament_id=offenes_turnier.id).one()
    assert team.name == "SV Winkel I"
    assert team.group_id == gr.id
    assert team.payment is not None
    assert team.payment.paid is False
    assert team.payment.amount == 25.0


def test_bestaetigen_ohne_gruppe(client, admin_client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()
    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen",
        data={"group_id": ""}, follow_redirects=True)
    assert Team.query.one().group_id is None


def test_bestaetigen_lehnt_doppelten_teamnamen_ab(
        client, admin_client, offenes_turnier):
    gr = make_group(offenes_turnier)
    make_team(offenes_turnier, "SV Winkel I", gr)
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()

    resp = admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen",
        data={"team_name": "SV Winkel I"}, follow_redirects=True)
    assert "bereits ein Team".encode() in resp.data
    assert Registration.query.one().status == ANMELDUNG_OFFEN
    assert Team.query.count() == 1


def test_bestaetigen_ignoriert_fremde_gruppe(client, admin_client, app, offenes_turnier):
    fremd = make_tournament("Fremd Cup")
    fremde_gruppe = make_group(fremd, "Fremde Gruppe")
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()

    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen",
        data={"group_id": fremde_gruppe.id}, follow_redirects=True)

    team = Team.query.filter_by(tournament_id=offenes_turnier.id).one()
    assert team.group_id is None, "Gruppe eines anderen Turniers darf nicht greifen"


def test_ablehnen_und_warteliste(client, admin_client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()

    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/warteliste",
        data={"note": "Gruppe noch unklar"}, follow_redirects=True)
    a = Registration.query.one()
    assert a.status == ANMELDUNG_WARTELISTE
    assert a.decision_note == "Gruppe noch unklar"

    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/ablehnen",
        follow_redirects=True)
    assert Registration.query.one().status == ANMELDUNG_ABGELEHNT
    assert Team.query.count() == 0


def test_zuruecksetzen_behaelt_team(client, admin_client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()
    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen",
        follow_redirects=True)

    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/zuruecksetzen",
        follow_redirects=True)
    a = Registration.query.one()
    assert a.status == ANMELDUNG_OFFEN
    assert Team.query.count() == 1, "Team bleibt im Spielplan"


def test_loeschen_nur_superadmin(client, admin_client, editor_client,
                                 offenes_turnier):
    from app.models import Admin, UserTournamentAccess
    editor = Admin.query.filter_by(username="editor1").first()
    db.session.add(UserTournamentAccess(user_id=editor.id,
                                        tournament_id=offenes_turnier.id))
    db.session.commit()

    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()

    assert editor_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/loeschen"
    ).status_code == 403
    assert Registration.query.count() == 1

    admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/loeschen",
        follow_redirects=True)
    assert Registration.query.count() == 0


def test_viewer_darf_nicht_entscheiden(client, viewer_client, offenes_turnier):
    from app.models import Admin, UserTournamentAccess
    viewer = Admin.query.filter_by(username="viewer1").first()
    db.session.add(UserTournamentAccess(user_id=viewer.id,
                                        tournament_id=offenes_turnier.id))
    db.session.commit()

    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    a = Registration.query.one()

    assert viewer_client.get(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen").status_code == 200
    assert viewer_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen"
    ).status_code == 403


def test_anmeldung_aus_fremdem_turnier_nicht_entscheidbar(
        client, admin_client, app, offenes_turnier):
    fremd = make_tournament("Fremd Cup")
    set_setting(fremd.id, "registration_open", "1")
    client.post(f"/t/{fremd.slug}/anmeldung", data=GUT)
    a = Registration.query.one()

    resp = admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/{a.id}/bestaetigen")
    assert resp.status_code == 404


def test_einstellungen_speichern(admin_client, offenes_turnier):
    resp = admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/api/anmeldungen/einstellungen",
        data={
            "registration_open": "1",
            "registration_deadline": "2026-11-01",
            "registration_max_teams": "12",
            "registration_fee": "30,00",
            "registration_info": "Bitte um 8:30 Uhr da sein.",
        }, follow_redirects=True)
    assert resp.status_code == 200

    from app.models import get_all_settings
    s = get_all_settings(offenes_turnier.id)
    assert s["registration_open"] == "1"
    assert s["registration_deadline"] == "2026-11-01"
    assert s["registration_max_teams"] == "12"
    assert s["registration_fee"] == "30,00"
    assert s["registration_info"] == "Bitte um 8:30 Uhr da sein."


def test_einstellungen_lehnen_kaputtes_datum_ab(admin_client, offenes_turnier):
    resp = admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/api/anmeldungen/einstellungen",
        json={"registration_deadline": "31.11.2026"})
    assert resp.status_code == 400
    assert "Datum" in resp.get_json()["error"]


def test_einstellungen_lehnen_kaputte_teamzahl_ab(admin_client, offenes_turnier):
    resp = admin_client.post(
        f"/admin/t/{offenes_turnier.slug}/api/anmeldungen/einstellungen",
        json={"registration_max_teams": "viele"})
    assert resp.status_code == 400


def test_csv_export(client, admin_client, offenes_turnier):
    client.post(f"/t/{offenes_turnier.slug}/anmeldung", data=GUT)
    resp = admin_client.get(
        f"/admin/t/{offenes_turnier.slug}/anmeldungen/export.csv")
    assert resp.status_code == 200
    assert "anmeldungen-" in resp.headers["Content-Disposition"]

    text = resp.data.decode("utf-8")
    assert text.startswith("﻿"), "BOM fuer Excel fehlt"
    assert "Verein;Teamname" in text
    assert "SV Winkel;SV Winkel I" in text
    assert "maria@sv-winkel.de" in text
    # Zeilenumbrueche aus Anmerkungen duerfen die CSV nicht zerlegen
    assert len([z for z in text.strip().split("\r\n") if z]) == 2


def test_zahlen_je_status(client, admin_client, offenes_turnier):
    from app.models import anmeldungen_zaehlen
    for i, status in enumerate([ANMELDUNG_OFFEN, ANMELDUNG_OFFEN,
                                ANMELDUNG_WARTELISTE, ANMELDUNG_ABGELEHNT]):
        db.session.add(Registration(
            tournament_id=offenes_turnier.id,
            club_name=f"Verein {i}", contact_name="X",
            contact_email=f"x{i}@y.de", status=status,
            token=f"token-{i}",
        ))
    db.session.commit()

    zahlen = anmeldungen_zaehlen(offenes_turnier.id)
    assert zahlen[ANMELDUNG_OFFEN] == 2
    assert zahlen[ANMELDUNG_WARTELISTE] == 1
    assert zahlen[ANMELDUNG_ABGELEHNT] == 1
    assert zahlen[ANMELDUNG_BESTAETIGT] == 0
    assert zahlen["gesamt"] == 4


# ──────────────────────────────────────
# Verlinkung in den oeffentlichen Seiten
# ──────────────────────────────────────

def test_startseite_verlinkt_offene_anmeldung(client, offenes_turnier):
    resp = client.get("/")
    assert resp.status_code == 200
    assert f"/t/{offenes_turnier.slug}/anmeldung".encode() in resp.data
    assert "Anmeldung: Anmelde Cup".encode() in resp.data


def test_startseite_verlinkt_geschlossene_anmeldung_nicht(client, app):
    t = make_tournament("Zu Cup")
    resp = client.get("/")
    assert f"/t/{t.slug}/anmeldung".encode() not in resp.data


def test_startseite_zeigt_freie_plaetze(client, offenes_turnier):
    set_setting(offenes_turnier.id, "registration_max_teams", "8")
    gr = make_group(offenes_turnier)
    make_team(offenes_turnier, "Erstes Team", gr)
    resp = client.get("/")
    assert "7 Plätze frei".encode() in resp.data


def test_turnieradministration_verlinkt_anmeldungen(admin_client, offenes_turnier):
    resp = admin_client.get(f"/admin/t/{offenes_turnier.slug}/administration")
    assert resp.status_code == 200
    assert f"/admin/t/{offenes_turnier.slug}/anmeldungen".encode() in resp.data
