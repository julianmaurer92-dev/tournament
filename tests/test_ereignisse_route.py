"""Tests fuer die Erfassung von Spielereignissen (mit Datenbank)."""
from app import db
from app.models import MatchEvent, Team, set_setting
from tests.conftest import make_group, make_match, make_team, make_tournament


def _spiel(name="Ereignis Cup"):
    t = make_tournament(name)
    gr = make_group(t)
    a = make_team(t, "Alpha", gr)
    b = make_team(t, "Bravo", gr)
    a.players = "7 Lena Klein\n9 Mia Groß"
    b.players = "1 Tim Kurz, 4 Jan Lang"
    db.session.commit()
    m = make_match(t, a, b, gr, 1)
    return t, m, a, b


def _erfassen(admin_client, t, m, **felder):
    return admin_client.post(
        f"/admin/t/{t.slug}/api/matches/{m.id}/ereignisse", json=felder)


# ──────────────────────────────────────
# Anlegen
# ──────────────────────────────────────

def test_tor_erfassen_zieht_spielstand_mit(app, admin_client):
    t, m, a, b = _spiel()
    resp = _erfassen(admin_client, t, m, art="tor", team_id=a.id,
                     player_name="Lena Klein", minute=7)
    assert resp.status_code == 200
    assert resp.get_json()["ergebnis"] == {"team1": 1, "team2": 0}

    e = MatchEvent.query.one()
    assert e.art == "tor"
    assert e.team_id == a.id
    assert e.player_name == "Lena Klein"
    assert e.minute == 7
    assert e.tournament_id == t.id


def test_tor_ohne_spielstandanpassung(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id,
              player_name="Lena Klein", ergebnis_anpassen=False)
    assert m.score_team1 == 0, "Spielstand darf nicht angefasst werden"
    assert MatchEvent.query.count() == 1


def test_karte_veraendert_den_spielstand_nicht(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="gelb", team_id=a.id,
              player_name="Lena Klein")
    assert (m.score_team1, m.score_team2) == (0, 0)


def test_eigentor_zaehlt_fuer_den_gegner(app, admin_client):
    """Eingetragen wird die Mannschaft des Schuetzen – gutgeschrieben die andere."""
    t, m, a, b = _spiel()
    resp = _erfassen(admin_client, t, m, art="eigentor", team_id=a.id,
                     player_name="Lena Klein")
    assert resp.get_json()["ergebnis"] == {"team1": 0, "team2": 1}

    e = MatchEvent.query.one()
    assert e.team_id == b.id, "Tor geht auf das Konto von Bravo"
    assert e.player_name == "", "Eigentorschuetze gehoert nicht in die Torjaegerliste"
    assert "Eigentor von Lena Klein" in e.note


def test_mehrere_tore_summieren_sich(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Mia Groß")
    resp = _erfassen(admin_client, t, m, art="tor", team_id=b.id,
                     player_name="Tim Kurz")
    assert resp.get_json()["ergebnis"] == {"team1": 2, "team2": 1}


def test_unbekannte_ereignisart(app, admin_client):
    t, m, a, b = _spiel()
    resp = _erfassen(admin_client, t, m, art="elfmeter", team_id=a.id)
    assert resp.status_code == 400
    assert "Unbekannte Ereignisart" in resp.get_json()["error"]


def test_team_muss_mitspielen(app, admin_client):
    t, m, a, b = _spiel()
    fremd = make_tournament("Fremd Cup")
    fremdes_team = make_team(fremd, "Fremd FC", make_group(fremd))

    resp = _erfassen(admin_client, t, m, art="tor", team_id=fremdes_team.id)
    assert resp.status_code == 400
    assert "spielt nicht" in resp.get_json()["error"]
    assert MatchEvent.query.count() == 0


def test_team_fehlt(app, admin_client):
    t, m, a, b = _spiel()
    resp = _erfassen(admin_client, t, m, art="tor")
    assert resp.status_code == 400
    assert "Mannschaft fehlt" in resp.get_json()["error"]


def test_minute_muss_zahl_sein(app, admin_client):
    t, m, a, b = _spiel()
    resp = _erfassen(admin_client, t, m, art="tor", team_id=a.id, minute="spät")
    assert resp.status_code == 400
    assert "Zahl" in resp.get_json()["error"]


def test_minute_grenzen(app, admin_client):
    t, m, a, b = _spiel()
    assert _erfassen(admin_client, t, m, art="tor", team_id=a.id,
                     minute=-1).status_code == 400
    assert _erfassen(admin_client, t, m, art="tor", team_id=a.id,
                     minute=500).status_code == 400
    assert _erfassen(admin_client, t, m, art="tor", team_id=a.id,
                     minute=0).status_code == 200


def test_minute_darf_leer_sein(app, admin_client):
    t, m, a, b = _spiel()
    assert _erfassen(admin_client, t, m, art="tor", team_id=a.id,
                     minute="").status_code == 200
    assert MatchEvent.query.one().minute is None


def test_fremdes_spiel_nicht_bespielbar(app, admin_client):
    t, m, a, b = _spiel()
    fremd_t, fremd_m, fremd_a, _ = _spiel("Fremd Cup")

    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/matches/{fremd_m.id}/ereignisse",
        json={"art": "tor", "team_id": fremd_a.id})
    assert resp.status_code == 404


