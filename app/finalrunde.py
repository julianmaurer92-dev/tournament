"""Finalrunden: Baeume erzeugen, Paarungen vorausberechnen, Sieger weiterleiten.

Aus admin.py herausgezogen (Nachtschicht 2026-10-24). Der Inhalt ist
unveraendert – nur die Funktionen liegen jetzt in einem eigenen Modul,
damit admin.py nicht mehr alles auf einmal ist und die Finalrundenlogik
einzeln lesbar bleibt.

Unterstuetzte Modi: classic_ko, semi_final, direct_final, rank_vs_rank,
free_ko, custom.
"""
import math

from app import db
from app.models import (
    Group, Match, Team, calculate_overall_rankings, calculate_standings,
    get_seeded_teams_cross_group, get_setting,
)

# Deutsche Rundenbezeichnungen
ROUND_LABELS = {1: "Finale", 2: "Halbfinale", 3: "Viertelfinale", 4: "Achtelfinale"}


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
