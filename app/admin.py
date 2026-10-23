import time
import re
import json
import math
import random
import csv
import io
from datetime import date, datetime, time as dtime, timedelta, timezone
from itertools import combinations
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, abort, g, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from app import db, oauth
from app.models import (
    Admin, Tournament, Group, Team, Match, MenuItem,
    TournamentSettings, UserTournamentAccess, TeamPayment, slugify,
    get_all_settings, get_setting, set_setting, ensure_default_settings,
    calculate_overall_rankings, get_seeded_teams_cross_group,
    calculate_standings,
)
from app.auth import editor_required, superadmin_required, tournament_required
from app.security import anmeldebremse
from app.spielplan import Begegnung, erstelle_spielplan, finde_konflikte
from app.socket_events import broadcast_state

admin_bp = Blueprint("admin", __name__, template_folder="templates")


def euros_to_words(amount):
    """Convert euro amount to German words for receipts."""
    if not amount:
        return "null"
    _ones = ["", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
             "acht", "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn",
             "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn"]
    _tens = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig",
             "sechzig", "siebzig", "achtzig", "neunzig"]

    def _u100(n):
        if n == 0: return ""
        if n < 20: return _ones[n]
        o = _ones[n % 10]
        return (o + "und" + _tens[n // 10]) if o else _tens[n // 10]

    def _u1000(n):
        if n == 0: return ""
        if n < 100: return _u100(n)
        return _ones[n // 100] + "hundert" + _u100(n % 100)

    n = int(amount)  # floor, not round
    cents = round((amount - n) * 100)
    if n == 0:
        word = "null"
    elif n < 1000:
        word = _u1000(n)
    elif n < 1_000_000:
        t = ("ein" if n // 1000 == 1 else _u1000(n // 1000)) + "tausend"
        word = t + _u1000(n % 1000)
    else:
        word = str(n)
    word = word.capitalize()
    if cents:
        word += f" {cents}/100"
    return word

# Simple hex color validation
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Erlaubte Anzahl Spielfelder je Turnier
FELD_OPTIONEN = tuple(str(n) for n in range(1, 7))

# JSON-Backup: aktuelle Exportversion und die, die wir lesen koennen
EXPORT_VERSION = "2"
SUPPORTED_IMPORT_VERSIONS = ("1", "2")

# German round labels
ROUND_LABELS = {1: "Finale", 2: "Halbfinale", 3: "Viertelfinale", 4: "Achtelfinale"}


# Zugriffs-Decorators liegen in app/auth.py (siehe Import oben) – sie werden
# auch von app/anmeldung.py gebraucht.


# ──────────────────────────────────────
# Auth (global, no tournament context)
# ──────────────────────────────────────

def _bremsschluessel(username):
    """Schluessel fuer die Anmeldebremse: Benutzername + Absender-IP."""
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    ip = ip.split(",")[0].strip()
    return f"{username.lower()}|{ip}"


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.tournament_list"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        schluessel = _bremsschluessel(username)

        rest = anmeldebremse.restsperre(schluessel)
        if rest:
            minuten = max(1, rest // 60)
            flash(
                f"Zu viele Fehlversuche. Bitte in {minuten} Minute(n) "
                "erneut versuchen.", "error",
            )
            return render_template("admin/login.html"), 429

        user = Admin.query.filter_by(username=username).first()
        if user and user.check_password(password):
            anmeldebremse.erfolg(schluessel)
            login_user(user)
            return redirect(url_for("admin.tournament_list"))

        gesperrt = anmeldebremse.fehlversuch(schluessel)
        if gesperrt:
            flash(
                f"Zu viele Fehlversuche. Anmeldung fuer "
                f"{gesperrt // 60} Minuten gesperrt.", "error",
            )
        else:
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
    if current_user.role == "superadmin":
        tournaments = Tournament.query.order_by(
            Tournament.display_order, Tournament.name
        ).all()
    else:
        accessible_ids = [a.tournament_id for a in current_user.tournament_access.all()]
        tournaments = Tournament.query.filter(
            Tournament.id.in_(accessible_ids)
        ).order_by(Tournament.display_order, Tournament.name).all()
    final_modes = {t.id: get_setting(t.id, "final_mode", "") for t in tournaments}
    num_fields_map = {t.id: get_setting(t.id, "num_fields", "1") for t in tournaments}
    hide_results_map = {t.id: get_setting(t.id, "hide_results", "0") for t in tournaments}
    return render_template("admin/tournament_list.html", tournaments=tournaments, final_modes=final_modes, num_fields_map=num_fields_map, hide_results_map=hide_results_map)


@admin_bp.route("/tournaments", methods=["POST"])
@login_required
@superadmin_required
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
    event_time = request.form.get("event_time", "").strip() or None
    t = Tournament(
        name=name, slug=slug,
        description=request.form.get("description", ""),
        event_date=event_date,
        event_time=event_time,
    )
    max_order = db.session.query(db.func.max(Tournament.display_order)).scalar() or 0
    t.display_order = max_order + 1
    db.session.add(t)
    db.session.flush()
    ensure_default_settings(t.id)
    # Set tournament_name setting to the tournament name
    set_setting(t.id, "tournament_name", name)
    final_mode = request.form.get("final_mode", "").strip()
    if final_mode:
        set_setting(t.id, "final_mode", final_mode)
    num_fields = request.form.get("num_fields", "1").strip()
    if num_fields in FELD_OPTIONEN:
        set_setting(t.id, "num_fields", num_fields)
    hide_table = "1" if request.form.get("hide_table") == "1" else "0"
    set_setting(t.id, "hide_table", hide_table)
    hide_scores = "1" if request.form.get("hide_scores") == "1" else "0"
    set_setting(t.id, "hide_scores", hide_scores)
    # Timer settings (form sends minutes, store as seconds)
    try:
        timer_regular_min = float(request.form.get("timer_regular_min", "").strip() or "10")
        secs = max(60, min(5400, int(round(timer_regular_min * 60))))
        set_setting(t.id, "default_timer_regular", str(secs))
    except (ValueError, AttributeError):
        pass
    try:
        timer_extra_min = float(request.form.get("timer_extra_min", "").strip() or "5")
        secs = max(30, min(1800, int(round(timer_extra_min * 60))))
        set_setting(t.id, "default_timer_extra", str(secs))
    except (ValueError, AttributeError):
        pass
    db.session.commit()
    flash(f"Turnier '{name}' erstellt.", "success")
    return redirect(url_for("admin.tournament_list"))


@admin_bp.route("/tournaments/<int:tid>/edit", methods=["POST"])
@login_required
@superadmin_required
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
    t.event_time = request.form.get("event_time", "").strip() or None
    final_mode = request.form.get("final_mode", "").strip()
    set_setting(t.id, "final_mode", final_mode)
    num_fields = request.form.get("num_fields", "").strip()
    if num_fields in FELD_OPTIONEN:
        set_setting(t.id, "num_fields", num_fields)
    hide_table = "1" if request.form.get("hide_table") == "1" else "0"
    set_setting(t.id, "hide_table", hide_table)
    hide_scores = "1" if request.form.get("hide_scores") == "1" else "0"
    set_setting(t.id, "hide_scores", hide_scores)
    db.session.commit()
    flash(f"Turnier '{t.name}' aktualisiert.", "success")
    next_page = request.args.get("next", "")
    if next_page == "admin":
        return redirect(url_for("admin.tournament_admin", slug=t.slug))
    return redirect(url_for("admin.tournament_list"))


@admin_bp.route("/tournaments/<int:tid>/delete", methods=["POST"])
@login_required
@superadmin_required
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

def _projected_final_matchups(groups, standings_by_group, final_mode):
    """Return projected final match rows for display during GROUP_STAGE."""
    rows = []
    if not groups:
        return rows

    def team_desc(group_name, row):
        if row:
            return f"{row['rank']}. {group_name} ({row['team']['name']})"
        return f"?. {group_name}"

    if final_mode == "rank_vs_rank":
        group_pairs = [(groups[i], groups[i + 1]) for i in range(0, len(groups) - 1, 2)]
        min_teams = min(len(standings_by_group.get(g.id, [])) for g in groups) if groups else 0
        for rank_idx in range(min_teams):
            rank = rank_idx + 1
            place = 2 * rank - 1
            label = "Finale" if rank == 1 else f"Spiel um Platz {place}"
            for ga, gb in group_pairs:
                st_a = standings_by_group.get(ga.id, [])
                st_b = standings_by_group.get(gb.id, [])
                pair_label = f"{label} ({ga.name}/{gb.name})" if len(group_pairs) > 1 else label
                rows.append({
                    "label": pair_label,
                    "team1": team_desc(ga.name, st_a[rank_idx] if rank_idx < len(st_a) else None),
                    "team2": team_desc(gb.name, st_b[rank_idx] if rank_idx < len(st_b) else None),
                    "tbd": rank_idx >= len(st_a) or rank_idx >= len(st_b),
                })
        return rows

    elif final_mode == "direct_final":
        all_teams = []
        for g in groups:
            for row in standings_by_group.get(g.id, []):
                all_teams.append((g.name, row))
        all_teams.sort(key=lambda x: (x[1]["points"], x[1]["goal_diff"], x[1]["goals_for"]), reverse=True)
        t1 = all_teams[0] if all_teams else None
        t2 = all_teams[1] if len(all_teams) > 1 else None
        rows.append({
            "label": "Finale",
            "team1": team_desc(t1[0], t1[1]) if t1 else "1. Platz",
            "team2": team_desc(t2[0], t2[1]) if t2 else "2. Platz",
            "tbd": not (t1 and t2),
        })

    elif len(groups) == 2:
        # Cross-group seeding: 1.A vs 2.B, 1.B vs 2.A → Finale
        g1, g2 = groups[0], groups[1]
        st1 = standings_by_group.get(g1.id, [])
        st2 = standings_by_group.get(g2.id, [])
        rows.append({
            "label": "Halbfinale 1",
            "team1": team_desc(g1.name, st1[0] if st1 else None),
            "team2": team_desc(g2.name, st2[1] if len(st2) > 1 else None),
            "tbd": len(st1) < 1 or len(st2) < 2,
        })
        rows.append({
            "label": "Halbfinale 2",
            "team1": team_desc(g2.name, st2[0] if st2 else None),
            "team2": team_desc(g1.name, st1[1] if len(st1) > 1 else None),
            "tbd": len(st2) < 1 or len(st1) < 2,
        })
        rows.append({
            "label": "Finale",
            "team1": "Sieger HF 1",
            "team2": "Sieger HF 2",
            "tbd": True,
        })

    else:
        # Generic: overall ranking pairs
        all_teams = []
        for g in groups:
            for row in standings_by_group.get(g.id, []):
                all_teams.append((g.name, row))
        all_teams.sort(key=lambda x: (x[1]["points"], x[1]["goal_diff"], x[1]["goals_for"]), reverse=True)
        n = len(all_teams)
        half = min(n // 2, 4)
        for i in range(half):
            t1 = all_teams[i] if i < n else None
            t2 = all_teams[n - 1 - i] if (n - 1 - i) >= 0 else None
            rows.append({
                "label": f"Spiel {i + 1}",
                "team1": team_desc(t1[0], t1[1]) if t1 else "TBD",
                "team2": team_desc(t2[0], t2[1]) if t2 else "TBD",
                "tbd": not (t1 and t2),
            })

    return rows


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
    ).order_by(Match.match_order).all()
    live_matches = Match.query.filter_by(status="live", tournament_id=t.id).order_by(Match.field).all()
    # First match to open when clicking "Steuerung" – prefer live, then planned, then any
    all_ctrl = matches + final_matches
    control_match = (
        next((m for m in all_ctrl if m.status == "live"), None)
        or next((m for m in all_ctrl if m.status == "planned"), None)
        or (all_ctrl[0] if all_ctrl else None)
    )
    standings_by_group = {grp.id: calculate_standings(group_id=grp.id) for grp in groups}
    # Projected matchups shown in Finalrunde section during GROUP_STAGE
    projected_matchups = []
    if phase == "GROUP_STAGE" and not final_matches:
        final_mode_val = get_setting(t.id, "final_mode", "")
        projected_matchups = _projected_final_matchups(groups, standings_by_group, final_mode_val)
    return render_template(
        "admin/dashboard.html",
        groups=groups, teams=teams, matches=matches,
        final_matches=final_matches, phase=phase, settings=settings,
        tournament=t, live_matches=live_matches,
        control_match=control_match,
        standings_by_group=standings_by_group,
        projected_matchups=projected_matchups,
    )


# ──────────────────────────────────────
# Tournament Administration Page
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/administration")
@login_required
@tournament_required
def tournament_admin():
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
    live_matches = Match.query.filter_by(status="live", tournament_id=t.id).order_by(Match.field).all()
    all_ctrl = matches + Match.query.filter_by(is_final=True, tournament_id=t.id).order_by(Match.final_round.desc(), Match.final_position).all()
    control_match = (
        next((m for m in all_ctrl if m.status == "live"), None)
        or next((m for m in all_ctrl if m.status == "planned"), None)
        or (all_ctrl[0] if all_ctrl else None)
    )
    return render_template(
        "admin/tournament_admin.html",
        tournament=t, phase=phase, settings=settings,
        groups=groups, teams=teams, matches=matches,
        live_matches=live_matches, control_match=control_match,
    )


@admin_bp.route("/t/<slug>/cabin-signs")
@login_required
@tournament_required
def cabin_signs():
    t = g.tournament
    settings = get_all_settings(t.id)
    groups = Group.query.filter_by(tournament_id=t.id).order_by(
        Group.display_order, Group.name
    ).all()
    teams = Team.query.filter_by(tournament_id=t.id).order_by(Team.name).all()
    teams_by_group = {}
    for grp in groups:
        teams_by_group[grp.id] = [tm for tm in teams if tm.group_id == grp.id]
    return render_template(
        "admin/cabin_signs.html",
        tournament=t, settings=settings,
        groups=groups, teams_by_group=teams_by_group,
    )


# ──────────────────────────────────────
# Organisation (payments, receipts)
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/organisation")
@login_required
@tournament_required
def organisation():
    t = g.tournament
    settings = get_all_settings(t.id)
    teams = Team.query.filter_by(tournament_id=t.id).order_by(Team.name).all()
    # Load payment records
    payments = {p.team_id: p for p in TeamPayment.query.filter(
        TeamPayment.team_id.in_([tm.id for tm in teams])
    ).all()}
    paid_count = sum(1 for p in payments.values() if p.paid)
    entry_fee = float(settings.get("entry_fee") or 0)
    total_expected = entry_fee * len(teams)
    total_received = sum(
        (p.amount if p.amount is not None else entry_fee)
        for p in payments.values() if p.paid
    )
    return render_template(
        "admin/organisation.html",
        tournament=t, settings=settings, teams=teams,
        payments=payments, paid_count=paid_count,
        total_expected=total_expected, total_received=total_received,
        entry_fee=entry_fee,
    )


@admin_bp.route("/t/<slug>/api/org/settings", methods=["POST"])
@login_required
@editor_required
@tournament_required
def save_org_settings():
    t = g.tournament
    data = request.get_json() or {}
    for key in ["entry_fee", "org_logo_url"]:
        if key in data:
            set_setting(t.id, key, str(data[key]))
    return jsonify({"ok": True})


@admin_bp.route("/t/<slug>/api/teams/<int:tid>/toggle-paid", methods=["POST"])
@login_required
@editor_required
@tournament_required
def toggle_team_paid(tid):
    t = g.tournament
    team = db.session.get(Team, tid)
    if not team or team.tournament_id != t.id:
        return jsonify({"error": "Team nicht gefunden"}), 404
    data = request.get_json() or {}
    payment = db.session.get(TeamPayment, tid)
    if not payment:
        payment = TeamPayment(team_id=tid)
        db.session.add(payment)
    payment.paid = not payment.paid
    if payment.paid:
        from datetime import datetime, timezone
        payment.paid_at = datetime.now(timezone.utc)
        entry_fee = float(get_setting(t.id, "entry_fee") or 0)
        payment.amount = float(data.get("amount", entry_fee)) if data.get("amount") else entry_fee
        # Generate receipt number
        if not payment.receipt_number:
            prefix = get_setting(t.id, "receipt_prefix") or "QU"
            payment.receipt_number = f"{prefix}-{t.id:03d}-{tid:04d}"
    else:
        payment.paid_at = None
    db.session.commit()
    return jsonify({
        "ok": True, "paid": payment.paid,
        "receipt_number": payment.receipt_number,
        "paid_at": payment.paid_at.strftime("%d.%m.%Y") if payment.paid_at else None,
    })


@admin_bp.route("/t/<slug>/organisation/receipt/<int:tid>")
@login_required
@tournament_required
def receipt_single(tid):
    t = g.tournament
    team = db.session.get(Team, tid)
    if not team or team.tournament_id != t.id:
        return "Team nicht gefunden", 404
    settings = get_all_settings(t.id)
    payment = db.session.get(TeamPayment, tid)
    entry_fee = float(settings.get("entry_fee") or 0)
    return render_template(
        "admin/receipt_print.html",
        tournament=t, settings=settings,
        teams=[team], payments={tid: payment} if payment else {},
        entry_fee=entry_fee, single=True,
        euros_to_words=euros_to_words,
    )


@admin_bp.route("/t/<slug>/organisation/receipts/all")
@login_required
@tournament_required
def receipt_all():
    t = g.tournament
    settings = get_all_settings(t.id)
    all_teams = Team.query.filter_by(tournament_id=t.id).order_by(Team.name).all()
    payments = {p.team_id: p for p in TeamPayment.query.filter(
        TeamPayment.team_id.in_([tm.id for tm in all_teams])
    ).all()}
    entry_fee = float(settings.get("entry_fee") or 0)
    # Filter by selected IDs if provided
    ids_param = request.args.get("ids")
    if ids_param:
        try:
            selected_ids = {int(i) for i in ids_param.split(",") if i.strip()}
            teams = [tm for tm in all_teams if tm.id in selected_ids]
        except ValueError:
            teams = all_teams
    elif request.args.get("paid_only") == "1":
        teams = [tm for tm in all_teams if payments.get(tm.id) and payments[tm.id].paid]
    else:
        teams = all_teams
    return render_template(
        "admin/receipt_print.html",
        tournament=t, settings=settings,
        teams=teams, payments=payments,
        entry_fee=entry_fee, single=len(teams) == 1,
        euros_to_words=euros_to_words,
    )


# ──────────────────────────────────────
# Schedule Print View
# ──────────────────────────────────────

@admin_bp.route("/t/<slug>/schedule/print")
@login_required
@tournament_required
def schedule_print():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    settings = get_all_settings(t.id)
    groups = Group.query.filter_by(tournament_id=t.id).order_by(
        Group.display_order, Group.name
    ).all()
    matches = Match.query.filter_by(
        is_final=False, tournament_id=t.id
    ).order_by(Match.match_order).all()
    final_matches = Match.query.filter_by(
        is_final=True, tournament_id=t.id
    ).order_by(Match.final_round.desc(), Match.final_position).all()
    # Standings per group
    from app.models import calculate_standings
    standings_by_group = {
        grp.id: calculate_standings(group_id=grp.id)
        for grp in groups
    }
    hide_results = request.args.get("empty") == "1"
    return render_template(
        "admin/schedule_print.html",
        tournament=t, phase=phase, settings=settings,
        groups=groups, matches=matches, final_matches=final_matches,
        standings_by_group=standings_by_group,
        hide_results=hide_results,
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
@editor_required
@tournament_required
def update_settings():
    """Save design settings (colors, tournament name, timer defaults)."""
    t = g.tournament
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Ungueltige JSON-Anfrage"}), 400
    allowed_keys = {
        "tournament_name", "color_title", "color_primary", "color_secondary",
        "default_timer_regular", "default_timer_extra", "hide_results", "hide_table", "hide_scores", "theme",
        "final_mode",
        "num_fields",
        "org_logo_url",
        "tournament_rules",
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
        if key == "hide_results" and value not in ("0", "1"):
            return jsonify({"error": "hide_results muss 0 oder 1 sein"}), 400
        if key in ("hide_table", "hide_scores") and value not in ("0", "1"):
            return jsonify({"error": f"{key} muss 0 oder 1 sein"}), 400
        _valid_themes = {"dark", "midnight", "slate", "ocean", "crimson", "light"}
        if key == "theme" and value not in _valid_themes:
            return jsonify({"error": f"Ungueltiges Theme: {value}"}), 400
        _valid_final_modes = {"", "semi_final", "direct_final", "classic_ko", "free_ko", "custom"}
        if key == "final_mode" and value not in _valid_final_modes:
            return jsonify({"error": "Ungueltiger Finalrundentyp"}), 400
        if key == "num_fields" and value not in FELD_OPTIONEN:
            return jsonify({"error": "num_fields muss zwischen 1 und 6 liegen"}), 400
        set_setting(t.id, key, value)
        if key in ("hide_table", "hide_scores"):
            set_setting(t.id, "hide_results", "0")

    try:
        broadcast_state(t.id)
    except Exception:
        pass
    return jsonify(get_all_settings(t.id))


@admin_bp.route("/t/<slug>/api/announcement", methods=["POST"])
@login_required
@editor_required
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
@superadmin_required
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


@admin_bp.route("/t/<slug>/api/phase/no-finals", methods=["POST"])
@login_required
@superadmin_required
@tournament_required
def phase_no_finals():
    """End the tournament after the group phase — no final round."""
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        return jsonify({"error": "Gruppenphase ist nicht aktiv"}), 400
    set_setting(t.id, "final_mode", "none")
    set_setting(t.id, "tournament_phase", "FINISHED")
    try:
        broadcast_state(t.id)
    except Exception:
        pass
    return jsonify({"ok": True, "phase": "FINISHED"})


@admin_bp.route("/t/<slug>/api/phase/use-existing-finals", methods=["POST"])
@login_required
@superadmin_required
@tournament_required
def use_existing_finals():
    """End group stage and go straight to FINAL_ROUND using already-generated final matches."""
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
    has_finals = Match.query.filter_by(is_final=True, tournament_id=t.id).count()
    if not has_finals:
        return jsonify({"error": "Keine Finalrunde vorhanden"}), 400
    set_setting(t.id, "tournament_phase", "FINAL_ROUND")
    broadcast_state(t.id)
    return jsonify({"ok": True, "phase": "FINAL_ROUND"})


@admin_bp.route("/t/<slug>/api/phase/start-final-round", methods=["POST"])
@login_required
@superadmin_required
@tournament_required
def start_final_round():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase")
    if phase not in ("FINAL_SETUP",):
        return jsonify({"error": "Falscher Turnierstatus"}), 400
    data = request.get_json()
    mode = data.get("mode")
    config = data.get("config", {})
    if mode not in ("classic_ko", "semi_final", "direct_final", "free_ko", "rank_vs_rank", "custom"):
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
        elif mode == "rank_vs_rank":
            _generate_rank_vs_rank(t.id, config)
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
@superadmin_required
@tournament_required
def finish_tournament():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase")
    if phase not in ("FINAL_ROUND", "FINAL_SETUP"):
        return jsonify({"error": "Turnier kann in dieser Phase nicht beendet werden"}), 400
    if phase == "FINAL_ROUND":
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
@superadmin_required
@tournament_required
def reset_phase():
    """Reset final matches results to planned (keep pairings), go back to GROUP_STAGE."""
    t = g.tournament
    for m in Match.query.filter_by(is_final=True, tournament_id=t.id).all():
        m.status = "planned"
        m.score_team1 = 0
        m.score_team2 = 0
        m.timer_running = False
        m.timer_started_at = None
        m.is_extra_time = False
        m.is_penalty = False
    set_setting(t.id, "tournament_phase", "GROUP_STAGE")
    set_setting(t.id, "final_mode", "")
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "phase": "GROUP_STAGE"})


@admin_bp.route("/t/<slug>/api/phase/full-reset", methods=["POST"])
@login_required
@superadmin_required
@tournament_required
def full_reset():
    """Reset ALL match results to planned (keep pairings), reset phase to GROUP_STAGE."""
    t = g.tournament
    for m in Match.query.filter_by(tournament_id=t.id).all():
        m.status = "planned"
        m.score_team1 = 0
        m.score_team2 = 0
        m.timer_running = False
        m.timer_started_at = None
        m.is_extra_time = False
        m.is_penalty = False
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
    preset_mode = get_setting(t.id, "final_mode", "")
    return render_template(
        "admin/finals_setup.html",
        phase=phase, groups=groups, rankings=rankings,
        teams_json=teams_json, tournament=t,
        preset_mode=preset_mode,
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


def _generate_rank_vs_rank(tournament_id, config):
    """Pair same-rank teams across groups: 1.A vs 1.B, 2.A vs 2.B, ..."""
    groups = Group.query.filter_by(tournament_id=tournament_id).order_by(Group.display_order).all()
    if len(groups) < 2:
        raise ValueError("Mindestens 2 Gruppen erforderlich")
    dur = int(get_setting(tournament_id, "default_timer_regular", "600"))
    standings_per_group = {g.id: calculate_standings(group_id=g.id) for g in groups}
    min_teams = min(len(v) for v in standings_per_group.values())
    num_ranks = min(config.get("num_ranks", min_teams), min_teams)
    if num_ranks < 1:
        raise ValueError("Keine Teams verfuegbar")
    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == tournament_id
    ).scalar() or 0
    order_counter = max_order + 1
    # Pair groups in pairs: (A,B), (C,D), ...
    group_pairs = [(groups[i], groups[i + 1]) for i in range(0, len(groups) - 1, 2)]
    for rank_idx in range(num_ranks):
        rank = rank_idx + 1
        place = 2 * rank - 1
        label = "Finale" if rank == 1 else f"Spiel um Platz {place}"
        for pair_idx, (ga, gb) in enumerate(group_pairs):
            st_a = standings_per_group[ga.id]
            st_b = standings_per_group[gb.id]
            t1_id = st_a[rank_idx]["team"]["id"] if rank_idx < len(st_a) else None
            t2_id = st_b[rank_idx]["team"]["id"] if rank_idx < len(st_b) else None
            pair_label = f"{label} ({ga.name}/{gb.name})" if len(group_pairs) > 1 else label
            m = Match(
                tournament_id=tournament_id,
                team1_id=t1_id, team2_id=t2_id,
                is_final=True,
                final_round=num_ranks - rank_idx,
                final_position=pair_idx,
                final_label=pair_label,
                match_order=order_counter,
                timer_duration=dur, timer_remaining=dur,
            )
            db.session.add(m)
            order_counter += 1
    db.session.flush()


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
@editor_required
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
@editor_required
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
@superadmin_required
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
@editor_required
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
@editor_required
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
@superadmin_required
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
@editor_required
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
@editor_required
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
    field = request.form.get("field", 1, type=int)
    if field not in (1, 2):
        field = 1
    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == t.id
    ).scalar() or 0
    db.session.add(Match(
        tournament_id=t.id,
        team1_id=t1, team2_id=t2,
        group_id=gid,
        field=field,
        timer_duration=dur, timer_remaining=dur,
        match_order=max_order + 1,
    ))
    db.session.commit()
    broadcast_state(t.id)
    flash("Spiel erstellt.", "success")
    return redirect(url_for("admin.dashboard", slug=t.slug))


@admin_bp.route("/t/<slug>/api/matches/import-csv", methods=["POST"])
@login_required
@editor_required
@tournament_required
def import_matches_csv():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        return jsonify({"error": "Nur in der Gruppenphase möglich"}), 400

    data = request.get_json()
    csv_text = data.get("csv", "").strip()
    if not csv_text:
        return jsonify({"error": "Keine CSV-Daten angegeben"}), 400

    default_dur = int(get_setting(t.id, "default_timer_regular", "600"))
    num_fields = int(get_setting(t.id, "num_fields", "1"))

    reader = csv.reader(io.StringIO(csv_text), delimiter=",")
    created = 0
    errors = []

    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == t.id
    ).scalar() or 0

    for row_num, row in enumerate(reader, 1):
        if not row or not any(cell.strip() for cell in row):
            continue
        # Skip header row
        first = row[0].strip().lower()
        if first in ("heim", "home", "team1"):
            continue

        heim_name = row[0].strip() if len(row) > 0 else ""
        gast_name = row[1].strip() if len(row) > 1 else ""
        field_raw = row[2].strip() if len(row) > 2 else "1"

        if not heim_name or not gast_name:
            errors.append(f"Zeile {row_num}: Heim und Gast sind Pflichtfelder")
            continue

        team1 = Team.query.filter(
            db.func.lower(Team.name) == heim_name.lower(),
            Team.tournament_id == t.id
        ).first()
        team2 = Team.query.filter(
            db.func.lower(Team.name) == gast_name.lower(),
            Team.tournament_id == t.id
        ).first()

        if not team1:
            errors.append(f"Zeile {row_num}: Team '{heim_name}' nicht gefunden")
            continue
        if not team2:
            errors.append(f"Zeile {row_num}: Team '{gast_name}' nicht gefunden")
            continue
        if team1.id == team2.id:
            errors.append(f"Zeile {row_num}: Heim und Gast dürfen nicht identisch sein")
            continue

        # Both teams must be in the same group
        if not team1.group_id or team1.group_id != team2.group_id:
            errors.append(f"Zeile {row_num}: '{heim_name}' und '{gast_name}' sind nicht in derselben Gruppe")
            continue

        try:
            field = int(field_raw)
        except (ValueError, TypeError):
            field = 1
        if field not in range(1, num_fields + 1):
            field = 1

        max_order += 1
        db.session.add(Match(
            tournament_id=t.id,
            team1_id=team1.id,
            team2_id=team2.id,
            group_id=team1.group_id,
            field=field,
            timer_duration=default_dur,
            timer_remaining=default_dur,
            match_order=max_order,
        ))
        created += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Datenbankfehler: {str(e)}"}), 400

    broadcast_state(t.id)
    msg = f"{created} Spiel(e) importiert."
    if errors:
        msg += f" {len(errors)} Fehler: {'; '.join(errors)}"
    return jsonify({"ok": True, "created": created, "errors": errors, "message": msg})


@admin_bp.route("/t/<slug>/api/simulate-group-matches", methods=["POST"])
@login_required
@editor_required
@tournament_required
def simulate_group_matches():
    t = g.tournament
    data = request.get_json() or {}
    password = data.get("password", "")
    if not current_user.check_password(password):
        return jsonify({"error": "Falsches Passwort"}), 403
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase not in ("GROUP_STAGE",):
        return jsonify({"error": "Simulation nur in der Gruppenphase möglich"}), 400
    pending = Match.query.filter(
        Match.tournament_id == t.id,
        Match.is_final == False,
        Match.status.in_(["planned", "live"]),
    ).all()
    if not pending:
        return jsonify({"error": "Keine offenen Gruppenspiele vorhanden"}), 400
    for m in pending:
        m.score_team1 = random.randint(0, 5)
        m.score_team2 = random.randint(0, 5)
        m.status = "finished"
        m.timer_running = False
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Datenbankfehler: {str(e)}"}), 500
    broadcast_state(t.id)
    return jsonify({"ok": True, "simulated": len(pending)})


@admin_bp.route("/t/<slug>/matches/<int:mid>/delete", methods=["POST"])
@login_required
@superadmin_required
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


@admin_bp.route("/t/<slug>/api/finals/reorder", methods=["POST"])
@login_required
@editor_required
@tournament_required
def reorder_finals():
    t = g.tournament
    data = request.get_json()
    order = data.get("order", [])
    if not isinstance(order, list):
        return jsonify({"error": "order muss eine Liste sein"}), 400
    for idx, match_id in enumerate(order):
        match = db.session.get(Match, int(match_id))
        if match and match.tournament_id == t.id and match.is_final:
            match.match_order = idx
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True})


@admin_bp.route("/t/<slug>/api/matches/reorder", methods=["POST"])
@login_required
@editor_required
@tournament_required
def reorder_matches():
    t = g.tournament
    data = request.get_json()
    order = data.get("order", [])
    if not isinstance(order, list):
        return jsonify({"error": "order muss eine Liste sein"}), 400
    num_fields = int(get_setting(t.id, "num_fields") or 1)
    for idx, match_id in enumerate(order):
        match = db.session.get(Match, int(match_id))
        if match and match.tournament_id == t.id:
            match.match_order = idx
            match.field = (idx % num_fields) + 1
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True})


