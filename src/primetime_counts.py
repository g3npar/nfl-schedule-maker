import re
from collections import defaultdict

TNF_KEYWORDS          = ["Thursday Night Football", "Thursday Kickoff Game", "Friday Night Football"]
SNF_KEYWORDS          = ["Sunday Night Football"]
MNF_KEYWORDS          = ["Monday Night Football"]
THANKSGIVING_KEYWORDS = ["Thanksgiving Night Football", "Thanksgiving"]
CHRISTMAS_KEYWORDS    = ["Christmas Day"]

ALL_KEYWORDS = TNF_KEYWORDS + SNF_KEYWORDS + MNF_KEYWORDS + THANKSGIVING_KEYWORDS + CHRISTMAS_KEYWORDS

pattern = re.compile(
    r'^\s+([\w]+)\s+@\s+([\w]+)\s+.*?(' + '|'.join(re.escape(k) for k in ALL_KEYWORDS) + ')',
    re.IGNORECASE
)

def categorize(slot):
    s = slot.lower()
    if "christmas" in s:
        return "XMAS"
    if "thanksgiving night" in s:
        return "TDAY"
    if "thanksgiving" in s:
        return "TDAY"
    if any(k.lower() in s for k in TNF_KEYWORDS):
        return "TNF"
    if any(k.lower() in s for k in SNF_KEYWORDS):
        return "SNF"
    if any(k.lower() in s for k in MNF_KEYWORDS):
        return "MNF"
    return "OTHER"

ALL_TEAMS = [
    "Bears", "Bengals", "Bills", "Broncos", "Browns", "Buccaneers",
    "Cardinals", "Chargers", "Chiefs", "Colts", "Cowboys", "Dolphins",
    "Eagles", "Falcons", "Giants", "Jaguars", "Jets", "Lions",
    "Packers", "Panthers", "Patriots", "Raiders", "Rams", "Ravens",
    "Saints", "Seahawks", "Steelers", "Texans", "Titans", "Vikings",
    "Commanders", "49ers",
]

total  = defaultdict(int)
tnf    = defaultdict(int)
snf    = defaultdict(int)
mnf    = defaultdict(int)
tday   = defaultdict(int)
xmas   = defaultdict(int)

for team in ALL_TEAMS:
    total[team] = 0

with open("data/schedule_with_times.txt") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            away, home, slot = m.group(1), m.group(2), m.group(3)
            cat = categorize(slot)
            for team in (away, home):
                total[team] += 1
                if cat == "TNF":  tnf[team]  += 1
                if cat == "SNF":  snf[team]  += 1
                if cat == "MNF":  mnf[team]  += 1
                if cat == "TDAY": tday[team] += 1
                if cat == "XMAS": xmas[team] += 1

all_teams = sorted(total.keys(), key=lambda t: -total[t])

print(f"{'Team':<15} {'Total':>5}  {'TNF':>3}  {'SNF':>3}  {'MNF':>3}  {'TDay':>4}  {'Xmas':>4}")
print("-" * 52)
for team in all_teams:
    print(f"{team:<15} {total[team]:>5}  {tnf[team]:>3}  {snf[team]:>3}  {mnf[team]:>3}  {tday[team]:>4}  {xmas[team]:>4}")

# ── Primetime games per division ─────────────────────────────────────────────

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

print()
print(f"{'Division':<12} {'Total':>5}  {'TNF':>3}  {'SNF':>3}  {'MNF':>3}  {'TDay':>4}  {'Xmas':>4}")
print("-" * 52)
for div, teams in DIVISIONS.items():
    d_total = sum(total[t] for t in teams)
    d_tnf   = sum(tnf[t]   for t in teams)
    d_snf   = sum(snf[t]   for t in teams)
    d_mnf   = sum(mnf[t]   for t in teams)
    d_tday  = sum(tday[t]  for t in teams)
    d_xmas  = sum(xmas[t]  for t in teams)
    print(f"{div:<12} {d_total:>5}  {d_tnf:>3}  {d_snf:>3}  {d_mnf:>3}  {d_tday:>4}  {d_xmas:>4}")
