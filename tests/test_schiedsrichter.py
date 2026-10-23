"""Tests fuer die Schiedsrichter-Zuteilung (reine Logik, ohne Datenbank)."""
from datetime import datetime, timedelta

from app.schiedsrichter import (
    einsatzzahlen, finde_schiedsrichter_konflikte, verteile_schiedsrichter,
)


def sr(sid, name=None, team_id=None, aktiv=True):
    return {"id": sid, "name": name or f"SR {sid}",
            "team_id": team_id, "aktiv": aktiv}


def spiel(sid, anstoss=None, feld=1, teams=(), schiedsrichter_id=None,
          nummer=None):
    return {"id": sid, "anstoss": anstoss, "feld": feld, "teams": tuple(teams),
            "schiedsrichter_id": schiedsrichter_id, "nummer": nummer or sid}


NEUN = datetime(2026, 11, 14, 9, 0)
NEUN15 = datetime(2026, 11, 14, 9, 15)
NEUN30 = datetime(2026, 11, 14, 9, 30)


# ──────────────────────────────────────
# Grundfunktion
# ──────────────────────────────────────

def test_jedes_spiel_bekommt_einen_schiedsrichter():
    spiele = [spiel(1, NEUN, 1, (10, 11)), spiel(2, NEUN15, 1, (12, 13))]
    zuteilung, offen = verteile_schiedsrichter(spiele, [sr(1), sr(2)])
    assert offen == []
    assert set(zuteilung) == {1, 2}


def test_ohne_schiedsrichter_bleibt_alles_offen():
    spiele = [spiel(1, NEUN, 1, (10, 11))]
    zuteilung, offen = verteile_schiedsrichter(spiele, [])
    assert zuteilung == {}
    assert offen == [1]


def test_nur_inaktive_schiedsrichter():
    spiele = [spiel(1, NEUN, 1, (10, 11))]
    zuteilung, offen = verteile_schiedsrichter(spiele, [sr(1, aktiv=False)])
    assert zuteilung == {}
    assert offen == [1]


def test_leere_spielliste():
    assert verteile_schiedsrichter([], [sr(1)]) == ({}, [])


def test_niemand_pfeift_zwei_spiele_gleichzeitig():
    """Zwei Felder, gleiche Anstosszeit – es braucht zwei Schiedsrichter."""
    spiele = [spiel(1, NEUN, 1, (10, 11)), spiel(2, NEUN, 2, (12, 13))]
    zuteilung, offen = verteile_schiedsrichter(spiele, [sr(1), sr(2)])
    assert offen == []
    assert zuteilung[1] != zuteilung[2]


def test_zu_wenig_schiedsrichter_fuer_parallele_spiele():
    spiele = [spiel(1, NEUN, 1, (10, 11)), spiel(2, NEUN, 2, (12, 13))]
    zuteilung, offen = verteile_schiedsrichter(spiele, [sr(1)])
    assert len(zuteilung) == 1
    assert len(offen) == 1


def test_last_wird_gleichmaessig_verteilt():
    spiele = [spiel(i, NEUN + timedelta(minutes=i * 15), 1, (10, 11))
              for i in range(6)]
    zuteilung, offen = verteile_schiedsrichter(spiele, [sr(1), sr(2), sr(3)])
    assert offen == []
    zahlen = {}
    for sr_id in zuteilung.values():
        zahlen[sr_id] = zahlen.get(sr_id, 0) + 1
    assert sorted(zahlen.values()) == [2, 2, 2]


def test_bestehende_zuteilung_zaehlt_bei_der_last_mit():
    spiele = [
        spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=1),
        spiel(2, NEUN15, 1, (10, 11), schiedsrichter_id=1),
        spiel(3, NEUN30, 1, (10, 11)),
    ]
    zuteilung, _offen = verteile_schiedsrichter(spiele, [sr(1), sr(2)])
    assert zuteilung == {3: 2}, "SR 2 hat noch nichts gepfiffen"


def test_nur_leere_spiele_werden_angefasst():
    spiele = [
        spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=99),
        spiel(2, NEUN15, 1, (12, 13)),
    ]
    zuteilung, _offen = verteile_schiedsrichter(spiele, [sr(1)])
    assert 1 not in zuteilung, "bestehende Einteilung bleibt unberuehrt"
    assert zuteilung[2] == 1


def test_alles_neu_verteilen():
    spiele = [
        spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=99),
        spiel(2, NEUN15, 1, (12, 13)),
    ]
    zuteilung, offen = verteile_schiedsrichter(spiele, [sr(1)],
                                               nur_leere=False)
    assert set(zuteilung) == {1, 2}
    assert offen == []


# ──────────────────────────────────────
# Eigene Mannschaft
# ──────────────────────────────────────

def test_niemand_pfeift_ein_spiel_der_eigenen_mannschaft():
    spiele = [spiel(1, NEUN, 1, (10, 11))]
    schiris = [sr(1, "Elternteil Team 10", team_id=10), sr(2, "Neutral")]
    zuteilung, offen = verteile_schiedsrichter(spiele, schiris)
    assert zuteilung == {1: 2}
    assert offen == []


