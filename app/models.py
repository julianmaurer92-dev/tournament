import re as _re
import time
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


# ──────────────────────────────────────
# Helpers
# ──────────────────────────────────────

def slugify(text):
    """Generate URL-safe slug from text."""
    text = text.lower().strip()
    text = _re.sub(r"[^\w\s-]", "", text)
    text = _re.sub(r"[\s_]+", "-", text)
    text = _re.sub(r"-+", "-", text)
    return text.strip("-") or "turnier"


# ──────────────────────────────────────
# Admin user
# ──────────────────────────────────────

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    email = db.Column(db.String(254), unique=True, nullable=True)
    role = db.Column(db.String(20), default="editor", nullable=False)  # superadmin | editor | viewer

    tournament_access = db.relationship(
        "UserTournamentAccess", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_tournament_access(self, tournament_id):
        if self.role == "superadmin":
            return True
        return UserTournamentAccess.query.filter_by(
            user_id=self.id, tournament_id=tournament_id
        ).first() is not None

    def can_edit(self):
        return self.role in ("superadmin", "editor")

    def can_delete(self):
        return self.role == "superadmin"


# ──────────────────────────────────────
# User ↔ Tournament Access (many-to-many)
# ──────────────────────────────────────

class UserTournamentAccess(db.Model):
    __tablename__ = "user_tournament_access"
    user_id = db.Column(db.Integer, db.ForeignKey("admin.id"), primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"), primary_key=True)


# ──────────────────────────────────────
# Tournaments
# ──────────────────────────────────────

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    event_date = db.Column(db.Date, nullable=True)
    event_time = db.Column(db.String(5), nullable=True)  # "HH:MM"
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    groups = db.relationship("Group", backref="tournament", lazy="dynamic",
                             cascade="all, delete-orphan")
    teams = db.relationship("Team", backref="tournament", lazy="dynamic",
                            cascade="all, delete-orphan")
    matches = db.relationship("Match", backref="tournament", lazy="dynamic",
                              cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "is_active": self.is_active,
            "display_order": self.display_order,
        }


# ──────────────────────────────────────
# Key-value settings (per tournament)
# ──────────────────────────────────────

# Defaults applied when a tournament is created
SETTINGS_DEFAULTS = {
    "tournament_name": "TURNIER",
    "color_title": "#22c55e",
    "color_primary": "#22c55e",
    "color_secondary": "#1a2332",
    "tournament_phase": "GROUP_STAGE",
    "final_mode": "",
    "default_timer_regular": "600",
    "default_timer_extra": "300",
    "announcement": "",
    "hide_results": "0",
    "hide_table": "0",
    "hide_scores": "0",
    "theme": "dark",
    "num_fields": "1",
    "org_logo_url": "",
    "tournament_rules": "",
}


class TournamentSettings(db.Model):
    __tablename__ = "tournament_settings"
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"), primary_key=True)
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    tournament_rel = db.relationship("Tournament", backref="settings")


def get_setting(tournament_id, key, default=None):
    """Read a single setting for a specific tournament."""
    row = db.session.get(TournamentSettings, (tournament_id, key))
    if row:
        return row.value
    return default or SETTINGS_DEFAULTS.get(key, "")


def set_setting(tournament_id, key, value):
    """Write a single setting for a specific tournament."""
    row = db.session.get(TournamentSettings, (tournament_id, key))
    if row:
        row.value = value
    else:
        db.session.add(TournamentSettings(
            tournament_id=tournament_id, key=key, value=value
        ))
    db.session.commit()


def get_all_settings(tournament_id):
    """Return all settings for a tournament as a dict, with defaults."""
    result = dict(SETTINGS_DEFAULTS)
    for row in TournamentSettings.query.filter_by(tournament_id=tournament_id).all():
        result[row.key] = row.value
    return result


def ensure_default_settings(tournament_id):
    """Insert default settings for a tournament if they don't exist yet."""
    for key, value in SETTINGS_DEFAULTS.items():
        if not db.session.get(TournamentSettings, (tournament_id, key)):
            db.session.add(TournamentSettings(
                tournament_id=tournament_id, key=key, value=value
            ))
    db.session.commit()


# ──────────────────────────────────────
# Groups
# ──────────────────────────────────────

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("tournament_id", "name", name="uq_group_tournament_name"),
    )

    teams = db.relationship(
        "Team", backref="group", lazy="joined", order_by="Team.name"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tournament_id": self.tournament_id,
            "name": self.name,
            "display_order": self.display_order,
        }


# ──────────────────────────────────────
# Teams
# ──────────────────────────────────────

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    logo_url = db.Column(db.String(500), default="")
    players = db.Column(db.Text, default="")
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("tournament_id", "name", name="uq_team_tournament_name"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "logo_url": self.logo_url,
            "players": self.players,
            "group_id": self.group_id,
            "group_name": self.group.name if self.group else None,
        }


# ──────────────────────────────────────
# Team Payments (Startgebühr)
# ──────────────────────────────────────

class TeamPayment(db.Model):
    __tablename__ = "team_payment"
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), primary_key=True)
    paid = db.Column(db.Boolean, default=False, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    amount = db.Column(db.Float, nullable=True)   # actual paid amount (may differ from default)
    receipt_number = db.Column(db.String(50), nullable=True)

    team = db.relationship("Team", backref=db.backref("payment", uselist=False))


# ──────────────────────────────────────
# Matches
# ──────────────────────────────────────

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournament.id"), nullable=True)
    team1_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=True)
    team2_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    score_team1 = db.Column(db.Integer, default=0)
    score_team2 = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="planned")  # planned | live | finished
    scheduled_time = db.Column(db.DateTime, nullable=True)
    match_order = db.Column(db.Integer, default=0)

    field = db.Column(db.Integer, default=1)  # 1 or 2 – which pitch the match is played on

    # Timer (seconds)
    timer_duration = db.Column(db.Integer, default=600)
    timer_remaining = db.Column(db.Integer, default=600)
    timer_running = db.Column(db.Boolean, default=False)
    timer_started_at = db.Column(db.Float, nullable=True)
    is_extra_time = db.Column(db.Boolean, default=False)
    is_penalty = db.Column(db.Boolean, default=False)

    # Final round fields
    is_final = db.Column(db.Boolean, default=False)
    final_round = db.Column(db.Integer, nullable=True)       # 1=Finale, 2=HF, 3=VF, 4=AF
    final_position = db.Column(db.Integer, nullable=True)     # Position within round (0-based)
    final_label = db.Column(db.String(100), nullable=True)    # e.g. "Halbfinale 1"
    next_match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=True)
    next_match_slot = db.Column(db.Integer, nullable=True)    # 1=team1, 2=team2
    loser_next_match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=True)
    loser_next_match_slot = db.Column(db.Integer, nullable=True)
    is_loser_match = db.Column(db.Boolean, default=False)     # True for "Platz 3" match

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    team1 = db.relationship("Team", foreign_keys=[team1_id], lazy="joined")
    team2 = db.relationship("Team", foreign_keys=[team2_id], lazy="joined")
    group = db.relationship("Group", lazy="joined")

    def to_dict(self):
        remaining = self.timer_remaining
        if self.timer_running and self.timer_started_at:
            elapsed = time.time() - self.timer_started_at
            remaining = max(0, self.timer_remaining - int(elapsed))

        return {
            "id": self.id,
            "team1": self.team1.to_dict() if self.team1 else None,
            "team2": self.team2.to_dict() if self.team2 else None,
            "group_id": self.group_id,
            "group_name": self.group.name if self.group else None,
            "score_team1": self.score_team1,
            "score_team2": self.score_team2,
            "status": self.status,
            "scheduled_time": (
                self.scheduled_time.isoformat() if self.scheduled_time else None
            ),
            "match_order": self.match_order,
            "field": self.field or 1,
            "timer_duration": self.timer_duration,
            "timer_remaining": remaining,
            "timer_running": self.timer_running,
            "is_extra_time": self.is_extra_time,
            "is_penalty": self.is_penalty,
            "is_final": self.is_final,
            "final_round": self.final_round,
            "final_position": self.final_position,
            "final_label": self.final_label,
            "next_match_id": self.next_match_id,
            "next_match_slot": self.next_match_slot,
            "is_loser_match": self.is_loser_match,
        }


