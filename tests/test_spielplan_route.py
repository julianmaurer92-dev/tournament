"""Tests fuer den Spielplan-Generator als Route (mit Datenbank)."""
from datetime import date, datetime

from app import db
from app.models import Match, Team, get_setting, set_setting
from tests.conftest import make_group, make_match, make_team, make_tournament


def _turnier_mit_teams(name="Plan Cup", gruppen=2, pro_gruppe=4,
                       datum=date(2026, 11, 14), uhrzeit="09:00"):
    t = make_tournament(name, event_date=datum)
    t.event_time = uhrzeit
    db.session.commit()
    buchstaben = "ABCDEF"
    nummer = 0
    for i in range(gruppen):
        gr = make_group(t, f"Gruppe {buchstaben[i]}", i)
        for _ in range(pro_gruppe):
            nummer += 1
            make_team(t, f"Team {nummer}", gr)
    return t


def _generieren(admin_client, t, **optionen):
    return admin_client.post(
        f"/admin/t/{t.slug}/api/matches/generate-round-robin", json=optionen)


def test_generator_legt_spiele_mit_anstosszeiten_an(app, admin_client):
    t = _turnier_mit_teams()
    set_setting(t.id, "num_fields", "2")

    resp = _generieren(admin_client, t, spielzeit_min=10, pause_min=5)
    assert resp.status_code == 200
    daten = resp.get_json()
    assert daten["created"] == 12       # 2 Gruppen x 6 Paarungen
    assert daten["beginn"] == "14.11.2026 09:00"

    spiele = Match.query.filter_by(tournament_id=t.id).all()
    assert all(m.scheduled_time is not None for m in spiele), \
        "Jedes Spiel braucht eine Anstosszeit"
    assert min(m.scheduled_time for m in spiele) == datetime(2026, 11, 14, 9, 0)


def test_generator_vermeidet_doppelbelegung(app, admin_client):
    """Der Kern der Verbesserung: niemand spielt zweimal gleichzeitig."""
    t = _turnier_mit_teams(gruppen=2, pro_gruppe=4)
    _generieren(admin_client, t, felder=2)

    nach_zeit = {}
    for m in Match.query.filter_by(tournament_id=t.id).all():
        nach_zeit.setdefault(m.scheduled_time, []).append(m)

    for zeit, gleichzeitig in nach_zeit.items():
        teams = []
        felder = []
        for m in gleichzeitig:
            teams += [m.team1_id, m.team2_id]
            felder.append(m.field)
        assert len(teams) == len(set(teams)), f"Team doppelt um {zeit}"
        assert len(felder) == len(set(felder)), f"Feld doppelt um {zeit}"


def test_generator_verteilt_auf_vier_felder(app, admin_client):
    t = _turnier_mit_teams(gruppen=4, pro_gruppe=4)
    resp = _generieren(admin_client, t, felder=4, spielzeit_min=8, pause_min=2)
    assert resp.status_code == 200
    assert resp.get_json()["felder"] == 4

    felder = {m.field for m in Match.query.filter_by(tournament_id=t.id)}
    assert felder == {1, 2, 3, 4}
    # Einstellung wird mitgezogen, sonst blendet die Oberflaeche Felder aus
    assert get_setting(t.id, "num_fields") == "4"


def test_generator_begrenzt_felder_auf_sechs(app, admin_client):
    t = _turnier_mit_teams(gruppen=2, pro_gruppe=4)
    resp = _generieren(admin_client, t, felder=99)
    assert resp.get_json()["felder"] == 6


def test_generator_mit_eigener_startzeit(app, admin_client):
    t = _turnier_mit_teams(uhrzeit="09:00")
    _generieren(admin_client, t, startdatum="2026-12-01", startzeit="13:30",
                felder=2, spielzeit_min=12, pause_min=3)

    erstes = Match.query.filter_by(tournament_id=t.id).order_by(
        Match.scheduled_time).first()
    assert erstes.scheduled_time == datetime(2026, 12, 1, 13, 30)


def test_generator_lehnt_kaputte_startzeit_ab(app, admin_client):
    t = _turnier_mit_teams()
    resp = _generieren(admin_client, t, startzeit="viertel nach drei")
    assert resp.status_code == 400
    assert "nicht lesbar" in resp.get_json()["error"]
    assert Match.query.count() == 0


