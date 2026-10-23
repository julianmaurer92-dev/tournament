"""Tests fuer die Auswertungslogik (Torschuetzen, Fair-Play) – ohne Datenbank."""
import pytest

from app.statistik import (
    ergebnis_stimmt, fairplay_tabelle, karten_je_spieler, tore_je_team,
    tore_ohne_schuetzen, torschuetzenliste,
)


def tor(name, team_id=1, team_name="A", minute=None):
    return {"art": "tor", "team_id": team_id, "team_name": team_name,
            "player_name": name, "minute": minute}


def karte(art, name="Spieler", team_id=1, team_name="A"):
    return {"art": art, "team_id": team_id, "team_name": team_name,
            "player_name": name, "minute": None}


# ──────────────────────────────────────
# Torschuetzenliste
# ──────────────────────────────────────

def test_torschuetzen_zaehlen_und_sortieren():
    ereignisse = [
        tor("Lena Klein"), tor("Lena Klein"), tor("Lena Klein"),
        tor("Mia Groß"), tor("Mia Groß"),
        tor("Tim Kurz"),
    ]
    liste = torschuetzenliste(ereignisse)
    assert [(e["player_name"], e["tore"]) for e in liste] == [
        ("Lena Klein", 3), ("Mia Groß", 2), ("Tim Kurz", 1),
    ]
    assert [e["platz"] for e in liste] == [1, 2, 3]


def test_torschuetzen_gleicher_platz_bei_gleichstand():
    ereignisse = [tor("Anna"), tor("Anna"), tor("Bea"), tor("Bea"), tor("Cem")]
    liste = torschuetzenliste(ereignisse)
    assert [(e["player_name"], e["platz"]) for e in liste] == [
        ("Anna", 1), ("Bea", 1), ("Cem", 3),
    ]


def test_torschuetzen_alphabetisch_bei_gleichstand():
    liste = torschuetzenliste([tor("Zoe"), tor("Ada")])
    assert [e["player_name"] for e in liste] == ["Ada", "Zoe"]


def test_torschuetzen_fasst_schreibweisen_zusammen():
    """Tippfehler in Leerzeichen und Gross-/Kleinschreibung sollen nicht trennen."""
    liste = torschuetzenliste([
        tor("Max Mustermann"), tor("max mustermann"),
        tor("Max  Mustermann"), tor(" Max Mustermann "),
    ])
    assert len(liste) == 1
    assert liste[0]["tore"] == 4
    assert liste[0]["player_name"] == "Max Mustermann", \
        "erste Schreibweise wird angezeigt"


def test_torschuetzen_trennt_gleiche_namen_in_verschiedenen_teams():
    liste = torschuetzenliste([
        tor("Max Müller", team_id=1, team_name="A"),
        tor("Max Müller", team_id=2, team_name="B"),
    ])
    assert len(liste) == 2
    assert {e["team_name"] for e in liste} == {"A", "B"}


def test_torschuetzen_ohne_namen_werden_ignoriert():
    liste = torschuetzenliste([tor(""), tor("   "), tor(None), tor("Echt")])
    assert len(liste) == 1
    assert liste[0]["player_name"] == "Echt"


def test_eigentore_zaehlen_nicht_als_treffer():
    ereignisse = [
        tor("Anna"),
        {"art": "eigentor", "team_id": 2, "team_name": "B",
         "player_name": "Bea", "minute": 5},
    ]
    liste = torschuetzenliste(ereignisse)
    assert [e["player_name"] for e in liste] == ["Anna"]


def test_karten_zaehlen_nicht_als_tore():
    liste = torschuetzenliste([karte("gelb", "Anna"), tor("Anna")])
    assert liste[0]["tore"] == 1


def test_torschuetzen_mindestanzahl():
    ereignisse = [tor("Viel"), tor("Viel"), tor("Wenig")]
    assert len(torschuetzenliste(ereignisse, mindest_tore=2)) == 1


def test_torschuetzen_leer():
    assert torschuetzenliste([]) == []


def test_tore_ohne_schuetzen():
    ereignisse = [tor("Anna"), tor(""), tor(None), karte("gelb")]
    assert tore_ohne_schuetzen(ereignisse) == 2


# ──────────────────────────────────────
# Fair-Play
# ──────────────────────────────────────

TEAMS = [(1, "Alpha"), (2, "Bravo"), (3, "Charlie")]


def test_fairplay_strafpunkte():
    ereignisse = [
        karte("gelb", team_id=1, team_name="Alpha"),
        karte("gelb", team_id=1, team_name="Alpha"),
        karte("rot", team_id=2, team_name="Bravo"),
    ]
    tabelle = fairplay_tabelle(ereignisse, TEAMS)
    nach_team = {e["team_name"]: e for e in tabelle}
    assert nach_team["Alpha"]["strafpunkte"] == 2
    assert nach_team["Alpha"]["gelb"] == 2
    assert nach_team["Bravo"]["strafpunkte"] == 5
    assert nach_team["Charlie"]["strafpunkte"] == 0