def _zahl(daten, schluessel, standard, minimum=None, maximum=None):
    """Zahl aus JSON/Formular lesen, mit Grenzen und Rueckfall."""
    rohwert = daten.get(schluessel)
    if rohwert in (None, ""):
        return standard
    try:
        wert = int(rohwert)
    except (TypeError, ValueError):
        return standard
    if minimum is not None:
        wert = max(minimum, wert)
    if maximum is not None:
        wert = min(maximum, wert)
    return wert


def _startzeitpunkt(t, daten, spielzeit_min, pause_min):
    """Ersten Anstoss bestimmen.

    Reihenfolge: ausdrueckliche Angabe > hinter dem letzten geplanten Spiel
    > Turnierdatum und -uhrzeit > heute 09:00.
    """
    datum_text = (daten.get("startdatum") or "").strip()
    zeit_text = (daten.get("startzeit") or "").strip()

    if datum_text or zeit_text:
        try:
            datum = (datetime.strptime(datum_text, "%Y-%m-%d").date()
                     if datum_text else (t.event_date or date.today()))
            stunde, minute = (zeit_text or "09:00").split(":")[:2]
            return datetime.combine(datum, dtime(int(stunde), int(minute))), None
        except (ValueError, TypeError):
            return None, "Startdatum oder Startzeit sind nicht lesbar."

    # An einen bestehenden Spielplan anschliessen
    letztes = (
        Match.query.filter(
            Match.tournament_id == t.id,
            Match.is_final.is_(False),
            Match.scheduled_time.isnot(None),
        ).order_by(Match.scheduled_time.desc()).first()
    )
    if letztes:
        return (letztes.scheduled_time
                + timedelta(minutes=spielzeit_min + pause_min)), None

    datum = t.event_date or date.today()
    zeit_text = t.event_time or "09:00"
    try:
        stunde, minute = zeit_text.split(":")[:2]
        return datetime.combine(datum, dtime(int(stunde), int(minute))), None
    except (ValueError, TypeError):
        return datetime.combine(datum, dtime(9, 0)), None


