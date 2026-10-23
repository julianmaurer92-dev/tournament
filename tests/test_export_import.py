"""Tests fuer das JSON-Backup (Export/Import).

Das Backup ist die einzige Absicherung der echten Turnierdaten. Ein Export,
der Felder vergisst, faellt erst auf, wenn man ihn braucht.
"""
import io
import json

from app import db
from app.models import (
    Match, MenuItem, Team, TeamPayment, Tournament, get_all_settings,
    get_setting, set_setting,
)
from tests.conftest import (
    finish_match, make_group, make_match, make_team, make_tournament,
)


def _export(admin_client, tournament_ids, include_menu=False):
    ids = ",".join(str(i) for i in tournament_ids)
    url = f"/admin/api/export?ids={ids}"
    if include_menu:
        url += "&include_menu=1"
    resp = admin_client.get(url)
    assert resp.status_code == 200, resp.data[:300]
    return json.loads(resp.data)


def _import(admin_client, payload, names, include_menu=False):
    daten = {"file": (io.BytesIO(json.dumps(payload).encode()), "backup.json"),
             "names": names}
    if include_menu:
        daten["include_menu"] = "1"
    return admin_client.post("/admin/api/import", data=daten,
                             content_type="multipart/form-data",
                             follow_redirects=True)


# ──────────────────────────────────────
# Export
# ──────────────────────────────────────

def test_export_ohne_ids_ist_fehler(admin_client):
    assert admin_client.get("/admin/api/export").status_code == 400


def test_export_mit_kaputten_ids_ist_fehler(admin_client):
    assert admin_client.get("/admin/api/export?ids=abc").status_code == 400


def test_export_grundstruktur(admin_client, simple_tournament):
    t = simple_tournament["tournament"]
    data = _export(admin_client, [t.id])

    assert data["tournaments"][0]["name"] == "Simple Cup"
    assert len(data["tournaments"][0]["groups"]) == 1
    assert len(data["tournaments"][0]["teams"]) == 4
    assert len(data["tournaments"][0]["matches"]) == 6


def test_export_als_datei_mit_dateinamen(admin_client, simple_tournament):
    t = simple_tournament["tournament"]
    resp = admin_client.get(f"/admin/api/export?ids={t.id}")
    assert "attachment" in resp.headers["Content-Disposition"]
    assert "turnier-backup-" in resp.headers["Content-Disposition"]


def test_export_enthaelt_anstosszeit_des_turniers(app, admin_client):
    """event_time darf nicht verloren gehen."""
    t = make_tournament("Mit Uhrzeit")
    t.event_time = "09:30"
    db.session.commit()

    data = _export(admin_client, [t.id])
    assert data["tournaments"][0]["event_time"] == "09:30"


def test_export_enthaelt_spielfeld_und_neunmeter(app, admin_client):
    """field und is_penalty duerfen nicht verloren gehen."""
    t = make_tournament("Zwei Felder")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    make_match(t, a, b, gr, 1, field=2, is_penalty=True)

    m_data = _export(admin_client, [t.id])["tournaments"][0]["matches"][0]
    assert m_data["field"] == 2
    assert m_data["is_penalty"] is True


def test_export_enthaelt_startgebuehren(app, admin_client):
    """Bezahlte Startgebuehren sind Buchhaltung – sie muessen mit."""
    t = make_tournament("Mit Gebuehren")
    gr = make_group(t)
    team = make_team(t, "Zahler FC", gr)
    db.session.add(TeamPayment(team_id=team.id, paid=True, amount=25.0,
                               receipt_number="2026-001"))
    db.session.commit()

    team_data = _export(admin_client, [t.id])["tournaments"][0]["teams"][0]
    assert team_data["payment"]["paid"] is True
    assert team_data["payment"]["amount"] == 25.0
    assert team_data["payment"]["receipt_number"] == "2026-001"


def test_export_mit_speisekarte(admin_client, simple_tournament, menu_items):
    t = simple_tournament["tournament"]
    data = _export(admin_client, [t.id], include_menu=True)
    namen = [m["name"] for m in data["menu_items"]]
    assert "Bratwurst" in namen


# ──────────────────────────────────────
# Import
# ──────────────────────────────────────

def test_import_falsche_version_wird_abgelehnt(admin_client):
    resp = _import(admin_client, {"version": "99", "tournaments": []}, ["x"])
    assert "Ungueltiges Exportformat".encode() in resp.data


