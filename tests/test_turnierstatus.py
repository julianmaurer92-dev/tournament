"""Tests fuer den Wegweiser "Naechster Schritt" (reine Logik)."""
import pytest

from app.turnierstatus import SCHRITTE, fortschritt, naechster_schritt


def zahlen(**felder):
    """Vollstaendiger Zustand mit sinnvollen Vorgaben."""
    standard = {
        "phase": "GROUP_STAGE",
        "gruppen": 2, "teams": 8, "teams_ohne_gruppe": 0,
        "gruppen_mit_zu_wenig_teams": 0,
        "gruppenspiele": 12, "gruppenspiele_offen": 0,
        "spiele_ohne_zeit": 0, "konflikte": 0,
        "schiedsrichter": 0, "spiele_ohne_schiedsrichter": 0,
        "finalspiele": 0, "finalspiele_offen": 0,
    }
    standard.update(felder)
    return standard


# ──────────────────────────────────────
# Reihenfolge in der Gruppenphase
# ──────────────────────────────────────

def test_leeres_turnier_will_gruppen():
    s = naechster_schritt(zahlen(gruppen=0, teams=0, gruppenspiele=0))
    assert s["schluessel"] == "gruppen"
    assert "Gruppen anlegen" in s["ueberschrift"]


def test_gruppen_ohne_teams():
    s = naechster_schritt(zahlen(teams=0, gruppenspiele=0))
    assert s["schluessel"] == "teams"
    assert s["ziel"] == "anmeldungen", \
        "soll auf die Vereinsanmeldung verweisen, nicht nur aufs Formular"


def test_gruppe_mit_nur_einem_team():
    s = naechster_schritt(zahlen(gruppen_mit_zu_wenig_teams=1,
                                 gruppenspiele=0))
    assert s["schluessel"] == "teams_pro_gruppe"


def test_teams_aber_kein_spielplan():
    s = naechster_schritt(zahlen(gruppenspiele=0))
    assert s["schluessel"] == "spielplan"


def test_konflikte_haben_vorrang_vor_zeiten():
    s = naechster_schritt(zahlen(konflikte=2, spiele_ohne_zeit=5,
                                 gruppenspiele_offen=12))
    assert s["schluessel"] == "konflikte"


def test_fehlende_anstosszeiten():
    s = naechster_schritt(zahlen(spiele_ohne_zeit=3, gruppenspiele_offen=12))
    assert s["schluessel"] == "anstosszeiten"


def test_schiedsrichter_nur_wenn_welche_angelegt_sind():
    """Wer keine Schiedsrichter fuehrt, soll nicht dauernd erinnert werden."""
    ohne = naechster_schritt(zahlen(schiedsrichter=0,
                                    spiele_ohne_schiedsrichter=12,
                                    gruppenspiele_offen=12))
    assert ohne["schluessel"] == "spiele_austragen"

    mit = naechster_schritt(zahlen(schiedsrichter=3,
                                   spiele_ohne_schiedsrichter=4,
                                   gruppenspiele_offen=12))
    assert mit["schluessel"] == "schiedsrichter"


def test_alles_bereit_heisst_spielen():
    s = naechster_schritt(zahlen(gruppenspiele_offen=12))
    assert s["schluessel"] == "spiele_austragen"
    assert s["ziel"] == "steuerung"


def test_alle_gruppenspiele_durch():
    s = naechster_schritt(zahlen(gruppenspiele_offen=0))
    assert s["schluessel"] == "gruppenphase_beenden"


# ──────────────────────────────────────
# Spaetere Phasen
# ──────────────────────────────────────

def test_final_setup():
    s = naechster_schritt(zahlen(phase="FINAL_SETUP"))
    assert s["schluessel"] == "finalrunde"
    assert s["ziel"] == "finals"


def test_finalrunde_laeuft():
    s = naechster_schritt(zahlen(phase="FINAL_ROUND", finalspiele=4,
                                 finalspiele_offen=2))
    assert s["schluessel"] == "finalspiele"


def test_finalrunde_durch():
    s = naechster_schritt(zahlen(phase="FINAL_ROUND", finalspiele=4,
                                 finalspiele_offen=0))
    assert s["schluessel"] == "turnier_beenden"


