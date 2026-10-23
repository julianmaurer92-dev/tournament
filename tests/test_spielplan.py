"""Tests fuer die Spielplanung (reine Logik, ohne Datenbank)."""
from datetime import datetime

import pytest

from app.spielplan import (
    Begegnung, begegnungen_fuer_gruppen, erstelle_spielplan, finde_konflikte,
    jeder_gegen_jeden, plane_slots, slot_zeiten,
)


# ──────────────────────────────────────
# Paarungen
# ──────────────────────────────────────

def test_jeder_gegen_jeden_anzahl():
    assert len(jeder_gegen_jeden([1, 2, 3, 4])) == 6
    assert len(jeder_gegen_jeden([1, 2, 3, 4, 5])) == 10
    assert len(jeder_gegen_jeden([1, 2])) == 1
    assert jeder_gegen_jeden([1]) == []
    assert jeder_gegen_jeden([]) == []


def test_jeder_gegen_jeden_keine_doppelten_paarungen():
    paarungen = {frozenset(b.teams) for b in jeder_gegen_jeden([1, 2, 3, 4])}
    assert len(paarungen) == 6


def test_begegnungen_fuer_gruppen_ueberspringt_zu_kleine_gruppen():
    begegnungen = begegnungen_fuer_gruppen([
        ("A", [1, 2, 3]),
        ("B", [4]),            # zu klein
        ("C", []),             # leer
        ("D", [5, 6]),
    ])
    assert len(begegnungen) == 3 + 1
    assert {b.gruppe for b in begegnungen} == {"A", "D"}


# ──────────────────────────────────────
# Slot-Verteilung
# ──────────────────────────────────────

def test_kein_team_spielt_zweimal_im_selben_slot():
    """Die Regel, an der der alte Generator gescheitert ist."""
    begegnungen = jeder_gegen_jeden([1, 2, 3, 4, 5, 6], gruppe="A")
    slots = plane_slots(begegnungen, felder=3)

    for slot in slots:
        teams = [t for _feld, b in slot for t in b.teams]
        assert len(teams) == len(set(teams)), (
            f"Mannschaft doppelt im selben Slot: {slot}")


def test_alle_begegnungen_kommen_genau_einmal_vor():
    begegnungen = jeder_gegen_jeden([1, 2, 3, 4, 5], gruppe="A")
    slots = plane_slots(begegnungen, felder=2)

    geplant = [b for slot in slots for _feld, b in slot]
    assert len(geplant) == len(begegnungen)
    assert {frozenset(b.teams) for b in geplant} == \
           {frozenset(b.teams) for b in begegnungen}


def test_felder_werden_aufgefuellt():
    begegnungen = jeder_gegen_jeden([1, 2, 3, 4, 5, 6, 7, 8], gruppe="A")
    slots = plane_slots(begegnungen, felder=2, mindestpause=0)
    # 28 Begegnungen auf 2 Feldern -> 14 Slots, alle voll
    assert len(slots) == 14
    assert all(len(slot) == 2 for slot in slots)


def test_feldnummern_beginnen_bei_eins():
    slots = plane_slots(jeder_gegen_jeden([1, 2, 3, 4]), felder=2, mindestpause=0)
    for slot in slots:
        felder = [feld for feld, _b in slot]
        assert felder == list(range(1, len(slot) + 1))


def test_ein_feld_ergibt_einen_slot_pro_spiel():
    begegnungen = jeder_gegen_jeden([1, 2, 3, 4])
    slots = plane_slots(begegnungen, felder=1)
    assert len(slots) == 6
    assert all(len(slot) == 1 for slot in slots)


def test_mehr_felder_als_spiele_moeglich():
    slots = plane_slots(jeder_gegen_jeden([1, 2]), felder=5)
    assert len(slots) == 1
    assert len(slots[0]) == 1


def test_null_felder_ist_ein_fehler():
    with pytest.raises(ValueError):
        plane_slots(jeder_gegen_jeden([1, 2]), felder=0)


def test_leere_eingabe_ergibt_leeren_plan():
    assert plane_slots([], felder=2) == []


