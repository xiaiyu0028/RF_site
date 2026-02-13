import argparse
import csv
import itertools
import json
import math
import os
import sys
from collections import defaultdict, namedtuple
from heapq import heappush, heappop
from typing import Dict, List, Tuple

# Data structures
# Added level per actor (effective level after rarity cap or provided level) and weapon_type
Actor = namedtuple('Actor', ['name', 'scarcity', 'category', 'nation', 'level', 'weapon_type', 'self_effect', 'cat_buff', 'nat_buff'])


def floor_to_10(n: int) -> int:
    try:
        n = int(n)
    except Exception:
        return 0
    return n - (n % 10)


def load_parsed_actors(base_dir: str) -> Dict:
    """
    Load parsed actors JSON from likely locations.
    """
    candidates = [
        os.path.join(base_dir, 'parsed_actors_skill.json'),
        os.path.join(base_dir, 'cal_power', 'parsed_actors_skill.json')
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    raise FileNotFoundError('parsed_actors_skill.json not found in expected locations.')


def get_effect_at_level(effect_map: Dict, level: int) -> Dict:
    """
    Return effect dict at exact level if present, else empty dict.
    """
    return effect_map.get(str(level), {}) if effect_map else {}


def zero_stat():
    return {'atk': 0.0, 'def': 0.0, 'hp': 0.0}


def add_stats(a: Dict, b: Dict):
    a['atk'] += float(b.get('atk', 0) or 0)
    a['def'] += float(b.get('def', 0) or 0)
    a['hp'] += float(b.get('hp', 0) or 0)


def cal_power(effects: Dict[str, float], scarcity: str, level: int, weapon: str) -> float:
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
    # Apply rarity level caps (match calculate_power.py)
    if scarcity == "R":
        level = min(level, 90)
    elif scarcity == "SR":
        level = min(level, 160)
    elif scarcity == "SSR":
        level = min(level, 300)
    # Floor to nearest lower multiple of 10 when computing power
    # level = floor_to_10(level)

    multiplier = power_multiplier.get(scarcity, 1.0)
    weapon_mult = weapon_multiplier.get(weapon, 1.0)
    atk = float(effects.get('atk', 0) or 0)
    dff = float(effects.get('def', 0) or 0)
    hp = float(effects.get('hp', 0) or 0)
    total_power = level * multiplier * weapon_mult * (1 + (((1 + (atk/100 + hp/100)) * (1 + dff/100)) - 1) * 0.2) / 10 + 4
    return float(total_power)


def rarity_cap(scarcity: str) -> int:
    if scarcity == "R":
        return 90
    if scarcity == "SR":
        return 160
    if scarcity == "SSR":
        return 300
    return 160


def build_actors(parsed: Dict, level: int, rarity_filter: List[str]) -> List[Actor]:
    actors: List[Actor] = []
    for name, data in parsed.items():
        scarcity = data.get('scarcity')
        if rarity_filter and scarcity not in rarity_filter:
            continue
        actor_category = data.get('actor_category')
        actor_nation = data.get('nation')
        weapon_type = data.get('weapon_name')  # 直接從 JSON 讀取
        passive = data.get('parsed_passive_skills') or {}
        # Determine effective level: if level <= 0, use rarity cap; otherwise clamp to cap
        cap = rarity_cap(scarcity)
        effective_level = cap if (level is None or level <= 0) else min(level, cap)
        # Floor to multiple of 10 for passive lookup
        effective_level = floor_to_10(effective_level)
        effect = get_effect_at_level(passive, effective_level)
        self_effect = dict(effect.get('self') or {})
        # Normalize to floats and ensure keys exist
        se = {'atk': float(self_effect.get('atk', 0) or 0),
              'def': float(self_effect.get('def', 0) or 0),
              'hp': float(self_effect.get('hp', 0) or 0)}
        cat_buff = {}
        for cat, stats in (effect.get('category') or {}).items():
            cat_buff[cat] = {
                'atk': float(stats.get('atk', 0) or 0),
                'def': float(stats.get('def', 0) or 0),
                'hp': float(stats.get('hp', 0) or 0),
            }
        nat_buff = {}
        for nat, stats in (effect.get('nation') or {}).items():
            nat_buff[nat] = {
                'atk': float(stats.get('atk', 0) or 0),
                'def': float(stats.get('def', 0) or 0),
                'hp': float(stats.get('hp', 0) or 0),
            }
        actors.append(Actor(name=name, scarcity=scarcity, category=actor_category, nation=actor_nation,
                    level=effective_level, weapon_type=weapon_type, self_effect=se, cat_buff=cat_buff, nat_buff=nat_buff))
    return actors


def team_total_power(team: List[Actor], weapon: str) -> Tuple[float, List[float]]:
    # Aggregate team buffs by category and nation
    total_cat: Dict[str, Dict[str, float]] = defaultdict(zero_stat)
    total_nat: Dict[str, Dict[str, float]] = defaultdict(zero_stat)

    # Sum buffs contributed by each member
    for a in team:
        for cat, stats in a.cat_buff.items():
            sc = total_cat[cat]
            sc['atk'] += stats['atk']
            sc['def'] += stats['def']
            sc['hp'] += stats['hp']
        for nat, stats in a.nat_buff.items():
            sn = total_nat[nat]
            sn['atk'] += stats['atk']
            sn['def'] += stats['def']
            sn['hp'] += stats['hp']

    # Compute each actor's final effects and power
    member_powers: List[float] = []
    total = 0.0
    for a in team:
        eff = {'atk': a.self_effect['atk'], 'def': a.self_effect['def'], 'hp': a.self_effect['hp']}
        cat_eff = total_cat.get(a.category)
        if cat_eff:
            eff['atk'] += cat_eff['atk']
            eff['def'] += cat_eff['def']
            eff['hp'] += cat_eff['hp']
        nat_eff = total_nat.get(a.nation)
        if nat_eff:
            eff['atk'] += nat_eff['atk']
            eff['def'] += nat_eff['def']
            eff['hp'] += nat_eff['hp']
        p = cal_power(eff, a.scarcity, a.level, weapon)
        member_powers.append(p)
        total += p
    return total, member_powers


def main():
    parser = argparse.ArgumentParser(description='Find top-N 5-actor teams by total power.')
    parser.add_argument('--base-dir', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
                        help='Base RF_TW_mod directory (default: parent of this script).')
    parser.add_argument('--level', type=int, default=0, help='Level to evaluate; 0 uses rarity max cap (default: 0).')
    parser.add_argument('--weapon', type=str, default='原初', choices=['原初', '強化', '高等', '限定', '排名', '庚子'],
                        help='Weapon type multiplier (default: 原初).')
    parser.add_argument('--team-size', type=int, default=5, help='Team size (fixed to 5).')
    parser.add_argument('--results', type=int, default=100, help='Number of top results to return (default: 100).')
    parser.add_argument('--rarity', type=str, default=None,
                        help='Comma-separated list to filter rarity, e.g., SSR,SR (default: all).')
    parser.add_argument('--output', type=str, default='top_teams.json', help='Output JSON file.')
    parser.add_argument('--csv', type=str, default=None, help='Optional CSV output file (e.g., top_teams.csv).')
    parser.add_argument('--limit-weapon-types', action='store_true', default=True,
                        help='Enforce at most one of {匕首, 重擊, 刀劍} per team (default: enabled).')
    parser.add_argument('--ignore-red-limits', action='store_true', default=False, help="不考慮紅軍限定角 渤雍跟趙彤")

    args = parser.parse_args()

    if args.team_size != 5:
        print('Warning: team size is expected to be 5; proceeding with given value.', file=sys.stderr)

    rarity_filter = None
    if args.rarity:
        rarity_filter = [r.strip() for r in args.rarity.split(',') if r.strip()]

    parsed = load_parsed_actors(args.base_dir)
    actors = build_actors(parsed, args.level, rarity_filter)
    if not actors:
        print('No actors loaded after filtering.', file=sys.stderr)
        sys.exit(1)

    # Brute force over ALL actors (no candidate pre-filtering)
    candidates = actors
    print(f'Brute force using all {len(candidates)} actors to evaluate combinations.')

    # Evaluate all combinations among candidates
    k = args.team_size
    total_combos = math.comb(len(candidates), k) if hasattr(math, 'comb') else 0
    print(f'Evaluating up to {total_combos} combinations... (this may take a long time)')

    # Maintain a min-heap of fixed size for top results
    heap: List[Tuple[float, Tuple[str, ...], List[float]]] = []

    checked = 0
    restricted_set = {'匕首', '重擊', '刀劍'}
    for team in itertools.combinations(candidates, k):
        if args.limit_weapon_types:
            cnt = sum(1 for a in team if a.weapon_type in restricted_set)
            if cnt > 1:
                continue
        if args.ignore_red_limits and any(a.name in ["渤雍", "趙彤"] for a in team):
            continue  # Skip red army limits
        total, member_powers = team_total_power(list(team), args.weapon)
        names = tuple(a.name for a in team)
        if len(heap) < args.results:
            heappush(heap, (total, names, member_powers))
        else:
            if total > heap[0][0]:
                heappop(heap)
                heappush(heap, (total, names, member_powers))
        checked += 1
        if checked % 100000 == 0:
            print(f'Checked {checked} teams... best so far: {max(heap)[0]:.2f}' if heap else f'Checked {checked} teams...')

    # Extract and sort results descending
    results = sorted(heap, key=lambda x: x[0], reverse=True)

    output = []
    for rank, (total, names, member_powers) in enumerate(results, start=1):
        team_info = {
            'rank': rank,
            'total_power': round(total, 2),
            'weapon': args.weapon,
            'level': args.level if args.level and args.level > 0 else 'auto-cap',
            'members': []
        }
        for i, name in enumerate(names):
            a = next(x for x in candidates if x.name == name)
            team_info['members'].append({
                'name': name,
                'scarcity': a.scarcity,
                'category': a.category,
                'nation': a.nation,
                'weapon_type': a.weapon_type,
                'level': a.level,
                'power': round(member_powers[i], 2)
            })
        output.append(team_info)

    out_path = os.path.join(os.getcwd(), args.output)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'Wrote top {len(output)} teams to {out_path}')

    # Generate CSV if requested
    if args.csv:
        csv_path = os.path.join(os.getcwd(), args.csv)
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header row
            header = ['排名', '總戰力', '武器']
            # Add columns for 5 actors (name and power)
            for i in range(1, 6):
                header.extend([f'角色{i}', f'角色{i}戰力'])
            writer.writerow(header)
            
            # Data rows
            for team_info in output:
                row = [
                    team_info['rank'],
                    team_info['total_power'],
                    team_info['weapon']
                ]
                # Add each member's name and power
                for member in team_info['members']:
                    row.extend([member['name'], member['power']])
                writer.writerow(row)
        
        print(f'Wrote CSV output to {csv_path}')


if __name__ == '__main__':
    main()