# ──────────────────────────────────────
# Standings calculation (per group)
# ──────────────────────────────────────

def calculate_standings(group_id=None, tournament_id=None):
    """Build sorted standings table from finished group matches only."""
    if group_id:
        teams = Team.query.filter_by(group_id=group_id).all()
        finished = (
            Match.query
            .filter_by(status="finished", group_id=group_id, is_final=False)
            .all()
        )
    elif tournament_id:
        teams = Team.query.filter_by(tournament_id=tournament_id).all()
        finished = Match.query.filter_by(
            status="finished", tournament_id=tournament_id, is_final=False
        ).all()
    else:
        return []

    table = {}
    for t in teams:
        table[t.id] = {
            "team": t.to_dict(),
            "played": 0, "won": 0, "drawn": 0, "lost": 0,
            "goals_for": 0, "goals_against": 0, "goal_diff": 0, "points": 0,
        }

    for m in finished:
        s1 = table.get(m.team1_id)
        s2 = table.get(m.team2_id)
        if not s1 or not s2:
            continue
        s1["played"] += 1
        s2["played"] += 1
        s1["goals_for"] += m.score_team1
        s1["goals_against"] += m.score_team2
        s2["goals_for"] += m.score_team2
        s2["goals_against"] += m.score_team1
        if m.score_team1 > m.score_team2:
            s1["won"] += 1; s1["points"] += 3; s2["lost"] += 1
        elif m.score_team1 < m.score_team2:
            s2["won"] += 1; s2["points"] += 3; s1["lost"] += 1
        else:
            s1["drawn"] += 1; s2["drawn"] += 1
            s1["points"] += 1; s2["points"] += 1

    for s in table.values():
        s["goal_diff"] = s["goals_for"] - s["goals_against"]

    ranked = sorted(
        table.values(),
        key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]),
        reverse=True,
    )
    for i, s in enumerate(ranked, 1):
        s["rank"] = i
    return ranked


