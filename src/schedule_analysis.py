import os
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = "data/charts"
os.makedirs(OUT, exist_ok=True)

SCHEDULE_FILE = "data/schedule_with_times.txt"

DIVISIONS = {
    "AFC East":  ["Bills", "Dolphins", "Patriots", "Jets"],
    "AFC North": ["Ravens", "Steelers", "Browns", "Bengals"],
    "AFC South": ["Texans", "Colts", "Jaguars", "Titans"],
    "AFC West":  ["Chiefs", "Raiders", "Chargers", "Broncos"],
    "NFC East":  ["Eagles", "Cowboys", "Commanders", "Giants"],
    "NFC North": ["Lions", "Packers", "Vikings", "Bears"],
    "NFC South": ["Buccaneers", "Falcons", "Saints", "Panthers"],
    "NFC West":  ["49ers", "Seahawks", "Rams", "Cardinals"],
}

TEAM_ORDER = []
for div in DIVISIONS.values():
    TEAM_ORDER.extend(div)

COLORS = {
    "TNF": "#e05c00", "SNF": "#1a6bbf", "MNF": "#2ca02c",
    "Thanksgiving": "#9b59b6", "Christmas": "#c0392b",
    "1PM": "#aec7e8", "4PM": "#ffbb78", "Other": "#cccccc",
}

def slot_category(time_str):
    t = time_str
    if "Christmas" in t:
        if "8:20" in t or "8:15" in t or "Night" in t:
            return "Christmas"
        return "Christmas"
    if "Thanksgiving" in t:
        return "Thanksgiving"
    if "Thursday Night" in t or "Friday Night" in t or "Melbourne" in t:
        return "TNF"
    if "Sunday Night" in t or "Wednesday Kickoff" in t:
        return "SNF"
    if "Monday Night" in t:
        return "MNF"
    if "London" in t or "Madrid" in t or "Rio" in t or "Paris" in t or "Mexico" in t or "Munich" in t:
        return "Other"
    if "1:00 PM" in t or "12:30 PM" in t or "9:30 AM" in t:
        return "1PM"
    if "4:05 PM" in t or "4:25 PM" in t or "4:30 PM" in t or "3:00 PM" in t:
        return "4PM"
    return "Other"

def is_broadcast_primetime(cat):
    return cat in ("TNF", "SNF", "MNF", "Thanksgiving", "Christmas")

def parse_schedule():
    games = []
    byes = {}
    current_week = None
    with open(SCHEDULE_FILE) as f:
        for line in f:
            line = line.rstrip()
            if re.match(r"^Week \d+:", line):
                current_week = int(re.search(r"\d+", line).group())
            elif line.strip().startswith("Bye:"):
                teams = [t.strip() for t in line.split("Bye:")[1].split(",")]
                byes[current_week] = teams
            elif " @ " in line and current_week is not None:
                parts = line.strip().split("  ")
                matchup = parts[0].strip()
                away, home = matchup.split(" @ ")
                time_str = "  ".join(p for p in parts[1:] if p.strip()).strip()
                cat = slot_category(time_str)
                games.append({
                    "week": current_week, "away": away, "home": home,
                    "time": time_str, "cat": cat,
                })
    return games, byes

games, byes = parse_schedule()
all_teams = TEAM_ORDER

# ── Chart 1: Primetime appearances ───────────────────────────────────────────

CHART1_CATS = ("Christmas", "Thanksgiving", "MNF", "SNF", "TNF")

pt_counts = {cat: defaultdict(int) for cat in CHART1_CATS}
for g in games:
    if is_broadcast_primetime(g["cat"]):
        pt_counts[g["cat"]][g["away"]] += 1
        pt_counts[g["cat"]][g["home"]] += 1

pt_totals = {t: sum(pt_counts[cat][t] for cat in CHART1_CATS) for t in all_teams}
sorted_teams = sorted(all_teams, key=lambda t: pt_totals[t], reverse=True)

fig, ax = plt.subplots(figsize=(14, 7))
x = np.arange(len(sorted_teams))
bottoms = np.zeros(len(sorted_teams))
for cat in ("Christmas", "Thanksgiving", "MNF", "SNF", "TNF"):
    vals = np.array([pt_counts[cat][t] for t in sorted_teams], dtype=float)
    ax.bar(x, vals, bottom=bottoms, color=COLORS[cat], label=cat, width=0.7)
    bottoms += vals
