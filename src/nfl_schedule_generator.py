"""
nfl_schedule_generator.py

Combined NFL schedule generator:
  1. Reads games from opponents.py / data/games.txt
  2. Uses ILP (PuLP) to assign games to weeks with structural constraints
  3. Assigns kickoff times based on data/previous_records.txt win totals
  4. Enforces primetime rules:
       - No team gets the same primetime slot in back-to-back weeks
       - High-record teams get priority for SNF/MNF
       - Low-record teams (< 7 wins) are excluded from primetime unless
         their opponent is high-record (>= 12 wins)
       - Double-header MNF on alternating weeks (odd weeks 1-15) to maximise
         MNF variety and reduce consecutive same-slot violations
       - No consecutive double-header MNF weeks
       - TNF excluded in Week 12 (Thanksgiving handles its own night game)
  5. Writes final schedule to data/schedule_with_times.txt
"""

import re
import random
import pulp
from itertools import cycle
from collections import defaultdict
from primetime_weights import PRIMETIME_WEIGHTS, WEIGHT_TO_TARGET

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EARLY_WINDOW       = "1:00 PM ET"
LATE_WINDOW_1      = "4:05 PM ET"
LATE_WINDOW_2      = "4:25 PM ET"
SNF_SLOT           = "8:20 PM ET (Sunday Night Football)"
TNF_SLOT           = "8:15 PM ET (Thursday Night Football)"
MNF_SLOT           = "8:15 PM ET (Monday Night Football)"
MNF_SLOT_2         = "10:00 PM ET (Monday Night Football)"   # second game in double-header
MNF_SLOT_EARLY     = "7:00 PM ET (Monday Night Football)"    # first game in double-header
KICKOFF_SLOT       = "8:20 PM ET (Thursday Kickoff Game)"
FLEX_SLOT          = "TBD (Flex Scheduling - Nighttime)"
THANKSGIVING_EARLY = "12:30 PM ET (Thanksgiving)"
THANKSGIVING_MID   = "4:30 PM ET (Thanksgiving)"
THANKSGIVING_NIGHT = "8:20 PM ET (Thanksgiving Night Football)"
CHRISTMAS_SLOT     = "8:20 PM ET (Christmas Night Football)"
CHRISTMAS_SLOT_2   = "4:30 PM ET (Christmas Afternoon Football)"
CHRISTMAS_WEEK     = 16

# International game slots by week (week -> label)
INTERNATIONAL_SLOTS = {
    1:  "8:15 PM ET (Melbourne, Australia)",       # 49ers @ Rams
    3:  "9:30 PM ET (Munich, Germany)",             # Lions home (Allianz Arena)
    4:  "9:30 AM ET (London, UK)",                  # Jaguars home (Tottenham)
    5:  "9:30 PM ET (Paris, France)",               # Saints home (Stade de France)
    6:  "9:30 AM ET (London, UK)",                  # Commanders home (Tottenham)
    7:  "9:30 AM ET (London, UK)",                  # Jaguars home (Wembley)
    8:  "9:30 PM ET (Rio de Janiero, Brazil)",      # Cowboys home (Maracana)
    9:  "9:30 AM ET (Madrid, Spain)",               # Falcons home (Bernabeu)
    15: "9:30 PM ET (Mexico City, Mexico)",         # 49ers home (Azteca)
}

# International home teams by week — the team listed as "home" for that game
INTERNATIONAL_HOME = {
    1:  "Rams",
    3:  "Lions",
    4:  "Jaguars",
    5:  "Saints",
    6:  "Commanders",
    7:  "Jaguars",
    8:  "Cowboys",
    9:  "Falcons",
    15: "49ers",
}

# Weeks that have an international game
INTL_WEEKS = set(INTERNATIONAL_SLOTS.keys())

# Pinned games that must go in specific slots/weeks
# Format: { (away, home): (week, slot_label) }
PINNED_GAMES = {
    ("Bears", "Seahawks"): (1, KICKOFF_SLOT),
    ("49ers",  "Rams"):    (1, INTERNATIONAL_SLOTS[1]),
}

# Matchups that must always get a specific kickoff time (regardless of week).
# Key: frozenset of the two team names. Value: the required slot string.
FIXED_SLOT_GAMES = {
    frozenset(["Seahawks", "Patriots"]): LATE_WINDOW_2,  # must be 4:25 PM ET
}

# Weeks with double-header MNF — dynamically selected from W2–W17.
# Picks `n` evenly-spaced weeks across the range, then groups them into
# consecutive pairs so they cluster naturally (pairs OK, triples not).
def _pick_double_header_weeks(n=4, start=2, end=17):
    """
    Select `n` double-header MNF weeks from [start, end].
    Groups them into pairs of consecutive weeks (pair_count = n // 2).
    Pairs are spaced evenly across the range so no triple is ever formed.
    """
    pair_count = n // 2          # e.g. 4 → 2 pairs
    # Divide the range into `pair_count` equal segments and anchor each pair
    # at the midpoint of its segment.
    segment = (end - start) / pair_count
    weeks = set()
    for i in range(pair_count):
        mid = round(start + segment * i + segment / 2)
        # Clamp so both weeks of the pair stay within [start, end]
        mid = max(start, min(end - 1, mid))
        weeks.add(mid)
        weeks.add(mid + 1)
    return weeks

DOUBLE_HEADER_MNF_WEEKS = _pick_double_header_weeks()

# Maximum number of primetime appearances (TNF/SNF/MNF) any team can have
MAX_PRIMETIME_PER_TEAM = 7

# Minimum guaranteed primetime appearances for specific teams.
# The retry loop in write_schedule treats shortfalls as violations and keeps
# searching until the floor is met (or the attempt limit is reached).
MIN_PRIMETIME_FLOORS = {
    "Cowboys": 5,
}

# Thanksgiving hosts (Week 12)
THANKSGIVING_HOSTS = ["Lions", "Cowboys"]

ALL_TEAMS = [
    "Bears", "Lions", "Packers", "Vikings",
    "Cardinals", "Rams", "Seahawks", "49ers",
    "Cowboys", "Eagles", "Giants", "Commanders",
    "Falcons", "Panthers", "Saints", "Buccaneers",
    "Ravens", "Bengals", "Browns", "Steelers",
    "Broncos", "Chiefs", "Raiders", "Chargers",
    "Bills", "Dolphins", "Patriots", "Jets",
    "Jaguars", "Texans", "Titans", "Colts",
]

