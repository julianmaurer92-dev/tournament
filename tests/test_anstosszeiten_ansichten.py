"""Anstosszeiten muessen in den oeffentlichen Ansichten ankommen.

Die Darstellung passiert im Browser, deshalb pruefen diese Tests, dass
(a) die Daten im Zustand stehen und (b) die Ansichten den Code dafuer
mitbringen. Das ist die Grenze, die ohne Browser pruefbar ist.
"""
from datetime import datetime

from app.models import set_setting
from tests.conftest import make_group, make_match, make_team, make_tournament


def _turnier_mit_zeiten():
    t = make_tournament("Zeiten Cup")
    gr = make_group(t)
    a = make_team(t, "Alpha", gr)
    b = make_team(t, "Bravo", gr)
    c = make_team(t, "Charlie", gr)
    d = make_team(t, "Delta", gr)
    make_match(t, a, b, gr, 1, scheduled_time=datetime(2026, 11, 14, 9, 0),
               field=1)
    make_match(t, c, d, gr, 2, scheduled_time=datetime(2026, 11, 14, 9, 0),
               field=2)
    return t


def test_api_state_liefert_anstosszeit_und_feld(client, app):
    t = _turnier_mit_zeiten()
    daten = client.get(f"/t/{t.slug}/api/state").get_json()
    kommende = daten["upcoming_matches"]
    assert len(kommende) == 2
    assert all(m["scheduled_time"] for m in kommende)
    assert kommende[0]["scheduled_time"].startswith("2026-11-14T09:00")
    assert sorted(m["field"] for m in kommende) == [1, 2]
    assert daten["settings"]["num_fields"] in ("1", "2")


def test_api_state_liefert_schiedsrichter(client, app):
    from app import db
    from app.models import Match, Referee
    t = _turnier_mit_zeiten()
    schiri = Referee(tournament_id=t.id, name="Hans Meier")
    db.session.add(schiri)
    db.session.commit()
    spiel = Match.query.filter_by(tournament_id=t.id).first()
    spiel.referee_id = schiri.id
    db.session.commit()

    daten = client.get(f"/t/{t.slug}/api/state").get_json()
    namen = {m["referee_name"] for m in daten["upcoming_matches"]}
    assert "Hans Meier" in namen


def test_live_ansicht_bringt_zeitdarstellung_mit(client, app):
    t = _turnier_mit_zeiten()
    resp = client.get(f"/t/{t.slug}/")
    assert resp.status_code == 200
    # main.js wird geladen und enthaelt die Zeitfunktion
    assert b"js/main.js" in resp.data
    js = client.get("/static/js/main.js").data.decode()
    assert "function matchTime" in js
    assert "scheduled_time" in js
    assert "match-meta" in js


def test_handyansicht_bringt_zeitdarstellung_mit(client, app):
    t = _turnier_mit_zeiten()
    text = client.get(f"/t/{t.slug}/phone/").data.decode()
    assert "phMatchTime" in text
    assert "phZeitBadge" in text
    assert "scheduled_time" in text


def test_tv_ansicht_bringt_zeitdarstellung_mit(client, app):
    t = _turnier_mit_zeiten()
    text = client.get(f"/t/{t.slug}/tv/").data.decode()
    assert "scheduled_time" in text
    assert "Uhr" in text


def test_zeitformat_ohne_zeitzonenverschiebung(client, app):
    """Der Server liefert lokale Turnierzeit ohne Zeitzone.

    Wird daraus im Browser ein Date-Objekt gebaut, verschiebt sich die
    Uhrzeit je nach Geraeteeinstellung. Deshalb darf im Zustand kein "Z"
    und kein Offset stehen – und die Ansichten duerfen die Zeit nur per
    Textauswertung lesen.
    """
    t = _turnier_mit_zeiten()
    daten = client.get(f"/t/{t.slug}/api/state").get_json()
    zeit = daten["upcoming_matches"][0]["scheduled_time"]
    assert zeit.endswith("09:00:00"), zeit
    assert "Z" not in zeit and "+" not in zeit

    js = client.get("/static/js/main.js").data.decode()
    # Der Zeit-Helfer darf kein new Date() verwenden
    anfang = js.index("function matchTime")
    ende = js.index("}", js.index("return treffer", anfang))
    assert "new Date" not in js[anfang:ende]


def test_css_fuer_die_zeitzeile_vorhanden(client, app):
    css = client.get("/static/css/style.css").data.decode()
    assert ".match-meta" in css


def test_spiele_ohne_zeit_brechen_die_ansicht_nicht(client, app):
    t = make_tournament("Ohne Zeit Cup")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    make_match(t, a, b, gr, 1)

    daten = client.get(f"/t/{t.slug}/api/state").get_json()
    assert daten["upcoming_matches"][0]["scheduled_time"] is None
    for pfad in (f"/t/{t.slug}/", f"/t/{t.slug}/phone/", f"/t/{t.slug}/tv/"):
        assert client.get(pfad).status_code == 200, pfad
