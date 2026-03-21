import sys
import os
import re
from datetime import date, timedelta

SCHEDULE_FILE = "schedule_with_times.txt"

NFL_TEAMS = [
    "Bears", "Bengals", "Bills", "Broncos", "Browns", "Buccaneers",
    "Cardinals", "Chargers", "Chiefs", "Colts", "Cowboys", "Commanders",
    "Dolphins", "Eagles", "Falcons", "Giants", "Jaguars", "Jets",
    "Lions", "Packers", "Panthers", "Patriots", "Raiders", "Rams",
    "Ravens", "Saints", "Seahawks", "Steelers", "Texans", "Titans",
    "Vikings", "49ers",
]

# Primary and secondary colors for each NFL team
TEAM_COLORS = {
    "Bears":      {"primary": "#0B162A", "secondary": "#C83803"},
    "Bengals":    {"primary": "#FB4F14", "secondary": "#000000"},
    "Bills":      {"primary": "#00338D", "secondary": "#C60C30"},
    "Broncos":    {"primary": "#FB4F14", "secondary": "#002244"},
    "Browns":     {"primary": "#311D00", "secondary": "#FF3C00"},
    "Buccaneers": {"primary": "#D50A0A", "secondary": "#34302B"},
    "Cardinals":  {"primary": "#97233F", "secondary": "#000000"},
    "Chargers":   {"primary": "#0080C6", "secondary": "#FFC20E"},
    "Chiefs":     {"primary": "#E31837", "secondary": "#FFB81C"},
    "Colts":      {"primary": "#002C5F", "secondary": "#A2AAAD"},
    "Cowboys":    {"primary": "#003594", "secondary": "#869397"},
    "Commanders": {"primary": "#5A1414", "secondary": "#FFB612"},
    "Dolphins":   {"primary": "#008E97", "secondary": "#FC4C02"},
    "Eagles":     {"primary": "#004C54", "secondary": "#A5ACAF"},
    "Falcons":    {"primary": "#A71930", "secondary": "#000000"},
    "Giants":     {"primary": "#0B2265", "secondary": "#A71930"},
    "Jaguars":    {"primary": "#006778", "secondary": "#D7A22A"},
    "Jets":       {"primary": "#125740", "secondary": "#000000"},
    "Lions":      {"primary": "#0076B6", "secondary": "#B0B7BC"},
    "Packers":    {"primary": "#203731", "secondary": "#FFB612"},
    "Panthers":   {"primary": "#0085CA", "secondary": "#101820"},
    "Patriots":   {"primary": "#002244", "secondary": "#C60C30"},
    "Raiders":    {"primary": "#000000", "secondary": "#A5ACAF"},
    "Rams":       {"primary": "#003594", "secondary": "#FFA300"},
    "Ravens":     {"primary": "#241773", "secondary": "#9E7C0C"},
    "Saints":     {"primary": "#101820", "secondary": "#D3BC8D"},
    "Seahawks":   {"primary": "#002244", "secondary": "#69BE28"},
    "Steelers":   {"primary": "#101820", "secondary": "#FFB612"},
    "Texans":     {"primary": "#03202F", "secondary": "#A71930"},
    "Titans":     {"primary": "#0C2340", "secondary": "#4B92DB"},
    "Vikings":    {"primary": "#4F2683", "secondary": "#FFC62F"},
    "49ers":      {"primary": "#AA0000", "secondary": "#B3995D"},
}

# Sunday dates for each week of the 2026 NFL season
WEEK_SUNDAYS = {
    "Week 1":  date(2026, 9, 13),
    "Week 2":  date(2026, 9, 20),
    "Week 3":  date(2026, 9, 27),
    "Week 4":  date(2026, 10, 4),
    "Week 5":  date(2026, 10, 11),
    "Week 6":  date(2026, 10, 18),
    "Week 7":  date(2026, 10, 25),
    "Week 8":  date(2026, 11, 1),
    "Week 9":  date(2026, 11, 8),
    "Week 10": date(2026, 11, 15),
    "Week 11": date(2026, 11, 22),
    "Week 12": date(2026, 11, 29),   # Sunday after Thanksgiving (Thu Nov 26)
    "Week 13": date(2026, 12, 6),
    "Week 14": date(2026, 12, 13),
    "Week 15": date(2026, 12, 20),
    "Week 16": date(2026, 12, 27),
    "Week 17": date(2027, 1, 3),
    "Week 18": date(2027, 1, 10),
}