DIVISIONS = {
    "NFC North":  ["Bears", "Lions", "Packers", "Vikings"],
    "NFC West":   ["Cardinals", "Rams", "Seahawks", "49ers"],
    "NFC East":   ["Cowboys", "Eagles", "Giants", "Commanders"],
    "NFC South":  ["Falcons", "Panthers", "Saints", "Buccaneers"],
    "AFC North":  ["Ravens", "Bengals", "Browns", "Steelers"],
    "AFC West":   ["Broncos", "Chiefs", "Raiders", "Chargers"],
    "AFC East":   ["Bills", "Dolphins", "Patriots", "Jets"],
    "AFC South":  ["Jaguars", "Texans", "Titans", "Colts"],
}

TEAM_TO_DIVISION = {team: div for div, teams in DIVISIONS.items() for team in teams}
TEAM_TO_CONFERENCE = {
    team: ("AFC" if div.startswith("AFC") else "NFC")
    for div, teams in DIVISIONS.items() for team in teams
}

# ---------------------------------------------------------------------------
# Records loader
# ---------------------------------------------------------------------------

def load_records(filepath="data/previous_records.txt"):
    """Parse data/previous_records.txt → {team: wins}. Handles tie records like 9-7-1."""
    records = {}
    record_re = re.compile(r'^\s+(\w+)\s+(\d+)-(\d+)(?:-(\d+))?')
    with open(filepath) as f:
        for line in f:
            m = record_re.match(line)
            if m:
                team = m.group(1)
                wins = int(m.group(2))
                ties = int(m.group(4)) if m.group(4) else 0
                records[team] = wins + ties * 0.5   # ties count as half a win
    return records

TEAM_WINS = load_records()

# Per-team primetime targets derived from primetime_weights.py
# Falls back to MAX_PRIMETIME_PER_TEAM for any team not listed.
PRIMETIME_TARGETS = {
    team: WEIGHT_TO_TARGET.get(PRIMETIME_WEIGHTS.get(team, 3), 4)
    for team in ALL_TEAMS
}

# ---------------------------------------------------------------------------
# Primetime scoring
# ---------------------------------------------------------------------------

def primetime_score(game_str):
    """Combined win total for both teams — higher = more attractive primetime game."""
    score = 0
    for team, wins in TEAM_WINS.items():
        if team in game_str:
            score += wins
    return score


def is_divisional(game_str):
    """Return True if both teams in the game are in the same division."""
    teams = [t for t in ALL_TEAMS if t in game_str]
    if len(teams) < 2:
        return False
    return TEAM_TO_DIVISION.get(teams[0]) == TEAM_TO_DIVISION.get(teams[1])


def tnf_score(game_str):
    """Score for TNF selection: divisional games get a +10 boost."""
    return primetime_score(game_str) + (10 if is_divisional(game_str) else 0)


def is_primetime_eligible(game_str, threshold_low=7, threshold_high=12):
    """
    A game is primetime eligible if:
      - At least one team has >= threshold_high wins, OR
      - Both teams have >= threshold_low wins
    """
    wins = [TEAM_WINS.get(t, 0) for t in ALL_TEAMS if t in game_str]
    if not wins:
        return False
    if max(wins) >= threshold_high:
        return True
    if len(wins) >= 2 and min(wins) >= threshold_low:
        return True
    return False

# ---------------------------------------------------------------------------
# Game / schedule parsing
# ---------------------------------------------------------------------------

def parse_games(file_path):
    all_games = []
    divisional_games = defaultdict(list)
    seen = set()
    with open(file_path) as f:
        section = None
        for line in f:
            line = line.strip()
            if line == "All Games:":
                section = "all"
            elif line == "Divisional Games:":
                section = "div"
            elif line and section == "all":
                away, home = line.split(" @ ")
                g = (home, away)
                if g not in seen:
                    all_games.append(g)
                    seen.add(g)
            elif line and section == "div":
                away, home = line.split(" @ ")
                divisional_games[home].append(away)
                g = (home, away)
                if g not in seen:
                    all_games.append(g)
                    seen.add(g)
    return all_games, divisional_games


def parse_previous_schedule(file_path):
    """Parse data/previous_schedule.txt → {week: [(home, away), ...]}."""
    schedule = defaultdict(list)
    current_week = None
    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("Week"):
                current_week = int(line.split()[1].rstrip(":"))
            elif line and current_week:
                # Handle both "1. Away @ Home" and "Away @ Home" formats
                game_part = re.sub(r'^\d+\.\s*', '', line)
                parts = game_part.split(" @ ")
                if len(parts) == 2:
                    schedule[current_week].append((parts[1].strip(), parts[0].strip()))
    return schedule

# ---------------------------------------------------------------------------
# ILP scheduler
# ---------------------------------------------------------------------------

