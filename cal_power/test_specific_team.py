import json
import sys
sys.path.insert(0, '.')
from find_top_teams import build_actors, team_total_power, load_parsed_actors

# 載入資料
parsed = load_parsed_actors('.')
all_actors = build_actors(parsed, 0, None)

# 找到指定的五個角色
target_names = ['59式戰車', '渤雍', '阿雯', '習近平', '趙彤']
team = [a for a in all_actors if a.name in target_names]

print(f"找到 {len(team)} 個角色")
for a in team:
    print(f"  {a.name} - {a.scarcity} - {a.weapon_type} - Level {a.level}")

if len(team) == 5:
    weapon = '庚子'
    total, member_powers = team_total_power(team, weapon)
    print(f"\n武器: {weapon}")
    print(f"總戰力: {total:.2f}")
    print("\n各成員戰力:")
    for i, a in enumerate(team):
        print(f"  {a.name}: {member_powers[i]:.2f}")
