import random
from opponents import teams

team_names = [
    "Bears", "Lions", "Packers", "Vikings",
    "Cardinals", "Rams", "Seahawks", "49ers",
    "Cowboys", "Eagles", "Giants", "Commanders",
    "Falcons", "Panthers", "Saints", "Buccaneers",
    "Ravens", "Bengals", "Browns", "Steelers",
    "Broncos", "Chiefs", "Raiders", "Chargers",
    "Bills", "Dolphins", "Patriots", "Jets",
    "Jaguars", "Texans", "Titans", "Colts"
]

def rand_team(division):
    start_index = division * 4
    return random.choice(team_names[start_index:start_index + 4])

def main():
    all_games = set()  # Store games as pairs of teams
    divisional_games = []  # Separate list for divisional games

    # Add games from opponents.py
    for team in teams:
        for home_opponent in team["home"]:
            all_games.add((team["name"], home_opponent))
        for away_opponent in team["away"]:
            all_games.add((away_opponent, team["name"]))

    # Generate divisional games
    for division in range(8):  # 8 divisions
        division_teams = team_names[division * 4:(division + 1) * 4]
        for i, team1 in enumerate(division_teams):
            for j, team2 in enumerate(division_teams):
                if i != j:
                    divisional_games.append((team1, team2))

    # Write all games to games.txt
    with open("games.txt", "w") as out_file:
        out_file.write("All Games:\n")
        for game in all_games:
            out_file.write(f"{game[0]} vs. {game[1]}\n")

        out_file.write("\nDivisional Games:\n")
        for game in divisional_games:
            out_file.write(f"{game[0]} vs. {game[1]}\n")

if __name__ == "__main__":
    main()