def test_mindestpause_wird_eingehalten_wenn_moeglich():
    """Zwei Gruppen mit je vier Teams: niemand muss zweimal hintereinander."""
    begegnungen = (jeder_gegen_jeden([1, 2, 3, 4], gruppe="A")
                   + jeder_gegen_jeden([5, 6, 7, 8], gruppe="B"))
    slots = plane_slots(begegnungen, felder=2, mindestpause=1)

    letzter = {}
    verstoesse = []
    for i, slot in enumerate(slots):
        for _feld, b in slot:
            for team in b.teams:
                if letzter.get(team) == i - 1:
                    verstoesse.append((team, i))
                letzter[team] = i
    assert verstoesse == [], f"Teams ohne Pause: {verstoesse}"


def test_mindestpause_wird_gelockert_statt_zu_scheitern():
    """Vier Teams auf zwei Feldern: Pausen sind gar nicht moeglich."""
    begegnungen = jeder_gegen_jeden([1, 2, 3, 4], gruppe="A")
    slots = plane_slots(begegnungen, felder=2, mindestpause=5)

    # Trotzdem vollstaendig und ohne Doppelbelegung
    geplant = [b for slot in slots for _feld, b in slot]
    assert len(geplant) == 6
    for slot in slots:
        teams = [t for _feld, b in slot for t in b.teams]
        assert len(teams) == len(set(teams))


def test_vier_teams_zwei_felder_ergibt_drei_slots():
    """Jeder Spieltag hat zwei parallele Partien – der Idealfall."""
    slots = plane_slots(jeder_gegen_jeden([1, 2, 3, 4]), felder=2, mindestpause=0)
    assert len(slots) == 3
    assert all(len(slot) == 2 for slot in slots)
    # In jedem Slot spielen alle vier Teams
    for slot in slots:
        teams = {t for _feld, b in slot for t in b.teams}
        assert teams == {1, 2, 3, 4}


def test_planung_ist_reproduzierbar():
    begegnungen = jeder_gegen_jeden([1, 2, 3, 4, 5], gruppe="A")
    a = plane_slots(list(begegnungen), felder=2)
    b = plane_slots(list(begegnungen), felder=2)
    assert [[(f, bg.teams) for f, bg in s] for s in a] == \
           [[(f, bg.teams) for f, bg in s] for s in b]


def test_ungerade_teamzahl_laesst_niemanden_liegen():
    begegnungen = jeder_gegen_jeden([1, 2, 3, 4, 5, 6, 7], gruppe="A")
    slots = plane_slots(begegnungen, felder=3)
    geplant = [b for slot in slots for _feld, b in slot]
    assert len(geplant) == 21
    gespielt = {}
    for b in geplant:
        for team in b.teams:
            gespielt[team] = gespielt.get(team, 0) + 1
    assert set(gespielt.values()) == {6}, "jedes Team spielt gegen alle anderen"


# ──────────────────────────────────────
# Anstosszeiten
# ──────────────────────────────────────

def test_slot_zeiten_einfach():
    zeiten = slot_zeiten(4, datetime(2026, 11, 14, 9, 0),
                         spielzeit_min=10, pause_min=5)
    assert [z.strftime("%H:%M") for z in zeiten] == \
           ["09:00", "09:15", "09:30", "09:45"]


def test_slot_zeiten_ohne_pause():
    zeiten = slot_zeiten(3, datetime(2026, 11, 14, 9, 0),
                         spielzeit_min=12, pause_min=0)
    assert [z.strftime("%H:%M") for z in zeiten] == ["09:00", "09:12", "09:24"]


def test_slot_zeiten_mit_mittagspause():
    zeiten = slot_zeiten(4, datetime(2026, 11, 14, 9, 0),
                         spielzeit_min=10, pause_min=5,
                         lange_pause_nach=2, lange_pause_min=30)
    assert [z.strftime("%H:%M") for z in zeiten] == \
           ["09:00", "09:15", "10:00", "10:15"]


def test_slot_zeiten_ueber_mitternacht():
    zeiten = slot_zeiten(3, datetime(2026, 11, 14, 23, 40),
                         spielzeit_min=10, pause_min=5)
    assert zeiten[-1].strftime("%d.%m. %H:%M") == "15.11. 00:10"


def test_slot_zeiten_null_slots():
    assert slot_zeiten(0, datetime(2026, 1, 1, 9, 0), spielzeit_min=10) == []


@pytest.mark.parametrize("spielzeit,pause", [(0, 5), (-5, 5), (10, -1)])
def test_slot_zeiten_unsinnige_werte(spielzeit, pause):
    with pytest.raises(ValueError):
        slot_zeiten(2, datetime(2026, 1, 1, 9, 0),
                    spielzeit_min=spielzeit, pause_min=pause)