@admin_bp.route("/t/<slug>/api/matches/generate-round-robin", methods=["POST"])
@login_required
@editor_required
@tournament_required
def generate_round_robin():
    """Gruppenspiele erzeugen – mit Anstosszeiten und ohne Doppelbelegung.

    Optionen (JSON, alle optional):
        felder, spielzeit_min, pause_min, mindestpause,
        startdatum ("JJJJ-MM-TT"), startzeit ("HH:MM"),
        lange_pause_nach, lange_pause_min, vorhandene_loeschen
    Ohne Optionen verhaelt sich der Aufruf wie bisher, nur dass die Spiele
    jetzt Anstosszeiten bekommen und keine Mannschaft mehr zweimal
    gleichzeitig angesetzt wird.
    """
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        return jsonify({"error": "Nur in der Gruppenphase moeglich"}), 400

    groups = Group.query.filter_by(tournament_id=t.id).order_by(
        Group.display_order, Group.name).all()
    if not groups:
        return jsonify({"error": "Keine Gruppen vorhanden"}), 400

    daten = request.get_json(silent=True) or {}

    if daten.get("vorhandene_loeschen"):
        geloescht = Match.query.filter_by(
            tournament_id=t.id, is_final=False).delete()
        db.session.commit()
    else:
        geloescht = 0

    # Schon angesetzte Paarungen nicht doppelt erzeugen
    vorhanden = set()
    for m in Match.query.filter_by(is_final=False, tournament_id=t.id).all():
        if m.team1_id and m.team2_id:
            vorhanden.add((min(m.team1_id, m.team2_id),
                           max(m.team1_id, m.team2_id)))

    offene_begegnungen = []
    nummer = 0
    for group in groups:
        team_ids = sorted(te.id for te in group.teams)
        if len(team_ids) < 2:
            continue
        for t1_id, t2_id in combinations(team_ids, 2):
            paar = (min(t1_id, t2_id), max(t1_id, t2_id))
            if paar in vorhanden:
                continue
            vorhanden.add(paar)
            nummer += 1
            offene_begegnungen.append(
                Begegnung(t1_id, t2_id, group.id, nummer))

    if not offene_begegnungen:
        return jsonify({"ok": True, "created": 0, "deleted": geloescht,
                        "hinweis": "Alle Paarungen sind schon angesetzt."})

    standard_spielzeit = max(1, int(
        get_setting(t.id, "default_timer_regular", "600") or 600) // 60)
    felder = _zahl(daten, "felder",
                   int(get_setting(t.id, "num_fields") or 1), 1, 6)
    spielzeit_min = _zahl(daten, "spielzeit_min", standard_spielzeit, 1, 90)
    pause_min = _zahl(daten, "pause_min", 5, 0, 120)
    mindestpause = _zahl(daten, "mindestpause", 1, 0, 10)
    lange_pause_nach = _zahl(daten, "lange_pause_nach", None, 1, 99)
    lange_pause_min = _zahl(daten, "lange_pause_min", 0, 0, 300)

    start, fehler = _startzeitpunkt(t, daten, spielzeit_min, pause_min)
    if fehler:
        return jsonify({"error": fehler}), 400

    max_order = db.session.query(db.func.max(Match.match_order)).filter(
        Match.tournament_id == t.id
    ).scalar() or 0

    plan = erstelle_spielplan(
        offene_begegnungen, felder=felder, mindestpause=mindestpause,
        start=start, spielzeit_min=spielzeit_min, pause_min=pause_min,
        lange_pause_nach=lange_pause_nach, lange_pause_min=lange_pause_min,
        startnummer=max_order + 1,
    )

    dauer_sekunden = spielzeit_min * 60
    for eintrag in plan:
        begegnung = eintrag["begegnung"]
        db.session.add(Match(
            tournament_id=t.id,
            team1_id=begegnung.team1, team2_id=begegnung.team2,
            group_id=begegnung.gruppe,
            timer_duration=dauer_sekunden, timer_remaining=dauer_sekunden,
            match_order=eintrag["nummer"],
            field=eintrag["feld"],
            scheduled_time=eintrag["anstoss"],
        ))

    # Mehr Felder verplant als eingestellt? Einstellung mitziehen, sonst
    # blendet die Oberflaeche die Feldspalte aus.
    if felder > int(get_setting(t.id, "num_fields") or 1):
        set_setting(t.id, "num_fields", str(felder))

    db.session.commit()
    broadcast_state(t.id)

    letzter = plan[-1]["anstoss"]
    return jsonify({
        "ok": True,
        "created": len(plan),
        "deleted": geloescht,
        "slots": plan[-1]["slot"],
        "felder": felder,
        "beginn": start.strftime("%d.%m.%Y %H:%M"),
        "ende": (letzter + timedelta(minutes=spielzeit_min)).strftime("%H:%M"),
    })


@admin_bp.route("/t/<slug>/api/matches/konflikte")
@login_required
@tournament_required
def spielplan_konflikte():
    """Doppelbelegungen im bestehenden Spielplan melden."""
    t = g.tournament
    spiele = Match.query.filter_by(tournament_id=t.id).order_by(
        Match.match_order).all()
    konflikte = finde_konflikte([
        {
            "nummer": m.match_order,
            "anstoss": m.scheduled_time,
            "feld": m.field or 1,
            "teams": (m.team1_id, m.team2_id),
        }
        for m in spiele
    ])
    return jsonify({"konflikte": konflikte, "anzahl": len(konflikte)})


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
    num_fields = int(get_setting(t.id, "num_fields") or 1)

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

    parallel_match = None
    if num_fields >= 2:
        # Navigate in pairs: prev/next jump 2 slots at a time
        pair_idx = idx // 2
        prev_pair_start = (pair_idx - 1) * 2
        next_pair_start = (pair_idx + 1) * 2
        prev_match_id = match_ids[prev_pair_start] if pair_idx > 0 else None
        next_match_id = match_ids[next_pair_start] if next_pair_start < len(match_ids) else None
        # Pair partner: flip last bit (0↔1, 2↔3, 4↔5, …)
        partner_idx = idx ^ 1
        if 0 <= partner_idx < len(all_matches):
            parallel_match = all_matches[partner_idx]
    else:
        prev_match_id = match_ids[idx - 1] if idx > 0 else None
        next_match_id = match_ids[idx + 1] if idx >= 0 and idx < len(match_ids) - 1 else None

    return render_template(
        "admin/match_control.html",
        match=match, extra_time=extra_time,
        prev_match_id=prev_match_id, next_match_id=next_match_id,
        tournament=t, parallel_match=parallel_match, num_fields=num_fields,
    )


@admin_bp.route("/t/<slug>/api/matches/delete-all", methods=["POST"])
@login_required
@superadmin_required
@tournament_required
def delete_all_matches():
    t = g.tournament
    phase = get_setting(t.id, "tournament_phase", "GROUP_STAGE")
    if phase != "GROUP_STAGE":
        return jsonify({"error": "Nur in der Gruppenphase moeglich"}), 400
    Match.query.filter_by(tournament_id=t.id, is_final=False).delete()
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True})


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/set-field", methods=["POST"])
@login_required
@editor_required
@tournament_required
def set_match_field(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Nicht gefunden"}), 404
    num_fields = int(get_setting(t.id, "num_fields") or 1)
    new_field = (match.field % num_fields) + 1  # toggle: 1→2, 2→1
    match.field = new_field
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "field": new_field})


