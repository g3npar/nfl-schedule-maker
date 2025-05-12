import pulp
from collections import defaultdict

def parse_games(file_path):
    all_games = []
    divisional_games = defaultdict(list)
    with open(file_path, 'r') as f:
        lines = f.readlines()
        section = None
        for line in lines:
            line = line.strip()
            if line == "All Games:":
                section = "all_games"
            elif line == "Divisional Games:":
                section = "divisional_games"
            elif line and section == "all_games":
                all_games.append(tuple(line.split(" vs. ")))
            elif line and section == "divisional_games":
                team1, team2 = line.split(" vs. ")
                divisional_games[team1].append(team2)
                all_games.append((team1, team2))
    return all_games, divisional_games

def generate_schedule(all_games, divisional_games, weeks=18):
    prob = pulp.LpProblem("NFL_Schedule", pulp.LpMaximize)

    # x[game, week] = 1 if game is scheduled in week
    x = pulp.LpVariable.dicts("GameWeek", 
                               ((game, week) for game in all_games for week in range(1, weeks + 1)),
                               cat="Binary")

    # Constraint: Each game is scheduled exactly once
    for game in all_games:
        prob += pulp.lpSum(x[game, week] for week in range(1, weeks + 1)) == 1

    # Constraint: Each team plays at most one game per week
    teams = set(team for game in all_games for team in game)
    for team in teams:
        for week in range(1, weeks + 1):
            prob += pulp.lpSum(x[game, week] for game in all_games if team in game) <= 1

    # Constraint: Weeks 1-4 and 15-18 must have exactly 16 games
    for week in list(range(1, 5)) + list(range(15, 19)):
        prob += pulp.lpSum(x[game, week] for game in all_games) == 16

    # Constraint: Week 18 must contain only divisional games
    divisional_game_set = set((team1, team2) for team1, opponents in divisional_games.items() for team2 in opponents)
    prob += pulp.lpSum(x[game, 18] for game in all_games if game not in divisional_game_set) == 0

    # Constraint: Eagles vs. Cowboys (kickoff game) must be the first game in Week 1
    kickoff_game = ("Eagles", "Cowboys")
    if kickoff_game in all_games:
        prob += x[kickoff_game, 1] == 1

    # Constraint: Lions and Cowboys must host games in Week 12
    for host_team in ["Lions", "Cowboys"]:
        prob += pulp.lpSum(x[game, 12] for game in all_games if game[0] == host_team) == 1

    # Constraint: No team has more than 2 consecutive home or away games
    for team in teams:
        for week in range(1, weeks - 1):
            # Home games
            prob += (
                pulp.lpSum(x[game, week] for game in all_games if game[0] == team) +
                pulp.lpSum(x[game, week + 1] for game in all_games if game[0] == team) +
                pulp.lpSum(x[game, week + 2] for game in all_games if game[0] == team)
            ) <= 2
            # Away games
            prob += (
                pulp.lpSum(x[game, week] for game in all_games if game[1] == team) +
                pulp.lpSum(x[game, week + 1] for game in all_games if game[1] == team) +
                pulp.lpSum(x[game, week + 2] for game in all_games if game[1] == team)
            ) <= 2

    # Constraint: No team plays the same opponent in consecutive weeks
    for game in all_games:
        team1, team2 = game
        for week in range(1, weeks):
            reverse_game = (team2, team1)
            if reverse_game in all_games:
                prob += (
                    x[game, week] + x[reverse_game, week + 1]
                ) <= 1

    prob.solve()

    # Extract the schedule
    schedule = defaultdict(list)
    for game in all_games:
        for week in range(1, weeks + 1):
            if pulp.value(x[game, week]) == 1:
                schedule[week].append(game)

    # Ensure Eagles vs. Commanders is the first game in Week 1
    if kickoff_game in schedule[1]:
        schedule[1].remove(kickoff_game)
        schedule[1].insert(0, kickoff_game)

    return schedule

if __name__ == "__main__":
    games_file = "/home/parinr/nfl-schedule-maker/games.txt"
    all_games, divisional_games = parse_games(games_file)
    schedule = generate_schedule(all_games, divisional_games)

    # Write the schedule to schedule.txt with game numbering
    output_file = "/home/parinr/nfl-schedule-maker/schedule.txt"
    with open(output_file, "w") as f:
        for week in sorted(schedule.keys()):  # Ensure weeks are in order
            f.write(f"Week {week}:\n")
            for i, game in enumerate(schedule[week], start=1):
                f.write(f"  {i}. {game[0]} vs. {game[1]}\n")