# ──────────────────────────────────────
# Loeschen
# ──────────────────────────────────────

def test_tor_loeschen_nimmt_spielstand_zurueck(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    eid = MatchEvent.query.one().id

    resp = admin_client.post(f"/admin/t/{t.slug}/api/ereignisse/{eid}/loeschen",
                             json={"ergebnis_anpassen": True})
    assert resp.status_code == 200
    assert resp.get_json()["ergebnis"] == {"team1": 0, "team2": 0}
    assert MatchEvent.query.count() == 0


def test_tor_loeschen_ohne_spielstandaenderung(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    eid = MatchEvent.query.one().id

    admin_client.post(f"/admin/t/{t.slug}/api/ereignisse/{eid}/loeschen",
                      json={"ergebnis_anpassen": False})
    assert m.score_team1 == 1, "Spielstand bleibt stehen"
    assert MatchEvent.query.count() == 0


def test_spielstand_wird_nie_negativ(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id)
    m.score_team1 = 0           # von Hand auf 0 gesetzt
    db.session.commit()

    eid = MatchEvent.query.one().id
    admin_client.post(f"/admin/t/{t.slug}/api/ereignisse/{eid}/loeschen",
                      json={"ergebnis_anpassen": True})
    assert m.score_team1 == 0


def test_fremdes_ereignis_nicht_loeschbar(app, admin_client):
    t, m, a, b = _spiel()
    fremd_t, fremd_m, fremd_a, _ = _spiel("Fremd Cup")
    _erfassen(admin_client, fremd_t, fremd_m, art="tor", team_id=fremd_a.id)
    eid = MatchEvent.query.one().id

    resp = admin_client.post(
        f"/admin/t/{t.slug}/api/ereignisse/{eid}/loeschen")
    assert resp.status_code == 404
    assert MatchEvent.query.count() == 1


def test_ereignisse_verschwinden_mit_dem_spiel(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id)
    admin_client.post(f"/admin/t/{t.slug}/matches/{m.id}/delete",
                      follow_redirects=True)
    assert MatchEvent.query.count() == 0


def test_ereignisse_verschwinden_mit_dem_turnier(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id)
    admin_client.post(f"/admin/tournaments/{t.id}/delete", follow_redirects=True)
    assert MatchEvent.query.count() == 0


# ──────────────────────────────────────
# Rechte
# ──────────────────────────────────────

def test_viewer_darf_lesen_aber_nicht_erfassen(app, viewer_client):
    from app.models import Admin, UserTournamentAccess
    t, m, a, b = _spiel()
    viewer = Admin.query.filter_by(username="viewer1").first()
    db.session.add(UserTournamentAccess(user_id=viewer.id, tournament_id=t.id))
    db.session.commit()

    assert viewer_client.get(
        f"/admin/t/{t.slug}/matches/{m.id}/ereignisse").status_code == 200
    assert viewer_client.post(
        f"/admin/t/{t.slug}/api/matches/{m.id}/ereignisse",
        json={"art": "tor", "team_id": a.id}).status_code == 403


# ──────────────────────────────────────
# Oberflaeche und Auswertung
# ──────────────────────────────────────

def test_erfassungsseite_zeigt_spielernamen_als_vorschlag(app, admin_client):
    t, m, a, b = _spiel()
    resp = admin_client.get(f"/admin/t/{t.slug}/matches/{m.id}/ereignisse")
    assert resp.status_code == 200
    assert "Lena Klein".encode() in resp.data
    assert "Jan Lang".encode() in resp.data, "Komma-getrennte Spieler auch"


def test_erfassungsseite_warnt_bei_abweichendem_ergebnis(app, admin_client):
    t, m, a, b = _spiel()
    m.score_team1 = 3
    db.session.commit()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id,
              player_name="Lena Klein", ergebnis_anpassen=False)

    resp = admin_client.get(f"/admin/t/{t.slug}/matches/{m.id}/ereignisse")
    assert b"Hinweis" in resp.data
    assert "Die erfassten Tore ergeben".encode() in resp.data


def test_admin_statistik_seite(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    _erfassen(admin_client, t, m, art="gelb", team_id=b.id, player_name="Tim Kurz")

    resp = admin_client.get(f"/admin/t/{t.slug}/statistik")
    assert resp.status_code == 200
    assert "Lena Klein".encode() in resp.data
    assert "Fair-Play".encode() in resp.data


def test_admin_statistik_ohne_ereignisse(app, admin_client):
    t, m, a, b = _spiel()
    resp = admin_client.get(f"/admin/t/{t.slug}/statistik")
    assert resp.status_code == 200
    assert "Noch keine Spielereignisse".encode() in resp.data


def test_oeffentliche_statistik(client, admin_client, app):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")

    resp = client.get(f"/t/{t.slug}/statistik")
    assert resp.status_code == 200
    assert "Lena Klein".encode() in resp.data
    assert "Torschützenliste".encode() in resp.data


def test_oeffentliche_statistik_respektiert_hide_results(client, admin_client, app):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    set_setting(t.id, "hide_results", "1")

    resp = client.get(f"/t/{t.slug}/statistik")
    assert resp.status_code == 200
    assert "Lena Klein".encode() not in resp.data
    assert "noch nicht öffentlich".encode() in resp.data

    assert client.get(f"/t/{t.slug}/api/statistik").get_json() == {"verborgen": True}


def test_statistik_api(client, admin_client, app):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    _erfassen(admin_client, t, m, art="rot", team_id=b.id, player_name="Tim Kurz")

    daten = client.get(f"/t/{t.slug}/api/statistik").get_json()
    assert daten["torschuetzen"][0]["player_name"] == "Lena Klein"
    assert daten["anzahl_ereignisse"] == 2
    bravo = [e for e in daten["fairplay"] if e["team_name"] == "Bravo"][0]
    assert bravo["strafpunkte"] == 5


def test_statistik_api_unbekanntes_turnier(client):
    assert client.get("/t/gibts-nicht/api/statistik").status_code == 404


def test_statistik_seite_unbekanntes_turnier(client):
    assert client.get("/t/gibts-nicht/statistik").status_code == 404


def test_torschuetzen_csv(app, admin_client):
    t, m, a, b = _spiel()
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")
    _erfassen(admin_client, t, m, art="tor", team_id=a.id, player_name="Lena Klein")

    resp = admin_client.get(f"/admin/t/{t.slug}/statistik/torschuetzen.csv")
    assert resp.status_code == 200
    text = resp.data.decode("utf-8")
    assert text.startswith("﻿"), "BOM fuer Excel"
    assert "Platz;Spieler;Mannschaft;Tore" in text
    assert "1;Lena Klein;Alpha;2" in text


def test_statistik_trennt_turniere(app, admin_client):
    """Die Statistik eines Turniers darf keine Schuetzen des anderen zeigen.

    Die Namen sind bewusst eigenwillig: Seit die Admin-Navigation einen
    Turnier-Umschalter hat, stehen ALLE Turniernamen auf jeder Seite.
    Ein Test, der schlicht nach "Zwei" sucht, findet dann "Zweites Cup"
    und schlaegt fehl, obwohl die Statistik korrekt getrennt ist.
    """
    t1, m1, a1, _ = _spiel("Erstes Cup")
    t2, m2, a2, _ = _spiel("Zweites Cup")
    _erfassen(admin_client, t1, m1, art="tor", team_id=a1.id,
              player_name="Xaver Erstling")
    _erfassen(admin_client, t2, m2, art="tor", team_id=a2.id,
              player_name="Yvonne Zweitling")

    daten1 = admin_client.get(f"/admin/t/{t1.slug}/statistik")
    assert "Xaver Erstling".encode() in daten1.data
    assert "Yvonne Zweitling".encode() not in daten1.data

    daten2 = admin_client.get(f"/admin/t/{t2.slug}/statistik")
    assert "Yvonne Zweitling".encode() in daten2.data
    assert "Xaver Erstling".encode() not in daten2.data