def test_generator_mit_mittagspause(app, admin_client):
    t = _turnier_mit_teams(gruppen=2, pro_gruppe=4)
    _generieren(admin_client, t, felder=2, spielzeit_min=10, pause_min=5,
                lange_pause_nach=3, lange_pause_min=45)

    zeiten = sorted({m.scheduled_time for m in
                     Match.query.filter_by(tournament_id=t.id)})
    # Slots 1-3 im 15-Minuten-Takt, danach 45 Minuten extra
    assert [z.strftime("%H:%M") for z in zeiten[:5]] == \
           ["09:00", "09:15", "09:30", "10:30", "10:45"]


def test_generator_erzeugt_keine_doppelten_paarungen(app, admin_client):
    t = _turnier_mit_teams(gruppen=1, pro_gruppe=4)
    _generieren(admin_client, t, felder=1)
    anzahl = Match.query.filter_by(tournament_id=t.id).count()

    # Zweiter Aufruf darf nichts hinzufuegen
    resp = _generieren(admin_client, t, felder=1)
    assert resp.get_json()["created"] == 0
    assert "schon angesetzt" in resp.get_json()["hinweis"]
    assert Match.query.filter_by(tournament_id=t.id).count() == anzahl


def test_generator_schliesst_an_bestehenden_plan_an(app, admin_client):
    t = _turnier_mit_teams(gruppen=1, pro_gruppe=4)
    gruppe = t.groups.first()
    teams = t.teams.all()
    # Ein Spiel steht schon um 09:00
    make_match(t, teams[0], teams[1], gruppe, 1,
               scheduled_time=datetime(2026, 11, 14, 9, 0), field=1)

    _generieren(admin_client, t, felder=1, spielzeit_min=10, pause_min=5)

    zeiten = sorted(m.scheduled_time for m in
                    Match.query.filter_by(tournament_id=t.id))
    assert zeiten[0] == datetime(2026, 11, 14, 9, 0)
    assert zeiten[1] == datetime(2026, 11, 14, 9, 15), \
        "Neue Spiele muessen hinter dem bestehenden Plan anfangen"


def test_generator_kann_alles_neu_machen(app, admin_client):
    t = _turnier_mit_teams(gruppen=1, pro_gruppe=4)
    _generieren(admin_client, t, felder=1)
    alt = Match.query.filter_by(tournament_id=t.id).count()

    resp = _generieren(admin_client, t, felder=2, vorhandene_loeschen=True,
                       startzeit="10:00")
    daten = resp.get_json()
    assert daten["deleted"] == alt
    assert daten["created"] == 6
    assert Match.query.filter_by(tournament_id=t.id).count() == 6
    erstes = Match.query.order_by(Match.scheduled_time).first()
    assert erstes.scheduled_time.strftime("%H:%M") == "10:00"


def test_generator_spielzeit_landet_im_timer(app, admin_client):
    t = _turnier_mit_teams(gruppen=1, pro_gruppe=3)
    _generieren(admin_client, t, spielzeit_min=12)
    for m in Match.query.filter_by(tournament_id=t.id):
        assert m.timer_duration == 12 * 60
        assert m.timer_remaining == 12 * 60


def test_generator_nutzt_turnier_spielzeit_als_standard(app, admin_client):
    t = _turnier_mit_teams(gruppen=1, pro_gruppe=3)
    set_setting(t.id, "default_timer_regular", "900")   # 15 Minuten
    _generieren(admin_client, t)
    assert Match.query.first().timer_duration == 900


def test_generator_ohne_gruppen_ist_fehler(app, admin_client):
    t = make_tournament("Ohne Gruppen")
    resp = _generieren(admin_client, t)
    assert resp.status_code == 400
    assert "Keine Gruppen" in resp.get_json()["error"]


def test_generator_ueberspringt_gruppen_mit_einem_team(app, admin_client):
    t = make_tournament("Schief Cup", event_date=date(2026, 11, 14))
    g1 = make_group(t, "Gruppe A", 0)
    g2 = make_group(t, "Gruppe B", 1)
    make_team(t, "A1", g1)
    make_team(t, "A2", g1)
    make_team(t, "B1", g2)       # allein

    resp = _generieren(admin_client, t)
    assert resp.get_json()["created"] == 1