def get_game_date(week: str, time_str: str) -> str:
    """Return the correct calendar date for a game based on its type."""
    sunday = WEEK_SUNDAYS.get(week)
    if sunday is None:
        return "TBD"

    t = time_str.lower()

    # Special fixed dates
    if "thanksgiving" in t:
        # Thanksgiving is always the 4th Thursday of November
        # Week 12 Sunday is Nov 27 → Thursday is Nov 26 (Sunday - 1... actually Thu = Sun - 3)
        return (sunday - timedelta(days=3)).strftime("%B %-d")

    if "christmas" in t:
        return "December 25"

    if "friday" in t:
        return (sunday - timedelta(days=2)).strftime("%B %-d")

    if "thursday" in t or "thursday night" in t:
        return (sunday - timedelta(days=3)).strftime("%B %-d")

    if "monday" in t:
        return (sunday + timedelta(days=1)).strftime("%B %-d")

    # International games: listed with a city (e.g. "London, UK", "Munich, Germany")
    # They kick off Saturday morning ET (or very early Sunday), but are played on Sunday local time.
    # The NFL schedules them on Sunday on the official calendar, so keep Sunday.
    # However some are listed as Saturday-equivalent; we treat them as Sunday unless noted.
    international_keywords = [
        "london", "munich", "melbourne", "madrid", "paris",
        "mexico city", "rio de janeiro", "sao paulo",
    ]
    if any(kw in t for kw in international_keywords):
        # These games are played on Sunday (local time) but may have an early ET kickoff.
        # Display them as Sunday.
        return sunday.strftime("%B %-d")

    # Default: Sunday
    return sunday.strftime("%B %-d")

def get_team_schedule(team_name):
    # Find the canonical team name (case-insensitive match)
    matched = next((t for t in NFL_TEAMS if t.lower() == team_name.strip().lower()), None)
    if not matched:
        close = [t for t in NFL_TEAMS if team_name.strip().lower() in t.lower()]
        if len(close) == 1:
            matched = close[0]
        else:
            return None, None, close

    team_name_lower = matched.lower()
    results = []
    current_week = ""
    bye_weeks = []

    with open(SCHEDULE_FILE, "r") as f:
        for line in f:
            week_match = re.match(r"^(Week \d+):", line)
            if week_match:
                current_week = week_match.group(1)
                continue

            bye_match = re.match(r"^\s+Bye:\s+(.+)$", line)
            if bye_match:
                bye_teams = [t.strip().lower() for t in bye_match.group(1).split(",")]
                if team_name_lower in bye_teams:
                    bye_weeks.append(current_week)
                continue

            game_match = re.match(r"^\s{2}(\w[\w\s]+?)\s+@\s+(\w[\w\s]+?)\s{2,}(.+)$", line)
            if game_match:
                away = game_match.group(1).strip()
                home = game_match.group(2).strip()
                time = game_match.group(3).strip()
                if team_name_lower in away.lower() or team_name_lower in home.lower():
                    is_away = team_name_lower in away.lower()
                    opponent = home if is_away else away
                    results.append((current_week, is_away, opponent, time))

    return results, bye_weeks, matched

