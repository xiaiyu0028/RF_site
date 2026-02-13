import json
import os

with open("./parsed_actors_skill.json", "r") as outfile:
    parsed_actors = json.load(outfile)
cal_actors = [
    {'name':'卡姆蘭',
            'scarcity' : None,
            'level': 300}, 
    {'name':'仙姑',
            'scarcity' : None,
            'level': 300},
    {'name':'瓦旦',
            'scarcity' : None,
            'level': 160},
    {'name':'粉圓',
            'scarcity' : None,
            'level': 160},
    {'name':'范姜',
            'scarcity' : None,
            'level': 160}
]

def _floor_to_10(n: int) -> int:
    try:
        n = int(n)
    except Exception:
        return 0
    return n - (n % 10)


def calculate_passtive(actors):
    category_keys = list(set(parsed_actors[actor]['actor_category'] for actor in parsed_actors))
    nation_keys = list(set(parsed_actors[actor]['nation'] for actor in parsed_actors))
    total_effects = {
            # 'self': { 'atk': 0, 'def': 0, 'hp': 0 },
            'category': { cat:{ 'atk': 0, 'def': 0, 'hp': 0 } for cat in category_keys },
            'nation': { nat:{ 'atk': 0, 'def': 0, 'hp': 0 } for nat in nation_keys },
        }
    for actor in actors:
        if actor['name'] not in parsed_actors.keys():
            continue
        actor_data = parsed_actors[actor['name']]
        passive_skills = actor_data['parsed_passive_skills']
        # 使用捨去各位數後的等級（取 10 的倍數）
        active_level = _floor_to_10(actor['level'])
        active_effect = passive_skills.get(str(active_level), {})
        print(f"計算 {actor['name']} 等級 {active_level} 被動效果: {active_effect}")
        for key,value in active_effect.items():
            if key == 'category':
                for cat in value.keys():
                    for stat_key in ['atk', 'def', 'hp']:
                        total_effects['category'][cat][stat_key] += value[cat].get(stat_key, 0)
            elif key == 'nation':
                for nat in value.keys():                    
                    for stat_key in ['atk', 'def', 'hp']:
                        total_effects['nation'][nat][stat_key] += value[nat].get(stat_key, 0)
                    
    return total_effects
    
    
def cal_power(effects, scarcity, level, weapon="原初"):
    power_multiplier = {
        'R': 1.0,
        'SR': 1.2,
        'SSR': 1.4,
    }
    weapon_multiplier = {
        '原初': 1.0,
        '強化': 2.1,
        '高等': 5.0,
        '限定': 2.5,
        '排名': 7.0,
        '庚子': 8.0,
    }
    # 稀有度等級上限
    if scarcity == "R":
        level = min(level, 90)
    elif scarcity == "SR":
        level = min(level, 160)
    elif scarcity == "SSR":
        level = min(level, 300)
    # 非 10 的倍數時，捨去各位數（向下取整到 10 的倍數）
    # level = _floor_to_10(level)
    
    multiplier = power_multiplier.get(scarcity, 1.0)
    weapon_mult = weapon_multiplier.get(weapon, 1.0)
    total_power = level * multiplier * weapon_mult * ( 1 + ( (1 + (effects.get('atk', 0)/100 + effects.get('hp', 0)/100)) * (1 + effects.get('def', 0)/100) - 1 ) * 0.2 ) / 10 + 4
    return total_power    
    
for act in cal_actors:
    if act['name'] in parsed_actors:
        act['scarcity'] = parsed_actors[act['name']]['scarcity']
effects = calculate_passtive(cal_actors)
print("\n總計", effects)

print('\n\ncalculate total effects')

for act in cal_actors:
    print(f"{act['name']} ({act['scarcity']}): 等級 {act['level']}")
    self_effects = {'atk': 0, 'def': 0, 'hp': 0}
    passive_skills = parsed_actors[act['name']]['parsed_passive_skills']
    active_level = _floor_to_10(act['level'])
    active_effect = passive_skills.get(str(active_level), {})
    actor_category = parsed_actors[act['name']]['actor_category']
    actor_nation = parsed_actors[act['name']]['nation']
    if 'self' in active_effect.keys():
        print(f"  自身效果: {active_effect['self']}")
        for stat_key in ['atk', 'def', 'hp']:
            self_effects[stat_key] += active_effect['self'].get(stat_key, 0)
            
    for stat_key in ['atk', 'def', 'hp']:
        self_effects[stat_key] += effects['category'][actor_category].get(stat_key, 0)
        self_effects[stat_key] += effects['nation'][actor_nation].get(stat_key, 0)
    print(f"  總計效果: {self_effects}\n")    
    power = cal_power(self_effects, act['scarcity'], act['level'])
    print(f"  戰力: {power}\n")