def test_import_ohne_datei(admin_client):
    resp = admin_client.post("/admin/api/import", data={},
                             content_type="multipart/form-data",
                             follow_redirects=True)
    assert "Keine Datei ausgewaehlt".encode() in resp.data


def test_import_kaputtes_json(admin_client):
    resp = admin_client.post("/admin/api/import", data={
        "file": (io.BytesIO(b"{kein json"), "x.json"), "names": ["x"],
    }, content_type="multipart/form-data", follow_redirects=True)
    assert "Ungueltige JSON-Datei".encode() in resp.data


def test_import_ohne_auswahl(admin_client, simple_tournament):
    payload = _export(admin_client, [simple_tournament["tournament"].id])
    resp = _import(admin_client, payload, [])
    assert "Keine Turniere ausgewaehlt".encode() in resp.data


def test_roundtrip_erhaelt_alles(app, admin_client):
    """Export -> Import muss ein identisches Turnier erzeugen."""
    t = make_tournament("Rundreise Cup")
    t.event_time = "14:15"
    db.session.commit()
    set_setting(t.id, "num_fields", "2")
    set_setting(t.id, "tournament_rules", "Spielzeit 10 Minuten")

    g1 = make_group(t, "Gruppe A", 0)
    g2 = make_group(t, "Gruppe B", 1)
    a1 = make_team(t, "A1", g1)
    a2 = make_team(t, "A2", g1)
    b1 = make_team(t, "B1", g2)
    b2 = make_team(t, "B2", g2)
    db.session.add(TeamPayment(team_id=a1.id, paid=True, amount=30.0,
                               receipt_number="R-7"))
    db.session.commit()

    finish_match(make_match(t, a1, a2, g1, 1, field=1), 3, 1)
    finish_match(make_match(t, b1, b2, g2, 2, field=2), 0, 0)
    # Finalspiel mit Weiterleitung
    halb = make_match(t, a1, b1, None, 3, field=1, is_final=True,
                      final_round=2, final_position=0,
                      final_label="Halbfinale 1")
    finale = make_match(t, None, None, None, 4, field=1, is_final=True,
                        final_round=1, final_position=0, final_label="Finale")
    halb.next_match_id = finale.id
    halb.next_match_slot = 1
    db.session.commit()

    payload = _export(admin_client, [t.id])
    resp = _import(admin_client, payload, ["Rundreise Cup"])
    assert "erfolgreich importiert".encode() in resp.data

    kopien = Tournament.query.filter_by(name="Rundreise Cup").all()
    assert len(kopien) == 2
    neu = [k for k in kopien if k.id != t.id][0]

    assert neu.slug != t.slug, "Slug muss eindeutig bleiben"
    assert neu.event_time == "14:15"
    assert get_setting(neu.id, "num_fields") == "2"
    assert get_setting(neu.id, "tournament_rules") == "Spielzeit 10 Minuten"

    assert neu.groups.count() == 2
    assert neu.teams.count() == 4
    assert neu.matches.count() == 4

    # Spielfelder erhalten
    felder = sorted(m.field for m in neu.matches.filter_by(is_final=False))
    assert felder == [1, 2]

    # Startgebuehr erhalten
    neu_a1 = Team.query.filter_by(tournament_id=neu.id, name="A1").first()
    assert neu_a1.payment is not None
    assert neu_a1.payment.paid is True
    assert neu_a1.payment.amount == 30.0
    assert neu_a1.payment.receipt_number == "R-7"

    # Finalbaum erhalten
    neu_halb = neu.matches.filter_by(final_label="Halbfinale 1").first()
    neu_finale = neu.matches.filter_by(final_label="Finale").first()
    assert neu_halb.next_match_id == neu_finale.id
    assert neu_halb.next_match_slot == 1


