import re
from collections import defaultdict

TNF_KEYWORDS          = ["Thursday Night Football", "Thursday Kickoff Game"]
FNF_KEYWORDS          = ["Friday Night Football"]
SNF_KEYWORDS          = ["Sunday Night Football"]
MNF_KEYWORDS          = ["Monday Night Football"]
THANKSGIVING_KEYWORDS = ["Thanksgiving Night Football", "Thanksgiving"]
CHRISTMAS_KEYWORDS    = ["Christmas Day"]

ALL_KEYWORDS = TNF_KEYWORDS + FNF_KEYWORDS + SNF_KEYWORDS + MNF_KEYWORDS + THANKSGIVING_KEYWORDS + CHRISTMAS_KEYWORDS

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
    if any(k.lower() in s for k in FNF_KEYWORDS):
        return "FNF"
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
fnf    = defaultdict(int)
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
                if cat == "FNF":  fnf[team]  += 1
                if cat == "SNF":  snf[team]  += 1
                if cat == "MNF":  mnf[team]  += 1
                if cat == "TDAY": tday[team] += 1
                if cat == "XMAS": xmas[team] += 1

all_teams = sorted(total.keys(), key=lambda t: -total[t])

print(f"{'Team':<15} {'Total':>5}  {'TNF':>3}  {'FNF':>3}  {'SNF':>3}  {'MNF':>3}  {'TDay':>4}  {'Xmas':>4}")
print("-" * 57)
for team in all_teams:
    print(f"{team:<15} {total[team]:>5}  {tnf[team]:>3}  {fnf[team]:>3}  {snf[team]:>3}  {mnf[team]:>3}  {tday[team]:>4}  {xmas[team]:>4}")