def test_eigene_mannschaft_wird_zugelassen_wenn_es_nicht_anders_geht():
    """Ein Betreuer der eigenen Mannschaft ist besser als niemand."""
    spiele = [spiel(1, NEUN, 1, (10, 11))]
    schiris = [sr(1, "Elternteil Team 10", team_id=10)]
    zuteilung, offen = verteile_schiedsrichter(spiele, schiris)
    assert zuteilung == {1: 1}
    assert offen == []


def test_niemand_pfeift_waehrend_die_eigene_mannschaft_spielt():
    """Feld 1: Team 10 spielt. Feld 2 gleichzeitig: der Betreuer von
    Team 10 soll dort nicht pfeifen, weil er bei seinem Spiel gebraucht wird."""
    spiele = [spiel(1, NEUN, 1, (10, 11)), spiel(2, NEUN, 2, (12, 13))]
    schiris = [sr(1, "Betreuer Team 10", team_id=10), sr(2, "Neutral A"),
               sr(3, "Neutral B")]
    zuteilung, offen = verteile_schiedsrichter(spiele, schiris)
    assert offen == []
    assert 1 not in zuteilung.values(), \
        "Betreuer von Team 10 darf im Zeitfenster seines Spiels nicht pfeifen"


def test_betreuer_pfeift_wenn_eigene_mannschaft_pausiert():
    spiele = [spiel(1, NEUN, 1, (10, 11)), spiel(2, NEUN15, 1, (12, 13))]
    schiris = [sr(1, "Betreuer Team 10", team_id=10)]
    zuteilung, offen = verteile_schiedsrichter(spiele, schiris)
    assert zuteilung[2] == 1, "im zweiten Fenster spielt Team 10 nicht"


# ──────────────────────────────────────
# Spiele ohne Anstosszeit
# ──────────────────────────────────────

def test_spiele_ohne_anstosszeit_werden_trotzdem_verteilt():
    spiele = [spiel(1, None, 1, (10, 11)), spiel(2, None, 1, (12, 13))]
    zuteilung, offen = verteile_schiedsrichter(spiele, [sr(1)])
    assert offen == []
    assert set(zuteilung) == {1, 2}, \
        "ohne Zeitangabe kann niemand gleichzeitig pfeifen"


def test_spiele_ohne_zeit_kommen_zuletzt():
    spiele = [spiel(1, None, 1, (10, 11)), spiel(2, NEUN, 1, (12, 13))]
    zuteilung, _offen = verteile_schiedsrichter(spiele, [sr(1), sr(2)])
    # Das Spiel mit Zeit wird zuerst bedient und bekommt SR 1
    assert zuteilung[2] == 1


# ──────────────────────────────────────
# Konfliktpruefung
# ──────────────────────────────────────

def test_konflikte_saubere_einteilung():
    spiele = [
        spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=1),
        spiel(2, NEUN, 2, (12, 13), schiedsrichter_id=2),
    ]
    assert finde_schiedsrichter_konflikte(spiele, [sr(1), sr(2)]) == []


def test_konflikt_doppelt_eingeteilt():
    spiele = [
        spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=1, nummer=5),
        spiel(2, NEUN, 2, (12, 13), schiedsrichter_id=1, nummer=6),
    ]
    konflikte = finde_schiedsrichter_konflikte(spiele, [sr(1, "Hans Meier")])
    assert len(konflikte) == 1
    assert "Hans Meier" in konflikte[0]
    assert "09:00" in konflikte[0]
    assert "#5" in konflikte[0] and "#6" in konflikte[0]


def test_konflikt_eigene_mannschaft():
    spiele = [spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=1, nummer=3)]
    konflikte = finde_schiedsrichter_konflikte(
        spiele, [sr(1, "Papa von Team 10", team_id=10)])
    assert len(konflikte) == 1
    assert "eigenen" in konflikte[0]
    assert "#3" in konflikte[0]


def test_konflikte_ignorieren_spiele_ohne_schiedsrichter():
    spiele = [spiel(1, NEUN, 1, (10, 11)), spiel(2, NEUN, 2, (12, 13))]
    assert finde_schiedsrichter_konflikte(spiele, [sr(1)]) == []


def test_konflikt_unbekannter_schiedsrichter_bricht_nicht():
    spiele = [spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=99)]
    assert finde_schiedsrichter_konflikte(spiele, [sr(1)]) == []


# ──────────────────────────────────────
# Einsatzzahlen
# ──────────────────────────────────────

def test_einsatzzahlen():
    spiele = [
        spiel(1, NEUN, 1, (10, 11), schiedsrichter_id=1),
        spiel(2, NEUN15, 1, (10, 11), schiedsrichter_id=1),
        spiel(3, NEUN30, 1, (10, 11), schiedsrichter_id=2),
        spiel(4, NEUN30, 2, (12, 13)),
    ]
    assert einsatzzahlen(spiele, [sr(1), sr(2), sr(3)]) == {1: 2, 2: 1, 3: 0}


def test_verteilung_ist_reproduzierbar():
    spiele = [spiel(i, NEUN + timedelta(minutes=i * 15), 1, (10, 11))
              for i in range(4)]
    schiris = [sr(1), sr(2)]
    a, _ = verteile_schiedsrichter(list(spiele), schiris)
    b, _ = verteile_schiedsrichter(list(spiele), schiris)
    assert a == b
