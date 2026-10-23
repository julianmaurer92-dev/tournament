"""Tests fuer das Loeschen von Turnieren und Teams.

Hintergrund: Beim Umstellen des Seed-Skripts flog ein Fehler auf, der die
Live-App betrifft – ein Turnier mit erfassten Startgebuehren liess sich nicht
loeschen, weil TeamPayment keine Loeschweitergabe hatte. SQLAlchemy versucht
dann, den Primaerschluessel team_payment.team_id auf NULL zu setzen, und
bricht ab ("Dependency rule on column 'team.id' tried to blank-out primary
key column 'team_payment.team_id'").
"""
from app import db
from app.models import (
    Match, Registration, Team, TeamPayment, Tournament, TournamentSettings,
)
from tests.conftest import make_group, make_match, make_team, make_tournament


def test_turnier_mit_startgebuehren_loeschen(app, admin_client):
    t = make_tournament("Weg Cup")
    gr = make_group(t)
    team = make_team(t, "Zahler FC", gr)
    db.session.add(TeamPayment(team_id=team.id, paid=True, amount=25.0,
                               receipt_number="2026-007"))
    db.session.commit()

    resp = admin_client.post(f"/admin/tournaments/{t.id}/delete",
                             follow_redirects=True)
    assert resp.status_code == 200
    assert Tournament.query.filter_by(name="Weg Cup").count() == 0
    assert Team.query.count() == 0
    assert TeamPayment.query.count() == 0, "Zahlung muss mitgeloescht werden"


def test_turnier_mit_allem_drum_und_dran_loeschen(app, admin_client):
    """Gruppen, Teams, Spiele, Zahlungen, Einstellungen, Anmeldungen."""
    t = make_tournament("Voll Cup")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    make_match(t, a, b, gr, 1)
    db.session.add(TeamPayment(team_id=a.id, paid=True, amount=25.0))
    db.session.add(Registration(
        tournament_id=t.id, club_name="A", contact_name="X",
        contact_email="x@y.de", token="tok-voll", team_id=a.id,
    ))
    db.session.commit()

    admin_client.post(f"/admin/tournaments/{t.id}/delete",
                      follow_redirects=True)

    assert Tournament.query.count() == 0
    assert Team.query.count() == 0
    assert Match.query.count() == 0
    assert TeamPayment.query.count() == 0
    assert Registration.query.count() == 0
    assert TournamentSettings.query.count() == 0


def test_team_mit_zahlung_loeschen(app, admin_client):
    t = make_tournament("Team Weg Cup")
    gr = make_group(t)
    team = make_team(t, "Weg FC", gr)
    db.session.add(TeamPayment(team_id=team.id, paid=False, amount=25.0))
    db.session.commit()

    resp = admin_client.post(
        f"/admin/t/{t.slug}/teams/{team.id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert Team.query.count() == 0
    assert TeamPayment.query.count() == 0


def test_team_aus_bestaetigter_anmeldung_loeschen(app, admin_client):
    """Die Anmeldung bleibt als Historie, verliert aber den Teamverweis."""
    t = make_tournament("Anmelde Weg Cup")
    gr = make_group(t)
    team = make_team(t, "Weg FC", gr)
    anmeldung = Registration(
        tournament_id=t.id, club_name="Weg FC", contact_name="X",
        contact_email="x@y.de", token="tok-weg", team_id=team.id,
        status="bestaetigt",
    )
    db.session.add(anmeldung)
    db.session.commit()

    resp = admin_client.post(
        f"/admin/t/{t.slug}/teams/{team.id}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert Team.query.count() == 0

    anmeldung = Registration.query.one()
    assert anmeldung.team_id is None, "Verweis auf das geloeschte Team muss weg"
    assert anmeldung.club_name == "Weg FC", "Historie bleibt erhalten"


def test_team_mit_spielen_wird_nicht_geloescht(app, admin_client):
    t = make_tournament("Schutz Cup")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    make_match(t, a, b, gr, 1)

    resp = admin_client.post(f"/admin/t/{t.slug}/teams/{a.id}/delete",
                             follow_redirects=True)
    assert "in Spielen zugeordnet".encode() in resp.data
    assert Team.query.count() == 2


def test_gruppe_mit_teams_wird_nicht_geloescht(app, admin_client):
    t = make_tournament("Gruppen Cup")
    gr = make_group(t)
    make_team(t, "A", gr)

    resp = admin_client.post(f"/admin/t/{t.slug}/groups/{gr.id}/delete",
                             follow_redirects=True)
    assert "enthaelt noch Teams".encode() in resp.data
    assert t.groups.count() == 1


def test_turnier_direkt_ueber_die_orm_loeschen(app):
    """db.session.delete(turnier) muss funktionieren.

    Die Loeschroute raeumt die Einstellungen vorher von Hand weg und
    verdeckte damit, dass TournamentSettings keine Loeschweitergabe hatte.
    Jeder andere Aufrufer (Skripte, Import, kuenftige Features) lief in
    einen AssertionError.
    """
    t = make_tournament("ORM Weg Cup")
    gr = make_group(t)
    a = make_team(t, "A", gr)
    b = make_team(t, "B", gr)
    make_match(t, a, b, gr, 1)
    db.session.add(TeamPayment(team_id=a.id, paid=True, amount=25.0))
    db.session.commit()

    db.session.delete(t)
    db.session.commit()

    assert Tournament.query.count() == 0
    assert TournamentSettings.query.count() == 0
    assert Team.query.count() == 0
    assert Match.query.count() == 0
    assert TeamPayment.query.count() == 0
