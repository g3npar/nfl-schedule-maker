import sys
import os
import re
from datetime import date, timedelta

SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "schedule_with_times.txt")

NFL_TEAMS = [
    "Bears", "Bengals", "Bills", "Broncos", "Browns", "Buccaneers",
    "Cardinals", "Chargers", "Chiefs", "Colts", "Cowboys", "Commanders",
    "Dolphins", "Eagles", "Falcons", "Giants", "Jaguars", "Jets",
    "Lions", "Packers", "Panthers", "Patriots", "Raiders", "Rams",
    "Ravens", "Saints", "Seahawks", "Steelers", "Texans", "Titans",
    "Vikings", "49ers",
]

_DIVISION_GROUPS = [
    {"Bears", "Lions", "Packers", "Vikings"},
    {"Cardinals", "Rams", "Seahawks", "49ers"},
    {"Cowboys", "Eagles", "Giants", "Commanders"},
    {"Falcons", "Panthers", "Saints", "Buccaneers"},
    {"Ravens", "Bengals", "Browns", "Steelers"},
    {"Broncos", "Chiefs", "Raiders", "Chargers"},
    {"Bills", "Dolphins", "Patriots", "Jets"},
    {"Jaguars", "Texans", "Titans", "Colts"},
]
DIVISIONS = {team: div for div in _DIVISION_GROUPS for team in div}

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
    "Cowboys":    {"primary": "#001532", "secondary": "#869397"},
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
    "Titans":     {"primary": "#4495D2", "secondary": "#D50A0A"},
    "Vikings":    {"primary": "#4F2683", "secondary": "#FFC62F"},
    "49ers":      {"primary": "#AA0000", "secondary": "#B3995D"},
}

