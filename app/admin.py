import time
import re
import json
import math
import random
import csv
import io
from datetime import datetime
from functools import wraps
from itertools import combinations
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, abort, g, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import (
    Admin, Tournament, Group, Team, Match, MenuItem,
    TournamentSettings, slugify,
    get_all_settings, get_setting, set_setting, ensure_default_settings,
    calculate_overall_rankings, get_seeded_teams_cross_group,
    calculate_standings,
)
from app.socket_events import broadcast_state

admin_bp = Blueprint("admin", __name__, template_folder="templates")

# Simple hex color validation
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# German round labels
ROUND_LABELS = {1: "Finale", 2: "Halbfinale", 3: "Viertelfinale", 4: "Achtelfinale"}


# ──────────────────────────────────────
# Tournament context decorator
# ──────────────────────────────────────

def tournament_required(f):
    """Load tournament from URL slug into g.tournament."""
    @wraps(f)
    def decorated(*args, **kwargs):
        slug = kwargs.pop("slug")
        tournament = Tournament.query.filter_by(slug=slug).first()
        if not tournament:
            abort(404)
        g.tournament = tournament
        g.tid = tournament.id
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────
# Auth (global, no tournament context)
# ──────────────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.tournament_list"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = Admin.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin.tournament_list"))
        flash("Ungueltige Anmeldedaten.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/login/google")