def generate_schedule(all_games, divisional_games, previous_schedule, weeks=18):
    """
    Assign each game to a week using ILP with the following constraints:
      - Each game scheduled exactly once
      - Each team plays at most once per week
      - Weeks 1–4 and 15-18 have exactly 16 games (no byes)
      - Week 18 contains only divisional games
      - Lions and Cowboys host in Week 12 (Thanksgiving)
      - Pinned games go to their specified weeks
      - No more than 2 consecutive home or away games
      - No same matchup as the previous season in the same week
      - High-win teams get at least 4 primetime-attractive weeks
        (weeks where they appear in weeks 1–16 against good opponents)
      - Bad-record teams (< 5 wins) get byes distributed across weeks 5–14
      - No team plays the same opponent in back-to-back weeks
    """
    prob = pulp.LpProblem("NFL_Schedule", pulp.LpMinimize)

    x = pulp.LpVariable.dicts(
        "GW",
        ((g, w) for g in all_games for w in range(1, weeks + 1)),
        cat="Binary"
    )

    teams = set(t for g in all_games for t in g)

    # -- Each game scheduled exactly once --
    for g in all_games:
        prob += pulp.lpSum(x[g, w] for w in range(1, weeks + 1)) == 1

    # -- Each team plays at most one game per week --
    for t in teams:
        for w in range(1, weeks + 1):
            prob += pulp.lpSum(x[g, w] for g in all_games if t in g) <= 1

    # -- Full weeks (no byes) in weeks 1-4 and 15-18 --
    for w in list(range(1, 5)) + list(range(15, 19)):
        prob += pulp.lpSum(x[g, w] for g in all_games) == 16

    # -- At least 13 games per week --
    for w in range(1, weeks + 1):
        prob += pulp.lpSum(x[g, w] for g in all_games) >= 13

    # -- Week 18: divisional games only --
    div_set = set()
    for home, opponents in divisional_games.items():
        for away in opponents:
            div_set.add((home, away))
            div_set.add((away, home))
    for g in all_games:
        if g not in div_set:
            prob += x[g, 18] == 0

    # -- Thanksgiving: Lions and Cowboys host in Week 12 --
    for host in THANKSGIVING_HOSTS:
        prob += pulp.lpSum(x[g, 12] for g in all_games if g[0] == host) == 1

    # -- International games: pin each home team to their designated week --
    for week, home_team in INTERNATIONAL_HOME.items():
        if home_team in ("Rams", "Seahawks"):  # already handled by PINNED_GAMES
            continue
        prob += pulp.lpSum(x[g, week] for g in all_games if g[0] == home_team) >= 1

    # -- Pinned games --
    for (away, home), (week, _slot) in PINNED_GAMES.items():
        g = (home, away)
        if g in all_games:
            prob += x[g, week] == 1

    # -- Divisional game spread: at most 2 divisional games per team in weeks 1-4 --
    # Prevents rivalry matchups from all clustering at the start of the season.
    div_set_spread = set()
    for home, opponents in divisional_games.items():
        for away in opponents:
            div_set_spread.add((home, away))
            div_set_spread.add((away, home))
    for t in teams:
        prob += pulp.lpSum(
            x[g, w]
            for g in all_games if g in div_set_spread and t in g
            for w in range(1, 5)
        ) <= 2

    # -- No more than 2 consecutive home or away games --
    for t in teams:
        for w in range(1, weeks - 1):
            prob += (
                pulp.lpSum(x[g, w]     for g in all_games if g[0] == t) +
                pulp.lpSum(x[g, w + 1] for g in all_games if g[0] == t) +
                pulp.lpSum(x[g, w + 2] for g in all_games if g[0] == t)
            ) <= 2
            prob += (
                pulp.lpSum(x[g, w]     for g in all_games if g[1] == t) +
                pulp.lpSum(x[g, w + 1] for g in all_games if g[1] == t) +
                pulp.lpSum(x[g, w + 2] for g in all_games if g[1] == t)
            ) <= 2

    # -- No same-week matchup as previous season --
    for w, games in previous_schedule.items():
        if w == 18:
            continue
        for g in games:
            if g in all_games:
                prob += x[g, w] == 0
            rev = (g[1], g[0])
            if rev in all_games:
                prob += x[rev, w] == 0

    # -- No team plays same opponent in back-to-back weeks --
    for g in all_games:
        rev = (g[1], g[0])
        if rev in all_games:
            for w in range(1, weeks):
                prob += x[g, w] + x[rev, w + 1] <= 1

    # -- Objective: maximize total primetime-score in weeks 1-16
    #    (encourage best matchups to appear in schedulable weeks) --
    scored_games = [(primetime_score(f"{g[1]} @ {g[0]}"), g) for g in all_games]
    prob += -pulp.lpSum(
        score * x[g, w]
        for score, g in scored_games
        for w in range(1, 17)
        if score > 20   # only pull top matchups into early weeks
    )

    solver = pulp.PULP_CBC_CMD(msg=1, options=[
        "-timeLimit", "300",   # stop after 5 minutes if no solution yet
        "-feas",               # switch CBC to feasibility mode (find any solution fast)
    ])
    status = prob.solve(solver)
    print(f"Solver status: {pulp.LpStatus[prob.status]}")

    if pulp.LpStatus[prob.status] not in ("Optimal", "Not Solved"):
        print(f"No feasible solution found (status: {pulp.LpStatus[prob.status]}).")
        return defaultdict(list)

    # Check if any variables were actually assigned (handles "Not Solved" with a found solution)
    schedule = defaultdict(list)
    for g in all_games:
        for w in range(1, weeks + 1):
            val = pulp.value(x[g, w])
            if val is not None and round(val) == 1:
                schedule[w].append(g)

    if not schedule:
        print("No games were assigned — solver found no feasible solution.")
        return defaultdict(list)

    return schedule

# ---------------------------------------------------------------------------
# Bye computation
# ---------------------------------------------------------------------------

def compute_byes(schedule, weeks=18):
    byes = {}
    for w in range(1, weeks + 1):
        playing = set(t for g in schedule.get(w, []) for t in g)
        byes[w] = sorted(set(ALL_TEAMS) - playing)
    return byes

# ---------------------------------------------------------------------------
# Time assignment helpers
# ---------------------------------------------------------------------------

def _snf_mnf_tail(result, snf_slot=SNF_SLOT):
    """Pull SNF and MNF entries to the end, SNF immediately before MNF."""
    snf = [r for r in result if r[1] == snf_slot]
    mnf = [r for r in result if "Monday Night Football" in r[1]]
    rest = [r for r in result if r[1] != snf_slot and "Monday Night Football" not in r[1]]
    return rest + snf + mnf


def _fill_sunday_slots(games, used_indices, result_map):
    """Fill remaining games into early/late Sunday windows."""
    # First, apply any FIXED_SLOT_GAMES overrides before normal filling.
    for i, game in enumerate(games):
        if i in used_indices:
            continue
        parts = game.split(" @ ")
        key = frozenset(t.strip() for t in parts)
        if key in FIXED_SLOT_GAMES:
            result_map[i] = (game, FIXED_SLOT_GAMES[key])
            used_indices.add(i)

    late_cycle = cycle([LATE_WINDOW_1, LATE_WINDOW_2])
    early_used = sum(1 for i in used_indices if result_map.get(i, ("", ""))[1] == EARLY_WINDOW)
    early_count = early_used

    for i, game in enumerate(games):
        if i in used_indices:
            continue
        if early_count < 10:
            result_map[i] = (game, EARLY_WINDOW)
            early_count += 1
        else:
            result_map[i] = (game, next(late_cycle))
        used_indices.add(i)


