with open("schedule_with_times.txt") as f:
    lines = f.readlines()

tnf = []
snf = []
mnf = []

current_week = ""

for line in lines:
    if line.strip().startswith("Week"):
        current_week = line.strip().rstrip(":")
    elif "Thursday Night Football" in line or "Thursday Kickoff Game" in line:
        tnf.append(f"  {current_week}: {line.strip()}")
    elif "Sunday Night Football" in line or "Thanksgiving Night Football" in line:
        snf.append(f"  {current_week}: {line.strip()}")
    elif "Monday Night Football" in line:
        mnf.append(f"  {current_week}: {line.strip()}")

print("=" * 60)
print("THURSDAY NIGHT FOOTBALL SCHEDULE")
print("=" * 60)
for game in tnf:
    print(game)

print()
print("=" * 60)
print("SUNDAY NIGHT FOOTBALL SCHEDULE")
print("=" * 60)
for game in snf:
    print(game)

print()
print("=" * 60)
print("MONDAY NIGHT FOOTBALL SCHEDULE")
print("=" * 60)
for game in mnf:
    print(game)