def generate_html(team, schedule, bye_weeks):
    colors = TEAM_COLORS.get(team, {"primary": "#2e7ab5", "secondary": "#1a5a8a"})
    primary = colors["primary"]
    secondary = colors["secondary"]
    rows = ""
    week_nums_seen = set()

    all_weeks = sorted(
        set([r[0] for r in schedule] + bye_weeks),
        key=lambda w: int(re.search(r"\d+", w).group())
    )

    game_map = {r[0]: r for r in schedule}

    for week in all_weeks:
        week_num = re.search(r"\d+", week).group()
        row_class = "bye-row" if week in bye_weeks else ""

        if week in bye_weeks:
            bye_date = WEEK_SUNDAYS.get(week, None)
            date_str = bye_date.strftime("%B %-d") if bye_date else "TBD"
            rows += f"""
        <tr class="bye-row">
          <td>{week_num}</td>
          <td>{date_str}</td>
          <td colspan="2" style="text-align:center; font-style:italic; color:#666;">Bye</td>
        </tr>"""
        else:
            _, is_away, opponent, time = game_map[week]
            date_str = get_game_date(week, time)
            at_prefix = "at " if is_away else ""
            rows += f"""
        <tr>
          <td>{week_num}</td>
          <td>{date_str}</td>
          <td class="opponent">{at_prefix}<span class="opp-name">{opponent}</span></td>
          <td>{time}</td>
        </tr>"""

    # Compute a lightened tint of the primary color for alternating rows
    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = hex_to_rgb(primary)
    tint = f"rgba({r},{g},{b},0.08)"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>2026 {team} Schedule</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      max-width: 800px;
      margin: 40px auto;
      background: #f9f9f9;
      color: #333;
    }}
    h2 {{
      margin-bottom: 10px;
      color: {primary};
      border-left: 6px solid {secondary};
      padding-left: 12px;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      background: white;
      box-shadow: 0 1px 4px rgba(0,0,0,0.1);
    }}
    th {{
      background-color: {primary};
      color: white;
      padding: 10px 14px;
      text-align: center;
      border-bottom: 3px solid {secondary};
    }}
    td {{
      padding: 8px 14px;
      border-bottom: 1px solid #ddd;
      text-align: center;
    }}
    tr:nth-child(even) {{ background-color: {tint}; }}
    tr:nth-child(odd)  {{ background-color: #ffffff; }}
    tr.bye-row td {{ background-color: #f0f0f0; color: #888; }}
    .opponent {{ text-align: left; }}
    .opp-name {{ color: {primary}; font-weight: bold; }}
  </style>
</head>
<body>
  <h2>2026 {team} Schedule</h2>
  <table>
    <thead>
      <tr>
        <th>Week</th>
        <th>Date</th>
        <th>Opponent</th>
        <th>Time (ET)</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>"""
    return html

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python team_schedule.py <TeamName>")
        print("       python team_schedule.py --all")
        print("Example: python team_schedule.py Bears")
        print(f"\nValid teams: {', '.join(sorted(NFL_TEAMS))}")
        sys.exit(1)

    if sys.argv[1] == "--all":
        out_dir = "schedules"
        os.makedirs(out_dir, exist_ok=True)
        generated = []
        for team in sorted(NFL_TEAMS):
            schedule, bye_weeks, result = get_team_schedule(team)
            if schedule is None:
                print(f"Warning: could not build schedule for {team}")
                continue
            html = generate_html(result, schedule, bye_weeks)
            filename = os.path.join(out_dir, f"{result.replace(' ', '_')}_schedule.html")
            with open(filename, "w") as f:
                f.write(html)
            generated.append(filename)
            print(f"  {filename}")
        print(f"\nGenerated {len(generated)} schedules in '{out_dir}/'.")
        sys.exit(0)

    team = " ".join(sys.argv[1:])
    schedule, bye_weeks, result = get_team_schedule(team)

    if schedule is None:
        if result:
            print(f"Ambiguous team name '{team}'. Did you mean one of: {', '.join(result)}?")
        else:
            print(f"Unknown team '{team}'.")
            print(f"Valid teams: {', '.join(sorted(NFL_TEAMS))}")
        sys.exit(1)

    html = generate_html(result, schedule, bye_weeks)
    out_dir = "schedules"
    os.makedirs(out_dir, exist_ok=True)
    filename = os.path.join(out_dir, f"{result.replace(' ', '_')}_schedule.html")
    with open(filename, "w") as f:
        f.write(html)
    print(f"Schedule saved to {filename}")
