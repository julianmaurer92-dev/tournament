"""Tests fuer die Schiedsrichter-Verwaltung als Routen (mit Datenbank)."""
from datetime import datetime

from app import db
from app.models import Match, Referee, set_setting
from tests.conftest import make_group, make_match, make_team, make_tournament

NEUN = datetime(2026, 11, 14, 9, 0)
NEUN15 = datetime(2026, 11, 14, 9, 15)


def _turnier(name="Schiri Cup"):
    t = make_tournament(name)
    gr = make_group(t)
    a = make_team(t, "Alpha", gr)
    b = make_team(t, "Bravo", gr)
    c = make_team(t, "Charlie", gr)
    d = make_team(t, "Delta", gr)
    make_match(t, a, b, gr, 1, scheduled_time=NEUN, field=1)
    make_match(t, c, d, gr, 2, scheduled_time=NEUN, field=2)
    make_match(t, a, c, gr, 3, scheduled_time=NEUN15, field=1)
    return t, {"a": a, "b": b, "c": c, "d": d}


def _anlegen(admin_client, t, name, **felder):
    daten = {"name": name}
    daten.update(felder)
    return admin_client.post(f"/admin/t/{t.slug}/schiedsrichter/neu",
                             data=daten, follow_redirects=True)


# ──────────────────────────────────────
# Stammdaten
# ──────────────────────────────────────

def test_schiedsrichter_anlegen(app, admin_client):
    t, teams = _turnier()
    resp = _anlegen(admin_client, t, "Hans Meier", phone="0171 1",
                    note="nur vormittags", team_id=teams["a"].id)
    assert resp.status_code == 200

    s = Referee.query.one()
    assert s.name == "Hans Meier"
    assert s.phone == "0171 1"
    assert s.note == "nur vormittags"
    assert s.team_id == teams["a"].id
    assert s.is_active is True
    assert s.tournament_id == t.id


def test_schiedsrichter_ohne_name(app, admin_client):
    t, _teams = _turnier()
    resp = _anlegen(admin_client, t, "")
    assert "Name erforderlich".encode() in resp.data
    assert Referee.query.count() == 0


