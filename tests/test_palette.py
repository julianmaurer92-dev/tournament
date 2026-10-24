"""Die Befehlspalette liefert, was sie verspricht.

Die Suche selbst laeuft im Browser; hier wird geprueft, dass die
Eintraege vollstaendig und benutzbar beim Browser ankommen – jeder
mit Name, Ziel und Herkunft, und mit Stichwoertern, die auf
tatsaechlich vorhandene Menuepunkte zeigen.
"""
from app.navigation import STICHWORTE, navigation, palette_eintraege
from tests.conftest import make_group, make_match, make_team, make_tournament


def test_stichworte_zeigen_auf_echte_punkte(app):
    """Jeder Stichwort-Schluessel muss ein Navigationspunkt sein.

    Beim Bauen hatte ich "Turniere", "Export / Import" und "E-Mail"
    eingetragen – die Punkte heissen aber "Alle Turniere",
    "Sicherung" und existieren im Repository gar nicht. Die
    Stichwoerter liefen damit ins Leere, ohne dass irgendetwas
    fehlschlug.
    """
    with app.test_request_context("/admin/"):
        namen = {p["name"] for p in navigation(None)}
    # Turnierbezogene Punkte brauchen ein Turnier im Kontext
    turnierpunkte = {
        "Übersicht", "Spielplan", "Teams & Gruppen", "Schiedsrichter",
        "Statistik", "Siegerehrung", "Organisation", "Design",
    }
    unbekannt = set(STICHWORTE) - namen - turnierpunkte
    assert not unbekannt, f"Stichwoerter ohne passenden Menuepunkt: {unbekannt}"


def _turnier_mit_daten():
    t = make_tournament(name="Palettenturnier")
    g = make_group(t)
    a = make_team(t, "SV Alpha", g)
    b = make_team(t, "SV Beta", g)
    make_match(t, a, b, g)
    return t


def test_eintraege_sind_vollstaendig(app):
    turnier = _turnier_mit_daten()
    with app.test_request_context(f"/admin/t/{turnier.slug}/"):
        from app.models import Match, Team
        eintraege = palette_eintraege(
            turnier,
            Team.query.filter_by(tournament_id=turnier.id).all(),
            Match.query.filter_by(tournament_id=turnier.id).all(),
            [("rasen", "Rasen")])

    assert eintraege
    for e in eintraege:
        assert e["name"], e
        assert e["ziel"].startswith("/"), e
        assert e["art"] in {"Seite", "Aktion", "Mannschaft", "Spiel", "Theme"}, e
        assert e["icon"], e
        assert "stichwort" in e, e


def test_ohne_turnier_nur_allgemeine_seiten(app):
    with app.test_request_context("/admin/"):
        eintraege = palette_eintraege(None)
    assert eintraege
    assert {e["art"] for e in eintraege} == {"Seite"}


def test_jede_art_hat_ein_eigenes_icon(app):
    """Gleiche Symbole fuer verschiedene Dinge machen die Liste unlesbar."""
    turnier = _turnier_mit_daten()
    with app.test_request_context(f"/admin/t/{turnier.slug}/"):
        from app.models import Match, Team
        eintraege = palette_eintraege(
            turnier,
            Team.query.filter_by(tournament_id=turnier.id).all(),
            Match.query.filter_by(tournament_id=turnier.id).all())
    nach_art = {}
    for e in eintraege:
        nach_art.setdefault(e["art"], set()).add(e["icon"])
    assert nach_art["Spiel"] == {"player-play"}
    assert nach_art["Mannschaft"] == {"users-group"}