def test_generator_nur_in_gruppenphase(app, admin_client):
    t = _turnier_mit_teams()
    set_setting(t.id, "tournament_phase", "FINALS")
    resp = _generieren(admin_client, t)
    assert resp.status_code == 400
    assert "Gruppenphase" in resp.get_json()["error"]


def test_generator_braucht_editor_rechte(app, viewer_client, admin_client):
    from app.models import Admin, UserTournamentAccess
    t = _turnier_mit_teams()
    viewer = Admin.query.filter_by(username="viewer1").first()
    db.session.add(UserTournamentAccess(user_id=viewer.id, tournament_id=t.id))
    db.session.commit()

    resp = viewer_client.post(
        f"/admin/t/{t.slug}/api/matches/generate-round-robin", json={})
    assert resp.status_code == 403


# ──────────────────────────────────────
# Konfliktpruefung
# ──────────────────────────────────────

def test_konfliktpruefung_sauberer_plan(app, admin_client):
    t = _turnier_mit_teams(gruppen=2, pro_gruppe=4)
    _generieren(admin_client, t, felder=2)

    resp = admin_client.get(f"/admin/t/{t.slug}/api/matches/konflikte")
    assert resp.status_code == 200
    assert resp.get_json() == {"konflikte": [], "anzahl": 0}


def test_konfliktpruefung_findet_doppelbelegung(app, admin_client):
    t = _turnier_mit_teams(gruppen=1, pro_gruppe=4)
    gruppe = t.groups.first()
    teams = t.teams.all()
    neun = datetime(2026, 11, 14, 9, 0)
    make_match(t, teams[0], teams[1], gruppe, 1, scheduled_time=neun, field=1)
    make_match(t, teams[0], teams[2], gruppe, 2, scheduled_time=neun, field=2)

    daten = admin_client.get(
        f"/admin/t/{t.slug}/api/matches/konflikte").get_json()
    assert daten["anzahl"] >= 1
    assert any("gleichzeitig" in k for k in daten["konflikte"])


def test_konfliktpruefung_meldet_doppeltes_feld(app, admin_client):
    t = _turnier_mit_teams(gruppen=1, pro_gruppe=4)
    gruppe = t.groups.first()
    teams = t.teams.all()
    neun = datetime(2026, 11, 14, 9, 0)
    make_match(t, teams[0], teams[1], gruppe, 1, scheduled_time=neun, field=1)
    make_match(t, teams[2], teams[3], gruppe, 2, scheduled_time=neun, field=1)

    daten = admin_client.get(
        f"/admin/t/{t.slug}/api/matches/konflikte").get_json()
    assert any("Feld 1" in k for k in daten["konflikte"])


# ──────────────────────────────────────
# Mehr als zwei Spielfelder
# ──────────────────────────────────────

def test_einstellung_erlaubt_bis_sechs_felder(app, admin_client):
    t = make_tournament("Felder Cup")
    for anzahl in ("1", "2", "3", "4", "5", "6"):
        resp = admin_client.post(f"/admin/t/{t.slug}/api/settings",
                                 json={"num_fields": anzahl})
        assert resp.status_code == 200, f"{anzahl} Felder wurden abgelehnt"
        assert get_setting(t.id, "num_fields") == anzahl


def test_einstellung_lehnt_sieben_felder_ab(app, admin_client):
    t = make_tournament("Felder Cup")
    resp = admin_client.post(f"/admin/t/{t.slug}/api/settings",
                             json={"num_fields": "7"})
    assert resp.status_code == 400


def test_turnier_anlegen_mit_drei_feldern(app, admin_client):
    resp = admin_client.post("/admin/tournaments", data={
        "name": "Drei Felder Cup", "num_fields": "3",
    }, follow_redirects=True)
    assert resp.status_code == 200
    from app.models import Tournament
    t = Tournament.query.filter_by(name="Drei Felder Cup").first()
    assert get_setting(t.id, "num_fields") == "3"


def test_dashboard_zeigt_feldspalte_bei_drei_feldern(app, admin_client):
    t = _turnier_mit_teams(gruppen=2, pro_gruppe=4)
    set_setting(t.id, "num_fields", "3")
    _generieren(admin_client, t, felder=3)

    resp = admin_client.get(f"/admin/t/{t.slug}/")
    assert resp.status_code == 200
    assert b"Feld" in resp.data, \
        "Bei mehreren Feldern muss die Feldspalte sichtbar sein"