def test_schiedsrichter_name_nur_einmal(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Hans Meier")
    resp = _anlegen(admin_client, t, "Hans Meier")
    assert "schon eingetragen".encode() in resp.data
    assert Referee.query.count() == 1


def test_gleicher_name_in_anderem_turnier_ist_ok(app, admin_client):
    t1, _ = _turnier()
    t2 = make_tournament("Zweites Cup")
    _anlegen(admin_client, t1, "Hans Meier")
    _anlegen(admin_client, t2, "Hans Meier")
    assert Referee.query.count() == 2


def test_fremdes_team_wird_ignoriert(app, admin_client):
    t, _teams = _turnier()
    fremd = make_tournament("Fremd Cup")
    fremdes_team = make_team(fremd, "Fremd FC", make_group(fremd))

    _anlegen(admin_client, t, "Hans Meier", team_id=fremdes_team.id)
    assert Referee.query.one().team_id is None


def test_schiedsrichter_bearbeiten(app, admin_client):
    t, teams = _turnier()
    _anlegen(admin_client, t, "Hans Meier")
    s = Referee.query.one()

    admin_client.post(
        f"/admin/t/{t.slug}/schiedsrichter/{s.id}/bearbeiten",
        data={"name": "Hans Müller", "phone": "0172 2",
              "team_id": teams["b"].id, "note": "neu"},
        follow_redirects=True)

    s = Referee.query.one()
    assert s.name == "Hans Müller"
    assert s.phone == "0172 2"
    assert s.team_id == teams["b"].id
    assert s.is_active is False, "ohne Haekchen wird inaktiv gesetzt"


def test_bearbeiten_team_entfernen(app, admin_client):
    t, teams = _turnier()
    _anlegen(admin_client, t, "Hans", team_id=teams["a"].id)
    s = Referee.query.one()
    admin_client.post(f"/admin/t/{t.slug}/schiedsrichter/{s.id}/bearbeiten",
                      data={"name": "Hans", "team_id": "", "is_active": "1"},
                      follow_redirects=True)
    assert Referee.query.one().team_id is None


def test_fremden_schiedsrichter_nicht_bearbeitbar(app, admin_client):
    t1, _ = _turnier()
    t2 = make_tournament("Zweites Cup")
    _anlegen(admin_client, t2, "Fremd Schiri")
    s = Referee.query.one()

    resp = admin_client.post(
        f"/admin/t/{t1.slug}/schiedsrichter/{s.id}/bearbeiten",
        data={"name": "Gekapert"})
    assert resp.status_code == 404
    assert Referee.query.one().name == "Fremd Schiri"


def test_loeschen_loest_zuteilung(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Hans Meier")
    s = Referee.query.one()
    spiel = Match.query.filter_by(tournament_id=t.id).first()
    spiel.referee_id = s.id
    db.session.commit()

    resp = admin_client.post(
        f"/admin/t/{t.slug}/schiedsrichter/{s.id}/loeschen",
        follow_redirects=True)
    assert "ohne Schiedsrichter".encode() in resp.data
    assert Referee.query.count() == 0
    assert db.session.get(Match, spiel.id).referee_id is None


def test_loeschen_nur_superadmin(app, admin_client, editor_client):
    from app.models import Admin, UserTournamentAccess
    t, _teams = _turnier()
    editor = Admin.query.filter_by(username="editor1").first()
    db.session.add(UserTournamentAccess(user_id=editor.id, tournament_id=t.id))
    db.session.commit()
    _anlegen(admin_client, t, "Hans Meier")
    s = Referee.query.one()

    assert editor_client.post(
        f"/admin/t/{t.slug}/schiedsrichter/{s.id}/loeschen").status_code == 403
    assert Referee.query.count() == 1


def test_schiedsrichter_verschwinden_mit_dem_turnier(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Hans Meier")
    admin_client.post(f"/admin/tournaments/{t.id}/delete",
                      follow_redirects=True)
    assert Referee.query.count() == 0


# ──────────────────────────────────────
# Zuteilung
# ──────────────────────────────────────

def test_einzelne_zuteilung(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Hans Meier")
    s = Referee.query.one()
    spiel = Match.query.filter_by(tournament_id=t.id).first()

    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/matches/{spiel.id}/schiedsrichter",
        json={"schiedsrichter_id": s.id})
    assert resp.status_code == 200
    assert resp.get_json()["match"]["referee_name"] == "Hans Meier"
    assert db.session.get(Match, spiel.id).referee_id == s.id


def test_zuteilung_loesen(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Hans Meier")
    s = Referee.query.one()
    spiel = Match.query.filter_by(tournament_id=t.id).first()
    spiel.referee_id = s.id
    db.session.commit()

    admin_client.post(
        f"/admin/t/{t.slug}/api/matches/{spiel.id}/schiedsrichter",
        json={"schiedsrichter_id": ""})
    assert db.session.get(Match, spiel.id).referee_id is None


def test_zuteilung_fremder_schiedsrichter(app, admin_client):
    t, _teams = _turnier()
    t2 = make_tournament("Zweites Cup")
    _anlegen(admin_client, t2, "Fremd Schiri")
    s = Referee.query.one()
    spiel = Match.query.filter_by(tournament_id=t.id).first()

    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/matches/{spiel.id}/schiedsrichter",
        json={"schiedsrichter_id": s.id})
    assert resp.status_code == 404


def test_zuteilung_fremdes_spiel(app, admin_client):
    t, _teams = _turnier()
    t2, _teams2 = _turnier("Zweites Schiri Cup")
    _anlegen(admin_client, t, "Hans Meier")
    s = Referee.query.filter_by(tournament_id=t.id).one()
    fremdes_spiel = Match.query.filter_by(tournament_id=t2.id).first()

    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/matches/{fremdes_spiel.id}/schiedsrichter",
        json={"schiedsrichter_id": s.id})
    assert resp.status_code == 404


def test_zuteilung_kaputte_id(app, admin_client):
    t, _teams = _turnier()
    spiel = Match.query.filter_by(tournament_id=t.id).first()
    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/matches/{spiel.id}/schiedsrichter",
        json={"schiedsrichter_id": "Hans"})
    assert resp.status_code == 400


def test_automatisch_verteilen(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A")
    _anlegen(admin_client, t, "Schiri B")

    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/schiedsrichter/verteilen", json={})
    daten = resp.get_json()
    assert daten["zugeteilt"] == 3
    assert daten["offen"] == 0
    assert daten["konflikte"] == []

    spiele = Match.query.filter_by(tournament_id=t.id).all()
    assert all(m.referee_id for m in spiele)
    # Die beiden parallelen Spiele um 9:00 haben verschiedene Schiedsrichter
    parallel = [m for m in spiele if m.scheduled_time == NEUN]
    assert parallel[0].referee_id != parallel[1].referee_id


def test_verteilen_ohne_schiedsrichter_ist_fehler(app, admin_client):
    t, _teams = _turnier()
    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/schiedsrichter/verteilen", json={})
    assert resp.status_code == 400
    assert "keine Schiedsrichter" in resp.get_json()["error"]


def test_verteilen_fuellt_nur_luecken(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A")
    _anlegen(admin_client, t, "Schiri B")
    a = Referee.query.filter_by(name="Schiri A").one()
    spiel = Match.query.filter_by(tournament_id=t.id).order_by(
        Match.match_order).first()
    spiel.referee_id = a.id
    db.session.commit()

    admin_client.post(f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
                      json={"nur_leere": "1"})
    assert db.session.get(Match, spiel.id).referee_id == a.id


def test_verteilen_alles_neu(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A")
    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
        json={"nur_leere": "0"})
    daten = resp.get_json()
    # Ein Schiedsrichter, zwei parallele Spiele -> eines bleibt offen
    assert daten["offen"] == 1


def test_verteilen_meidet_eigene_mannschaft(app, admin_client):
    t, teams = _turnier()
    _anlegen(admin_client, t, "Papa Alpha", team_id=teams["a"].id)
    _anlegen(admin_client, t, "Neutral A")
    _anlegen(admin_client, t, "Neutral B")

    admin_client.post(f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
                      json={})
    papa = Referee.query.filter_by(name="Papa Alpha").one()
    alpha_spiele = Match.query.filter(
        Match.tournament_id == t.id,
        (Match.team1_id == teams["a"].id) | (Match.team2_id == teams["a"].id),
    ).all()
    assert all(m.referee_id != papa.id for m in alpha_spiele)


# ──────────────────────────────────────
# Konflikte
# ──────────────────────────────────────

def test_konfliktpruefung_sauber(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A")
    _anlegen(admin_client, t, "Schiri B")
    admin_client.post(f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
                      json={})

    daten = admin_client.get(
        f"/admin/t/{t.slug}/api/schiedsrichter/konflikte").get_json()
    assert daten == {"konflikte": [], "anzahl": 0}


def test_konfliktpruefung_findet_doppelbelegung(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A")
    s = Referee.query.one()
    for m in Match.query.filter_by(tournament_id=t.id,
                                   scheduled_time=NEUN).all():
        m.referee_id = s.id
    db.session.commit()

    daten = admin_client.get(
        f"/admin/t/{t.slug}/api/schiedsrichter/konflikte").get_json()
    assert daten["anzahl"] == 1
    assert "Schiri A" in daten["konflikte"][0]
    assert "gleichzeitig" in daten["konflikte"][0]


# ──────────────────────────────────────
# Oberflaeche und Einsatzplan
# ──────────────────────────────────────

def test_uebersichtsseite(app, admin_client):
    t, teams = _turnier()
    _anlegen(admin_client, t, "Hans Meier", team_id=teams["a"].id)
    resp = admin_client.get(f"/admin/t/{t.slug}/schiedsrichter")
    assert resp.status_code == 200
    assert "Hans Meier".encode() in resp.data
    assert b"Alpha" in resp.data
    assert "3 ohne Schiedsrichter".encode() in resp.data


def test_uebersicht_zeigt_konflikte(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A")
    s = Referee.query.one()
    for m in Match.query.filter_by(tournament_id=t.id,
                                   scheduled_time=NEUN).all():
        m.referee_id = s.id
    db.session.commit()

    resp = admin_client.get(f"/admin/t/{t.slug}/schiedsrichter")
    assert "Problem(e) in der Einteilung".encode() in resp.data


def test_einsatzplan(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A", phone="0171 99")
    _anlegen(admin_client, t, "Schiri B")
    admin_client.post(f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
                      json={})

    resp = admin_client.get(f"/admin/t/{t.slug}/schiedsrichter/plan")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Schiedsrichter-Einsatzplan" in text
    assert "Schiri A" in text
    assert "0171 99" in text
    assert "09:00" in text


def test_einsatzplan_warnt_vor_luecken(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A")
    resp = admin_client.get(f"/admin/t/{t.slug}/schiedsrichter/plan")
    assert "ohne Schiedsrichter".encode() in resp.data


def test_einsatzplan_csv(app, admin_client):
    t, _teams = _turnier()
    _anlegen(admin_client, t, "Schiri A", phone="0171 99")
    _anlegen(admin_client, t, "Schiri B")
    admin_client.post(f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
                      json={})

    resp = admin_client.get(f"/admin/t/{t.slug}/schiedsrichter/plan.csv")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert text.startswith("﻿")
    assert "Spiel;Anstoss;Feld;Begegnung;Schiedsrichter;Telefon" in text
    assert "Alpha - Bravo" in text
    assert "0171 99" in text


def test_viewer_darf_lesen_aber_nicht_aendern(app, viewer_client, admin_client):
    from app.models import Admin, UserTournamentAccess
    t, _teams = _turnier()
    viewer = Admin.query.filter_by(username="viewer1").first()
    db.session.add(UserTournamentAccess(user_id=viewer.id, tournament_id=t.id))
    db.session.commit()
    _anlegen(admin_client, t, "Schiri A")

    assert viewer_client.get(
        f"/admin/t/{t.slug}/schiedsrichter").status_code == 200
    assert viewer_client.get(
        f"/admin/t/{t.slug}/schiedsrichter/plan").status_code == 200
    assert viewer_client.post(
        f"/admin/t/{t.slug}/schiedsrichter/neu",
        data={"name": "Heimlich"}).status_code == 403
    assert viewer_client.post(
        f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
        json={}).status_code == 403


def test_turnieradministration_verlinkt_schiedsrichter(app, admin_client):
    t, _teams = _turnier()
    resp = admin_client.get(f"/admin/t/{t.slug}/administration")
    assert f"/admin/t/{t.slug}/schiedsrichter".encode() in resp.data


# ──────────────────────────────────────
# Spielplan-Druckansicht
# ──────────────────────────────────────

def test_druckplan_zeigt_anstosszeit_und_schiedsrichter(app, admin_client):
    t, _teams = _turnier()
    set_setting(t.id, "num_fields", "2")
    _anlegen(admin_client, t, "Schiri A")
    _anlegen(admin_client, t, "Schiri B")
    admin_client.post(f"/admin/t/{t.slug}/api/schiedsrichter/verteilen",
                      json={})

    resp = admin_client.get(f"/admin/t/{t.slug}/schedule/print")
    text = resp.data.decode()
    assert "Anstoß" in text
    assert "Schiedsrichter" in text
    assert "09:00" in text
    assert "Schiri A" in text


def test_druckplan_ohne_zeiten_zeigt_keine_leere_spalte(app, admin_client):
    t = make_tournament("Ohne Zeiten Cup")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    make_match(t, a, b, gr, 1)        # keine scheduled_time

    resp = admin_client.get(f"/admin/t/{t.slug}/schedule/print")
    text = resp.data.decode()
    assert "Anstoß" not in text
    assert "Schiedsrichter" not in text