@admin_bp.route("/t/<slug>/api/matches/start-next", methods=["POST"])
@login_required
@editor_required
@tournament_required
def start_next_matches():
    """Start the next N planned matches (one per field) simultaneously."""
    t = g.tournament
    num_fields = int(get_setting(t.id, "num_fields") or 1)
    already_live = Match.query.filter_by(status="live", tournament_id=t.id).count()
    slots = num_fields - already_live
    if slots <= 0:
        return jsonify({"error": "Bereits alle Felder belegt"}), 400
    planned = Match.query.filter_by(
        status="planned", tournament_id=t.id
    ).order_by(Match.match_order).limit(slots).all()
    if not planned:
        return jsonify({"error": "Keine geplanten Spiele vorhanden"}), 400
    for match in planned:
        match.status = "live"
        match.timer_running = True
        match.timer_started_at = time.time()
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "started": len(planned)})


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/swap-teams", methods=["POST"])
@login_required
@editor_required
@tournament_required
def swap_match_teams(mid):
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Nicht gefunden"}), 404
    match.team1_id, match.team2_id = match.team2_id, match.team1_id
    match.score_team1, match.score_team2 = match.score_team2, match.score_team1
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True})


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/score", methods=["POST"])
@login_required
@editor_required
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
@editor_required
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
        num_fields = int(get_setting(t.id, "num_fields") or 1)
        live_count = Match.query.filter(
            Match.status == "live",
            Match.tournament_id == t.id,
            Match.id != mid,
        ).count()
        if live_count >= num_fields:
            return jsonify({"error": f"Bereits {live_count} Spiel(e) live (max. {num_fields} Felder)"}), 400
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
@editor_required
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
                num_fields = int(get_setting(t.id, "num_fields") or 1)
                live_count = Match.query.filter(
                    Match.status == "live", Match.tournament_id == t.id, Match.id != mid
                ).count()
                if live_count >= num_fields:
                    return jsonify({"error": f"Bereits {live_count} Spiel(e) live (max. {num_fields} Felder)"}), 400
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


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/set-phase", methods=["POST"])
@login_required
@editor_required
@tournament_required
def set_match_phase(mid):
    """Set match phase: normal | extra_time | penalty."""
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Nicht gefunden"}), 404
    data = request.get_json()
    phase = data.get("phase", "normal")
    match.is_extra_time = phase == "extra_time"
    match.is_penalty = phase == "penalty"
    db.session.commit()
    broadcast_state(t.id)
    return jsonify(match.to_dict())


