"""Tests fuer die Tabellenberechnung – das Herz des Turniers."""
from app.models import (
    calculate_overall_rankings, calculate_standings,
    get_seeded_teams_cross_group,
)
from tests.conftest import (
    finish_match, make_group, make_match, make_team, make_tournament,
)


def test_standings_punkte_und_reihenfolge(simple_tournament):
    gr = simple_tournament["group"]
    table = calculate_standings(group_id=gr.id)

    assert [row["team"]["name"] for row in table] == [
        "Alpha", "Charlie", "Bravo", "Delta",
    ]
    alpha = table[0]
    assert alpha["points"] == 7       # 2 Siege, 1 Remis
    assert alpha["played"] == 3
    assert alpha["won"] == 2
    assert alpha["drawn"] == 1
    assert alpha["lost"] == 0
    assert alpha["goals_for"] == 8
    assert alpha["goals_against"] == 1
    assert alpha["goal_diff"] == 7
    assert alpha["rank"] == 1

    delta = table[-1]
    assert delta["points"] == 0
    assert delta["goal_diff"] == -11


def test_standings_ignoriert_ungespielte_spiele(app):
    t = make_tournament("Offen")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    make_match(t, a, b, gr, 1)  # status "planned"

    table = calculate_standings(group_id=gr.id)
    assert all(row["played"] == 0 for row in table)
    assert all(row["points"] == 0 for row in table)


def test_standings_ignoriert_finalspiele(app):
    t = make_tournament("Mit Finale")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    finish_match(make_match(t, a, b, gr, 1), 1, 0)
    finish_match(make_match(t, a, b, None, 2, is_final=True, final_round=1), 0, 5)

    table = calculate_standings(group_id=gr.id)
    assert table[0]["team"]["name"] == "A"
    assert table[0]["played"] == 1, "Finalspiel darf nicht in die Gruppentabelle"


def test_tiebreak_tordifferenz_vor_toren(app):
    """Gleiche Punkte: bessere Tordifferenz gewinnt, dann mehr Tore."""
    t = make_tournament("Tiebreak")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    c = make_team(t, "C", gr)
    d = make_team(t, "D", gr)

    # A und B je 3 Punkte, A mit +3, B mit +1
    finish_match(make_match(t, a, c, gr, 1), 3, 0)
    finish_match(make_match(t, b, d, gr, 2), 1, 0)

    table = calculate_standings(group_id=gr.id)
    assert table[0]["team"]["name"] == "A"
    assert table[1]["team"]["name"] == "B"


def test_gleiche_punkte_gleiche_diff_mehr_tore_gewinnt(app):
    t = make_tournament("Tiebreak2")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    c = make_team(t, "C", gr)
    d = make_team(t, "D", gr)

    finish_match(make_match(t, a, c, gr, 1), 4, 3)   # A: +1, 4 Tore
    finish_match(make_match(t, b, d, gr, 2), 1, 0)   # B: +1, 1 Tor

    table = calculate_standings(group_id=gr.id)
    assert table[0]["team"]["name"] == "A"
    assert table[1]["team"]["name"] == "B"


def test_overall_rankings_ueber_gruppen(app):
    t = make_tournament("Zwei Gruppen")
    g1 = make_group(t, "Gruppe A", 0)
    g2 = make_group(t, "Gruppe B", 1)
    a1 = make_team(t, "A1", g1)
    a2 = make_team(t, "A2", g1)
    b1 = make_team(t, "B1", g2)
    b2 = make_team(t, "B2", g2)

    finish_match(make_match(t, a1, a2, g1, 1), 5, 0)
    finish_match(make_match(t, b1, b2, g2, 2), 1, 0)

    overall = calculate_overall_rankings(t.id)
    assert [r["team"]["name"] for r in overall] == ["A1", "B1", "B2", "A2"]
    assert overall[0]["overall_rank"] == 1
    assert overall[0]["group_name"] == "Gruppe A"
    assert overall[0]["group_rank"] == 1


def test_cross_group_seeding_zwei_gruppen(app):
    """Bei 2 Gruppen: A1 gegen B2, A2 gegen B1 (Ueberkreuz)."""
    t = make_tournament("Kreuz")
    g1 = make_group(t, "Gruppe A", 0)
    g2 = make_group(t, "Gruppe B", 1)
    a1 = make_team(t, "A1", g1)
    a2 = make_team(t, "A2", g1)
    b1 = make_team(t, "B1", g2)
    b2 = make_team(t, "B2", g2)

    finish_match(make_match(t, a1, a2, g1, 1), 3, 0)
    finish_match(make_match(t, b1, b2, g2, 2), 3, 0)

    pairs = get_seeded_teams_cross_group(t.id, 4)
    assert (a1.id, b2.id) in pairs
    assert (a2.id, b1.id) in pairs


def test_standings_leere_gruppe(app):
    t = make_tournament("Leer")
    gr = make_group(t)
    assert calculate_standings(group_id=gr.id) == []


def test_standings_ohne_argumente_liefert_leere_liste(app):
    assert calculate_standings() == []
