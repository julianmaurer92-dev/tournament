"""Ein komplettes Turnierwochenende durch die echten HTTP-Routen.

Dieser Test geht den Weg, den der Auftrag beschreibt: von der
Vereinsanmeldung bis zur Siegerehrung. Er ruft ausschliesslich die Routen
auf, die auch ein Browser aufruft – kein Zugriff auf Modelle, um etwas
"schnell einzurichten". Damit faellt auf, wenn zwei Bausteine einzeln
funktionieren, aber nicht zusammen.

Bewusst ein grosser Test statt zwanzig kleiner: Der Wert liegt in der Kette.
Jeder Abschnitt ist mit einer Zwischenpruefung abgeschlossen, damit man beim
Fehlschlag sofort sieht, wo die Kette reisst.
"""
import io
import json
import re
from datetime import date

import pytest

from app.models import (
    Match, Referee, Registration, Team, Tournament, get_setting, set_setting,
)
from app.security import formularbremse


@pytest.fixture(autouse=True)
def bremse_leeren():
    formularbremse.zuruecksetzen()
    yield
    formularbremse.zuruecksetzen()


VEREINE = [
    ("SV Winkel", "winkel@example.org"),
    ("TSV Oberbach", "oberbach@example.org"),
    ("FC Rosenheim", "rosenheim@example.org"),
    ("SG Talheim", "talheim@example.org"),
]