@admin_bp.route("/t/<slug>/api/matches/<int:mid>/announce-next", methods=["POST"])
@login_required
@editor_required
@tournament_required
def announce_next_match(mid):
    """Set the announcement to the next planned match after this one."""
    t = g.tournament
    match = db.session.get(Match, mid)
    if not match or match.tournament_id != t.id:
        return jsonify({"error": "Nicht gefunden"}), 404
    next_m = (
        Match.query.filter_by(status="planned", tournament_id=t.id)
        .filter(Match.match_order > match.match_order)
        .order_by(Match.match_order.asc())
        .first()
    )
    if not next_m:
        # fallback: first planned match overall
        next_m = Match.query.filter_by(status="planned", tournament_id=t.id).order_by(Match.match_order.asc()).first()
    if not next_m:
        return jsonify({"error": "Kein naechstes Spiel gefunden"}), 404
    t1 = next_m.team1.name if next_m.team1 else "TBD"
    t2 = next_m.team2.name if next_m.team2 else "TBD"
    label = next_m.final_label or (next_m.group.name if next_m.group else "")
    text = f"Nächstes Spiel: {t1} vs {t2}"
    if label:
        text += f"  ({label})"
    set_setting(t.id, "announcement", text)
    db.session.commit()
    broadcast_state(t.id)
    return jsonify({"ok": True, "announcement": text})


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
@superadmin_required
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
@superadmin_required
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
@superadmin_required
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


