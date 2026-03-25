# Weight = target primetime games. Soft cap; hard cap enforced in nfl_schedule_generator.py.
PRIMETIME_WEIGHTS = {
    # AFC East
    "Patriots":     6,
    "Bills":        5,
    "Dolphins":     1,
    "Jets":         1,

    # AFC North
    "Ravens":       4,
    "Steelers":     3,
    "Bengals":      2,
    "Browns":       0,

    # AFC South
    "Jaguars":      4,
    "Texans":       4,
    "Colts":        2,
    "Titans":       1,

    # AFC West
    "Broncos":      5,
    "Chiefs":       5,
    "Chargers":     4,
    "Raiders":      1,

    # NFC East
    "Eagles":       6,
    "Cowboys":      6,
    "Giants":       2,
    "Commanders":   3,

    # NFC North
    "Lions":        4,
    "Packers":      4,
    "Vikings":      3,
    "Bears":        5,

    # NFC South
    "Saints":       2,
    "Buccaneers":   3,
    "Panthers":     4,
    "Falcons":      4,

    # NFC West
    "Seahawks":     7,
    "Rams":         6,
    "49ers":        4,
    "Cardinals":    0,
}

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