def login_google():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("Google-Login ist nicht konfiguriert.", "error")
        return redirect(url_for("admin.login"))
    redirect_uri = url_for("admin.login_google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@admin_bp.route("/login/google/callback")
def login_google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash("Google-Anmeldung fehlgeschlagen.", "error")
        return redirect(url_for("admin.login"))

    user_info = token.get("userinfo")
    if not user_info:
        flash("Keine Benutzerinformationen von Google erhalten.", "error")
        return redirect(url_for("admin.login"))

    email = user_info.get("email", "").lower()
    if not email:
        flash("Keine E-Mail von Google erhalten.", "error")
        return redirect(url_for("admin.login"))

    allowed = current_app.config.get("ADMIN_EMAILS", [])
    if not allowed or email not in allowed:
        flash("Diese E-Mail ist nicht als Admin berechtigt.", "error")
        return redirect(url_for("admin.login"))

    admin = Admin.query.filter_by(email=email).first()
    if not admin:
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while Admin.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        admin = Admin(username=username, email=email)
        db.session.add(admin)
        db.session.commit()

    login_user(admin)
    return redirect(url_for("admin.tournament_list"))


@admin_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.landing"))


# ──────────────────────────────────────
# Tournament Management (admin landing)
# ──────────────────────────────────────

@admin_bp.route("/")
@login_required
def tournament_list():
    tournaments = Tournament.query.order_by(
        Tournament.display_order, Tournament.name
    ).all()
    return render_template("admin/tournament_list.html", tournaments=tournaments)


@admin_bp.route("/tournaments", methods=["POST"])
@login_required
def create_tournament():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Turniername erforderlich.", "error")
        return redirect(url_for("admin.tournament_list"))
    slug = slugify(name)
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while Tournament.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    event_date = None
    date_str = request.form.get("event_date", "").strip()
    if date_str:
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    t = Tournament(
        name=name, slug=slug,
        description=request.form.get("description", ""),
        event_date=event_date,
    )
    max_order = db.session.query(db.func.max(Tournament.display_order)).scalar() or 0
    t.display_order = max_order + 1
    db.session.add(t)
    db.session.flush()
    ensure_default_settings(t.id)
    # Set tournament_name setting to the tournament name
    set_setting(t.id, "tournament_name", name)
    db.session.commit()
    flash(f"Turnier '{name}' erstellt.", "success")
    return redirect(url_for("admin.tournament_list"))


@admin_bp.route("/tournaments/<int:tid>/edit", methods=["POST"])
@login_required
def edit_tournament(tid):
    t = db.session.get(Tournament, tid)
    if not t:
        flash("Turnier nicht gefunden.", "error")
        return redirect(url_for("admin.tournament_list"))
    name = request.form.get("name", "").strip()
    if name:
        t.name = name
    desc = request.form.get("description")
    if desc is not None:
        t.description = desc
    date_str = request.form.get("event_date", "").strip()
    if date_str:
        try:
            t.event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    elif "event_date" in request.form:
        t.event_date = None
    db.session.commit()
    flash(f"Turnier '{t.name}' aktualisiert.", "success")
    return redirect(url_for("admin.tournament_list"))


@admin_bp.route("/tournaments/<int:tid>/delete", methods=["POST"])
@login_required
def delete_tournament(tid):
    t = db.session.get(Tournament, tid)
    if not t:
        flash("Turnier nicht gefunden.", "error")
        return redirect(url_for("admin.tournament_list"))
    # Delete settings
    TournamentSettings.query.filter_by(tournament_id=tid).delete()
    db.session.delete(t)
    db.session.commit()
    flash("Turnier geloescht.", "success")
    return redirect(url_for("admin.tournament_list"))


# ──────────────────────────────────────
# Dashboard (per tournament)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/")
@login_required
@tournament_required
def dashboard():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    settings = get_all_settings(t.id)
    groups = Group.query.filter_by(tournament_id=t.id).order_by(
        Group.display_order, Group.name
    ).all()
    teams = Team.query.filter_by(tournament_id=t.id).order_by(Team.name).all()
    matches = Match.query.filter_by(
        is_final=False, tournament_id=t.id
    ).order_by(Match.match_order).all()
    final_matches = Match.query.filter_by(
        is_final=True, tournament_id=t.id
    ).order_by(Match.final_round.desc(), Match.final_position).all()
    return render_template(
        "admin/dashboard.html",
        groups=groups, teams=teams, matches=matches,
        final_matches=final_matches, phase=phase, settings=settings,
        tournament=t,
    )


# ──────────────────────────────────────
# Design Settings (per tournament)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/design", methods=["GET"])
@login_required
@tournament_required
def design():
    t = g.tournament
    settings = get_all_settings(t.id)
    return render_template("admin/design.html", settings=settings, tournament=t)


@admin_bp.route("/t/<slug>/api/settings", methods=["POST"])
@login_required
@tournament_required
def update_settings():
    """Save design settings (colors, tournament name, timer defaults)."""
    t = g.tournament
    data = request.get_json()
    allowed_keys = {
        "tournament_name", "color_title", "color_primary", "color_secondary",
        "default_timer_regular", "default_timer_extra",
    }
    for key in allowed_keys:
        if key not in data:
            continue
        value = str(data[key]).strip()
        if key.startswith("color_") and not _HEX_RE.match(value):
            return jsonify({"error": f"Ungueltige Farbe fuer {key}"}), 400
        if key == "tournament_name" and (len(value) < 1 or len(value) > 100):
            return jsonify({"error": "Name muss 1-100 Zeichen lang sein"}), 400
        if key.startswith("default_timer_"):
            try:
                int_val = int(value)
                if int_val < 60 or int_val > 5400:
                    return jsonify({"error": f"{key}: Wert muss zwischen 60 und 5400 Sekunden liegen"}), 400
            except ValueError:
                return jsonify({"error": f"{key}: Ungueltige Zahl"}), 400
        set_setting(t.id, key, value)

    broadcast_state(t.id)
    return jsonify(get_all_settings(t.id))


@admin_bp.route("/t/<slug>/api/announcement", methods=["POST"])
@login_required
@tournament_required
def update_announcement():
    """Save or clear the announcement message."""
    t = g.tournament
    data = request.get_json()
    text = str(data.get("announcement", "")).strip()[:200]
    set_setting(t.id, "announcement", text)
    broadcast_state(t.id)
    return jsonify({"ok": True, "announcement": text})


# ──────────────────────────────────────
# Phase Management (per tournament)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/api/phase/end-group-stage", methods=["POST"])
@login_required
@tournament_required
def end_group_stage():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        return jsonify({"error": "Gruppenphase ist nicht aktiv"}), 400
    unfinished = Match.query.filter(
        Match.is_final == False,
        Match.status != "finished",
        Match.tournament_id == t.id,
    ).count()
    if unfinished > 0:
        return jsonify({"error": f"Noch {unfinished} Gruppenspiel(e) nicht beendet"}), 400
    set_setting(t.id, "tournament_phase", "FINAL_SETUP")
    broadcast_state(t.id)
    return jsonify({"ok": True, "phase": "FINAL_SETUP"})


@admin_bp.route("/t/<slug>/api/phase/start-final-round", methods=["POST"])
@login_required
@tournament_required
def start_final_round():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase")
    if phase not in ("FINAL_SETUP",):
        return jsonify({"error": "Falscher Turnierstatus"}), 400
    data = request.get_json()
    mode = data.get("mode")
    config = data.get("config", {})
    if mode not in ("classic_ko", "semi_final", "direct_final", "free_ko", "custom"):
        return jsonify({"error": "Ungueltiger Modus"}), 400
    set_setting(t.id, "final_mode", mode)
    try:
        if mode == "classic_ko":
            _generate_classic_ko(t.id, config)
        elif mode == "semi_final":
            _generate_semi_final(t.id, config)
        elif mode == "direct_final":
            _generate_direct_final(t.id, config)
        elif mode == "free_ko":
            _generate_free_ko(t.id, config)
        elif mode == "custom":
            _generate_custom(t.id, config)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    set_setting(t.id, "tournament_phase", "FINAL_ROUND")
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "phase": "FINAL_ROUND"})


