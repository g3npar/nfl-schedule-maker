import re
import random
import json
import os
import pulp
from itertools import cycle
from collections import defaultdict

EARLY_WINDOW       = "1:00 PM ET"
LATE_WINDOW_1      = "4:05 PM ET"
LATE_WINDOW_2      = "4:25 PM ET"
KICKOFF_SLOT       = "8:20 PM ET (Wednesday Kickoff Game)"
FLEX_SLOT          = "TBD (Flex Scheduling - Nighttime)"
SUNDAY_NIGHT       = "8:20 PM ET (Sunday Night Football)"
MONDAY_NIGHT       = "8:15 PM ET (Monday Night Football)"
THURSDAY_NIGHT     = "8:15 PM ET (Thursday Night Football)"
THANKSGIVING_EVE   = "8:00 PM ET (Thanksgiving Eve)"
THANKSGIVING_EARLY = "12:30 PM ET (Thanksgiving)"
THANKSGIVING_MID   = "4:30 PM ET (Thanksgiving)"
THANKSGIVING_NIGHT = "8:20 PM ET (Thanksgiving Night Football)"
BLACK_FRIDAY       = "3:00 PM ET (Black Friday)"
CHRISTMAS_SLOT     = "8:20 PM ET (Christmas Night Football)"
CHRISTMAS_SLOT_2   = "4:30 PM ET (Christmas Afternoon Football)"
CHRISTMAS_SLOT_3   = "1:00 PM ET (Christmas Day Football)"
CHRISTMAS_WEEK     = 16

# International game slots by week (week -> label) — confirmed games only
INTERNATIONAL_SLOTS = {
  1:  "8:35 PM ET (Melbourne, Australia)",
  3:  "4:25 PM ET (Rio de Janeiro, Brazil)",
  4:  "9:30 AM ET (London, England)",
  5:  "9:30 AM ET (London, England)",
  6:  "9:30 AM ET (London, England)",
  7:  "9:30 AM ET (Paris, France)",
  9:  "9:30 PM ET (Madrid, Spain)",
  10: "9:30 AM ET (Munich, Germany)",
  11: "8:15 PM ET (Sunday Night Football - Mexico City, Mexico)",
}

INTL_WEEKS = set(INTERNATIONAL_SLOTS.keys())

# Load confirmed (pinned) games from data/confirmed_games.json
_CG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "confirmed_games.json")

def _load_pinned():
    if not os.path.exists(_CG_PATH):
        return {}
    with open(_CG_PATH, encoding="utf-8") as _f:
        _games = json.load(_f)
    return {(g["away"], g["home"]): (g["week"], g["slot"]) for g in _games}

PINNED_GAMES = _load_pinned()

# Derive INTERNATIONAL_HOME from PINNED_GAMES (home team for each intl week)
INTERNATIONAL_HOME = {
    week: home
    for (away, home), (week, slot) in PINNED_GAMES.items()
    if week in INTL_WEEKS
}

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