def test_alter_export_ohne_neue_felder_bleibt_importierbar(app, admin_client):
    """Rueckwaertskompatibilitaet: Backups von v1 muessen weiter laufen."""
    alt = {
        "version": "1",
        "exported_at": "2026-01-01T00:00:00",
        "tournaments": [{
            "name": "Altes Backup",
            "slug": "altes-backup",
            "description": "aus Version 1",
            "event_date": "2026-05-01",
            "is_active": True,
            "display_order": 1,
            "settings": {"tournament_name": "ALTES BACKUP"},
            "groups": [{"name": "Gruppe A", "display_order": 0}],
            "teams": [
                {"name": "Alt FC", "logo_url": "", "players": "",
                 "group_name": "Gruppe A"},
                {"name": "Neu FC", "logo_url": "", "players": "",
                 "group_name": "Gruppe A"},
            ],
            "matches": [{
                "_index": 0, "team1_name": "Alt FC", "team2_name": "Neu FC",
                "group_name": "Gruppe A", "score_team1": 2, "score_team2": 1,
                "status": "finished", "scheduled_time": None,
                "match_order": 1, "timer_duration": 600,
                "timer_remaining": 0, "is_extra_time": False,
                "is_final": False, "final_round": None,
                "final_position": None, "final_label": None,
                "next_match_index": None, "next_match_slot": None,
                "loser_next_match_index": None, "loser_next_match_slot": None,
                "is_loser_match": False,
            }],
        }],
    }
    resp = _import(admin_client, alt, ["Altes Backup"])
    assert "erfolgreich importiert".encode() in resp.data

    t = Tournament.query.filter_by(name="Altes Backup").first()
    assert t is not None
    assert t.event_time is None
    m = t.matches.first()
    assert m.field == 1, "fehlendes field muss auf 1 zurueckfallen"
    assert m.is_penalty is False
    assert t.teams.count() == 2


def test_import_speisekarte_ueberspringt_doppelte(admin_client, menu_items):
    payload = {
        "version": "1", "tournaments": [],
        "menu_items": [
            {"name": "Bratwurst", "price": "9,99", "category": "speise"},
            {"name": "Pizzabroetchen", "price": "3,50", "category": "speise"},
        ],
    }
    resp = _import(admin_client, payload, ["dummy"], include_menu=True)
    assert MenuItem.query.filter_by(name="Pizzabroetchen").count() == 1
    assert MenuItem.query.filter_by(name="Bratwurst").count() == 1, \
        "Bratwurst darf nicht doppelt angelegt werden"
    assert MenuItem.query.filter_by(name="Bratwurst").first().price == "3,00", \
        "bestehender Preis darf nicht ueberschrieben werden"


# ──────────────────────────────────────
# Neue Daten im Backup: Anmeldungen und Spielereignisse
# ──────────────────────────────────────

def test_export_enthaelt_spielereignisse(app, admin_client):
    from app.models import MatchEvent
    t = make_tournament("Ereignis Backup Cup")
    gr = make_group(t)
    a = make_team(t, "Alpha", gr)
    b = make_team(t, "Bravo", gr)
    m = make_match(t, a, b, gr, 1)
    db.session.add_all([
        MatchEvent(match_id=m.id, tournament_id=t.id, team_id=a.id,
                   art="tor", player_name="Lena Klein", minute=7),
        MatchEvent(match_id=m.id, tournament_id=t.id, team_id=b.id,
                   art="gelb", player_name="Tim Kurz", minute=12),
    ])
    db.session.commit()

    m_data = _export(admin_client, [t.id])["tournaments"][0]["matches"][0]
    arten = {e["art"]: e for e in m_data["events"]}
    assert arten["tor"]["player_name"] == "Lena Klein"
    assert arten["tor"]["team_name"] == "Alpha"
    assert arten["tor"]["minute"] == 7
    assert arten["gelb"]["team_name"] == "Bravo"


def test_export_enthaelt_anmeldungen(app, admin_client):
    from app.models import Registration
    t = make_tournament("Anmelde Backup Cup")
    gr = make_group(t)
    team = make_team(t, "Alpha", gr)
    db.session.add(Registration(
        tournament_id=t.id, club_name="SV Winkel", team_name="Alpha",
        contact_name="Maria", contact_email="maria@sv.de",
        contact_phone="0171", player_count=12, notes="Zwei Busse",
        status="bestaetigt", token="tok-export", team_id=team.id,
        decision_note="passt",
    ))
    db.session.commit()

    r_data = _export(admin_client, [t.id])["tournaments"][0]["registrations"][0]
    assert r_data["club_name"] == "SV Winkel"
    assert r_data["contact_email"] == "maria@sv.de"
    assert r_data["player_count"] == 12
    assert r_data["status"] == "bestaetigt"
    assert r_data["team_name_ref"] == "Alpha"
    assert r_data["decision_note"] == "passt"


