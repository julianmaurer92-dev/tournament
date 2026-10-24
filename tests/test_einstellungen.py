"""Einstellungen bleiben stehen, wo man sie hingestellt hat.

Hintergrund: Die Route zum Bearbeiten der Turnierdaten las bei jedem
Speichern auch "hide_table" und "hide_scores" aus dem Formular. Das
Formular "Turnierverwaltung" enthaelt diese Haken aber gar nicht – also
kam jedes Mal "nicht angehakt" heraus. Wer die Tabelle ausgeblendet
hatte und danach das Spieldatum korrigierte, hatte die Tabelle wieder
oeffentlich im Netz, ohne es zu merken.
"""
from app.models import get_setting, set_setting
from tests.conftest import make_tournament


def test_turnierdaten_speichern_laesst_anzeige_in_ruhe(app, admin_client):
    t = make_tournament(name="Formularturnier")
    set_setting(t.id, "hide_table", "1")
    set_setting(t.id, "hide_scores", "1")

    antwort = admin_client.post(
        f"/admin/tournaments/{t.id}/edit?next=admin",
        data={"name": t.name, "event_date": "", "event_time": "",
              "description": "Nur die Beschreibung geaendert", "final_mode": ""},
        follow_redirects=True)
    assert antwort.status_code == 200

    assert get_setting(t.id, "hide_table") == "1"
    assert get_setting(t.id, "hide_scores") == "1"


def test_formular_darf_die_haken_weiterhin_setzen(app, admin_client):
    """Schickt ein Formular die Haken mit, zaehlen sie natuerlich."""
    t = make_tournament(name="Hakenturnier")
    set_setting(t.id, "hide_table", "0")

    admin_client.post(
        f"/admin/tournaments/{t.id}/edit?next=admin",
        data={"name": t.name, "event_date": "", "event_time": "",
              "description": "", "final_mode": "", "hide_table": "1"},
        follow_redirects=True)
    assert get_setting(t.id, "hide_table") == "1"

    admin_client.post(
        f"/admin/tournaments/{t.id}/edit?next=admin",
        data={"name": t.name, "event_date": "", "event_time": "",
              "description": "", "final_mode": "", "hide_table": "0"},
        follow_redirects=True)
    assert get_setting(t.id, "hide_table") == "0"


def test_spielfelder_ueber_die_einstellungen(app, admin_client):
    """Spielfelder werden jetzt sofort gespeichert statt per Formular."""
    t = make_tournament(name="Feldturnier")
    antwort = admin_client.post(
        f"/admin/t/{t.slug}/api/settings",
        json={"num_fields": "3"})
    assert antwort.status_code == 200
    assert get_setting(t.id, "num_fields") == "3"


def test_unsinnige_feldzahl_wird_abgelehnt(app, admin_client):
    t = make_tournament(name="Feldturnier zwei")
    set_setting(t.id, "num_fields", "2")
    admin_client.post(f"/admin/t/{t.slug}/api/settings",
                      json={"num_fields": "99"})
    assert get_setting(t.id, "num_fields") == "2"


def test_einstellungen_stehen_nur_an_einer_stelle(app, admin_client):
    """Die Anzeige-Haken duerfen nicht zweimal bedienbar sein.

    Vorher gab es sie sowohl auf der Spielplanseite als auch in der
    Design-Ansicht. Zwei Schalter fuer dieselbe Sache laufen frueher
    oder spaeter auseinander.
    """
    t = make_tournament(name="Doppelturnier")
    design = admin_client.get(f"/admin/t/{t.slug}/design").get_data(as_text=True)
    assert 'data-einstellung="hide_table"' not in design
    assert 'data-einstellung="hide_scores"' not in design
    # Stattdessen ein Verweis auf die eine Stelle
    assert "#einstellungen" in design

    plan = admin_client.get(
        f"/admin/t/{t.slug}/administration").get_data(as_text=True)
    assert plan.count('id="cfg-hide-table"') == 1
    assert plan.count('id="cfg-num-fields"') == 1
    # Die Spielfelder duerfen nicht mehr im Speichern-Formular stehen
    assert 'name="num_fields"' not in plan