# Full city + team names for file naming
TEAM_FULL_NAMES = {
    "Bears":      "chicago-bears",
    "Bengals":    "cincinnati-bengals",
    "Bills":      "buffalo-bills",
    "Broncos":    "denver-broncos",
    "Browns":     "cleveland-browns",
    "Buccaneers": "tampa-bay-buccaneers",
    "Cardinals":  "arizona-cardinals",
    "Chargers":   "los-angeles-chargers",
    "Chiefs":     "kansas-city-chiefs",
    "Colts":      "indianapolis-colts",
    "Cowboys":    "dallas-cowboys",
    "Commanders": "washington-commanders",
    "Dolphins":   "miami-dolphins",
    "Eagles":     "philadelphia-eagles",
    "Falcons":    "atlanta-falcons",
    "Giants":     "new-york-giants",
    "Jaguars":    "jacksonville-jaguars",
    "Jets":       "new-york-jets",
    "Lions":      "detroit-lions",
    "Packers":    "green-bay-packers",
    "Panthers":   "carolina-panthers",
    "Patriots":   "new-england-patriots",
    "Raiders":    "las-vegas-raiders",
    "Rams":       "los-angeles-rams",
    "Ravens":     "baltimore-ravens",
    "Saints":     "new-orleans-saints",
    "Seahawks":   "seattle-seahawks",
    "Steelers":   "pittsburgh-steelers",
    "Texans":     "houston-texans",
    "Titans":     "tennessee-titans",
    "Vikings":    "minnesota-vikings",
    "49ers":      "san-francisco-49ers",
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
    "Week 12": date(2026, 11, 29),
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
        return (sunday - timedelta(days=3)).strftime("%B %-d")

    if "christmas" in t:
        return "December 25"

    if "friday" in t:
        return (sunday - timedelta(days=2)).strftime("%B %-d")

    if "thursday" in t:
        return (sunday - timedelta(days=3)).strftime("%B %-d")

    if "monday" in t:
        return (sunday + timedelta(days=1)).strftime("%B %-d")
    
    if "wednesday" in t:
        return (sunday - timedelta(days=4)).strftime("%B %-d")

    # International games and all other Sunday games fall through to the same date.
    return sunday.strftime("%B %-d")

def _hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def get_team_schedule(team_name):
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

    bye_set = set(bye_weeks)
    all_weeks = sorted(
        {r[0] for r in schedule} | bye_set,
        key=lambda w: int(w.split()[1])
    )
    game_map = {r[0]: r for r in schedule}

    for week in all_weeks:
        week_num = week.split()[1]

        if week in bye_set:
            bye_date = WEEK_SUNDAYS.get(week)
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
            div_class = "divisional" if opponent in DIVISIONS.get(team, ()) else ""
            rows += f"""
        <tr class="{div_class}">
          <td>{week_num}</td>
          <td>{date_str}</td>
          <td class="opponent">{at_prefix}<span class="opp-name">{opponent}</span></td>
          <td>{time}</td>
        </tr>"""

    r, g, b = _hex_to_rgb(primary)
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
      margin: 16px auto;
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
    tr.divisional td {{ font-weight: bold; }}
    .opponent {{ text-align: left; }}
    .opp-name {{ color: {primary}; }}
    .back-btn {{
      display: inline-block;
      margin-bottom: 16px;
      padding: 7px 16px;
      background: {primary};
      color: #fff;
      text-decoration: none;
      border-radius: 5px;
      font-size: 0.85rem;
      font-weight: bold;
      border-bottom: 3px solid {secondary};
    }}
    .back-btn:hover {{ filter: brightness(1.15); }}
    .team-header {{
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 16px;
    }}
    .team-header img {{
      height: 72px;
      width: 72px;
      object-fit: contain;
    }}
    .team-header h2 {{
      margin: 0;
      color: {primary};
      border-left: 6px solid {secondary};
      padding-left: 12px;
    }}
  </style>
</head>
<body>
  <a class="back-btn" href="../index.html">← All Teams</a>
  <div class="team-header">
    <img src="../logos/{TEAM_FULL_NAMES.get(team, team.lower())}.png" alt="{team} logo">
    <h2>2026 {team} Schedule</h2>
  </div>
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

SLUG = TEAM_FULL_NAMES  # alias for use in primetime generator

def _logo(team):
    return f"../logos/{SLUG.get(team, team.lower())}.png"

def _game_card(away, home, time_et, note, css_class, badge_label):
    away_slug = SLUG.get(away, away.lower())
    home_slug = SLUG.get(home, home.lower())
    note_html = f'\n          <div class="game-note">{note}</div>' if note else ""
    return f"""      <div class="game-card {css_class}">
        <div class="team-logos"><img src="../logos/{away_slug}.png" alt="{away}"><span class="vs-sep">@</span><img src="../logos/{home_slug}.png" alt="{home}"></div>
        <div class="game-info">
          <div class="matchup">{away} @ {home}</div>
          <div class="game-meta">{time_et}</div>{note_html}
        </div>
        <span class="badge {css_class}">{badge_label}</span>
      </div>"""

def _panel(panel_id, count_id, week_groups_html):
    active = " active" if panel_id == "panel-tnf" else ""
    return f"""
  <div class="tab-panel{active}" id="{panel_id}">
    <p class="count-label" id="{count_id}"></p>
{week_groups_html}
  </div><!-- /{panel_id} -->
"""

def generate_primetime_html():
    INTL_PATTERN = re.compile(
        r"\b(Melbourne|Munich|London|Paris|Madrid|Mexico|Brazil|Rio)\b",
        re.IGNORECASE,
    )
    # Parse schedule into categorised game lists
    mnf, tnf, snf, tday, xmas, intl = [], [], [], [], [], []

    current_week = ""
    with open(SCHEDULE_FILE) as f:
        for line in f:
            wm = re.match(r"^(Week \d+):", line)
            if wm:
                current_week = wm.group(1)
                continue
            gm = re.match(r"^\s{2}(\w[\w\s]+?)\s+@\s+(\w[\w\s]+?)\s{2,}(.+)$", line)
            if not gm:
                continue
            away  = gm.group(1).strip()
            home  = gm.group(2).strip()
            slot  = gm.group(3).strip()
            tl    = slot.lower()

            # Extract note from parentheses
            note_m = re.search(r"\(([^)]+)\)", slot)
            note   = note_m.group(1) if note_m else ""

            # Classify — intl is independent so a game can appear in both intl AND broadcast tab
            is_intl = bool(INTL_PATTERN.search(slot))
            if is_intl:
                intl.append((current_week, away, home, slot, note))

            if "christmas" in tl:
                xmas.append((current_week, away, home, slot, note))
            elif "thanksgiving night" in tl:
                tday.append((current_week, away, home, slot, note))
                snf.append((current_week, away, home, slot, note))
            elif "thanksgiving" in tl:
                tday.append((current_week, away, home, slot, note))
            elif "monday night" in tl:
                mnf.append((current_week, away, home, slot, note))
            elif ("thursday night" in tl or "friday night" in tl) and not is_intl:
                tnf.append((current_week, away, home, slot, note))
            elif "sunday night" in tl:
                snf.append((current_week, away, home, slot, note))
            elif "wednesday" in tl:
                snf.append((current_week, away, home, slot, note))

    def build_panel(games, css_class, badge_label):
        # Group by week
        from collections import OrderedDict
        weeks = OrderedDict()
        for week, away, home, slot, note in games:
            weeks.setdefault(week, []).append((away, home, slot, note))
        html = ""
        for week, entries in weeks.items():
            # Annotate week label for special weeks
            label = week
            if any("thanksgiving" in e[2].lower() for e in entries):
                label = f"{week} \u2014 Thanksgiving"
            elif any("christmas" in e[2].lower() for e in entries):
                label = f"{week} \u2014 Christmas Day"
            html += f'    <div class="week-group">\n      <div class="week-label">{label}</div>\n'
            for away, home, slot, note in entries:
                # Extract just the time portion (before the parenthesis)
                time_et = slot.split("(")[0].strip()
                # Override note for special slots
                disp_note = note
                if "friday night football" in slot.lower():
                    disp_note = "Friday Night Football"
                elif "melbourne" in slot.lower():
                    disp_note = "Melbourne, Australia"
                html += _game_card(away, home, time_et, disp_note, css_class, badge_label) + "\n"
            html += "    </div>\n"
        return html

    mnf_html  = build_panel(mnf,  "mnf",  "MNF")
    tnf_html  = build_panel(tnf,  "tnf",  "TNF")
    snf_html  = build_panel(snf,  "snf",  "SNF")
    tday_html = build_panel(tday, "tday", "T-Day")
    xmas_html = build_panel(xmas, "xmas", "Xmas")
    intl_html = build_panel(intl, "intl", "Intl")

    counts = dict(mnf=len(mnf), tnf=len(tnf), snf=len(snf), tday=len(tday), xmas=len(xmas), intl=len(intl))

    panels = (
        _panel("panel-tnf",  "count-tnf",  tnf_html)  +
        _panel("panel-snf",  "count-snf",  snf_html)  +
        _panel("panel-mnf",  "count-mnf",  mnf_html)  +
        _panel("panel-tday", "count-tday", tday_html) +
        _panel("panel-xmas", "count-xmas", xmas_html) +
        _panel("panel-intl", "count-intl", intl_html)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>2026 NFL Primetime Schedule</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: Arial, sans-serif;
      background: #ffffff;
      color: #222;
      min-height: 100vh;
      padding: 16px 20px;
    }}
    h1 {{
      text-align: center;
      font-size: 2rem;
      margin-bottom: 8px;
      color: #111;
      letter-spacing: 1px;
    }}
    p.subtitle {{
      text-align: center;
      color: #666;
      margin-bottom: 28px;
      font-size: 0.95rem;
    }}
    .back-btn {{
      display: inline-block;
      margin-bottom: 16px;
      padding: 7px 16px;
      background: #111;
      color: #fff;
      text-decoration: none;
      border-radius: 5px;
      font-size: 0.85rem;
      font-weight: bold;
      border-bottom: 3px solid #555;
    }}
    .back-btn:hover {{ filter: brightness(1.3); }}
    .tabs {{
      display: flex;
      justify-content: center;
      gap: 10px;
      margin-bottom: 28px;
      flex-wrap: wrap;
      max-width: 680px;
      margin-left: auto;
      margin-right: auto;
    }}
    .tab-btn {{
      flex: 1;
      padding: 10px 12px;
      border: none;
      border-radius: 6px;
      font-size: 0.88rem;
      font-weight: bold;
      cursor: pointer;
      letter-spacing: 0.5px;
      transition: filter 0.15s, transform 0.1s;
      color: #fff;
      border-bottom: 4px solid rgba(0,0,0,0.25);
    }}
    .tab-btn:hover {{ filter: brightness(1.15); transform: translateY(-2px); }}
    .tab-btn.active {{ filter: brightness(1.0); transform: none; outline: 3px solid #111; outline-offset: 2px; }}
    .tab-btn[data-tab="mnf"]  {{ background: #1a1aff; }}
    .tab-btn[data-tab="tnf"]  {{ background: #0d7c3b; }}
    .tab-btn[data-tab="snf"]  {{ background: #b8000d; }}
    .tab-btn[data-tab="tday"] {{ background: #c45e00; }}
    .tab-btn[data-tab="xmas"] {{ background: #b8000d; }}
    .tab-btn[data-tab="intl"] {{ background: #2a7a7a; }}
    .tab-panel {{ display: none; max-width: 680px; margin: 0 auto; }}
    .tab-panel.active {{ display: block; }}
    .week-group {{ margin-bottom: 26px; }}
    .week-label {{
      font-size: 0.75rem;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: #999;
      margin-bottom: 8px;
      padding-bottom: 4px;
      border-bottom: 1px solid #eee;
    }}
    .game-card {{
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 12px 16px;
      border-radius: 8px;
      margin-bottom: 8px;
      background: #f5f5f5;
      border-left: 5px solid #ccc;
    }}
    .game-card.mnf  {{ border-left-color: #1a1aff; }}
    .game-card.tnf  {{ border-left-color: #0d7c3b; }}
    .game-card.snf  {{ border-left-color: #b8000d; }}
    .game-card.tday {{ border-left-color: #c45e00; }}
    .game-card.xmas {{ border-left-color: #b8000d; }}
    .game-card.intl {{ border-left-color: #2a7a7a; }}
    .team-logos {{
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }}
    .team-logos img {{ height: 36px; width: 36px; object-fit: contain; }}
    .vs-sep {{ font-size: 0.75rem; color: #aaa; font-weight: bold; }}
    .game-info {{ flex: 1; min-width: 0; }}
    .matchup {{
      font-size: 1rem;
      font-weight: bold;
      color: #111;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .game-meta {{ font-size: 0.8rem; color: #666; margin-top: 2px; }}
    .game-note {{ font-size: 0.75rem; color: #999; font-style: italic; margin-top: 1px; }}
    .badge {{
      font-size: 0.7rem;
      font-weight: bold;
      padding: 3px 8px;
      border-radius: 4px;
      color: #fff;
      white-space: nowrap;
      flex-shrink: 0;
    }}
    .badge.mnf  {{ background: #1a1aff; }}
    .badge.tnf  {{ background: #0d7c3b; }}
    .badge.snf  {{ background: #b8000d; }}
    .badge.tday {{ background: #c45e00; }}
    .badge.xmas {{ background: #b8000d; }}
    .badge.intl {{ background: #2a7a7a; }}
    .count-label {{ text-align: center; color: #888; font-size: 0.82rem; margin-bottom: 18px; }}
  </style>
</head>
<body>
  <div style="max-width:680px; margin:0 auto;">
    <a class="back-btn" href="index.html">\u2190 Back to Schedule Home</a>
  </div>
  <h1>\U0001f319 2026 NFL Primetime Schedule</h1>
  <p class="subtitle">Toggle between MNF, TNF, SNF, Thanksgiving, Christmas, and International games</p>

  <div class="tabs">
    <button class="tab-btn active" data-tab="tnf">Thursday Night Football</button>
    <button class="tab-btn" data-tab="snf">Sunday Night Football</button>
    <button class="tab-btn" data-tab="mnf">Monday Night Football</button>
    <button class="tab-btn" data-tab="tday">Thanksgiving</button>
    <button class="tab-btn" data-tab="xmas">Christmas</button>
    <button class="tab-btn" data-tab="intl">International</button>
  </div>

{panels}
  <script>
    const counts = {counts};
    const labels = {{
      mnf: "Monday Night Football", tnf: "Thursday Night Football",
      snf: "Sunday Night Football", tday: "Thanksgiving", xmas: "Christmas",
      intl: "International Games"
    }};
    document.querySelectorAll(".tab-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        const tab = btn.dataset.tab;
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("panel-" + tab).classList.add("active");
      }});
    }});
    Object.keys(counts).forEach(tab => {{
      document.getElementById("count-" + tab).textContent =
        counts[tab] + " " + labels[tab] + " games";
    }});
  </script>
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
        out_dir = os.path.join(os.path.dirname(__file__), "..", "schedules")
        os.makedirs(out_dir, exist_ok=True)
        # Pre-parse the schedule file once, then generate HTML for every team.
        all_data = {team: get_team_schedule(team) for team in NFL_TEAMS}
        generated = []
        for team in sorted(NFL_TEAMS):
            schedule, bye_weeks, result = all_data[team]
            if schedule is None:
                print(f"Warning: could not build schedule for {team}")
                continue
            html = generate_html(result, schedule, bye_weeks)
            slug = TEAM_FULL_NAMES.get(str(result), str(result).lower())
            filename = os.path.join(out_dir, f"{slug}.html")
            with open(filename, "w") as f:
                f.write(html)
            generated.append(filename)
            print(f"  {filename}")
        print(f"\nGenerated {len(generated)} schedules in '{out_dir}/'.")

        # Regenerate primetime.html
        primetime_path = os.path.join(os.path.dirname(__file__), "..", "primetime.html")
        with open(primetime_path, "w") as f:
            f.write(generate_primetime_html())
        print(f"  {os.path.normpath(primetime_path)}")
        print("Regenerated primetime.html.")
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
    filename = os.path.join(out_dir, f"{result}_schedule.html")
    with open(filename, "w") as f:
        f.write(html)
    print(f"Schedule saved to {filename}")
