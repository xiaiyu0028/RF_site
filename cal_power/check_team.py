import json

with open('parsed_actors_skill.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

actors = ['59式戰車', '渤雍', '阿雯', '習近平', '趙彤']

print("檢查角色武器類型：")
for name in actors:
    if name in data:
        weapon = data[name].get('weapon_name', '無')
        print(f"{name}: {weapon}")
    else:
        print(f"{name}: 找不到")

# 檢查武器限制
restricted = ['匕首', '重擊', '刀劍']
count = sum(1 for name in actors if name in data and data[name].get('weapon_name') in restricted)
print(f"\n限制武器類型數量: {count}")
print(f"是否符合限制 (≤1): {count <= 1}")