# ──────────────────────────────────────
# Overall rankings (cross-group)
# ──────────────────────────────────────

def calculate_overall_rankings(tournament_id):
    """Rank all teams across all groups by points, goal_diff, goals_for."""
    groups = Group.query.filter_by(tournament_id=tournament_id).all()
    all_ranked = []
    for g in groups:
        standings = calculate_standings(group_id=g.id)
        for s in standings:
            s["group_rank"] = s["rank"]
            s["group_name"] = g.name
            s["group_id"] = g.id
        all_ranked.extend(standings)

    all_ranked.sort(
        key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]),
        reverse=True,
    )
    for i, s in enumerate(all_ranked, 1):
        s["overall_rank"] = i
    return all_ranked


def get_seeded_teams_cross_group(tournament_id, num_teams):
    """
    For KO rounds: return team pairs seeded cross-group.
    With 2 groups: A1 vs B(last), A2 vs B(last-1), etc.
    Fallback to overall ranking for >2 groups or uneven groups.
    """
    groups = Group.query.filter_by(tournament_id=tournament_id).order_by(
        Group.display_order
    ).all()
    standings_per_group = {}
    for g in groups:
        standings_per_group[g.id] = calculate_standings(group_id=g.id)

    # 2 groups with enough teams: classic cross-seeding
    if len(groups) == 2:
        g1 = standings_per_group[groups[0].id]
        g2 = standings_per_group[groups[1].id]
        per_group = num_teams // 2
        if len(g1) >= per_group and len(g2) >= per_group:
            g1_top = g1[:per_group]
            g2_top = g2[:per_group]
            pairs = []
            for i in range(per_group):
                pairs.append((
                    g1_top[i]["team"]["id"],
                    g2_top[per_group - 1 - i]["team"]["id"],
                ))
            return pairs

    # Fallback: overall ranking, standard bracket seeding 1v(n), 2v(n-1), ...
    overall = calculate_overall_rankings(tournament_id)[:num_teams]
    pairs = []
    half = len(overall) // 2
    for i in range(half):
        pairs.append((
            overall[i]["team"]["id"],
            overall[len(overall) - 1 - i]["team"]["id"],
        ))
    return pairs


# ──────────────────────────────────────
# Menu items (global, for the event)
# ──────────────────────────────────────

class MenuItem(db.Model):
    __tablename__ = "menu_item"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.String(20), default="")
    category = db.Column(db.String(20), default="speise")  # speise | getraenk
    description = db.Column(db.String(300), default="")
    display_order = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "category": self.category,
            "description": self.description,
            "display_order": self.display_order,
        }