@admin_bp.route("/api/menu/import-csv", methods=["POST"])
@login_required
@superadmin_required
def menu_import_csv():
    """Import menu items from CSV. Format: Name;Preis;Beschreibung;Kategorie (speise|getraenk)"""
    data = request.get_json()
    csv_text = (data or {}).get("csv", "").strip()
    if not csv_text:
        return jsonify({"error": "Keine Daten"}), 400
    imported = 0
    skipped = 0
    for line in csv_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Support both ; and , as delimiter (auto-detect)
        sep = ";" if ";" in line else ","
        parts = [p.strip() for p in line.split(sep)]
        name = parts[0] if parts else ""
        if not name:
            skipped += 1
            continue
        price = parts[1] if len(parts) > 1 else ""
        description = parts[2] if len(parts) > 2 else ""
        category = parts[3].lower().strip() if len(parts) > 3 else "speise"
        if category not in ("speise", "getraenk"):
            category = "speise"
        max_order = db.session.query(db.func.max(MenuItem.display_order)).scalar() or 0
        item = MenuItem(name=name, price=price, description=description,
                        category=category, display_order=max_order + 1)
        db.session.add(item)
        imported += 1
    db.session.commit()
    return jsonify({"ok": True, "imported": imported, "skipped": skipped})


@admin_bp.route("/api/menu/reorder", methods=["POST"])
@login_required
@superadmin_required
def menu_reorder():
    data = request.get_json(silent=True)
    if not data or "ids" not in data:
        return jsonify({"error": "ids required"}), 400
    for idx, item_id in enumerate(data["ids"]):
        MenuItem.query.filter_by(id=item_id).update({"display_order": idx})
    db.session.commit()
    return jsonify({"ok": True})