def assign_times(games, week, double_header_mnf=False, intl_game=None,
                 used_primetime_matchups=None, primetime_counts=None,
                 last_primetime_slot=None, bye_teams=None):
    """
    Assign kickoff times for a standard week.

    Args:
        games:                   list of game strings for this week
        week:                    week number (used for international slot label)
        double_header_mnf:       if True, schedule two MNF games
        intl_game:               game string that should get the international slot
        used_primetime_matchups: set of frozensets already used in primetime;
                                 no matchup (or its reverse) can appear twice
        primetime_counts:        dict mapping team name -> current primetime count
        last_primetime_slot:     dict mapping team name -> last slot label (TNF/SNF/MNF);
                                 used to avoid back-to-back same slot for a team
        bye_teams:               set of team names that had a bye in week-1;
                                 both teams in a TNF game should ideally come off a bye
                                 (short-week protection)
    """
    if used_primetime_matchups is None:
        used_primetime_matchups = set()
    if primetime_counts is None:
        primetime_counts = {}
    if last_primetime_slot is None:
        last_primetime_slot = {}
    if bye_teams is None:
        bye_teams = set()
    result_map = {}
    used = set()

    def matchup_key(g):
        parts = g.split(" @ ")
        return frozenset(parts) if len(parts) == 2 else frozenset([g])

    def is_fresh(g):
        return matchup_key(g) not in used_primetime_matchups

    def under_cap(g):
        """Return True if neither team in g has exceeded their per-team primetime target."""
        parts = g.split(" @ ")
        return all(
            primetime_counts.get(t.strip(), 0) < PRIMETIME_TARGETS.get(t.strip(), MAX_PRIMETIME_PER_TEAM)
            for t in parts
        )

    def slot_label(slot):
        """Normalise any MNF variant to 'MNF', TNF to 'TNF', SNF to 'SNF'."""
        if "Monday" in slot:   return "MNF"
        if "Thursday" in slot: return "TNF"
        if "Sunday" in slot or "Thanksgiving" in slot: return "SNF"
        return slot

    def no_repeat_slot(g, slot):
        """Return True if neither team had the same slot within the last 2 weeks."""
        label = slot_label(slot)
        parts = g.split(" @ ")
        return all(
            last_primetime_slot.get(t.strip(), (0, None))[1] != label
            or week - last_primetime_slot.get(t.strip(), (0, None))[0] > 2
            for t in parts
        )

    def primetime_ok(g, slot):
        return is_fresh(g) and under_cap(g) and no_repeat_slot(g, slot)

    # -- International game (if any) --
    if intl_game and intl_game in games:
        idx = games.index(intl_game)
        result_map[idx] = (intl_game, INTERNATIONAL_SLOTS[week])
        used.add(idx)
        # Register immediately so later weeks can't pick the same matchup again
        used_primetime_matchups.add(matchup_key(intl_game))

    # -- TNF: short-week protection + quality filter --
    # Prefer games where both teams had a bye the previous week (most rest).
    # Fall back progressively: one bye team, then standard filters, then any game.
    def both_had_bye(g):
        parts = g.split(" @ ")
        return all(t.strip() in bye_teams for t in parts)

    def one_had_bye(g):
        parts = g.split(" @ ")
        return any(t.strip() in bye_teams for t in parts)

    tnf_idx = None
    for filter_fn, extra_filter in [
        (both_had_bye,  lambda g: primetime_ok(g, TNF_SLOT)),
        (one_had_bye,   lambda g: primetime_ok(g, TNF_SLOT)),
        (lambda g: True, lambda g: primetime_ok(g, TNF_SLOT)),
        (both_had_bye,  lambda g: is_fresh(g) and under_cap(g)),
        (one_had_bye,   lambda g: is_fresh(g) and under_cap(g)),
        (lambda g: True, lambda g: is_fresh(g) and under_cap(g)),
        (lambda g: True, lambda g: is_fresh(g)),
        (lambda g: True, lambda g: True),
    ]:
        candidates = [(tnf_score(games[j]), j)
                      for j in range(len(games)) if j not in used
                      and filter_fn(games[j]) and extra_filter(games[j])]
        if candidates:
            candidates.sort(key=lambda t: -t[0])
            tnf_idx = candidates[0][1]
            break
    result_map[tnf_idx] = (games[tnf_idx], TNF_SLOT)
    used.add(tnf_idx)

    # -- MNF: prefer fresh, under cap, no back-to-back same slot --
    if double_header_mnf:
        mnf_candidates = [(primetime_score(games[j]), j)
                          for j in range(len(games)) if j not in used
                          and primetime_ok(games[j], MNF_SLOT)]
        if len(mnf_candidates) < 2:  # relax no-repeat
            mnf_candidates = [(primetime_score(games[j]), j)
                              for j in range(len(games)) if j not in used
                              and is_fresh(games[j]) and under_cap(games[j])]
        if len(mnf_candidates) < 2:  # relax cap
            mnf_candidates = [(primetime_score(games[j]), j)
                              for j in range(len(games)) if j not in used
                              and is_fresh(games[j])]
        if len(mnf_candidates) < 2:  # total fallback
            mnf_candidates = [(primetime_score(games[j]), j)
                              for j in range(len(games)) if j not in used]
        mnf_candidates.sort(key=lambda t: -t[0])
        m1_idx = mnf_candidates[0][1]
        m2_idx = mnf_candidates[1][1]
        result_map[m1_idx] = (games[m1_idx], MNF_SLOT_EARLY)
        result_map[m2_idx] = (games[m2_idx], MNF_SLOT_2)
        used.add(m1_idx)
        used.add(m2_idx)
    else:
        mnf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used
                     and primetime_ok(games[j], MNF_SLOT)]
        if not mnf_cands:  # relax no-repeat
            mnf_cands = [(primetime_score(games[j]), j)
                         for j in range(len(games)) if j not in used
                         and is_fresh(games[j]) and under_cap(games[j])]
        if not mnf_cands:  # relax cap
            mnf_cands = [(primetime_score(games[j]), j)
                         for j in range(len(games)) if j not in used
                         and is_fresh(games[j])]
        if not mnf_cands:  # total fallback
            mnf_cands = [(primetime_score(games[j]), j)
                         for j in range(len(games)) if j not in used]
        mnf_cands.sort(key=lambda t: -t[0])
        best_mnf = mnf_cands[0][1]
        result_map[best_mnf] = (games[best_mnf], MNF_SLOT)
        used.add(best_mnf)

    # -- SNF: always the best matchup (highest primetime_score) that passes filters --
    # Try progressively relaxed filters, always sorting by raw primetime_score.
    snf_candidates = [(primetime_score(games[j]), j)
                      for j in range(len(games)) if j not in used
                      and is_primetime_eligible(games[j])
                      and primetime_ok(games[j], SNF_SLOT)]
    if not snf_candidates:  # relax no-repeat
        snf_candidates = [(primetime_score(games[j]), j)
                          for j in range(len(games)) if j not in used
                          and is_primetime_eligible(games[j])
                          and is_fresh(games[j]) and under_cap(games[j])]
    if not snf_candidates:  # relax eligibility
        snf_candidates = [(primetime_score(games[j]), j)
                          for j in range(len(games)) if j not in used
                          and primetime_ok(games[j], SNF_SLOT)]
    if not snf_candidates:  # relax everything — pure best score
        snf_candidates = [(primetime_score(games[j]), j)
                          for j in range(len(games)) if j not in used]
    snf_candidates.sort(key=lambda t: -t[0])
    snf_idx = snf_candidates[0][1]
    result_map[snf_idx] = (games[snf_idx], SNF_SLOT)
    used.add(snf_idx)

    # -- Fill remaining Sunday slots --
    _fill_sunday_slots(games, used, result_map)

    ordered = [result_map[i] for i in range(len(games))]
    result = _snf_mnf_tail(ordered)

    # Register primetime matchups as used (freshness tracking only)
    # Per-team counts are registered centrally in write_schedule.
    # Includes international slots so the same matchup can't appear twice in primetime.
    for game, slot in result:
        if any(s in slot for s in ("Night Football", "Kickoff Game")) or slot in INTERNATIONAL_SLOTS.values():
            used_primetime_matchups.add(matchup_key(game))

    return result


