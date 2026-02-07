from flask import Blueprint, render_template, jsonify, request, g, abort
from app.models import (
    Tournament, Group, Match, MenuItem, calculate_standings, get_all_settings,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    tournaments = Tournament.query.filter_by(is_active=True).order_by(
        Tournament.display_order, Tournament.name
    ).all()
    return render_template("landing.html", tournaments=tournaments)


@main_bp.route("/t/<slug>/")
def tournament_view(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        abort(404)
    g.tournament = tournament
    groups = Group.query.filter_by(tournament_id=tournament.id).order_by(
        Group.display_order, Group.name
    ).all()
    return render_template("index.html", groups=groups, tournament=tournament)


@main_bp.route("/t/<slug>/api/state")
def api_state(slug):
    """Full tournament state for frontend (HTTP fallback for WebSocket)."""
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        return jsonify({"error": "not found"}), 404

    tid = tournament.id

    live_match = Match.query.filter_by(status="live", tournament_id=tid).first()

    past_matches = (
        Match.query.filter_by(status="finished", is_final=False, tournament_id=tid)
        .order_by(Match.match_order.desc()).all()
    )
    upcoming_matches = (
        Match.query.filter_by(status="planned", is_final=False, tournament_id=tid)
        .order_by(Match.match_order.asc()).all()
    )

    final_matches = (
        Match.query.filter_by(is_final=True, tournament_id=tid)
        .order_by(Match.final_round.desc(), Match.final_position).all()
    )

    groups = Group.query.filter_by(tournament_id=tid).order_by(
        Group.display_order, Group.name
    ).all()
    standings_by_group = {}
    for grp in groups:
        standings_by_group[grp.id] = {
            "group": grp.to_dict(),
            "standings": calculate_standings(group_id=grp.id),
        }

    return jsonify({
        "tournament": tournament.to_dict(),
        "live_match": live_match.to_dict() if live_match else None,
        "past_matches": [m.to_dict() for m in past_matches],
        "upcoming_matches": [m.to_dict() for m in upcoming_matches],
        "final_matches": [m.to_dict() for m in final_matches],
        "standings_by_group": standings_by_group,
        "groups": [grp.to_dict() for grp in groups],
        "settings": get_all_settings(tid),
    })


@main_bp.route("/speisekarte")
def speisekarte():
    speisen = MenuItem.query.filter_by(category="speise").order_by(MenuItem.display_order).all()
    getraenke = MenuItem.query.filter_by(category="getraenk").order_by(MenuItem.display_order).all()
    return render_template("speisekarte.html", speisen=speisen, getraenke=getraenke)