@admin_bp.route("/t/<slug>/api/phase/finish-tournament", methods=["POST"])
@login_required
@tournament_required
def finish_tournament():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase")
    if phase != "FINAL_ROUND":
        return jsonify({"error": "Finalrunde nicht aktiv"}), 400
    unfinished = Match.query.filter_by(
        is_final=True, tournament_id=t.id
    ).filter(Match.status != "finished").count()
    if unfinished > 0:
        return jsonify({"error": f"Noch {unfinished} Finalspiel(e) nicht beendet"}), 400
    set_setting(t.id, "tournament_phase", "FINISHED")
    broadcast_state(t.id)
    return jsonify({"ok": True, "phase": "FINISHED"})


@admin_bp.route("/t/<slug>/api/phase/reset", methods=["POST"])
@login_required
@tournament_required
def reset_phase():
    t = g.tournament
    Match.query.filter_by(is_final=True, tournament_id=t.id).delete()
    set_setting(t.id, "tournament_phase", "GROUP_STAGE")
    set_setting(t.id, "final_mode", "")
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "phase": "GROUP_STAGE"})


# ──────────────────────────────────────
# Finals Setup Page
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/finals-setup")
@login_required
@tournament_required
def finals_setup():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    groups = Group.query.filter_by(tournament_id=t.id).order_by(Group.display_order).all()
    rankings = calculate_overall_rankings(t.id)
    teams = Team.query.filter_by(tournament_id=t.id).order_by(Team.name).all()
    teams_json = json.dumps([te.to_dict() for te in teams])
    return render_template(
        "admin/finals_setup.html",
        phase=phase, groups=groups, rankings=rankings,
        teams_json=teams_json, tournament=t,
    )


@admin_bp.route("/t/<slug>/api/rankings/overall")
@login_required
@tournament_required
def overall_rankings():
    t = g.tournament
    return jsonify({"rankings": calculate_overall_rankings(t.id)})


# ──────────────────────────────────────
# Bracket Generation Helpers
# ──────────────────────────────────────

def _round_label(round_num, position, total_in_round):
    base = ROUND_LABELS.get(round_num, f"Runde {round_num}")
    if total_in_round > 1 and round_num > 1:
        return f"{base} {position + 1}"
    return base


def _create_bracket(tournament_id, first_round_pairs, starting_round, platz3=False):
    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == tournament_id
    ).scalar() or 0
    order_counter = max_order + 1
    dur = int(get_setting(tournament_id, "default_timer_regular", "600"))
    rounds_matches = {}

    for rnd in range(1, starting_round + 1):
        num_matches = 2 ** (rnd - 1)
        rounds_matches[rnd] = []
        for pos in range(num_matches):
            if rnd == starting_round and pos < len(first_round_pairs):
                t1_id, t2_id = first_round_pairs[pos]
            else:
                t1_id, t2_id = None, None
            label = _round_label(rnd, pos, num_matches)
            match = Match(
                tournament_id=tournament_id,
                team1_id=t1_id, team2_id=t2_id,
                is_final=True, final_round=rnd, final_position=pos,
                final_label=label,
                timer_duration=dur, timer_remaining=dur,
                match_order=order_counter,
            )
            db.session.add(match)
            db.session.flush()
            rounds_matches[rnd].append(match)
            order_counter += 1

    for rnd in range(starting_round, 1, -1):
        for i, match in enumerate(rounds_matches[rnd]):
            next_idx = i // 2
            next_slot = (i % 2) + 1
            if next_idx < len(rounds_matches[rnd - 1]):
                match.next_match_id = rounds_matches[rnd - 1][next_idx].id
                match.next_match_slot = next_slot

    if platz3 and starting_round >= 2 and 2 in rounds_matches:
        semis = rounds_matches[2]
        platz3_match = Match(
            tournament_id=tournament_id,
            team1_id=None, team2_id=None,
            is_final=True, final_round=1,
            final_position=len(rounds_matches.get(1, [])),
            final_label="Spiel um Platz 3",
            is_loser_match=True,
            timer_duration=dur, timer_remaining=dur,
            match_order=order_counter,
        )
        db.session.add(platz3_match)
        db.session.flush()
        rounds_matches[1].append(platz3_match)
        for slot_idx, semi in enumerate(semis[:2]):
            semi.loser_next_match_id = platz3_match.id
            semi.loser_next_match_slot = slot_idx + 1

    db.session.flush()