def assign_times_week1(games, primetime_counts=None, last_primetime_slot=None):
    """Week 1: Thursday Kickoff + International + SNF + MNF + Sunday."""
    if primetime_counts is None:
        primetime_counts = {}
    if last_primetime_slot is None:
        last_primetime_slot = {}

    def under_cap(g):
        parts = g.split(" @ ")
        return all(
            primetime_counts.get(t.strip(), 0) < PRIMETIME_TARGETS.get(t.strip(), MAX_PRIMETIME_PER_TEAM)
            for t in parts
        )

    def no_repeat_slot(g, slot):
        label = "MNF" if "Monday" in slot else ("TNF" if "Thursday" in slot else "SNF")
        parts = g.split(" @ ")
        return all(
            last_primetime_slot.get(t.strip(), (0, None))[1] != label
            or 1 - last_primetime_slot.get(t.strip(), (0, None))[0] > 2
            for t in parts
        )

    result_map = {}
    used = set()

    for (away, home), (wk, slot) in PINNED_GAMES.items():
        game_str = f"{away} @ {home}"
        if wk == 1 and game_str in games:
            idx = games.index(game_str)
            result_map[idx] = (game_str, slot)
            used.add(idx)

    # MNF — prefer under-cap, no back-to-back same slot
    mnf_cands = [(primetime_score(games[j]), j)
                 for j in range(len(games)) if j not in used
                 and under_cap(games[j]) and no_repeat_slot(games[j], MNF_SLOT)]
    if not mnf_cands:
        mnf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used and under_cap(games[j])]
    if not mnf_cands:
        mnf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used]
    mnf_cands.sort(key=lambda t: -t[0])
    mnf_idx = mnf_cands[0][1]
    result_map[mnf_idx] = (games[mnf_idx], MNF_SLOT)
    used.add(mnf_idx)

    # SNF — best matchup: sort by primetime_score, prefer under-cap + no-repeat
    snf_cands = [(primetime_score(games[j]), j)
                 for j in range(len(games)) if j not in used
                 and under_cap(games[j]) and no_repeat_slot(games[j], SNF_SLOT)]
    if not snf_cands:
        snf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used and under_cap(games[j])]
    if not snf_cands:
        snf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used]
    snf_cands.sort(key=lambda t: -t[0])
    snf_idx = snf_cands[0][1]
    result_map[snf_idx] = (games[snf_idx], SNF_SLOT)
    used.add(snf_idx)

    _fill_sunday_slots(games, used, result_map)

    ordered = [result_map[i] for i in range(len(games))]
    kickoff = [r for r in ordered if r[1] == KICKOFF_SLOT]
    intl    = [r for r in ordered if r[1] == INTERNATIONAL_SLOTS[1]]
    snf     = [r for r in ordered if r[1] == SNF_SLOT]
    mnf     = [r for r in ordered if "Monday Night Football" in r[1]]
    rest    = [r for r in ordered if r not in kickoff + intl + snf + mnf]
    return kickoff + intl + rest + snf + mnf


