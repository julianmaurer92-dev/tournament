"""JSON-Backup: Turniere exportieren und importieren.

Aus admin.py herausgezogen (Nachtschicht 2026-10-24).

Exportversion 2 ergaenzt gegenueber Version 1: event_time, match.field,
match.is_penalty, Startgebuehren je Team, Spielereignisse, Schiedsrichter
und Vereinsanmeldungen. Version-1-Backups bleiben importierbar – fehlende
Felder fallen auf Standardwerte zurueck.
"""
import json
from datetime import datetime, timezone

from flask import (
    current_app, flash, jsonify, redirect, render_template, request, url_for,
)
from flask_login import login_required

from app import db
from app.auth import superadmin_required
from app.blueprints import admin_bp
from app.models import (
    ANMELDUNG_OFFEN, ANMELDUNG_STATUS, EREIGNIS_ARTEN,
    Group, Match, MatchEvent, MenuItem, Referee, Registration, Team,
    TeamPayment, Tournament, TournamentSettings, get_all_settings,
    neues_token, slugify,
)

# Aktuelle Exportversion und die Versionen, die der Import lesen kann
EXPORT_VERSION = "2"
SUPPORTED_IMPORT_VERSIONS = ("1", "2")


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

    schiedsrichter = Referee.query.filter_by(tournament_id=t.id).order_by(
        Referee.name).all()
    referee_id_to_name = {r.id: r.name for r in schiedsrichter}

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
                "referee_name": referee_id_to_name.get(m.referee_id) if m.referee_id else None,
                # Tore und Karten gehoeren zum Spiel (seit Exportversion 2)
                "events": [
                    {
                        "art": e.art,
                        "team_name": team_id_to_name.get(e.team_id) if e.team_id else None,
                        "player_name": e.player_name or "",
                        "minute": e.minute,
                        "note": e.note or "",
                    }
                    for e in m.events
                ],
            }
            for i, m in enumerate(matches)
        ],
        # Schiedsrichter (seit Exportversion 2)
        "referees": [
            {
                "name": r.name,
                "phone": r.phone or "",
                "note": r.note or "",
                "team_name": team_id_to_name.get(r.team_id) if r.team_id else None,
                "is_active": bool(r.is_active),
            }
            for r in schiedsrichter
        ],
        # Vereinsanmeldungen inkl. Entscheidungshistorie (seit Exportversion 2)
        "registrations": [
            {
                "club_name": r.club_name,
                "team_name": r.team_name or "",
                "contact_name": r.contact_name,
                "contact_email": r.contact_email,
                "contact_phone": r.contact_phone or "",
                "player_count": r.player_count,
                "notes": r.notes or "",
                "status": r.status,
                "token": r.token,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "decided_at": r.decided_at.isoformat() if r.decided_at else None,
                "decision_note": r.decision_note or "",
                "team_name_ref": team_id_to_name.get(r.team_id) if r.team_id else None,
            }
            for r in Registration.query.filter_by(tournament_id=t.id)
            .order_by(Registration.created_at).all()
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


def _als_zeitpunkt(text):
    """ISO-Text zu datetime, oder None bei leer/unlesbar."""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None


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

    # Schiedsrichter (fehlen in Backups vor Version 2) – vor den Spielen,
    # damit die Zuordnung je Spiel aufgeloest werden kann
    referee_name_to_id = {}
    for r_data in data.get("referees", []):
        name = (r_data.get("name") or "").strip()[:150]
        if not name or name in referee_name_to_id:
            continue
        referee = Referee(
            tournament_id=t.id,
            name=name,
            phone=(r_data.get("phone") or "")[:60],
            note=(r_data.get("note") or "")[:300],
            team_id=team_name_to_id.get(r_data.get("team_name")),
            is_active=bool(r_data.get("is_active", True)),
        )
        db.session.add(referee)
        db.session.flush()
        referee_name_to_id[name] = referee.id

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
            referee_id=referee_name_to_id.get(m_data.get("referee_name")),
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

        # Tore und Karten (fehlen in Backups vor Version 2)
        for e_data in m_data.get("events", []):
            art = e_data.get("art")
            if art not in EREIGNIS_ARTEN:
                continue
            db.session.add(MatchEvent(
                match_id=match.id,
                tournament_id=t.id,
                team_id=team_name_to_id.get(e_data.get("team_name")),
                art=art,
                player_name=(e_data.get("player_name") or "")[:150],
                minute=e_data.get("minute"),
                note=(e_data.get("note") or "")[:300],
            ))

    # Matches – second pass: resolve next_match_id / loser_next_match_id by index
    for match, m_data in created_matches:
        nmi = m_data.get("next_match_index")
        if nmi is not None and 0 <= nmi < len(created_matches):
            match.next_match_id = created_matches[nmi][0].id
        lnmi = m_data.get("loser_next_match_index")
        if lnmi is not None and 0 <= lnmi < len(created_matches):
            match.loser_next_match_id = created_matches[lnmi][0].id

    # Vereinsanmeldungen (fehlen in Backups vor Version 2)
    for r_data in data.get("registrations", []):
        if not r_data.get("club_name") or not r_data.get("contact_email"):
            continue
        # Token nicht uebernehmen, wenn es schon vergeben ist – sonst
        # scheitert der Import eines Backups in dieselbe Instanz.
        token = r_data.get("token") or neues_token()
        if Registration.query.filter_by(token=token).first():
            token = neues_token()
        db.session.add(Registration(
            tournament_id=t.id,
            club_name=r_data["club_name"][:150],
            team_name=(r_data.get("team_name") or "")[:150],
            contact_name=(r_data.get("contact_name") or "")[:150],
            contact_email=r_data["contact_email"][:254],
            contact_phone=(r_data.get("contact_phone") or "")[:60],
            player_count=r_data.get("player_count"),
            notes=r_data.get("notes") or "",
            status=(r_data.get("status") if r_data.get("status") in ANMELDUNG_STATUS
                    else ANMELDUNG_OFFEN),
            token=token,
            created_at=_als_zeitpunkt(r_data.get("created_at")),
            decided_at=_als_zeitpunkt(r_data.get("decided_at")),
            decision_note=r_data.get("decision_note") or "",
            team_id=team_name_to_id.get(r_data.get("team_name_ref")),
        ))

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