@admin_bp.route("/api/menu/bulk-delete", methods=["POST"])
@login_required
@superadmin_required
def menu_bulk_delete():
    data = request.get_json(silent=True)
    if not data or "ids" not in data:
        return jsonify({"error": "ids required"}), 400
    MenuItem.query.filter(MenuItem.id.in_(data["ids"])).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"ok": True})


# ──────────────────────────────────────
# User Management (superadmin only)
# ──────────────────────────────────────

@admin_bp.route("/users")
@login_required
@superadmin_required
def user_list():
    users = Admin.query.order_by(Admin.username).all()
    tournaments = Tournament.query.order_by(Tournament.display_order, Tournament.name).all()
    return render_template("admin/users.html", users=users, tournaments=tournaments)


@admin_bp.route("/users/create", methods=["POST"])
@login_required
@superadmin_required
def create_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "editor")
    if role not in ("superadmin", "editor", "viewer"):
        role = "editor"
    if not username:
        flash("Benutzername erforderlich.", "error")
        return redirect(url_for("admin.user_list"))
    if not password:
        flash("Passwort erforderlich.", "error")
        return redirect(url_for("admin.user_list"))
    if Admin.query.filter_by(username=username).first():
        flash("Benutzername existiert bereits.", "error")
        return redirect(url_for("admin.user_list"))
    user = Admin(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    # Tournament access (not applicable for superadmin - they have all)
    if role != "superadmin":
        tournament_ids = request.form.getlist("tournament_ids", type=int)
        for tid in tournament_ids:
            db.session.add(UserTournamentAccess(user_id=user.id, tournament_id=tid))
    db.session.commit()
    flash(f"Benutzer '{username}' erstellt.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:uid>/edit", methods=["GET", "POST"])
@login_required
@superadmin_required
def edit_user(uid):
    user = db.session.get(Admin, uid)
    if not user:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for("admin.user_list"))
    tournaments = Tournament.query.order_by(Tournament.display_order, Tournament.name).all()
    if request.method == "GET":
        assigned_ids = {a.tournament_id for a in user.tournament_access.all()}
        return render_template("admin/user_edit.html", user=user, tournaments=tournaments, assigned_ids=assigned_ids)
    # POST
    new_role = request.form.get("role", user.role)
    if new_role not in ("superadmin", "editor", "viewer"):
        new_role = user.role
    # Prevent removing own superadmin if last superadmin
    if user.id == current_user.id and new_role != "superadmin":
        flash("Du kannst deine eigene Superadmin-Rolle nicht entfernen.", "error")
        return redirect(url_for("admin.user_list"))
    user.role = new_role
    new_password = request.form.get("password", "").strip()
    if new_password:
        user.set_password(new_password)
    # Update tournament access
    UserTournamentAccess.query.filter_by(user_id=uid).delete()
    if new_role != "superadmin":
        tournament_ids = request.form.getlist("tournament_ids", type=int)
        for tid in tournament_ids:
            db.session.add(UserTournamentAccess(user_id=uid, tournament_id=tid))
    db.session.commit()
    flash(f"Benutzer '{user.username}' aktualisiert.", "success")
    return redirect(url_for("admin.user_list"))


@admin_bp.route("/users/<int:uid>/delete", methods=["POST"])
@login_required
@superadmin_required
def delete_user(uid):
    if uid == current_user.id:
        flash("Du kannst dich nicht selbst loeschen.", "error")
        return redirect(url_for("admin.user_list"))
    user = db.session.get(Admin, uid)
    if not user:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for("admin.user_list"))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"Benutzer '{username}' geloescht.", "success")
    return redirect(url_for("admin.user_list"))


# ──────────────────────────────────────
# Export / Import
# ──────────────────────────────────────

@admin_bp.route("/export-import")
@login_required
@superadmin_required
def export_import_page():
    tournaments = Tournament.query.order_by(Tournament.display_order, Tournament.name).all()
    return render_template("admin/export_import.html", tournaments=tournaments)


def _export_tournament(t):
    """Serialize a full tournament to a dict."""
    groups = Group.query.filter_by(tournament_id=t.id).order_by(Group.display_order, Group.name).all()
    teams = Team.query.filter_by(tournament_id=t.id).all()
    matches = Match.query.filter_by(tournament_id=t.id).order_by(Match.match_order, Match.id).all()

    match_id_to_index = {m.id: i for i, m in enumerate(matches)}
    group_id_to_name = {g.id: g.name for g in groups}
    team_id_to_name = {team.id: team.name for team in teams}

    def _payment(team):
        p = team.payment
        if not p:
            return None
        return {
            "paid": bool(p.paid),
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
            "amount": p.amount,
            "receipt_number": p.receipt_number,
        }

    return {
        "name": t.name,
        "slug": t.slug,
        "description": t.description or "",
        "event_date": t.event_date.isoformat() if t.event_date else None,
        "event_time": t.event_time,
        "is_active": t.is_active,
        "display_order": t.display_order,
        "settings": get_all_settings(t.id),
        "groups": [
            {"name": g.name, "display_order": g.display_order}
            for g in groups
        ],
        "teams": [
            {
                "name": team.name,
                "logo_url": team.logo_url or "",
                "players": team.players or "",
                "group_name": group_id_to_name.get(team.group_id) if team.group_id else None,
                "payment": _payment(team),
            }
            for team in teams
        ],
        "matches": [
            {
                "_index": i,
                "team1_name": team_id_to_name.get(m.team1_id) if m.team1_id else None,
                "team2_name": team_id_to_name.get(m.team2_id) if m.team2_id else None,
                "group_name": group_id_to_name.get(m.group_id) if m.group_id else None,
                "score_team1": m.score_team1,
                "score_team2": m.score_team2,
                "status": m.status,
                "scheduled_time": m.scheduled_time.isoformat() if m.scheduled_time else None,
                "match_order": m.match_order,
                "field": m.field or 1,
                "timer_duration": m.timer_duration,
                "timer_remaining": m.timer_remaining,
                "is_extra_time": m.is_extra_time,
                "is_penalty": bool(m.is_penalty),
                "is_final": m.is_final,
                "final_round": m.final_round,
                "final_position": m.final_position,
                "final_label": m.final_label,
                "next_match_index": match_id_to_index.get(m.next_match_id) if m.next_match_id else None,
                "next_match_slot": m.next_match_slot,
                "loser_next_match_index": match_id_to_index.get(m.loser_next_match_id) if m.loser_next_match_id else None,
                "loser_next_match_slot": m.loser_next_match_slot,
                "is_loser_match": m.is_loser_match,
            }
            for i, m in enumerate(matches)
        ],
    }