def test_komplettes_turnierwochenende(app, client, admin_client):
    # ══ 1. Turnier anlegen ═══════════════════════════════════════════
    resp = admin_client.post("/admin/tournaments", data={
        "name": "E-Jugend Herbstcup 2026",
        "event_date": "2026-11-14",
        "event_time": "09:00",
        "description": "E-Jugend, Jahrgang 2017/2018",
        "num_fields": "2",
        "timer_regular_min": "10",
        "final_mode": "semi_final",
    }, follow_redirects=True)
    assert resp.status_code == 200

    turnier = Tournament.query.filter_by(name="E-Jugend Herbstcup 2026").one()
    slug = turnier.slug
    assert get_setting(turnier.id, "num_fields") == "2"
    assert get_setting(turnier.id, "default_timer_regular") == "600"

    # ══ 2. Anmeldung öffnen ══════════════════════════════════════════
    resp = admin_client.post(
        f"/admin/t/{slug}/api/anmeldungen/einstellungen", data={
            "registration_open": "1",
            "registration_deadline": "2026-11-07",
            "registration_max_teams": "4",
            "registration_fee": "25,00",
            "registration_info": "Bitte 30 Minuten vor Anstoß da sein.",
        }, follow_redirects=True)
    assert resp.status_code == 200

    # Die Startseite verlinkt das Formular jetzt
    resp = client.get("/")
    assert f"/t/{slug}/anmeldung".encode() in resp.data
    assert "4 Plätze frei".encode() in resp.data

    # ══ 3. Vier Vereine melden sich an (öffentlich, ohne Login) ══════
    tokens = {}
    for name, mail in VEREINE:
        resp = client.post(f"/t/{slug}/anmeldung", data={
            "club_name": name,
            "contact_name": f"Ansprechpartner {name}",
            "contact_email": mail,
            "contact_phone": "0171 1234567",
            "player_count": "12",
            "notes": "Wir kommen mit dem Bus.",
        })
        assert resp.status_code == 200, f"Anmeldung {name} fehlgeschlagen"
        assert "Anmeldung ist angekommen".encode() in resp.data
        tokens[name] = Registration.query.filter_by(club_name=name).one().token

    assert Registration.query.filter_by(tournament_id=turnier.id).count() == 4
    assert Team.query.filter_by(tournament_id=turnier.id).count() == 0, \
        "Teams entstehen erst beim Bestaetigen"

    # Der Verein kann seinen Stand selbst nachsehen
    resp = client.get(f"/t/{slug}/anmeldung/status/{tokens['SV Winkel']}")
    assert resp.status_code == 200
    assert b"SV Winkel" in resp.data

    # Ein fünfter Verein landet auf der Warteliste (4 Plätze, 4 bestätigt
    # kommt gleich – erst mal ist noch Platz, also normal offen)
    resp = client.post(f"/t/{slug}/anmeldung", data={
        "club_name": "SpVgg Au", "contact_name": "X",
        "contact_email": "au@example.org",
    })
    assert resp.status_code == 200

    # ══ 4. Gruppen anlegen ═══════════════════════════════════════════
    for gruppe in ("Gruppe A", "Gruppe B"):
        resp = admin_client.post(f"/admin/t/{slug}/groups",
                                 data={"name": gruppe}, follow_redirects=True)
        assert resp.status_code == 200
    gruppen = {g.name: g for g in turnier.groups.all()}
    assert set(gruppen) == {"Gruppe A", "Gruppe B"}

    # ══ 5. Anmeldungen freigeben – je zwei pro Gruppe ════════════════
    verteilung = [
        ("SV Winkel", "Gruppe A"), ("TSV Oberbach", "Gruppe A"),
        ("FC Rosenheim", "Gruppe B"), ("SG Talheim", "Gruppe B"),
    ]
    for verein, gruppe in verteilung:
        anmeldung = Registration.query.filter_by(club_name=verein).one()
        resp = admin_client.post(
            f"/admin/t/{slug}/anmeldungen/{anmeldung.id}/bestaetigen",
            data={"team_name": verein, "group_id": gruppen[gruppe].id},
            follow_redirects=True)
        assert resp.status_code == 200
        assert "bestätigt".encode() in resp.data

    teams = {t.name: t for t in turnier.teams.all()}
    assert set(teams) == {v for v, _ in verteilung}
    # Startgebühr steht als offener Posten
    assert all(t.payment is not None and t.payment.paid is False
               and t.payment.amount == 25.0 for t in teams.values())

    # Der fünfte Verein wird abgelehnt
    au = Registration.query.filter_by(club_name="SpVgg Au").one()
    admin_client.post(f"/admin/t/{slug}/anmeldungen/{au.id}/ablehnen",
                      data={"note": "ausgebucht"}, follow_redirects=True)
    assert Registration.query.filter_by(club_name="SpVgg Au").one().status \
        == "abgelehnt"

    # ══ 6. Spielplan erzeugen ════════════════════════════════════════
    resp = admin_client.post(
        f"/admin/t/{slug}/api/matches/generate-round-robin", json={
            "felder": 2, "spielzeit_min": 10, "pause_min": 5,
            "startdatum": "2026-11-14", "startzeit": "09:00",
        })
    assert resp.status_code == 200
    plan = resp.get_json()
    assert plan["created"] == 2, "2 Gruppen mit je 2 Teams -> 2 Spiele"
    assert plan["beginn"] == "14.11.2026 09:00"

    # Keine Doppelbelegungen
    konflikte = admin_client.get(
        f"/admin/t/{slug}/api/matches/konflikte").get_json()
    assert konflikte == {"konflikte": [], "anzahl": 0}

    gruppenspiele = Match.query.filter_by(
        tournament_id=turnier.id, is_final=False).order_by(
        Match.match_order).all()
    assert all(m.scheduled_time for m in gruppenspiele)

    # ══ 7. Schiedsrichter einteilen ══════════════════════════════════
    for name, team in (("Hans Meier", None),
                       ("Papa Winkel", teams["SV Winkel"].id)):
        daten = {"name": name, "phone": "0172 5"}
        if team:
            daten["team_id"] = team
        admin_client.post(f"/admin/t/{slug}/schiedsrichter/neu",
                          data=daten, follow_redirects=True)
    assert Referee.query.filter_by(tournament_id=turnier.id).count() == 2

    resp = admin_client.post(
        f"/admin/t/{slug}/api/schiedsrichter/verteilen", json={})
    verteilt = resp.get_json()
    assert verteilt["zugeteilt"] == 2
    assert verteilt["offen"] == 0
    assert verteilt["konflikte"] == []

    papa = Referee.query.filter_by(name="Papa Winkel").one()
    winkel_spiele = Match.query.filter(
        Match.tournament_id == turnier.id,
        (Match.team1_id == teams["SV Winkel"].id)
        | (Match.team2_id == teams["SV Winkel"].id),
    ).all()
    assert all(m.referee_id != papa.id for m in winkel_spiele), \
        "Papa Winkel darf kein Spiel seiner Mannschaft pfeifen"

    # Einsatzplan ist druckbar
    resp = admin_client.get(f"/admin/t/{slug}/schiedsrichter/plan")
    assert resp.status_code == 200
    assert "Hans Meier".encode() in resp.data

    # ══ 8. Gruppenspiele live durchführen ════════════════════════════
    ergebnisse = {}
    for spiel in gruppenspiele:
        # Spiel starten
        resp = admin_client.post(
            f"/admin/t/{slug}/api/matches/{spiel.id}/timer",
            json={"action": "start"})
        assert resp.status_code == 200
        assert resp.get_json()["timer_running"] is True
        assert resp.get_json()["status"] == "live"

        # Tore mit Schützen erfassen (Spielstand zieht mit)
        admin_client.post(
            f"/admin/t/{slug}/api/matches/{spiel.id}/ereignisse",
            json={"art": "tor", "team_id": spiel.team1_id,
                  "player_name": "Lena Klein", "minute": 4})
        admin_client.post(
            f"/admin/t/{slug}/api/matches/{spiel.id}/ereignisse",
            json={"art": "tor", "team_id": spiel.team1_id,
                  "player_name": "Lena Klein", "minute": 7})
        admin_client.post(
            f"/admin/t/{slug}/api/matches/{spiel.id}/ereignisse",
            json={"art": "gelb", "team_id": spiel.team2_id,
                  "player_name": "Tim Kurz", "minute": 9})

        # Spiel beenden
        resp = admin_client.post(
            f"/admin/t/{slug}/api/matches/{spiel.id}/status",
            json={"status": "finished"})
        assert resp.status_code == 200
        daten = resp.get_json()
        assert daten["score_team1"] == 2 and daten["score_team2"] == 0
        ergebnisse[spiel.id] = (spiel.team1_id, spiel.team2_id)

    # Erfasste Tore und Spielstand passen zusammen
    for spiel in gruppenspiele:
        pruefung = admin_client.get(
            f"/admin/t/{slug}/api/matches/{spiel.id}/ereignisse").get_json()
        assert pruefung["ergebnis_stimmt"] is True

    # ══ 9. Öffentliche Ansichten zeigen den Stand ════════════════════
    zustand = client.get(f"/t/{slug}/api/state").get_json()
    assert len(zustand["past_matches"]) == 2
    assert zustand["live_match"] is None
    assert len(zustand["groups"]) == 2

    statistik = client.get(f"/t/{slug}/api/statistik").get_json()
    assert statistik["torschuetzen"][0]["player_name"] == "Lena Klein"
    assert statistik["torschuetzen"][0]["tore"] == 2

    for pfad in (f"/t/{slug}/", f"/t/{slug}/tv/", f"/t/{slug}/phone/",
                 f"/t/{slug}/statistik", f"/t/{slug}/platzierung"):
        assert client.get(pfad).status_code == 200, pfad

    # ══ 10. Gruppenphase beenden, Finale starten ═════════════════════
    resp = admin_client.post(f"/admin/t/{slug}/api/phase/end-group-stage",
                             json={})
    assert resp.status_code == 200
    assert get_setting(turnier.id, "tournament_phase") != "GROUP_STAGE"

    resp = admin_client.post(f"/admin/t/{slug}/api/phase/start-final-round",
                             json={"mode": "direct_final", "config": {}})
    assert resp.status_code == 200, resp.data[:300]

    finalspiele = Match.query.filter_by(tournament_id=turnier.id,
                                        is_final=True).all()
    assert finalspiele, "Finalrunde wurde nicht erzeugt"
    finale = [m for m in finalspiele if m.final_round == 1][0]
    assert finale.team1_id and finale.team2_id

    # ══ 11. Finale spielen ═══════════════════════════════════════════
    admin_client.post(f"/admin/t/{slug}/api/matches/{finale.id}/score",
                      json={"score_team1": 3, "score_team2": 1})
    resp = admin_client.post(f"/admin/t/{slug}/api/matches/{finale.id}/status",
                             json={"status": "finished"})
    assert resp.status_code == 200

    admin_client.post(f"/admin/t/{slug}/api/phase/finish-tournament", json={})
    assert get_setting(turnier.id, "tournament_phase") == "FINISHED"

    # ══ 12. Siegerehrung ═════════════════════════════════════════════
    platzierung = client.get(f"/t/{slug}/api/platzierung").get_json()[
        "platzierung"]
    assert len(platzierung) == 4
    assert platzierung[0]["platz"] == 1
    assert platzierung[0]["quelle"] == "Finale"
    sieger = platzierung[0]["team_name"]
    zweiter = platzierung[1]["team_name"]
    assert sieger != zweiter
    # Lückenlose Plätze
    assert [e["platz"] for e in platzierung] == [1, 2, 3, 4]

    resp = admin_client.get(f"/admin/t/{slug}/siegerehrung")
    assert resp.status_code == 200
    assert sieger.encode() in resp.data

    # Urkunden: eine pro Mannschaft
    admin_client.post(f"/admin/t/{slug}/siegerehrung/einstellungen", data={
        "urkunde_veranstalter": "SV Winkel e. V.",
        "urkunde_ort": "Winkel",
        "urkunde_text": "Danke für das faire Spiel.",
        "urkunde_unterschrift": "Die Turnierleitung",
        "urkunde_alle_teams": "1",
    }, follow_redirects=True)
    resp = admin_client.get(f"/admin/t/{slug}/urkunden")
    text = resp.data.decode()
    assert text.count('class="urkunde"') == 4
    assert "SV Winkel e. V." in text
    assert "1. Platz" in text

    # ══ 13. Alles drucken und exportieren ════════════════════════════
    for pfad in (f"/admin/t/{slug}/schedule/print",
                 f"/admin/t/{slug}/cabin-signs",
                 f"/admin/t/{slug}/organisation",
                 f"/admin/t/{slug}/statistik",
                 f"/admin/t/{slug}/anmeldungen",
                 f"/admin/t/{slug}/anmeldungen/export.csv",
                 f"/admin/t/{slug}/statistik/torschuetzen.csv",
                 f"/admin/t/{slug}/siegerehrung/platzierung.csv",
                 f"/admin/t/{slug}/schiedsrichter/plan.csv"):
        assert admin_client.get(pfad).status_code == 200, pfad

    # Spielplan-Druckansicht zeigt Anstoßzeit und Schiedsrichter
    druck = admin_client.get(f"/admin/t/{slug}/schedule/print").data.decode()
    assert "Anstoß" in druck
    assert "Schiedsrichter" in druck
    assert "09:00" in druck

    # ══ 14. Backup und Wiederherstellung ═════════════════════════════
    export = json.loads(
        admin_client.get(f"/admin/api/export?ids={turnier.id}&include_menu=1")
        .data)
    assert export["version"] == "2"
    t_data = export["tournaments"][0]
    assert len(t_data["teams"]) == 4
    assert len(t_data["registrations"]) == 5, "auch die abgelehnte Anmeldung"
    assert len(t_data["referees"]) == 2
    assert sum(len(m["events"]) for m in t_data["matches"]) == 6

    resp = admin_client.post("/admin/api/import", data={
        "file": (io.BytesIO(json.dumps(export).encode()), "backup.json"),
        "names": ["E-Jugend Herbstcup 2026"],
    }, content_type="multipart/form-data", follow_redirects=True)
    assert "erfolgreich importiert".encode() in resp.data

    kopie = [t for t in Tournament.query.filter_by(
        name="E-Jugend Herbstcup 2026").all() if t.id != turnier.id][0]
    assert kopie.teams.count() == 4
    assert kopie.registrations.count() == 5
    assert kopie.referees.count() == 2
    assert kopie.events.count() == 6

    # Die Endplatzierung der Kopie ist dieselbe
    kopie_platzierung = client.get(
        f"/t/{kopie.slug}/api/platzierung").get_json()["platzierung"]
    assert [e["team_name"] for e in kopie_platzierung] == \
           [e["team_name"] for e in platzierung]