def test_roundtrip_mit_ereignissen_und_anmeldungen(app, admin_client):
    from app.models import MatchEvent, Registration
    t = make_tournament("Voller Roundtrip Cup")
    gr = make_group(t)
    a = make_team(t, "Alpha", gr)
    b = make_team(t, "Bravo", gr)
    m = finish_match(make_match(t, a, b, gr, 1), 2, 1)
    db.session.add_all([
        MatchEvent(match_id=m.id, tournament_id=t.id, team_id=a.id,
                   art="tor", player_name="Lena Klein", minute=3),
        MatchEvent(match_id=m.id, tournament_id=t.id, team_id=a.id,
                   art="tor", player_name="Lena Klein", minute=8),
        MatchEvent(match_id=m.id, tournament_id=t.id, team_id=b.id,
                   art="tor", player_name="Tim Kurz", minute=15),
        MatchEvent(match_id=m.id, tournament_id=t.id, team_id=b.id,
                   art="rot", player_name="Jan Lang", minute=19),
    ])
    db.session.add(Registration(
        tournament_id=t.id, club_name="SV Winkel", team_name="Alpha",
        contact_name="Maria", contact_email="maria@sv.de",
        status="bestaetigt", token="tok-rt", team_id=a.id,
    ))
    db.session.commit()

    payload = _export(admin_client, [t.id])
    resp = _import(admin_client, payload, ["Voller Roundtrip Cup"])
    assert "erfolgreich importiert".encode() in resp.data

    neu = [k for k in Tournament.query.filter_by(name="Voller Roundtrip Cup").all()
           if k.id != t.id][0]

    # Ereignisse
    assert neu.events.count() == 4
    neu_m = neu.matches.first()
    tore = [e for e in neu_m.events if e.art == "tor"]
    assert len(tore) == 3
    lena = [e for e in tore if e.player_name == "Lena Klein"]
    assert len(lena) == 2
    assert {e.minute for e in lena} == {3, 8}
    neu_alpha = Team.query.filter_by(tournament_id=neu.id, name="Alpha").first()
    assert all(e.team_id == neu_alpha.id for e in lena), \
        "Ereignis muss am Team der Kopie haengen, nicht am Original"

    # Torschuetzenliste der Kopie stimmt
    from app.ereignisse import turnier_statistik
    statistik = turnier_statistik(neu.id)
    assert statistik["torschuetzen"][0]["player_name"] == "Lena Klein"
    assert statistik["torschuetzen"][0]["tore"] == 2

    # Anmeldung
    neu_anmeldung = neu.registrations.one()
    assert neu_anmeldung.club_name == "SV Winkel"
    assert neu_anmeldung.status == "bestaetigt"
    assert neu_anmeldung.team_id == neu_alpha.id
    assert neu_anmeldung.token != "tok-rt", \
        "Token darf nicht doppelt vergeben werden"


def test_import_ignoriert_unbekannte_ereignisart(app, admin_client):
    payload = {
        "version": "2", "tournaments": [{
            "name": "Kaputt Cup", "slug": "kaputt-cup",
            "settings": {}, "groups": [{"name": "A", "display_order": 0}],
            "teams": [{"name": "T1", "group_name": "A"},
                      {"name": "T2", "group_name": "A"}],
            "matches": [{
                "_index": 0, "team1_name": "T1", "team2_name": "T2",
                "group_name": "A", "status": "finished",
                "score_team1": 1, "score_team2": 0, "match_order": 1,
                "events": [
                    {"art": "elfmeter", "team_name": "T1", "player_name": "X"},
                    {"art": "tor", "team_name": "T1", "player_name": "Echt"},
                ],
            }],
        }],
    }
    resp = _import(admin_client, payload, ["Kaputt Cup"])
    assert "erfolgreich importiert".encode() in resp.data
    t = Tournament.query.filter_by(name="Kaputt Cup").first()
    assert t.events.count() == 1
    assert t.events.first().player_name == "Echt"


def test_import_ohne_registrations_schluessel(app, admin_client):
    """Backups der Version 1 haben keine Anmeldungen – darf nicht scheitern."""
    payload = {
        "version": "1", "tournaments": [{
            "name": "Alt ohne Anmeldungen", "slug": "alt-ohne",
            "settings": {}, "groups": [], "teams": [], "matches": [],
        }],
    }
    resp = _import(admin_client, payload, ["Alt ohne Anmeldungen"])
    assert "erfolgreich importiert".encode() in resp.data
    t = Tournament.query.filter_by(name="Alt ohne Anmeldungen").first()
    assert t.registrations.count() == 0