def assign_times_thanksgiving(games, primetime_counts=None, last_primetime_slot=None):
    """Week 12 Thanksgiving.
    The three Thanksgiving slots go to the Lions home game, Cowboys home game,
    and the best remaining game — but sorted by primetime score so the best
    of those three gets the prime 8:20 PM slot, not necessarily Lions/Cowboys.
    """
    if primetime_counts is None:
        primetime_counts = {}
    if last_primetime_slot is None:
        last_primetime_slot = {}

    def under_cap(g):
        parts = g.split(" @ ")
        return all(
            primetime_counts.get(t.strip(), 0) < PRIMETIME_TARGETS.get(t.strip(), MAX_PRIMETIME_PER_TEAM)
            for t in parts
        )

    def no_repeat_slot(g, slot):
        label = "MNF" if "Monday" in slot else ("TNF" if "Thursday" in slot else "SNF")
        parts = g.split(" @ ")
        return all(
            last_primetime_slot.get(t.strip(), (0, None))[1] != label
            or 12 - last_primetime_slot.get(t.strip(), (0, None))[0] > 2
            for t in parts
        )

    result_map = {}
    used = set()
    tg_candidates = []

    # Lions home game
    for i, g in enumerate(games):
        if "Lions" in g and not g.startswith("Lions"):
            tg_candidates.append((primetime_score(g), i, THANKSGIVING_EARLY))
            break

    # Cowboys home game
    for i, g in enumerate(games):
        if "Cowboys" in g and not g.startswith("Cowboys"):
            tg_candidates.append((primetime_score(g), i, THANKSGIVING_MID))
            break

    # Sort the two host games by score — best host game gets the night slot
    tg_candidates.sort(key=lambda t: -t[0])
    slot_order = [THANKSGIVING_NIGHT, THANKSGIVING_MID, THANKSGIVING_EARLY]
    for rank, (score, idx, _orig_slot) in enumerate(tg_candidates[:2]):
        result_map[idx] = (games[idx], slot_order[rank])
        used.add(idx)

    # 3rd Thanksgiving game — best remaining non-host game
    night_cands = [(primetime_score(games[j]), j)
                   for j in range(len(games)) if j not in used]
    night_cands.sort(key=lambda t: -t[0])
    night_idx = night_cands[0][1]
    # Give it whichever Thanksgiving slot is left
    remaining_slot = slot_order[2]  # earliest remaining
    result_map[night_idx] = (games[night_idx], remaining_slot)
    used.add(night_idx)

    # MNF — prefer under-cap, no back-to-back same slot
    mnf_cands = [(primetime_score(games[j]), j)
                 for j in range(len(games)) if j not in used
                 and under_cap(games[j]) and no_repeat_slot(games[j], MNF_SLOT)]
    if not mnf_cands:
        mnf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used and under_cap(games[j])]
    if not mnf_cands:
        mnf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used]
    mnf_cands.sort(key=lambda t: -t[0])
    mnf_idx = mnf_cands[0][1]
    result_map[mnf_idx] = (games[mnf_idx], MNF_SLOT)
    used.add(mnf_idx)

    # SNF — best matchup: sort by primetime_score, prefer under-cap + no-repeat
    snf_cands = [(primetime_score(games[j]), j)
                 for j in range(len(games)) if j not in used
                 and under_cap(games[j]) and no_repeat_slot(games[j], SNF_SLOT)]
    if not snf_cands:
        snf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used and under_cap(games[j])]
    if not snf_cands:
        snf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used]
    snf_cands.sort(key=lambda t: -t[0])
    snf_idx = snf_cands[0][1]
    result_map[snf_idx] = (games[snf_idx], SNF_SLOT)
    used.add(snf_idx)

    _fill_sunday_slots(games, used, result_map)

    ordered = [result_map[i] for i in range(len(games))]
    tg_slots = (THANKSGIVING_EARLY, THANKSGIVING_MID, THANKSGIVING_NIGHT)
    tg      = sorted([r for r in ordered if r[1] in tg_slots],
                     key=lambda r: tg_slots.index(r[1]))
    snf_e   = [r for r in ordered if r[1] == SNF_SLOT]
    mnf_e   = [r for r in ordered if "Monday Night Football" in r[1]]
    rest    = [r for r in ordered if r[1] not in tg_slots + (SNF_SLOT,)
               and "Monday Night Football" not in r[1]]
    return tg + rest + snf_e + mnf_e


def assign_times_flex(games, primetime_counts=None):
    """Weeks 17 & 18: all flex, sorted by score, respecting primetime cap."""
    if primetime_counts is None:
        primetime_counts = {}

    def under_cap(g):
        parts = g.split(" @ ")
        return all(
            primetime_counts.get(t.strip(), 0) < PRIMETIME_TARGETS.get(t.strip(), MAX_PRIMETIME_PER_TEAM)
            for t in parts
        )

    # Sort all games by score; under-cap games float to the top
    scored = sorted(games, key=lambda g: (-under_cap(g), -primetime_score(g)))
    return [(g, FLEX_SLOT) for g in scored]


def assign_times_christmas(games, primetime_counts=None, last_primetime_slot=None):
    """Week 16 Christmas: two Christmas games + TNF + SNF + MNF + Sunday."""
    if primetime_counts is None:
        primetime_counts = {}
    if last_primetime_slot is None:
        last_primetime_slot = {}

    def under_cap(g):
        parts = g.split(" @ ")
        return all(
            primetime_counts.get(t.strip(), 0) < PRIMETIME_TARGETS.get(t.strip(), MAX_PRIMETIME_PER_TEAM)
            for t in parts
        )

    def no_repeat_slot(g, slot):
        label = "MNF" if "Monday" in slot else ("TNF" if "Thursday" in slot else "SNF")
        parts = g.split(" @ ")
        return all(
            last_primetime_slot.get(t.strip(), (0, None))[1] != label
            or CHRISTMAS_WEEK - last_primetime_slot.get(t.strip(), (0, None))[0] > 2
            for t in parts
        )

    result_map = {}
    used = set()

    # Christmas Afternoon game — 2nd best eligible matchup
    xmas_cands = [(primetime_score(games[j]), j)
                  for j in range(len(games)) if j not in used
                  and is_primetime_eligible(games[j]) and under_cap(games[j])]
    if not xmas_cands:
        xmas_cands = [(primetime_score(games[j]), j)
                      for j in range(len(games)) if j not in used]
    xmas_cands.sort(key=lambda t: -t[0])
    xmas_idx  = xmas_cands[0][1]   # best game → night
    xmas2_idx = xmas_cands[1][1] if len(xmas_cands) > 1 else xmas_cands[0][1]  # 2nd → afternoon
    result_map[xmas_idx]  = (games[xmas_idx],  CHRISTMAS_SLOT)
    result_map[xmas2_idx] = (games[xmas2_idx], CHRISTMAS_SLOT_2)
    used.add(xmas_idx)
    used.add(xmas2_idx)

    # TNF
    tnf_cands = [(tnf_score(games[j]), j)
                 for j in range(len(games)) if j not in used
                 and is_primetime_eligible(games[j]) and under_cap(games[j])]
    if not tnf_cands:
        tnf_cands = [(tnf_score(games[j]), j)
                     for j in range(len(games)) if j not in used]
    tnf_cands.sort(key=lambda t: -t[0])
    tnf_idx = tnf_cands[0][1]
    result_map[tnf_idx] = (games[tnf_idx], TNF_SLOT)
    used.add(tnf_idx)

    # MNF
    mnf_cands = [(primetime_score(games[j]), j)
                 for j in range(len(games)) if j not in used
                 and under_cap(games[j]) and no_repeat_slot(games[j], MNF_SLOT)]
    if not mnf_cands:
        mnf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used]
    mnf_cands.sort(key=lambda t: -t[0])
    mnf_idx = mnf_cands[0][1]
    result_map[mnf_idx] = (games[mnf_idx], MNF_SLOT)
    used.add(mnf_idx)

    # SNF
    snf_cands = [(primetime_score(games[j]), j)
                 for j in range(len(games)) if j not in used
                 and is_primetime_eligible(games[j]) and under_cap(games[j])]
    if not snf_cands:
        snf_cands = [(primetime_score(games[j]), j)
                     for j in range(len(games)) if j not in used]
    snf_cands.sort(key=lambda t: -t[0])
    snf_idx = snf_cands[0][1]
    result_map[snf_idx] = (games[snf_idx], SNF_SLOT)
    used.add(snf_idx)

    _fill_sunday_slots(games, used, result_map)

    ordered = [result_map[i] for i in range(len(games))]
    xmas_e  = [r for r in ordered if r[1] == CHRISTMAS_SLOT_2]
    xmas_n  = [r for r in ordered if r[1] == CHRISTMAS_SLOT]
    snf_e   = [r for r in ordered if r[1] == SNF_SLOT]
    mnf_e   = [r for r in ordered if "Monday Night Football" in r[1]]
    rest    = [r for r in ordered if r[1] not in (CHRISTMAS_SLOT, CHRISTMAS_SLOT_2, SNF_SLOT)
               and "Monday Night Football" not in r[1]]
    return xmas_e + xmas_n + rest + snf_e + mnf_e