def generate_schedule(all_games, divisional_games, previous_schedule, weeks=18):
    """Assign each game to a week using ILP."""
    prob = pulp.LpProblem("NFL_Schedule", pulp.LpMinimize)

    x = pulp.LpVariable.dicts(
        "GW",
        ((g, w) for g in all_games for w in range(1, weeks + 1)),
        cat="Binary"
    )

    teams = set(t for g in all_games for t in g)

    for g in all_games:
        prob += pulp.lpSum(x[g, w] for w in range(1, weeks + 1)) == 1

    for t in teams:
        for w in range(1, weeks + 1):
            prob += pulp.lpSum(x[g, w] for g in all_games if t in g) <= 1

    for w in list(range(1, 5)) + list(range(15, 19)):
        prob += pulp.lpSum(x[g, w] for g in all_games) == 16

    for w in range(1, weeks + 1):
        prob += pulp.lpSum(x[g, w] for g in all_games) >= 13

    # Week 18: divisional games only
    div_set = set()
    for home, opponents in divisional_games.items():
        for away in opponents:
            div_set.add((home, away))
            div_set.add((away, home))
    for g in all_games:
        if g not in div_set:
            prob += x[g, 18] == 0

    for host in THANKSGIVING_HOSTS:
        prob += pulp.lpSum(x[g, 12] for g in all_games if g[0] == host) == 1

    # Build set of (week, home_team) pairs that are already in PINNED_GAMES
    pinned_international = {(wk, home) for (away, home), (wk, _slot) in PINNED_GAMES.items() if wk in INTL_WEEKS}
    
    for week, home_team in INTERNATIONAL_HOME.items():
        if (week, home_team) in pinned_international:  # already handled by PINNED_GAMES
            continue
        prob += pulp.lpSum(x[g, week] for g in all_games if g[0] == home_team) >= 1

    for (away, home), (week, _slot) in PINNED_GAMES.items():
        g = (home, away)
        if g in all_games:
            prob += x[g, week] == 1

    # Jets and Bills both have away games in Week 1 (confirmed)
    for team in ["Jets", "Bills"]:
        prob += pulp.lpSum(x[g, 1] for g in all_games if g[1] == team) == 1
    
    # Bucs have an away game in Week 1 (confirmed)
    prob += pulp.lpSum(x[g, 1] for g in all_games if g[1] == "Buccaneers") == 1
    
    # Cowboys have a home game in Week 2 (confirmed)
    prob += pulp.lpSum(x[g, 2] for g in all_games if g[0] == "Cowboys") >= 1

    # Specific bye week assignments (confirmed)
    bye_assignments = {
        "Commanders": 5,
        "Jaguars": 7,
        "Saints": 8,
        "Falcons": 10,
        "Packers": 11,
        "Rams": 11,
        "49ers": 12,
    }
    for team, bye_week in bye_assignments.items():
        # Team must not play in their bye week
        prob += pulp.lpSum(x[g, bye_week] for g in all_games if team in g) == 0

    # Bye week constraints (weeks 5–14 only — weeks 1–4 and 15–18 are full):
    #   • No week has more than 6 teams on bye  (games >= 13)
    #   • At most ONE week has exactly 6 teams on bye
    #     (all other bye weeks have <= 4 teams on bye, i.e. games >= 14)
    # Introduce binary indicator: has6[w] = 1 iff exactly 6 teams on bye in week w
    has6 = pulp.LpVariable.dicts("Has6Bye", range(5, 15), cat="Binary")
    for w in range(5, 15):
        games_in_week = pulp.lpSum(x[g, w] for g in all_games)
        # Hard cap: never more than 6 on bye  => games >= 13
        prob += games_in_week >= 13
        # has6[w] = 1  =>  games_in_week <= 13  (6 on bye)
        # has6[w] = 0  =>  games_in_week >= 14  (<=4 on bye)
        # Encode via big-M (M=3 is enough since range is 13–16):
        prob += games_in_week >= 14 - has6[w]          # if has6=0 → games >= 14
        prob += games_in_week <= 13 + 3 * (1 - has6[w])  # if has6=1 → games <= 13 (tight); else relaxed
    # At most one week with 6-team bye
    prob += pulp.lpSum(has6[w] for w in range(5, 15)) <= 1

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

    # Build set of (game, week) pairs that are pinned — exempt from previous-schedule ban
    pinned_set = {((home, away), week) for (away, home), (week, _) in PINNED_GAMES.items()}

    for w, games in previous_schedule.items():
        if w == 18:
            continue
        for g in games:
            if g in all_games and (g, w) not in pinned_set:
                prob += x[g, w] == 0
            rev = (g[1], g[0])
            if rev in all_games and (rev, w) not in pinned_set:
                prob += x[rev, w] == 0

    for g in all_games:
        rev = (g[1], g[0])
        if rev in all_games:
            for w in range(1, weeks):
                prob += x[g, w] + x[rev, w + 1] <= 1

    prob += 0  # no objective — find any feasible solution

    solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=300, threads=4)
    status = prob.solve(solver)
    print(f"Solver status: {pulp.LpStatus[prob.status]}")

    if pulp.LpStatus[prob.status] not in ("Optimal", "Not Solved"):
        print(f"No feasible solution found (status: {pulp.LpStatus[prob.status]}).")
        return defaultdict(list)

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

def compute_byes(schedule, weeks=18):
    byes = {}
    for w in range(1, weeks + 1):
        playing = set(t for g in schedule.get(w, []) for t in g)
        on_bye = sorted(set(ALL_TEAMS) - playing)
        # Only weeks where teams genuinely have a bye (not full 16-game weeks)
        byes[w] = on_bye if on_bye else []
    return byes

def _snf_mnf_tail(result, snf_slot=None):
    return result


def _fill_sunday_slots(games, used_indices, result_map):
    # Apply FIXED_SLOT_GAMES overrides before normal filling.
    # (FIXED_SLOT_GAMES removed - all fixed slots now handled by PINNED_GAMES)

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


def assign_times(games, week, intl_game=None, **_kwargs):
    """Assign kickoff times for a standard week."""
    result_map = {}
    used = set()

    # Check for any pinned games in this week (TNF, international, etc.)
    for (away, home), (wk, slot) in PINNED_GAMES.items():
        if wk == week:
            game_str = f"{away} @ {home}"
            if game_str in games:
                idx = games.index(game_str)
                result_map[idx] = (game_str, slot)
                used.add(idx)

    _fill_sunday_slots(games, used, result_map)
    return [result_map[i] for i in range(len(games))]


def assign_times_week1(games, **_kwargs):
    result_map = {}
    used = set()

    for (away, home), (wk, slot) in PINNED_GAMES.items():
        game_str = f"{away} @ {home}"
        if wk == 1 and game_str in games:
            idx = games.index(game_str)
            result_map[idx] = (game_str, slot)
            used.add(idx)

    _fill_sunday_slots(games, used, result_map)

    ordered = [result_map[i] for i in range(len(games))]
    kickoff = [r for r in ordered if r[1] == KICKOFF_SLOT]
    intl    = [r for r in ordered if r[1] == INTERNATIONAL_SLOTS[1]]
    rest    = [r for r in ordered if r not in kickoff + intl]
    return kickoff + intl + rest