def _generate_classic_ko(tournament_id, config):
    round_map = {"achtelfinale": 4, "viertelfinale": 3, "halbfinale": 2, "finale": 1}
    starting_round = round_map.get(config.get("starting_round", "halbfinale"), 2)
    platz3 = config.get("platz3", False)
    num_first_round = 2 ** (starting_round - 1)
    num_teams = num_first_round * 2
    pairs = get_seeded_teams_cross_group(tournament_id, num_teams)
    if len(pairs) < num_first_round:
        raise ValueError(f"Nicht genug Teams. Benoetigt: {num_teams}")
    _create_bracket(tournament_id, pairs, starting_round, platz3)


def _generate_semi_final(tournament_id, config):
    platz3 = config.get("platz3", False)
    overall = calculate_overall_rankings(tournament_id)
    if len(overall) < 4:
        raise ValueError("Mindestens 4 Teams benoetigt")
    pairs = [
        (overall[0]["team"]["id"], overall[3]["team"]["id"]),
        (overall[1]["team"]["id"], overall[2]["team"]["id"]),
    ]
    _create_bracket(tournament_id, pairs, starting_round=2, platz3=platz3)


def _generate_direct_final(tournament_id, config):
    overall = calculate_overall_rankings(tournament_id)
    if len(overall) < 2:
        raise ValueError("Mindestens 2 Teams benoetigt")
    pairs = [(overall[0]["team"]["id"], overall[1]["team"]["id"])]
    _create_bracket(tournament_id, pairs, starting_round=1, platz3=False)


def _generate_free_ko(tournament_id, config):
    num_advance = config.get("num_advance", 4)
    platz3 = config.get("platz3", False)
    if num_advance < 2 or (num_advance & (num_advance - 1)) != 0:
        raise ValueError("Anzahl muss eine Zweierpotenz sein (2, 4, 8, 16)")
    starting_round = int(math.log2(num_advance))
    overall = calculate_overall_rankings(tournament_id)
    if len(overall) < num_advance:
        raise ValueError(f"Nicht genug Teams. Benoetigt: {num_advance}, verfuegbar: {len(overall)}")
    pairs = []
    for i in range(num_advance // 2):
        pairs.append((
            overall[i]["team"]["id"],
            overall[num_advance - 1 - i]["team"]["id"],
        ))
    _create_bracket(tournament_id, pairs, starting_round, platz3)


def _generate_custom(tournament_id, config):
    rounds_data = config.get("rounds", [])
    dur = int(get_setting(tournament_id, "default_timer_regular", "600"))

    # Fallback: old flat format
    if not rounds_data and config.get("matches"):
        matches_data = config["matches"]
        if not matches_data:
            raise ValueError("Keine Spiele angegeben")
        max_order = db.session.query(db.func.max(Match.match_order)).filter(
            Match.tournament_id == tournament_id
        ).scalar() or 0
        for i, md in enumerate(matches_data):
            t1 = md.get("team1_id")
            t2 = md.get("team2_id")
            label = md.get("label", f"Finalspiel {i + 1}")
            m = Match(
                tournament_id=tournament_id,
                team1_id=t1 if t1 else None,
                team2_id=t2 if t2 else None,
                is_final=True, final_round=1, final_position=i,
                final_label=label,
                timer_duration=dur, timer_remaining=dur,
                match_order=max_order + 1 + i,
            )
            db.session.add(m)
        db.session.flush()
        return

    if not rounds_data:
        raise ValueError("Keine Runden angegeben")

    regular_rounds = [r for r in rounds_data if not r.get("is_loser_round")]
    num_regular = len(regular_rounds)

    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == tournament_id
    ).scalar() or 0
    matches_by_label = {}
    order_counter = max_order + 1
    regular_idx = 0

    # First pass: create all matches
    for rd in rounds_data:
        is_loser = rd.get("is_loser_round", False)
        if is_loser:
            round_num = 1
        else:
            round_num = num_regular - regular_idx
            regular_idx += 1

        for mi, md in enumerate(rd.get("matches", [])):
            label = md.get("label", f"Spiel {order_counter - max_order}")
            t1_type = md.get("team1_type", "")
            t1_value = md.get("team1_value", "")
            t2_type = md.get("team2_type", "")
            t2_value = md.get("team2_value", "")

            t1_id = None
            t2_id = None
            if t1_type == "team" and t1_value:
                try:
                    t1_id = int(t1_value)
                except (ValueError, TypeError):
                    pass
            if t2_type == "team" and t2_value:
                try:
                    t2_id = int(t2_value)
                except (ValueError, TypeError):
                    pass

            m = Match(
                tournament_id=tournament_id,
                team1_id=t1_id, team2_id=t2_id,
                is_final=True, final_round=round_num,
                final_position=mi, final_label=label,
                match_order=order_counter,
                is_loser_match=is_loser,
                timer_duration=dur, timer_remaining=dur,
            )
            db.session.add(m)
            db.session.flush()
            matches_by_label[label] = m
            order_counter += 1

    # Second pass: link winner/loser references
    for rd in rounds_data:
        for md in rd.get("matches", []):
            label = md.get("label", "")
            target = matches_by_label.get(label)
            if not target:
                continue
            for slot, prefix in [(1, "team1"), (2, "team2")]:
                ref_type = md.get(f"{prefix}_type", "")
                ref_value = md.get(f"{prefix}_value", "")
                if not ref_type or not ref_value or ref_type == "team":
                    continue
                source = matches_by_label.get(ref_value)
                if not source:
                    continue
                if ref_type == "winner":
                    source.next_match_id = target.id
                    source.next_match_slot = slot
                elif ref_type == "loser":
                    source.loser_next_match_id = target.id
                    source.loser_next_match_slot = slot

    db.session.flush()


