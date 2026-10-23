"""Tests fuer die Endplatzierung (reine Logik, ohne Datenbank)."""
from app.platzierung import (
    endplatzierung, medaille, platz_aus_bezeichnung, siegerehrung_ablauf,
)


def rangliste(*namen_mit_id):
    """[(1, "Alpha"), ...] -> Struktur wie calculate_overall_rankings()."""
    return [{"team": {"id": tid, "name": name}}
            for tid, name in namen_mit_id]


def spiel(t1, t2, s1, s2, runde=1, label=None, verlierer_spiel=False,
          status="finished"):
    return {
        "team1_id": t1, "team2_id": t2,
        "score_team1": s1, "score_team2": s2,
        "status": status, "final_round": runde,
        "final_label": label, "is_loser_match": verlierer_spiel,
    }


ACHT = rangliste((1, "Alpha"), (2, "Bravo"), (3, "Charlie"), (4, "Delta"),
                 (5, "Echo"), (6, "Foxtrott"), (7, "Golf"), (8, "Hotel"))


def _namen_je_platz(ergebnis):
    return [(e["platz"], e["team_name"]) for e in ergebnis]


# ──────────────────────────────────────
# Ohne Finalrunde
# ──────────────────────────────────────

def test_ohne_finalrunde_gilt_die_gruppenphase():
    ergebnis = endplatzierung([], ACHT)
    assert _namen_je_platz(ergebnis) == [
        (1, "Alpha"), (2, "Bravo"), (3, "Charlie"), (4, "Delta"),
        (5, "Echo"), (6, "Foxtrott"), (7, "Golf"), (8, "Hotel"),
    ]
    assert all(e["quelle"] == "Gruppenphase" for e in ergebnis)
    assert not any(e["geteilt"] for e in ergebnis)


def test_leeres_turnier():
    assert endplatzierung([], []) == []


# ──────────────────────────────────────
# Direktes Finale
# ──────────────────────────────────────

def test_direktes_finale():
    finals = [spiel(1, 2, 3, 1, runde=1, label="Finale")]
    ergebnis = endplatzierung(finals, ACHT)
    assert _namen_je_platz(ergebnis)[:3] == [
        (1, "Alpha"), (2, "Bravo"), (3, "Charlie"),
    ]
    assert ergebnis[0]["quelle"] == "Finale"
    assert ergebnis[2]["quelle"] == "Gruppenphase"


def test_finale_mit_dem_schlechter_platzierten_sieger():
    """Wer das Finale gewinnt, ist Erster – auch als Gruppenzweiter."""
    finals = [spiel(1, 2, 0, 2, runde=1, label="Finale")]
    ergebnis = endplatzierung(finals, ACHT)
    assert ergebnis[0]["team_name"] == "Bravo"
    assert ergebnis[1]["team_name"] == "Alpha"


def test_unentschiedenes_finale_entscheidet_nichts():
    """Ein Remis im Finale vergibt keinen Platz – die Teams bleiben offen."""
    finals = [spiel(1, 2, 1, 1, runde=1, label="Finale")]
    ergebnis = endplatzierung(finals, ACHT)
    nach_name = {e["team_name"]: e for e in ergebnis}

    assert nach_name["Alpha"]["platz"] == 1
    assert nach_name["Alpha"]["quelle"] == "noch im Rennen"
    assert nach_name["Bravo"]["quelle"] == "noch im Rennen"
    assert nach_name["Charlie"]["quelle"] == "Gruppenphase"


def test_nicht_beendetes_finale_vergibt_keinen_platz():
    finals = [spiel(1, 2, 0, 0, runde=1, label="Finale", status="live")]
    ergebnis = endplatzierung(finals, ACHT)
    nach_name = {e["team_name"]: e for e in ergebnis}

    assert nach_name["Alpha"]["quelle"] == "noch im Rennen"
    assert nach_name["Bravo"]["quelle"] == "noch im Rennen"
    # Reihenfolge nach Gruppenphase, Finalteilnehmer stehen vorn
    assert nach_name["Alpha"]["platz"] == 1
    assert nach_name["Bravo"]["platz"] == 2
    assert nach_name["Charlie"]["platz"] == 3


# ──────────────────────────────────────
# Halbfinale + Finale
# ──────────────────────────────────────