# ---------------------------------------------------------------------------
# Primetime consecutive-slot violation checker & fixer
# ---------------------------------------------------------------------------

def get_team_primetime_map(schedule_lines):
    """
    Returns {team: [(week, slot), ...]} from already-formatted schedule lines.
    slot is one of TNF / SNF / MNF.
    """
    team_map = defaultdict(list)
    current_week = 0
    for line in schedule_lines:
        stripped = line.strip()
        wm = re.match(r'^Week (\d+):', stripped)
        if wm:
            current_week = int(wm.group(1))
            continue
        slot = None
        if "Thursday Night Football" in line or "Thursday Kickoff Game" in line:
            slot = "TNF"
        elif "Sunday Night Football" in line or "Thanksgiving Night Football" in line:
            slot = "SNF"
        elif "Monday Night Football" in line:
            slot = "MNF"
        if slot:
            m = re.search(r'(\w+) @ (\w+)', line)
            if m:
                team_map[m.group(1)].append((current_week, slot))
                team_map[m.group(2)].append((current_week, slot))
    for team in team_map:
        team_map[team].sort()
    return team_map


def has_consecutive_slot_violation(team_map):
    for team, games in team_map.items():
        for i in range(len(games) - 1):
            if games[i][1] == games[i + 1][1] and games[i + 1][0] - games[i][0] <= 2:
                return True
    return False


def has_consecutive_double_mnf(schedule_lines):
    """Return (found, pairs) where pairs is a list of (w1, w2, w3) triple-consecutive double-header MNF weeks.
    Two consecutive double-header weeks are allowed; three or more in a row are not.
    """
    mnf_counts = defaultdict(int)
    current_week = 0
    for line in schedule_lines:
        wm = re.match(r'^\s*Week (\d+):', line.strip())
        if wm:
            current_week = int(wm.group(1))
        elif "Monday Night Football" in line:
            mnf_counts[current_week] += 1
    double_weeks = sorted(w for w, c in mnf_counts.items() if c >= 2)
    triples = []
    for i in range(len(double_weeks) - 2):
        if (double_weeks[i + 1] - double_weeks[i] == 1 and
                double_weeks[i + 2] - double_weeks[i + 1] == 1):
            triples.append((double_weeks[i], double_weeks[i + 1], double_weeks[i + 2]))
    return bool(triples), triples

# ---------------------------------------------------------------------------
# Schedule writer
# ---------------------------------------------------------------------------