# ──────────────────────────────────────
# Kompletter Spielplan
# ──────────────────────────────────────

def test_erstelle_spielplan_komplett():
    begegnungen = (jeder_gegen_jeden([1, 2, 3, 4], gruppe="A")
                   + jeder_gegen_jeden([5, 6, 7, 8], gruppe="B"))
    plan = erstelle_spielplan(
        begegnungen, felder=2, mindestpause=1,
        start=datetime(2026, 11, 14, 9, 0),
        spielzeit_min=10, pause_min=5,
    )

    assert len(plan) == 12
    assert [p["nummer"] for p in plan] == list(range(1, 13))

    # Spiele sind nach Zeit sortiert, Felder innerhalb eines Slots aufsteigend
    for vorher, nachher in zip(plan, plan[1:]):
        assert (vorher["anstoss"], vorher["feld"]) < \
               (nachher["anstoss"], nachher["feld"])

    # Erster Slot startet um 9:00 auf beiden Feldern
    erste = [p for p in plan if p["slot"] == 1]
    assert len(erste) == 2
    assert all(p["anstoss"].strftime("%H:%M") == "09:00" for p in erste)
    assert sorted(p["feld"] for p in erste) == [1, 2]


def test_erstelle_spielplan_startnummer():
    plan = erstelle_spielplan(jeder_gegen_jeden([1, 2, 3]), felder=1,
                              start=datetime(2026, 1, 1, 9, 0), startnummer=18)
    assert [p["nummer"] for p in plan] == [18, 19, 20]


def test_erstelle_spielplan_ohne_startzeit_hat_keine_anstosszeiten():
    plan = erstelle_spielplan(jeder_gegen_jeden([1, 2, 3]), felder=1)
    assert all(p["anstoss"] is None for p in plan)


def test_erstelle_spielplan_leer():
    assert erstelle_spielplan([], felder=2) == []


# ──────────────────────────────────────
# Konflikte in bestehenden Plaenen
# ──────────────────────────────────────

def test_konflikte_sauberer_plan():
    neun = datetime(2026, 11, 14, 9, 0)
    neun_fuenfzehn = datetime(2026, 11, 14, 9, 15)
    spiele = [
        {"nummer": 1, "anstoss": neun, "feld": 1, "teams": (1, 2)},
        {"nummer": 2, "anstoss": neun, "feld": 2, "teams": (3, 4)},
        {"nummer": 3, "anstoss": neun_fuenfzehn, "feld": 1, "teams": (1, 3)},
    ]
    assert finde_konflikte(spiele) == []


def test_konflikt_zwei_spiele_auf_einem_feld():
    neun = datetime(2026, 11, 14, 9, 0)
    spiele = [
        {"nummer": 1, "anstoss": neun, "feld": 1, "teams": (1, 2)},
        {"nummer": 2, "anstoss": neun, "feld": 1, "teams": (3, 4)},
    ]
    konflikte = finde_konflikte(spiele)
    assert len(konflikte) == 1
    assert "Feld 1" in konflikte[0]
    assert "#1" in konflikte[0] and "#2" in konflikte[0]


def test_konflikt_team_doppelt_angesetzt():
    neun = datetime(2026, 11, 14, 9, 0)
    spiele = [
        {"nummer": 1, "anstoss": neun, "feld": 1, "teams": (1, 2)},
        {"nummer": 2, "anstoss": neun, "feld": 2, "teams": (1, 3)},
    ]
    konflikte = finde_konflikte(spiele)
    assert any("Mannschaft 1" in k for k in konflikte)


def test_konflikte_ignorieren_spiele_ohne_zeit():
    spiele = [
        {"nummer": 1, "anstoss": None, "feld": 1, "teams": (1, 2)},
        {"nummer": 2, "anstoss": None, "feld": 1, "teams": (1, 3)},
    ]
    assert finde_konflikte(spiele) == []


def test_konflikte_ignorieren_leere_teams():
    """Finalspiele ohne feststehende Teams duerfen nicht als Konflikt gelten."""
    neun = datetime(2026, 11, 14, 9, 0)
    spiele = [
        {"nummer": 1, "anstoss": neun, "feld": 1, "teams": (None, None)},
        {"nummer": 2, "anstoss": neun, "feld": 2, "teams": (None, None)},
    ]
    assert finde_konflikte(spiele) == []