def test_halbfinale_ohne_spiel_um_platz_drei_teilt_platz_drei():
    finals = [
        spiel(1, 4, 2, 0, runde=2, label="Halbfinale 1"),
        spiel(2, 3, 1, 3, runde=2, label="Halbfinale 2"),
        spiel(1, 3, 1, 0, runde=1, label="Finale"),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    nach_name = {e["team_name"]: e for e in ergebnis}

    assert nach_name["Alpha"]["platz"] == 1
    assert nach_name["Charlie"]["platz"] == 2
    # Bravo und Delta verloren im Halbfinale -> geteilter 3. Platz
    assert nach_name["Bravo"]["platz"] == 3
    assert nach_name["Delta"]["platz"] == 3
    assert nach_name["Bravo"]["geteilt"] is True
    assert nach_name["Delta"]["geteilt"] is True
    # Danach geht es bei 5 weiter, nicht bei 4
    assert nach_name["Echo"]["platz"] == 5


def test_halbfinale_mit_spiel_um_platz_drei():
    finals = [
        spiel(1, 4, 2, 0, runde=2, label="Halbfinale 1"),
        spiel(2, 3, 1, 3, runde=2, label="Halbfinale 2"),
        spiel(1, 3, 1, 0, runde=1, label="Finale"),
        spiel(4, 2, 2, 1, runde=1, label="Spiel um Platz 3",
              verlierer_spiel=True),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    nach_name = {e["team_name"]: e for e in ergebnis}

    assert nach_name["Alpha"]["platz"] == 1
    assert nach_name["Charlie"]["platz"] == 2
    assert nach_name["Delta"]["platz"] == 3
    assert nach_name["Bravo"]["platz"] == 4
    assert nach_name["Delta"]["geteilt"] is False
    assert nach_name["Echo"]["platz"] == 5


# ──────────────────────────────────────
# Klassische KO-Runde
# ──────────────────────────────────────

def test_viertelfinale_verlierer_belegen_plaetze_fuenf_bis_acht():
    finals = [
        # Viertelfinale (Runde 3)
        spiel(1, 8, 3, 0, runde=3, label="Viertelfinale 1"),
        spiel(2, 7, 2, 1, runde=3, label="Viertelfinale 2"),
        spiel(3, 6, 1, 0, runde=3, label="Viertelfinale 3"),
        spiel(4, 5, 2, 0, runde=3, label="Viertelfinale 4"),
        # Halbfinale (Runde 2)
        spiel(1, 4, 1, 0, runde=2, label="Halbfinale 1"),
        spiel(2, 3, 0, 1, runde=2, label="Halbfinale 2"),
        # Finale
        spiel(1, 3, 2, 1, runde=1, label="Finale"),
        spiel(4, 2, 1, 0, runde=1, label="Spiel um Platz 3",
              verlierer_spiel=True),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    nach_name = {e["team_name"]: e for e in ergebnis}

    assert nach_name["Alpha"]["platz"] == 1
    assert nach_name["Charlie"]["platz"] == 2
    assert nach_name["Delta"]["platz"] == 3
    assert nach_name["Bravo"]["platz"] == 4
    # Die vier Viertelfinal-Verlierer teilen Platz 5
    for name in ("Echo", "Foxtrott", "Golf", "Hotel"):
        assert nach_name[name]["platz"] == 5, name
        assert nach_name[name]["geteilt"] is True


def test_ko_verlierer_werden_nach_gruppenphase_sortiert():
    finals = [
        spiel(1, 8, 1, 0, runde=3, label="Viertelfinale 1"),
        spiel(2, 7, 1, 0, runde=3, label="Viertelfinale 2"),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    ausgeschieden = [e for e in ergebnis
                     if e["quelle"].startswith("ausgeschieden")]
    # Golf (Rang 7) steht vor Hotel (Rang 8)
    assert [e["team_name"] for e in ausgeschieden] == ["Golf", "Hotel"]


# ──────────────────────────────────────
# Platzierungsspiele (rank_vs_rank)
# ──────────────────────────────────────

def test_platzierungsspiele_aus_der_bezeichnung():
    finals = [
        spiel(1, 2, 2, 1, runde=4, label="Finale"),
        spiel(3, 4, 0, 1, runde=3, label="Spiel um Platz 3"),
        spiel(5, 6, 3, 2, runde=2, label="Spiel um Platz 5"),
        spiel(7, 8, 1, 2, runde=1, label="Spiel um Platz 7"),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    assert _namen_je_platz(ergebnis) == [
        (1, "Alpha"), (2, "Bravo"),
        (3, "Delta"), (4, "Charlie"),
        (5, "Echo"), (6, "Foxtrott"),
        (7, "Hotel"), (8, "Golf"),
    ]
    assert not any(e["geteilt"] for e in ergebnis)


def test_platzierungsspiele_teilweise_gespielt():
    """Finale durch, die uebrigen Platzierungsspiele laufen noch."""
    finals = [
        spiel(1, 2, 2, 1, runde=4, label="Finale"),
        spiel(3, 4, 0, 0, runde=3, label="Spiel um Platz 3", status="live"),
        spiel(5, 6, 0, 0, runde=2, label="Spiel um Platz 5", status="live"),
        spiel(7, 8, 0, 0, runde=1, label="Spiel um Platz 7", status="live"),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    nach_name = {e["team_name"]: e for e in ergebnis}

    assert nach_name["Alpha"]["platz"] == 1
    assert nach_name["Bravo"]["platz"] == 2
    # Die noch spielenden Teams stehen in der Reihenfolge der Gruppenphase
    assert [nach_name[n]["platz"] for n in
            ("Charlie", "Delta", "Echo", "Foxtrott", "Golf", "Hotel")] == \
           [3, 4, 5, 6, 7, 8]
    assert nach_name["Charlie"]["quelle"] == "noch im Rennen"


def test_bezeichnung_halbfinale_ist_kein_platzierungsspiel():
    """"Halbfinale" enthaelt "finale" – darf nicht als Platz 1 gelten."""
    finals = [spiel(1, 4, 2, 0, runde=2, label="Halbfinale 1")]
    ergebnis = endplatzierung(finals, ACHT)
    nach_name = {e["team_name"]: e for e in ergebnis}

    # Alpha hat das Halbfinale gewonnen, also noch keinen festen Platz
    assert nach_name["Alpha"]["quelle"] == "noch im Rennen"
    assert nach_name["Alpha"]["platz"] == 1
    # Delta ist ausgeschieden und steht hinter allen, die noch spielen
    assert nach_name["Delta"]["quelle"] == "ausgeschieden: Halbfinale"
    assert nach_name["Delta"]["platz"] > nach_name["Alpha"]["platz"]


def test_finale_mit_gruppenangabe_in_der_bezeichnung():
    finals = [spiel(1, 2, 1, 0, runde=1, label="Finale (Gruppe A/Gruppe B)")]
    ergebnis = endplatzierung(finals, ACHT)
    assert ergebnis[0]["team_name"] == "Alpha"
    assert ergebnis[1]["team_name"] == "Bravo"


# ──────────────────────────────────────
# Randfaelle
# ──────────────────────────────────────

def test_spiel_ohne_teams_wird_ignoriert():
    finals = [spiel(None, None, 0, 0, runde=1, label="Finale")]
    ergebnis = endplatzierung(finals, ACHT)
    assert all(e["quelle"] == "Gruppenphase" for e in ergebnis)


def test_team_nicht_in_der_rangliste_bekommt_namen_aus_der_tabelle():
    finals = [spiel(99, 1, 1, 0, runde=1, label="Finale")]
    ergebnis = endplatzierung(finals, ACHT, team_namen={99: "Gaststeam"})
    assert ergebnis[0]["team_name"] == "Gaststeam"
    assert ergebnis[0]["platz"] == 1


def test_kein_team_doppelt():
    finals = [
        spiel(1, 2, 2, 1, runde=1, label="Finale"),
        spiel(1, 3, 1, 0, runde=2, label="Halbfinale 1"),
        spiel(2, 4, 1, 0, runde=2, label="Halbfinale 2"),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    ids = [e["team_id"] for e in ergebnis]
    assert len(ids) == len(set(ids))
    assert len(ids) == 8, "alle Teams kommen genau einmal vor"


def test_plaetze_sind_lueckenlos_aufsteigend():
    finals = [
        spiel(1, 4, 2, 0, runde=2, label="Halbfinale 1"),
        spiel(2, 3, 1, 3, runde=2, label="Halbfinale 2"),
        spiel(1, 3, 1, 0, runde=1, label="Finale"),
    ]
    ergebnis = endplatzierung(finals, ACHT)
    plaetze = [e["platz"] for e in ergebnis]
    assert plaetze == sorted(plaetze)
    assert plaetze[0] == 1


# ──────────────────────────────────────
# Siegerehrung
# ──────────────────────────────────────

def test_medaillen():
    assert medaille(1) == "🥇"
    assert medaille(2) == "🥈"
    assert medaille(3) == "🥉"
    assert medaille(4) == ""


def test_siegerehrung_von_hinten_nach_vorne():
    platzierung = endplatzierung([], ACHT)
    ablauf = siegerehrung_ablauf(platzierung)
    assert [e["platz"] for e in ablauf] == [8, 7, 6, 5, 4, 3, 2, 1]
    assert ablauf[-1]["team_name"] == "Alpha"
    assert ablauf[-1]["medaille"] == "🥇"
    assert ablauf[0]["medaille"] == ""


# ──────────────────────────────────────
# Bezeichnungen lesen
# ──────────────────────────────────────

import pytest


@pytest.mark.parametrize("label,erwartet", [
    ("Finale", 1),
    ("Finale (Gruppe A/Gruppe B)", 1),
    ("Spiel um Platz 3", 3),
    ("Spiel um Platz 11", 11),
    ("platz 5", 5),
    ("Halbfinale 1", None),
    ("Viertelfinale 2", None),
    ("Achtelfinale 3", None),
    ("", None),
    (None, None),
    ("Trostrunde", None),
])
def test_platz_aus_bezeichnung(label, erwartet):
    assert platz_aus_bezeichnung(label) == erwartet