# ──────────────────────────────────────
# Auto-Advancement
# ──────────────────────────────────────

def _advance_winner(match):
    if match.score_team1 > match.score_team2:
        winner_id = match.team1_id
        loser_id = match.team2_id
    else:
        winner_id = match.team2_id
        loser_id = match.team1_id

    if match.next_match_id and match.next_match_slot:
        next_match = db.session.get(Match, match.next_match_id)
        if next_match:
            if match.next_match_slot == 1:
                next_match.team1_id = winner_id
            else:
                next_match.team2_id = winner_id

    if match.loser_next_match_id and match.loser_next_match_slot:
        loser_match = db.session.get(Match, match.loser_next_match_id)
        if loser_match:
            if match.loser_next_match_slot == 1:
                loser_match.team1_id = loser_id
            else:
                loser_match.team2_id = loser_id


# ──────────────────────────────────────
# Group Management (per tournament)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/groups", methods=["POST"])
@login_required
@tournament_required
def create_group():
    t = g.tournament
    name = request.form.get("name", "").strip()
    if not name:
        flash("Gruppenname erforderlich.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    if Group.query.filter_by(name=name, tournament_id=t.id).first():
        flash("Gruppe existiert bereits.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    max_order = db.session.query(db.func.max(Group.display_order)).filter(
        Group.tournament_id == t.id
    ).scalar() or 0
    db.session.add(Group(name=name, display_order=max_order + 1, tournament_id=t.id))
    db.session.commit()
    broadcast_state(t.id)
    flash(f"Gruppe '{name}' erstellt.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/groups/<int:gid>/edit", methods=["POST"])
@login_required
@tournament_required
def edit_group(gid):
    t = g.tournament
    group = db.session.get(Group, gid)
    if not group or group.tournament_id != t.id:
        flash("Gruppe nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    name = request.form.get("name", "").strip()
    if name:
        group.name = name
    db.session.commit()
    broadcast_state(t.id)
    flash(f"Gruppe '{group.name}' aktualisiert.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/groups/<int:gid>/delete", methods=["POST"])
@login_required
@tournament_required
def delete_group(gid):
    t = g.tournament
    group = db.session.get(Group, gid)
    if not group or group.tournament_id != t.id:
        flash("Gruppe nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    if Team.query.filter_by(group_id=gid).count():
        flash("Gruppe enthaelt noch Teams.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    if Match.query.filter_by(group_id=gid).count():
        flash("Gruppe enthaelt noch Spiele.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    db.session.delete(group)
    db.session.commit()
    broadcast_state(t.id)
    flash("Gruppe geloescht.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


# ──────────────────────────────────────
# Team Management (per tournament)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/teams", methods=["POST"])
@login_required
@tournament_required
def create_team():
    t = g.tournament
    name = request.form.get("name", "").strip()
    if not name:
        flash("Teamname erforderlich.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    if Team.query.filter_by(name=name, tournament_id=t.id).first():
        flash("Team existiert bereits.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    db.session.add(Team(
        name=name,
        tournament_id=t.id,
        logo_url=request.form.get("logo_url", ""),
        players=request.form.get("players", ""),
        group_id=request.form.get("group_id", type=int) or None,
    ))
    db.session.commit()
    broadcast_state(t.id)
    flash(f"Team '{name}' erstellt.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/teams/<int:tid>/edit", methods=["POST"])
@login_required
@tournament_required
def edit_team(tid):
    t = g.tournament
    team = db.session.get(Team, tid)
    if not team or team.tournament_id != t.id:
        flash("Team nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    team.name = request.form.get("name", team.name).strip()
    team.logo_url = request.form.get("logo_url", team.logo_url)
    team.players = request.form.get("players", team.players)
    gid = request.form.get("group_id", type=int)
    team.group_id = gid if gid else None
    db.session.commit()
    broadcast_state(t.id)
    flash(f"Team '{team.name}' aktualisiert.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/teams/<int:tid>/delete", methods=["POST"])
@login_required
@tournament_required
def delete_team(tid):
    t = g.tournament
    team = db.session.get(Team, tid)
    if not team or team.tournament_id != t.id:
        flash("Team nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    if Match.query.filter(
        (Match.team1_id == tid) | (Match.team2_id == tid)
    ).count():
        flash("Team ist in Spielen zugeordnet.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    db.session.delete(team)
    db.session.commit()
    broadcast_state(t.id)
    flash("Team geloescht.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/api/teams/import-csv", methods=["POST"])
@login_required
@tournament_required
def import_teams_csv():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        return jsonify({"error": "Nur in der Gruppenphase moeglich"}), 400

    data = request.get_json()
    csv_text = data.get("csv", "").strip()
    if not csv_text:
        return jsonify({"error": "Keine CSV-Daten angegeben"}), 400

    reader = csv.reader(io.StringIO(csv_text), delimiter=",")
    created = 0
    skipped = []
    errors = []

    for row_num, row in enumerate(reader, 1):
        if not row or not any(cell.strip() for cell in row):
            continue
        first = row[0].strip().lower()
        if first in ("mannschaftsname", "teamname", "name", "team"):
            continue
        name = row[0].strip() if len(row) > 0 else ""
        group_name = row[1].strip() if len(row) > 1 else ""
        logo_url = row[2].strip() if len(row) > 2 else ""
        if not name:
            errors.append(f"Zeile {row_num}: Kein Teamname")
            continue
        if Team.query.filter_by(name=name, tournament_id=t.id).first():
            skipped.append(name)
            continue
        if name in [team.name for team in db.session.new if isinstance(team, Team)]:
            skipped.append(name)
            continue
        group_id = None
        if group_name:
            group = Group.query.filter_by(name=group_name, tournament_id=t.id).first()
            if not group:
                existing_new = [grp for grp in db.session.new if isinstance(grp, Group) and grp.name == group_name and grp.tournament_id == t.id]
                if existing_new:
                    group = existing_new[0]
                else:
                    max_order = db.session.query(db.func.max(Group.display_order)).filter(
                        Group.tournament_id == t.id
                    ).scalar() or 0
                    group = Group(name=group_name, display_order=max_order + 1, tournament_id=t.id)
                    db.session.add(group)
                    db.session.flush()
            group_id = group.id
        db.session.add(Team(name=name, logo_url=logo_url, group_id=group_id, tournament_id=t.id))
        created += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Datenbankfehler: {str(e)}"}), 400
    broadcast_state(t.id)
    msg = f"{created} Team(s) importiert."
    if skipped:
        msg += f" {len(skipped)} uebersprungen (existieren bereits: {', '.join(skipped)})."
    if errors:
        msg += f" {len(errors)} Fehler: {'; '.join(errors)}"
    return jsonify({"ok": True, "created": created, "skipped": len(skipped), "message": msg})


# ──────────────────────────────────────
# Match Management (per tournament)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/matches", methods=["POST"])
@login_required
@tournament_required
def create_match():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        flash("Gruppenphase ist bereits beendet.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    t1 = request.form.get("team1_id", type=int)
    t2 = request.form.get("team2_id", type=int)
    gid = request.form.get("group_id", type=int)
    if not t1 or not t2 or t1 == t2:
        flash("Zwei verschiedene Teams auswaehlen.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    if not gid:
        flash("Gruppe muss ausgewaehlt werden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    team1 = db.session.get(Team, t1)
    team2 = db.session.get(Team, t2)
    if not team1 or not team2:
        flash("Team nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    if team1.group_id != gid or team2.group_id != gid:
        flash("Beide Teams muessen in der ausgewaehlten Gruppe sein.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    default_dur = int(get_setting(t.id, "default_timer_regular", "600"))
    dur = request.form.get("timer_duration", default_dur, type=int)
    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == t.id
    ).scalar() or 0
    db.session.add(Match(
        tournament_id=t.id,
        team1_id=t1, team2_id=t2,
        group_id=gid,
        timer_duration=dur, timer_remaining=dur,
        match_order=max_order + 1,
    ))
    db.session.commit()
    broadcast_state(t.id)
    flash("Spiel erstellt.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/matches/<int:mid>/delete", methods=["POST"])
@login_required
@tournament_required
def delete_match(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        flash("Spiel nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    db.session.delete(match)
    db.session.commit()
    broadcast_state(t.id)
    flash("Spiel geloescht.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/api/matches/reorder", methods=["POST"])
@login_required
@tournament_required
def reorder_matches():
    t = g.tournament
    data = request.get_json()
    order = data.get("order", [])
    if not isinstance(order, list):
        return jsonify({"error": "order muss eine Liste sein"}), 400
    for idx, match_id in enumerate(order):
        match = db.session.get(Match, int(match_id))
        if match and match.tournament_id == t.id:
            match.match_order = idx
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True})


@admin_bp.route("/t/<slug>/api/matches/generate-round-robin", methods=["POST"])
@login_required
@tournament_required
def generate_round_robin():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        return jsonify({"error": "Nur in der Gruppenphase moeglich"}), 400

    groups = Group.query.filter_by(tournament_id=t.id).all()
    if not groups:
        return jsonify({"error": "Keine Gruppen vorhanden"}), 400

    existing = set()
    for m in Match.query.filter_by(is_final=False, tournament_id=t.id).all():
        if m.team1_id and m.team2_id:
            existing.add((min(m.team1_id, m.team2_id), max(m.team1_id, m.team2_id)))

    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == t.id
    ).scalar() or 0
    dur = int(get_setting(t.id, "default_timer_regular", "600"))
    created = 0
    new_matches = []

    for group in groups:
        team_ids = [te.id for te in group.teams]
        if len(team_ids) < 2:
            continue
        for t1_id, t2_id in combinations(team_ids, 2):
            pair = (min(t1_id, t2_id), max(t1_id, t2_id))
            if pair in existing:
                continue
            new_matches.append((t1_id, t2_id, group.id))
            existing.add(pair)

    random.shuffle(new_matches)

    for t1_id, t2_id, gid in new_matches:
        max_order += 1
        db.session.add(Match(
            tournament_id=t.id,
            team1_id=t1_id, team2_id=t2_id,
            group_id=gid,
            timer_duration=dur, timer_remaining=dur,
            match_order=max_order,
        ))
        created += 1

    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "created": created})


# ──────────────────────────────────────
# Match Control (Live)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/matches/<int:mid>/control")
@login_required
@tournament_required
def match_control(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        flash("Spiel nicht gefunden.", "error")
        return redirect(url_for("admin.dashboard", slug=t.slug))
    extra_time = int(get_setting(t.id, "default_timer_extra", "300"))

    if match.is_final:
        all_matches = (
            Match.query.filter_by(is_final=True, tournament_id=t.id)
            .order_by(Match.final_round.desc(), Match.final_position)
            .all()
        )
    else:
        all_matches = (
            Match.query.filter_by(is_final=False, tournament_id=t.id)
            .order_by(Match.match_order)
            .all()
        )
    match_ids = [m.id for m in all_matches]
    idx = match_ids.index(mid) if mid in match_ids else -1
    prev_match_id = match_ids[idx - 1] if idx > 0 else None
    next_match_id = match_ids[idx + 1] if idx >= 0 and idx < len(match_ids) - 1 else None

    return render_template(
        "admin/match_control.html",
        match=match, extra_time=extra_time,
        prev_match_id=prev_match_id, next_match_id=next_match_id,
        tournament=t,
    )


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/score", methods=["POST"])
@login_required
@tournament_required
def update_score(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Nicht gefunden"}), 404
    data = request.get_json()
    if "score_team1" in data:
        match.score_team1 = max(0, int(data["score_team1"]))
    if "score_team2" in data:
        match.score_team2 = max(0, int(data["score_team2"]))
    db.session.commit()
    broadcast_state(t.id)
    return jsonify(match.to_dict())


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/status", methods=["POST"])
@login_required
@tournament_required
def update_status(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Nicht gefunden"}), 404
    data = request.get_json()
    new_status = data.get("status")
    if new_status not in ("planned", "live", "finished"):
        return jsonify({"error": "Ungueltiger Status"}), 400
    if new_status == "live":
        current_live = Match.query.filter_by(status="live", tournament_id=t.id).first()
        if current_live and current_live.id != mid:
            return jsonify({"error": "Es laeuft bereits ein Spiel"}), 400
    if new_status == "finished" and match.is_final and match.next_match_id:
        if match.score_team1 == match.score_team2:
            return jsonify({"error": "Finalspiele duerfen nicht unentschieden enden"}), 400
    match.status = new_status
    if new_status == "finished":
        match.timer_running = False
        match.timer_started_at = None
        if match.is_final:
            _advance_winner(match)
    db.session.commit()
    broadcast_state(t.id)
    return jsonify(match.to_dict())


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/timer", methods=["POST"])
@login_required
@tournament_required
def control_timer(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Nicht gefunden"}), 404
    data = request.get_json()
    action = data.get("action")

    if action == "start":
        if not match.timer_running:
            match.timer_running = True
            match.timer_started_at = time.time()
            if match.status == "planned":
                live = Match.query.filter_by(status="live", tournament_id=t.id).first()
                if live and live.id != mid:
                    return jsonify({"error": "Es laeuft bereits ein Spiel"}), 400
                match.status = "live"
    elif action == "pause":
        if match.timer_running and match.timer_started_at:
            elapsed = time.time() - match.timer_started_at
            match.timer_remaining = max(0, match.timer_remaining - int(elapsed))
            match.timer_running = False
            match.timer_started_at = None
    elif action == "reset":
        match.timer_remaining = match.timer_duration
        match.timer_running = False
        match.timer_started_at = None
        match.is_extra_time = False
    elif action == "set":
        dur = data.get("duration", 600)
        match.timer_duration = dur
        match.timer_remaining = dur
        match.timer_running = False
        match.timer_started_at = None
        if data.get("is_extra_time"):
            match.is_extra_time = True
    else:
        return jsonify({"error": "Ungueltige Aktion"}), 400

    db.session.commit()
    broadcast_state(t.id)
    return jsonify(match.to_dict())


# ──────────────────────────────────────
# Menu / Speisekarte (global)
# ──────────────────────────────────────

@admin_bp.route("/speisekarte")
@login_required
def menu_admin():
    speisen = MenuItem.query.filter_by(category="speise").order_by(MenuItem.display_order).all()
    getraenke = MenuItem.query.filter_by(category="getraenk").order_by(MenuItem.display_order).all()
    return render_template("admin/menu.html", speisen=speisen, getraenke=getraenke)


@admin_bp.route("/speisekarte/add", methods=["POST"])
@login_required
def menu_add():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name erforderlich.", "error")
        return redirect(url_for("admin.menu_admin"))
    price = request.form.get("price", "").strip()
    category = request.form.get("category", "speise")
    if category not in ("speise", "getraenk"):
        category = "speise"
    description = request.form.get("description", "").strip()
    max_order = db.session.query(db.func.max(MenuItem.display_order)).filter(
        MenuItem.category == category
    ).scalar() or 0
    item = MenuItem(
        name=name, price=price, category=category,
        description=description, display_order=max_order + 1,
    )
    db.session.add(item)
    db.session.commit()
    flash(f"'{name}' hinzugefuegt.", "success")
    return redirect(url_for("admin.menu_admin"))


@admin_bp.route("/speisekarte/<int:item_id>/edit", methods=["POST"])
@login_required
def menu_edit(item_id):
    item = db.session.get(MenuItem, item_id)
    if not item:
        flash("Eintrag nicht gefunden.", "error")
        return redirect(url_for("admin.menu_admin"))
    name = request.form.get("name", "").strip()
    if name:
        item.name = name
    price = request.form.get("price")
    if price is not None:
        item.price = price.strip()
    description = request.form.get("description")
    if description is not None:
        item.description = description.strip()
    db.session.commit()
    flash(f"'{item.name}' aktualisiert.", "success")
    return redirect(url_for("admin.menu_admin"))


@admin_bp.route("/speisekarte/<int:item_id>/delete", methods=["POST"])
@login_required
def menu_delete(item_id):
    item = db.session.get(MenuItem, item_id)
    if not item:
        flash("Eintrag nicht gefunden.", "error")
        return redirect(url_for("admin.menu_admin"))
    name = item.name
    db.session.delete(item)
    db.session.commit()
    flash(f"'{name}' geloescht.", "success")
    return redirect(url_for("admin.menu_admin"))
