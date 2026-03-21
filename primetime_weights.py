# ---------------------------------------------------------------------------
# primetime_weights.py  —  Primetime game allocation config
# ---------------------------------------------------------------------------
# Assign a weight (0–7) to each team.  The weight maps directly to the number
# of primetime games that team is targeted for:
#
# The target is a soft preference — the scheduler will try not to exceed it
# but will fall back gracefully if no eligible games remain.
# The hard cap is always MAX_PRIMETIME_PER_TEAM from nfl_schedule_generator.py.
#
# Adjust the numbers below before running nfl_schedule_generator.py.
# ---------------------------------------------------------------------------

PRIMETIME_WEIGHTS = {
    # ── AFC East ────────────────────────────────────────────────────────────
    "Patriots":     6,
    "Bills":        5,
    "Dolphins":     1,   # +1
    "Jets":         1,   # +1

    # ── AFC North ───────────────────────────────────────────────────────────
    "Ravens":       4,
    "Steelers":     3,
    "Bengals":      2,   # +1
    "Browns":       0,   # +2

    # ── AFC South ───────────────────────────────────────────────────────────
    "Jaguars":      4,
    "Texans":       4,   # +1
    "Colts":        2,   # +1
    "Titans":       1,   # +1

    # ── AFC West ────────────────────────────────────────────────────────────
    "Broncos":      5,
    "Chiefs":       5,
    "Chargers":     4,
    "Raiders":      1,   # +1

    # ── NFC East ────────────────────────────────────────────────────────────
    "Eagles":       6,
    "Cowboys":      6,
    "Giants":       2,   # +1
    "Commanders":   3,   # +1

    # ── NFC North ───────────────────────────────────────────────────────────
    "Lions":        4,
    "Packers":      4,
    "Vikings":      3,   # +1
    "Bears":        5,

    # ── NFC South ───────────────────────────────────────────────────────────
    "Saints":       2,   # +1
    "Buccaneers":   3,   # +1
    "Panthers":     4,   # +1
    "Falcons":      4,   # +1

    # ── NFC West ────────────────────────────────────────────────────────────
    "Seahawks":     7,
    "Rams":         6,
    "49ers":        4,
    "Cardinals":    0,
}

# ---------------------------------------------------------------------------
# Weight → primetime target mapping.
# Each weight maps directly to that exact number of games (0–7).
# You can remap these if needed, e.g. make weight 3 → 4 games instead.
# ---------------------------------------------------------------------------
WEIGHT_TO_TARGET = {
    7: 7,
    6: 6,
    5: 5,
    4: 4,
    3: 3,
    2: 2,
    1: 1,
    0: 0,
}