def test_fairplay_reihenfolge_wenige_punkte_zuerst():
    ereignisse = [
        karte("rot", team_id=1, team_name="Alpha"),
        karte("gelb", team_id=2, team_name="Bravo"),
    ]
    tabelle = fairplay_tabelle(ereignisse, TEAMS)
    assert [e["team_name"] for e in tabelle] == ["Charlie", "Bravo", "Alpha"]


def test_fairplay_gelb_rot_zaehlt_drei():
    tabelle = fairplay_tabelle(
        [karte("gelb_rot", team_id=1, team_name="Alpha")], TEAMS)
    alpha = [e for e in tabelle if e["team_name"] == "Alpha"][0]
    assert alpha["strafpunkte"] == 3
    assert alpha["gelb_rot"] == 1
    assert alpha["karten"] == 1


def test_fairplay_teams_ohne_karten_erscheinen():
    tabelle = fairplay_tabelle([], TEAMS)
    assert len(tabelle) == 3
    assert all(e["strafpunkte"] == 0 for e in tabelle)
    assert all(e["platz"] == 1 for e in tabelle), "alle gleichauf"


def test_fairplay_gleicher_platz_bei_gleichstand():
    ereignisse = [
        karte("gelb", team_id=1, team_name="Alpha"),
        karte("gelb", team_id=2, team_name="Bravo"),
    ]
    tabelle = fairplay_tabelle(ereignisse, TEAMS)
    nach_team = {e["team_name"]: e["platz"] for e in tabelle}
    assert nach_team["Charlie"] == 1
    assert nach_team["Alpha"] == nach_team["Bravo"] == 2


def test_fairplay_ignoriert_unbekannte_teams():
    ereignisse = [karte("rot", team_id=99, team_name="Gibt es nicht")]
    tabelle = fairplay_tabelle(ereignisse, TEAMS)
    assert all(e["strafpunkte"] == 0 for e in tabelle)


def test_fairplay_tore_zaehlen_nicht():
    tabelle = fairplay_tabelle([tor("Anna", team_id=1)], TEAMS)
    assert all(e["strafpunkte"] == 0 for e in tabelle)


# ──────────────────────────────────────
# Karten je Spieler
# ──────────────────────────────────────

def test_karten_je_spieler():
    ereignisse = [
        karte("gelb", "Anna"), karte("gelb", "Anna"),
        karte("rot", "Bea"),
        tor("Cem"),
    ]
    liste = karten_je_spieler(ereignisse)
    assert [e["player_name"] for e in liste] == ["Bea", "Anna"]
    assert liste[0]["strafpunkte"] == 5
    assert liste[1]["gelb"] == 2


def test_karten_je_spieler_ohne_namen_ignoriert():
    assert karten_je_spieler([karte("gelb", "")]) == []


# ──────────────────────────────────────
# Abgleich mit dem Ergebnis
# ──────────────────────────────────────

def test_tore_je_team():
    ereignisse = [
        tor("Anna", team_id=1), tor("Bea", team_id=1),
        {"art": "eigentor", "team_id": 2, "team_name": "B",
         "player_name": "", "minute": None},
    ]
    assert tore_je_team(ereignisse) == {1: 2, 2: 1}


def test_ergebnis_stimmt_ja():
    ereignisse = [tor("Anna", team_id=1), tor("Bea", team_id=2)]
    stimmt, t1, t2 = ergebnis_stimmt(1, 1, 1, 2, ereignisse)
    assert stimmt is True
    assert (t1, t2) == (1, 1)


def test_ergebnis_stimmt_nein():
    ereignisse = [tor("Anna", team_id=1)]
    stimmt, t1, t2 = ergebnis_stimmt(3, 0, 1, 2, ereignisse)
    assert stimmt is False
    assert (t1, t2) == (1, 0)


def test_ergebnis_stimmt_bei_null_zu_null():
    stimmt, t1, t2 = ergebnis_stimmt(0, 0, 1, 2, [])
    assert stimmt is True
    assert (t1, t2) == (0, 0)


def test_ergebnis_stimmt_behandelt_none_als_null():
    stimmt, _, _ = ergebnis_stimmt(None, None, 1, 2, [])
    assert stimmt is True


def test_eigentor_wird_dem_gegner_zugerechnet():
    """Ein Eigentor muss das Ergebnis des Gegners erklaeren."""
    ereignisse = [{"art": "eigentor", "team_id": 2, "team_name": "B",
                   "player_name": "", "minute": 10}]
    stimmt, t1, t2 = ergebnis_stimmt(0, 1, 1, 2, ereignisse)
    assert stimmt is True
    assert (t1, t2) == (0, 1)