def test_turnier_ohne_finalrunde_komplett(app, client, admin_client):
    """Kurzer Durchlauf für die einfachste Variante: nur Gruppenphase."""
    admin_client.post("/admin/tournaments", data={
        "name": "F-Jugend Spielrunde", "event_date": "2026-11-15",
        "event_time": "10:00", "num_fields": "1", "hide_table": "1",
    }, follow_redirects=True)
    turnier = Tournament.query.filter_by(name="F-Jugend Spielrunde").one()
    slug = turnier.slug

    admin_client.post(f"/admin/t/{slug}/groups", data={"name": "Alle"},
                      follow_redirects=True)
    gruppe = turnier.groups.one()
    for name in ("Rot", "Blau", "Gelb"):
        admin_client.post(f"/admin/t/{slug}/teams",
                          data={"name": name, "group_id": gruppe.id},
                          follow_redirects=True)
    assert turnier.teams.count() == 3

    resp = admin_client.post(
        f"/admin/t/{slug}/api/matches/generate-round-robin",
        json={"felder": 1, "spielzeit_min": 8, "pause_min": 2})
    assert resp.get_json()["created"] == 3

    # Alle Spiele mit Ergebnis beenden
    for spiel in turnier.matches.all():
        admin_client.post(f"/admin/t/{slug}/api/matches/{spiel.id}/score",
                          json={"score_team1": 1, "score_team2": 0})
        admin_client.post(f"/admin/t/{slug}/api/matches/{spiel.id}/status",
                          json={"status": "finished"})

    admin_client.post(f"/admin/t/{slug}/api/phase/no-finals", json={})

    platzierung = client.get(f"/t/{slug}/api/platzierung").get_json()[
        "platzierung"]
    assert [e["platz"] for e in platzierung] == [1, 2, 3]
    assert all(e["quelle"] == "Gruppenphase" for e in platzierung)

    # Tabelle ist ausgeblendet, die Platzierung trotzdem abrufbar
    assert get_setting(turnier.id, "hide_table") == "1"
    assert client.get(f"/t/{slug}/").status_code == 200