def test_turnier_beendet_zeigt_siegerehrung():
    s = naechster_schritt(zahlen(phase="FINISHED"))
    assert s["schluessel"] == "siegerehrung"
    assert s["ziel"] == "siegerehrung"


def test_unbekannte_phase_faellt_auf_gruppenphase_zurueck():
    s = naechster_schritt({"phase": "WAS_AUCH_IMMER"})
    assert s["schluessel"] == "gruppen"


def test_leeres_dict_bricht_nicht():
    assert naechster_schritt({})["schluessel"] == "gruppen"


@pytest.mark.parametrize("schluessel", sorted(SCHRITTE))
def test_jeder_schritt_hat_text_und_ziel(schluessel):
    ueberschrift, erklaerung, ziel = SCHRITTE[schluessel]
    assert ueberschrift and len(ueberschrift) > 5
    assert erklaerung and len(erklaerung) > 20
    assert ziel in ("gruppen", "teams", "anmeldungen", "spielplan",
                    "schiedsrichter", "steuerung", "phase", "finals",
                    "siegerehrung")


# ──────────────────────────────────────
# Fortschrittszeile
# ──────────────────────────────────────

def test_fortschritt_leer():
    assert fortschritt({}) == "Noch nichts angelegt"


def test_fortschritt_gruppenphase():
    text = fortschritt(zahlen(gruppenspiele=12, gruppenspiele_offen=5))
    assert "2 Gruppen" in text
    assert "8 Mannschaften" in text
    assert "7/12 Gruppenspiele" in text


def test_fortschritt_mit_finale_und_schiedsrichtern():
    text = fortschritt(zahlen(finalspiele=4, finalspiele_offen=1,
                              schiedsrichter=3))
    assert "3/4 Finalspiele" in text
    assert "3 Schiedsrichter" in text


# ──────────────────────────────────────
# Anzeige in der Turnieradministration
# ──────────────────────────────────────

def test_banner_zeigt_naechsten_schritt(app, admin_client):
    from tests.conftest import make_tournament
    t = make_tournament("Wegweiser Cup")
    resp = admin_client.get(f"/admin/t/{t.slug}/administration")
    assert resp.status_code == 200
    text = resp.data.decode()
    assert "Nächster Schritt" in text
    assert "Gruppen anlegen" in text
    assert "Noch nichts angelegt" in text


def test_banner_fuehrt_durch_den_aufbau(app, admin_client):
    from tests.conftest import make_group, make_team, make_tournament
    t = make_tournament("Wegweiser Cup 2")

    def schritt():
        text = admin_client.get(
            f"/admin/t/{t.slug}/administration").data.decode()
        anfang = text.index('class="ns-titel"')
        return text[anfang:anfang + 120]

    assert "Gruppen anlegen" in schritt()

    gr = make_group(t, "Gruppe A")
    assert "Mannschaften eintragen" in schritt()

    make_team(t, "Alpha", gr)
    assert "verteilen" in schritt(), "eine Gruppe mit einem Team ist zu wenig"

    make_team(t, "Bravo", gr)
    assert "Spielplan erzeugen" in schritt()

    admin_client.post(f"/admin/t/{t.slug}/api/matches/generate-round-robin",
                      json={"felder": 1, "startzeit": "09:00",
                            "startdatum": "2026-11-14"})
    assert "Spiele austragen" in schritt()


def test_banner_zeigt_siegerehrung_am_ende(app, admin_client):
    from app.models import set_setting
    from tests.conftest import make_tournament
    t = make_tournament("Fertig Cup")
    set_setting(t.id, "tournament_phase", "FINISHED")
    text = admin_client.get(f"/admin/t/{t.slug}/administration").data.decode()
    assert "Siegerehrung vorbereiten" in text


def test_fortschritt_einzahl():
    text = fortschritt({"gruppen": 1, "teams": 1, "schiedsrichter": 1})
    assert "1 Gruppe ·" in text
    assert "1 Mannschaft ·" in text
    assert "Gruppen" not in text
    assert "Mannschaften" not in text