def assign_times_thanksgiving(games, **_kwargs):
    result_map = {}
    used = set()

    for i, g in enumerate(games):
        if g.startswith("Bears @ Lions"):
            result_map[i] = (g, THANKSGIVING_EARLY)
            used.add(i)
            break
    if not used:
        for i, g in enumerate(games):
            if "Lions" in g and not g.startswith("Lions"):
                result_map[i] = (g, THANKSGIVING_EARLY)
                used.add(i)
                break

    for i, g in enumerate(games):
        if i not in used and "Cowboys" in g and not g.startswith("Cowboys"):
            result_map[i] = (g, THANKSGIVING_MID)
            used.add(i)
            break

    night_cands = [j for j in range(len(games)) if j not in used]
    night_idx = night_cands[0]
    result_map[night_idx] = (games[night_idx], THANKSGIVING_NIGHT)
    used.add(night_idx)

    _fill_sunday_slots(games, used, result_map)

    ordered = [result_map[i] for i in range(len(games))]
    tg_slots = (THANKSGIVING_EARLY, THANKSGIVING_MID, THANKSGIVING_NIGHT)
    tg   = sorted([r for r in ordered if r[1] in tg_slots], key=lambda r: tg_slots.index(r[1]))
    rest = [r for r in ordered if r[1] not in tg_slots]
    return tg + rest


def assign_times_flex(games, primetime_counts=None):
    if primetime_counts is None:
        primetime_counts = {}

    scored = sorted(games, key=lambda g: (-primetime_score(g)))
    return [(g, FLEX_SLOT) for g in scored]


def assign_times_christmas(games, **_kwargs):
    result_map = {}
    used = set()

    indices = list(range(len(games)))
    xmas_idx  = indices[0]
    xmas2_idx = indices[1] if len(indices) > 1 else indices[0]
    xmas3_idx = indices[2] if len(indices) > 2 else indices[0]
    result_map[xmas_idx]  = (games[xmas_idx],  CHRISTMAS_SLOT)
    result_map[xmas2_idx] = (games[xmas2_idx], CHRISTMAS_SLOT_2)
    result_map[xmas3_idx] = (games[xmas3_idx], CHRISTMAS_SLOT_3)
    used.update([xmas_idx, xmas2_idx, xmas3_idx])

    _fill_sunday_slots(games, used, result_map)

    ordered = [result_map[i] for i in range(len(games))]
    xmas_m  = [r for r in ordered if r[1] == CHRISTMAS_SLOT_3]
    xmas_e  = [r for r in ordered if r[1] == CHRISTMAS_SLOT_2]
    xmas_n  = [r for r in ordered if r[1] == CHRISTMAS_SLOT]
    rest    = [r for r in ordered if r[1] not in (CHRISTMAS_SLOT, CHRISTMAS_SLOT_2, CHRISTMAS_SLOT_3)]
    return xmas_m + xmas_e + xmas_n + rest

def get_team_primetime_map(schedule_lines):
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
    """Returns (found, triples) — three+ consecutive double-header MNF weeks are not allowed."""
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

def write_schedule(schedule, byes, output_file=None, seed=None):
    """Assign times to each week. Returns (lines, n_violations)."""
    rng = random.Random(seed)
    lines = []
    lines.append("2026 NFL Schedule with Kickoff Times:\n\n")

    for week in sorted(schedule.keys()):
        games_raw = list(schedule[week])
        rng.shuffle(games_raw)
        games = [f"{g[1]} @ {g[0]}" for g in games_raw]

        lines.append(f"Week {week}:\n")

        # Find the pinned intl game for this week if applicable
        intl_game = None
        if week in INTL_WEEKS:
            for (away, home), (wk, _slot) in PINNED_GAMES.items():
                if wk == week:
                    candidate = f"{away} @ {home}"
                    if candidate in games:
                        intl_game = candidate
                        break

        if week == 1:
            timed = assign_times_week1(games)
        elif week == 12:
            timed = assign_times_thanksgiving(games)
        elif week == CHRISTMAS_WEEK:
            timed = assign_times_christmas(games)
        elif week in (17, 18):
            timed = assign_times_flex(games)
        else:
            timed = assign_times(games, week, intl_game=intl_game)

        for game, slot in timed:
            lines.append(f"  {game:<35}  {slot}\n")

        bye_teams = byes.get(week, [])
        if bye_teams:
            lines.append(f"  Bye: {', '.join(bye_teams)}\n")

        lines.append("\n")

    return lines

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
    lines = write_schedule(schedule, byes)

    with open(output_file, "w") as f:
        f.writelines(lines)
    print(f"Schedule written to '{output_file}'.")


if __name__ == "__main__":
    main()