ax.set_xticks(x)
ax.set_xticklabels(sorted_teams, rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Games")
ax.set_title("Primetime Appearances by Team (TNF / SNF / MNF / Thanksgiving / Christmas)")
ax.legend(loc="upper right", fontsize=8)
ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
plt.tight_layout()
plt.savefig(f"{OUT}/1_primetime_appearances.png", dpi=150)
plt.close()

# ── Chart 2: Timeslot distribution ────────────────────────────────────────────

slot_counts = defaultdict(lambda: defaultdict(int))
for g in games:
    if g["week"] == 18:
        continue
    slot_counts[g["cat"]][g["away"]] += 1
    slot_counts[g["cat"]][g["home"]] += 1

alpha_teams = sorted(all_teams)
alpha_x = np.arange(len(alpha_teams))

slot3 = {
    "Intl/Special": {t: slot_counts["Other"][t] for t in alpha_teams},
    "1pm":          {t: slot_counts["1PM"][t] for t in alpha_teams},
    "4pm":          {t: slot_counts["4PM"][t] for t in alpha_teams},
    "Primetime":    {t: sum(slot_counts[c][t] for c in ("TNF", "SNF", "MNF", "Thanksgiving", "Christmas")) for t in alpha_teams},
}
slot3_colors = {"Intl/Special": "#a8d8a8", "1pm": "#aec7e8", "4pm": "#f0a858", "Primetime": "#5c2d8a"}

fig, ax = plt.subplots(figsize=(20, 6))
bottoms = np.zeros(len(alpha_teams))
for cat in ("Intl/Special", "1pm", "4pm", "Primetime"):
    vals = np.array([slot3[cat][t] for t in alpha_teams], dtype=float)
    ax.bar(alpha_x, vals, bottom=bottoms, color=slot3_colors[cat], label=cat, width=0.7)
    bottoms += vals
ax.set_xticks(alpha_x)
ax.set_xticklabels(alpha_teams, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("# of Games")
ax.set_ylim(0, 20)
ax.set_title("Time Slot Distribution per Team (2026)", fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
plt.tight_layout()
plt.savefig(f"{OUT}/2_timeslot_distribution.png", dpi=150)
plt.close()

# ── Chart 3: Bye week distribution ───────────────────────────────────────────

# Build week → teams on bye mapping
bye_week_teams = defaultdict(list)
for week, teams in byes.items():
    for t in teams:
        bye_week_teams[week].append(t)

# Count how many teams have their bye each week
bye_weeks_sorted = sorted(bye_week_teams.keys())
bye_counts = [len(bye_week_teams[w]) for w in bye_weeks_sorted]

# Also build per-team bye week for labeling
team_bye = {}
for week, teams in byes.items():
    for t in teams:
        team_bye[t] = week

all_bye_weeks = list(range(5, 15))
bye_counts_full = [len(bye_week_teams.get(w, [])) for w in all_bye_weeks]

fig, ax = plt.subplots(figsize=(10, 5))

bars = ax.bar([str(w) for w in all_bye_weeks], bye_counts_full, color="#4c72b0", width=0.6, edgecolor="white")
for bar, week in zip(bars, all_bye_weeks):
    teams = bye_week_teams.get(week, [])
    if teams:
        label = "\n".join(teams)
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                label, ha="center", va="bottom", fontsize=6.5, color="#333")
ax.set_xlabel("Week")
ax.set_ylabel("# of Teams on Bye")
ax.set_title("Teams on Bye per Week (2026)", fontweight="bold")
ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))  # type: ignore[attr-defined]
ax.set_ylim(0, max(bye_counts_full) + 2.5 if any(bye_counts_full) else 5)

plt.tight_layout()
plt.savefig(f"{OUT}/3_bye_week_distribution.png", dpi=150)
plt.close()

# ── Chart 4: Primetime games per division ────────────────────────────────────

div_pt = {}
for div, teams in DIVISIONS.items():
    div_cats = {cat: sum(pt_counts[cat][t] for t in teams) for cat in CHART1_CATS}
    div_pt[div] = div_cats

div_names  = list(DIVISIONS.keys())
div_totals = [sum(div_pt[d].values()) for d in div_names]
sorted_divs = [d for _, d in sorted(zip(div_totals, div_names), reverse=True)]

fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(sorted_divs))
bottoms = np.zeros(len(sorted_divs))
for cat in ("Christmas", "Thanksgiving", "MNF", "SNF", "TNF"):
    vals = np.array([div_pt[d][cat] for d in sorted_divs], dtype=float)
    ax.bar(x, vals, bottom=bottoms, color=COLORS[cat], label=cat, width=0.5)
    bottoms += vals

# label total on top of each bar
for i, d in enumerate(sorted_divs):
    tot = sum(div_pt[d].values())
    ax.text(i, tot + 0.1, str(tot), ha="center", va="bottom", fontsize=9, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(sorted_divs, rotation=30, ha="right", fontsize=10)
ax.set_ylabel("Primetime Game Appearances")
ax.set_title("Primetime Appearances by Division (TNF / SNF / MNF / Thanksgiving / Christmas)", fontweight="bold")
ax.legend(loc="upper right", fontsize=9)
ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))  # type: ignore[attr-defined]
plt.tight_layout()
plt.savefig(f"{OUT}/4_primetime_by_division.png", dpi=150)
plt.close()

print("Charts saved to data/charts/")
for f in sorted(os.listdir(OUT)):
    print(f"  {f}")