def write_schedule(schedule, byes, output_file=None, seed=None):
    """
    Assign times to each week and optionally write to output_file.
    Returns (lines, n_violations) where n_violations is the total count of
    consecutive same-slot primetime violations + duplicate primetime matchups.
    Pass seed for reproducibility; None = random shuffle each call.
    """
    rng = random.Random(seed)
    lines = []
    lines.append("2026 NFL Schedule with Kickoff Times:\n\n")

    used_primetime_matchups = set()  # track matchups already used in any primetime slot
    primetime_counts: dict = {}       # track per-team primetime appearances
    last_primetime_slot: dict = {}    # track last slot (TNF/SNF/MNF) per team

    for week in sorted(schedule.keys()):
        games_raw = list(schedule[week])
        rng.shuffle(games_raw)          # shuffle so different games compete each attempt
        games = [f"{g[1]} @ {g[0]}" for g in games_raw]

        lines.append(f"Week {week}:\n")

        double_mnf = week in DOUBLE_HEADER_MNF_WEEKS
        intl_game  = None

        if week in INTL_WEEKS:
            # Find the game where the required home team is playing at home
            home_team = INTERNATIONAL_HOME[week]
            for g_str in games:
                # g_str is "Away @ Home"
                parts = g_str.split(" @ ")
                if len(parts) == 2 and parts[1].strip() == home_team:
                    intl_game = g_str
                    break
            # Fallback: if no home game found (team is away that week), pick lowest score
            if intl_game is None:
                pinned_strs = {f"{a} @ {h}" for (a, h) in PINNED_GAMES
                               if PINNED_GAMES[(a, h)][0] == week}
                candidates = sorted(games, key=lambda g: primetime_score(g))
                for g in candidates:
                    if g not in pinned_strs:
                        intl_game = g
                        break

        if week == 1:
            timed = assign_times_week1(games, primetime_counts=primetime_counts,
                                       last_primetime_slot=last_primetime_slot)
        elif week == 12:
            timed = assign_times_thanksgiving(games, primetime_counts=primetime_counts,
                                              last_primetime_slot=last_primetime_slot)
        elif week == CHRISTMAS_WEEK:
            timed = assign_times_christmas(games, primetime_counts=primetime_counts,
                                           last_primetime_slot=last_primetime_slot)
        elif week in (17, 18):
            timed = assign_times_flex(games, primetime_counts=primetime_counts)
        else:
            timed = assign_times(games, week,
                                 double_header_mnf=double_mnf,
                                 intl_game=intl_game,
                                 used_primetime_matchups=used_primetime_matchups,
                                 primetime_counts=primetime_counts,
                                 last_primetime_slot=last_primetime_slot,
                                 bye_teams=set(byes.get(week - 1, [])))

        # Register primetime picks from ALL weeks (including special weeks)
        for game, slot in timed:
            if any(s in slot for s in ("Night Football", "Kickoff Game", "Thanksgiving", "Christmas")):
                label = "MNF" if "Monday" in slot else ("TNF" if "Thursday" in slot else "SNF")
                for team in game.split(" @ "):
                    team = team.strip()
                    primetime_counts[team] = primetime_counts.get(team, 0) + 1
                    last_primetime_slot[team] = (week, label)

        for game, slot in timed:
            lines.append(f"  {game:<35}  {slot}\n")

        bye_teams = byes.get(week, [])
        if bye_teams:
            lines.append(f"  Bye: {', '.join(bye_teams)}\n")

        lines.append("\n")

    # Validate: no duplicate primetime matchups across the season
    primetime_matchups_seen = {}
    duplicate_matchup_violations = []
    current_week = 0
    for line in lines:
        wm = re.match(r'^\s*Week (\d+):', line.strip())
        if wm:
            current_week = int(wm.group(1))
        elif any(s in line for s in ("Night Football", "Kickoff Game", "Christmas")):
            m = re.search(r'(\w+) @ (\w+)', line)
            if m:
                key = frozenset([m.group(1), m.group(2)])
                if key in primetime_matchups_seen:
                    duplicate_matchup_violations.append(
                        f"  {m.group(1)} vs {m.group(2)}: W{primetime_matchups_seen[key]} and W{current_week}"
                    )
                else:
                    primetime_matchups_seen[key] = current_week
    if duplicate_matchup_violations:
        print(f"WARNING: {len(duplicate_matchup_violations)} duplicate primetime matchup(s):")
        for v in duplicate_matchup_violations:
            print(v)
    else:
        print("✓ No duplicate primetime matchups.")

    # Validate: no 3+ consecutive double-header MNF weeks
    consecutive, triples = has_consecutive_double_mnf(lines)
    if consecutive:
        for w1, w2, w3 in triples:
            print(f"WARNING: 3 consecutive double-header MNF weeks: W{w1}, W{w2}, W{w3}")

    # Validate: no team has same primetime slot in back-to-back or within-2-week window
    team_map = get_team_primetime_map(lines)
    slot_viol = []
    for team, tgames in team_map.items():
        for i in range(len(tgames) - 1):
            if tgames[i][1] == tgames[i + 1][1] and tgames[i + 1][0] - tgames[i][0] <= 2:
                slot_viol.append(
                    f"  {team}: {tgames[i][1]} W{tgames[i][0]} -> W{tgames[i+1][0]}"
                )

    # Validate: per-team primetime floor requirements
    floor_violations = []
    for team, floor in MIN_PRIMETIME_FLOORS.items():
        actual = primetime_counts.get(team, 0)
        if actual < floor:
            floor_violations.append(
                f"  {team}: needs >= {floor} primetime appearances, got {actual}"
            )

    n_violations = len(duplicate_matchup_violations) + len(slot_viol) + len(floor_violations)
    return lines, n_violations

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    games_file    = "data/games.txt"
    previous_file = "data/previous_schedule.txt"
    output_file   = "data/schedule_with_times.txt"

    print("Loading games...")
    all_games, divisional_games = parse_games(games_file)
    print(f"  {len(all_games)} total games loaded.")

    print("Loading previous schedule...")
    previous_schedule = parse_previous_schedule(previous_file)

    print("Running ILP scheduler...")
    schedule = generate_schedule(all_games, divisional_games, previous_schedule)

    print("Computing byes...")
    byes = compute_byes(schedule)

    print("Assigning kickoff times...")
    MAX_TIME_ATTEMPTS = 500
    best_lines: list = []
    best_violations = float("inf")
    for t_attempt in range(1, MAX_TIME_ATTEMPTS + 1):
        lines, n_violations = write_schedule(schedule, byes)
        if n_violations < best_violations:
            best_violations = n_violations
            best_lines = lines
        if n_violations == 0:
            print(f"  Clean schedule found on attempt {t_attempt}.")
            break
        if t_attempt % 25 == 0:
            print(f"  Attempt {t_attempt}: best so far has {best_violations} violation(s)...")
    else:
        print(f"  Could not eliminate all violations after {MAX_TIME_ATTEMPTS} attempts."
              f" Writing best result ({best_violations} violation(s)).")

    # Print final validation stats and write the best result to disk
    team_map = get_team_primetime_map(best_lines)
    slot_violations = []
    for team, tgames in team_map.items():
        for i in range(len(tgames) - 1):
            if tgames[i][1] == tgames[i + 1][1] and tgames[i + 1][0] - tgames[i][0] <= 2:
                slot_violations.append(
                    f"  {team}: {tgames[i][1]} W{tgames[i][0]} -> W{tgames[i+1][0]}"
                )
    if slot_violations:
        print(f"WARNING: {len(slot_violations)} consecutive same-slot primetime violations:")
        for v in slot_violations:
            print(v)
    else:
        print("\u2713 No consecutive same-slot primetime violations.")

    # Re-tally primetime counts from best_lines for floor check
    best_primetime_counts: dict = {}
    for line in best_lines:
        if any(s in line for s in ("Night Football", "Kickoff Game", "Thanksgiving", "Christmas")):
            m = re.search(r'(\w+) @ (\w+)', line)
            if m:
                for team in (m.group(1), m.group(2)):
                    best_primetime_counts[team] = best_primetime_counts.get(team, 0) + 1
    floor_violations = []
    for team, floor in MIN_PRIMETIME_FLOORS.items():
        actual = best_primetime_counts.get(team, 0)
        if actual < floor:
            floor_violations.append(f"  {team}: needs >= {floor}, got {actual}")
    if floor_violations:
        print(f"WARNING: {len(floor_violations)} primetime floor violation(s):")
        for v in floor_violations:
            print(v)
    else:
        print("\u2713 All primetime floor requirements met.")

    with open(output_file, "w") as f:
        f.writelines(best_lines)
    print(f"Schedule written to '{output_file}'.")


if __name__ == "__main__":
    main()
