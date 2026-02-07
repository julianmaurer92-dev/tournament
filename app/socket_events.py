from flask import current_app
from flask_socketio import join_room, emit
from app import socketio
from app.models import (
    Tournament, Group, Match, calculate_standings, get_all_settings,
)


def _build_state(tournament_id):
    """Assemble the full tournament state dict for a specific tournament."""
    tournament = db_get_tournament(tournament_id)
    if not tournament:
        return {}

    live_match = Match.query.filter_by(
        status="live", tournament_id=tournament_id
    ).first()

    # Group matches only (non-final)
    past_matches = (
        Match.query.filter_by(
            status="finished", is_final=False, tournament_id=tournament_id
        )
        .order_by(Match.match_order.desc()).all()
    )
    upcoming_matches = (
        Match.query.filter_by(
            status="planned", is_final=False, tournament_id=tournament_id
        )
        .order_by(Match.match_order.asc()).all()
    )

    # Final matches (all statuses)
    final_matches = (
        Match.query.filter_by(is_final=True, tournament_id=tournament_id)
        .order_by(Match.final_round.desc(), Match.final_position).all()
    )

    groups = Group.query.filter_by(tournament_id=tournament_id).order_by(
        Group.display_order, Group.name
    ).all()
    standings_by_group = {}
    for g in groups:
        standings_by_group[g.id] = {
            "group": g.to_dict(),
            "standings": calculate_standings(group_id=g.id),
        }

    return {
        "tournament": tournament.to_dict(),
        "live_match": live_match.to_dict() if live_match else None,
        "past_matches": [m.to_dict() for m in past_matches],
        "upcoming_matches": [m.to_dict() for m in upcoming_matches],
        "final_matches": [m.to_dict() for m in final_matches],
        "standings_by_group": standings_by_group,
        "groups": [g.to_dict() for g in groups],
        "settings": get_all_settings(tournament_id),
    }


def db_get_tournament(tournament_id):
    """Helper to get tournament by id."""
    from app import db
    return db.session.get(Tournament, tournament_id)


def broadcast_state(tournament_id):
    """Push current state to all clients watching a specific tournament."""
    with current_app.app_context():
        room = f"tournament_{tournament_id}"
        socketio.emit("state_update", _build_state(tournament_id), room=room)


@socketio.on("join_tournament")
def handle_join(data):
    """Client requests to join a tournament room."""
    tournament_id = data.get("tournament_id") if data else None
    if tournament_id:
        room = f"tournament_{tournament_id}"
        join_room(room)
        emit("state_update", _build_state(tournament_id))


@socketio.on("connect")
def handle_connect():
    # Don't auto-send state; wait for join_tournament
    pass


@socketio.on("request_state")
def handle_request_state(data=None):
    """Explicit state request. Client must specify tournament_id."""
    if data and data.get("tournament_id"):
        tournament_id = data["tournament_id"]
        emit("state_update", _build_state(tournament_id))