@admin_bp.route("/api/export")
@login_required
@superadmin_required
def export_tournaments():
    ids_param = request.args.get("ids", "")
    include_menu = request.args.get("include_menu") == "1"
    try:
        ids = [int(x) for x in ids_param.split(",") if x.strip()] if ids_param else []
    except ValueError:
        return jsonify({"error": "Ungueltige IDs"}), 400
    if not ids and not include_menu:
        return jsonify({"error": "Keine IDs angegeben"}), 400
    tournaments = Tournament.query.filter(
        Tournament.id.in_(ids)
    ).order_by(Tournament.display_order, Tournament.name).all() if ids else []

    data = {
        # Version 2 ergaenzt: event_time, match.field, match.is_penalty,
        # Startgebuehren je Team. Version-1-Backups bleiben importierbar.
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tournaments": [_export_tournament(t) for t in tournaments],
    }
    if include_menu:
        data["menu_items"] = [item.to_dict() for item in MenuItem.query.order_by(MenuItem.display_order).all()]
    filename = f"turnier-backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    response = current_app.response_class(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _import_tournament(data):
    """Import a single tournament from an exported dict. Raises on error."""
    from datetime import date as _date, datetime as _dt
    from app.models import SETTINGS_DEFAULTS

    # Unique slug
    base_slug = data.get("slug") or slugify(data["name"])
    slug = base_slug
    counter = 2
    while Tournament.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    event_date = None
    if data.get("event_date"):
        event_date = _date.fromisoformat(data["event_date"])

    t = Tournament(
        name=data["name"],
        slug=slug,
        description=data.get("description", ""),
        event_date=event_date,
        # event_time fehlt in Backups vor Version 2 -> dann None
        event_time=data.get("event_time") or None,
        is_active=data.get("is_active", True),
        display_order=data.get("display_order", 0),
    )
    db.session.add(t)
    db.session.flush()

    # Settings
    settings = data.get("settings", {})
    for key, default_val in SETTINGS_DEFAULTS.items():
        value = settings.get(key, default_val)
        db.session.add(TournamentSettings(tournament_id=t.id, key=key, value=str(value)))

    # Groups
    group_name_to_id = {}
    for g_data in data.get("groups", []):
        g = Group(
            tournament_id=t.id,
            name=g_data["name"],
            display_order=g_data.get("display_order", 0),
        )
        db.session.add(g)
        db.session.flush()
        group_name_to_id[g_data["name"]] = g.id

    # Teams
    team_name_to_id = {}
    for team_data in data.get("teams", []):
        group_id = group_name_to_id.get(team_data["group_name"]) if team_data.get("group_name") else None
        team = Team(
            tournament_id=t.id,
            name=team_data["name"],
            logo_url=team_data.get("logo_url", ""),
            players=team_data.get("players", ""),
            group_id=group_id,
        )
        db.session.add(team)
        db.session.flush()
        team_name_to_id[team_data["name"]] = team.id

        # Startgebuehr (fehlt in Backups vor Version 2)
        p_data = team_data.get("payment")
        if p_data:
            paid_at = None
            if p_data.get("paid_at"):
                try:
                    paid_at = _dt.fromisoformat(p_data["paid_at"])
                except ValueError:
                    paid_at = None
            db.session.add(TeamPayment(
                team_id=team.id,
                paid=bool(p_data.get("paid", False)),
                paid_at=paid_at,
                amount=p_data.get("amount"),
                receipt_number=p_data.get("receipt_number"),
            ))

    # Matches – first pass (no next_match/loser refs yet)
    created_matches = []
    for m_data in data.get("matches", []):
        scheduled_time = None
        if m_data.get("scheduled_time"):
            scheduled_time = _dt.fromisoformat(m_data["scheduled_time"])

        match = Match(
            tournament_id=t.id,
            team1_id=team_name_to_id.get(m_data["team1_name"]) if m_data.get("team1_name") else None,
            team2_id=team_name_to_id.get(m_data["team2_name"]) if m_data.get("team2_name") else None,
            group_id=group_name_to_id.get(m_data["group_name"]) if m_data.get("group_name") else None,
            score_team1=m_data.get("score_team1", 0),
            score_team2=m_data.get("score_team2", 0),
            status=m_data.get("status", "planned"),
            scheduled_time=scheduled_time,
            match_order=m_data.get("match_order", 0),
            # field/is_penalty fehlen in Backups vor Version 2
            field=m_data.get("field", 1) or 1,
            timer_duration=m_data.get("timer_duration", 600),
            timer_remaining=m_data.get("timer_remaining", 600),
            timer_running=False,
            is_extra_time=m_data.get("is_extra_time", False),
            is_penalty=m_data.get("is_penalty", False),
            is_final=m_data.get("is_final", False),
            final_round=m_data.get("final_round"),
            final_position=m_data.get("final_position"),
            final_label=m_data.get("final_label"),
            next_match_slot=m_data.get("next_match_slot"),
            loser_next_match_slot=m_data.get("loser_next_match_slot"),
            is_loser_match=m_data.get("is_loser_match", False),
        )
        db.session.add(match)
        db.session.flush()
        created_matches.append((match, m_data))

    # Matches – second pass: resolve next_match_id / loser_next_match_id by index
    for match, m_data in created_matches:
        nmi = m_data.get("next_match_index")
        if nmi is not None and 0 <= nmi < len(created_matches):
            match.next_match_id = created_matches[nmi][0].id
        lnmi = m_data.get("loser_next_match_index")
        if lnmi is not None and 0 <= lnmi < len(created_matches):
            match.loser_next_match_id = created_matches[lnmi][0].id

    db.session.commit()


@admin_bp.route("/api/import", methods=["POST"])
@login_required
@superadmin_required
def import_tournaments():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Keine Datei ausgewaehlt.", "error")
        return redirect(url_for("admin.export_import_page"))

    try:
        data = json.load(file)
    except Exception:
        flash("Ungueltige JSON-Datei.", "error")
        return redirect(url_for("admin.export_import_page"))

    if data.get("version") not in SUPPORTED_IMPORT_VERSIONS or "tournaments" not in data:
        flash("Ungueltiges Exportformat (falsche Version oder fehlende Daten).", "error")
        return redirect(url_for("admin.export_import_page"))

    selected_names = set(request.form.getlist("names"))
    if not selected_names:
        flash("Keine Turniere ausgewaehlt.", "error")
        return redirect(url_for("admin.export_import_page"))

    imported = 0
    errors = []
    for t_data in data["tournaments"]:
        if t_data.get("name") not in selected_names:
            continue
        try:
            _import_tournament(t_data)
            imported += 1
        except Exception as e:
            db.session.rollback()
            errors.append(f"'{t_data.get('name', '?')}': {e}")

    if imported:
        flash(f"{imported} Turnier(e) erfolgreich importiert.", "success")
    for err in errors:
        flash(f"Fehler beim Import – {err}", "error")

    # Optional: import menu items
    if request.form.get("include_menu") == "1" and "menu_items" in data:
        existing_names = {item.name for item in MenuItem.query.all()}
        max_order = db.session.query(db.func.max(MenuItem.display_order)).scalar() or 0
        menu_imported = 0
        for item_data in data["menu_items"]:
            name = item_data.get("name", "").strip()
            if not name or name in existing_names:
                continue
            max_order += 1
            db.session.add(MenuItem(
                name=name,
                price=item_data.get("price", ""),
                category=item_data.get("category", "speise"),
                description=item_data.get("description", ""),
                display_order=max_order,
            ))
            existing_names.add(name)
            menu_imported += 1
        db.session.commit()
        if menu_imported:
            flash(f"{menu_imported} Speisekarten-Eintraege importiert.", "success")

    return redirect(url_for("admin.export_import_page"))
