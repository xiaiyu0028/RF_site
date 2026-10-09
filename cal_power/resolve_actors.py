"""把 actors.jsonl 解析成網站使用的角色資料（取代 resolve_actors.ipynb）。

    python cal_power/resolve_actors.py             # 解析並寫入，同時記錄角色變動到首頁 changelog
    python cal_power/resolve_actors.py --dry-run   # 只解析並列出角色變動，不寫任何檔案

產出（皆在 cal_power/）：
- parsed_actors.json        基本資料 + 被動技能原文
- parsed_actors_skill.json  多一層 parsed_passive_skills（依等級拆出 self / category / nation 的 atk/def/hp）
- unique_actors.json        去重後的原始角色資料
- visit_plots.json          角色可拜訪地點

同名角色一律以最新資料為準，順序維持第一次出現的位置。run_all_get_actors.py 每次會清空
actors.jsonl，所以會以現有的 unique_actors.json 為底再覆蓋，沒有帳號持有的角色不會因此消失。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "scripts"))

import changelog  # noqa: E402

PASSIVE_SCOPES = {"自身": "self", "型": "category", "陣營": "nation"}
STAT_KEYS = {"攻擊力": "atk", "受到傷害": "def", "血量": "hp"}


def load_actor_lines(path: Path) -> list[dict[str, Any]]:
    actors = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                actors.extend(json.loads(line)[4]["response"]["actors"])
    return actors


def actor_key(actor: dict[str, Any]) -> tuple[str, Any]:
    proto = actor.get("actor_prototype")
    if isinstance(proto, dict) and proto.get("name"):
        return ("name", proto["name"])
    if actor.get("name"):
        return ("name", actor["name"])
    if actor.get("id") is not None:
        return ("id", actor["id"])
    return ("raw", json.dumps(actor, ensure_ascii=False, sort_keys=True))


def dedupe_latest(actors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, Any], dict[str, Any]] = {}
    for actor in actors:
        latest[actor_key(actor)] = actor
    return list(latest.values())


def build_parsed_actors(actors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    parsed = {}
    for actor in actors:
        proto = actor["actor_prototype"]
        parsed[proto["name"]] = {
            "name": proto["name"],
            "passive_skills": actor.get("passive_skills", []),
            "scarcity": actor.get("scarcity"),
            "nation": actor.get("nation"),
            "actor_category": (proto.get("actor_category") or {}).get("name"),
            "weapon_name": actor.get("no_weapon_name"),
        }
    return parsed


def effect_value(effect: str, stat_word: str) -> int:
    """「臺灣陣營成員攻擊力+5%」→ 5；「自身受到傷害-10%」→ 10。"""
    if "+" in effect:
        split_key = "+"
    elif "-" in effect:
        split_key = "-"
    else:
        split_key = stat_word
    return int(effect.split(split_key)[-1].strip()[:-1])


def parse_passive_description(description: str, categories: list[str], nations: list[str]) -> dict[str, Any]:
    result = {
        "self": {"atk": 0, "def": 0, "hp": 0},
        "category": {category: {"atk": 0, "def": 0, "hp": 0} for category in categories},
        "nation": {nation: {"atk": 0, "def": 0, "hp": 0} for nation in nations},
    }
    # 描述是多個效果直接串接，每個效果都以 % 結尾
    effects = [part.strip() + "%" for part in description.split("%") if part.strip()]
    for effect in effects:
        for scope_word, scope in PASSIVE_SCOPES.items():
            if scope_word not in effect:
                continue
            if scope == "self":
                targets = [result["self"]]
            else:
                names = categories if scope == "category" else nations
                targets = [result[scope][name] for name in names if name in effect]
            for stat_word, stat in STAT_KEYS.items():
                if stat_word in effect:
                    for target in targets:
                        target[stat] = effect_value(effect, stat_word)
    return result


def add_parsed_passive_skills(parsed: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    # 排序後輸出才穩定，不會每次重跑都讓 key 順序亂跳
    categories = sorted({actor["actor_category"] for actor in parsed.values()}, key=str)
    nations = sorted({actor["nation"] for actor in parsed.values()}, key=str)
    result = {}
    for name, actor in parsed.items():
        skills = {
            str(skill.get("level")): parse_passive_description(skill.get("description", ""), categories, nations)
            for skill in actor["passive_skills"]
        }
        result[name] = {**actor, "parsed_passive_skills": skills}
    return result


def build_visit_plots(actors: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    visit_plots, missing = {}, []
    for actor in actors:
        proto = actor.get("actor_prototype") or {}
        name = proto.get("name") or actor.get("name")
        if not name:
            continue
        has_plot = proto.get("has_visit_plot")
        city_id = actor.get("visitable_city_id") or proto.get("visitable_city_id")
        city = actor.get("visitable_city") or proto.get("visitable_city")
        if has_plot is None and city_id is None and city is None:
            missing.append(name)
            continue
        visit_plots[name] = {
            "name": name,
            "has_visit_plot": bool(has_plot),
            "visitable_city_id": city_id,
            "visitable_city": city.get("name") if isinstance(city, dict) else city,
            "relation_level_cap": proto.get("relation_level_cap"),
        }
    return visit_plots, missing


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="解析 actors.jsonl，產生網站用的角色資料")
    parser.add_argument("--input", type=Path, default=SCRIPT_DIR / "actors.jsonl", help="角色原始資料（預設 cal_power/actors.jsonl）")
    parser.add_argument("--output-dir", type=Path, default=SCRIPT_DIR, help="輸出資料夾（預設 cal_power/）")
    parser.add_argument("--dry-run", action="store_true", help="只解析並列出角色變動，不寫任何檔案")
    parser.add_argument("--no-changelog", action="store_true", help="不把角色變動記錄到首頁 changelog.json")
    parser.add_argument(
        "--drop-missing",
        action="store_true",
        help="只輸出這次有抓到的角色（預設會保留舊 unique_actors.json 裡本次沒抓到的角色）",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if not args.input.exists():
        print(f"找不到 {args.input}，請先執行 run_all_get_actors.py。")
        return 1

    raw_actors = load_actor_lines(args.input)
    if not raw_actors:
        print(f"{args.input.name} 沒有角色資料，已取消。")
        return 1
    fetched = dedupe_latest(raw_actors)
    print(f"讀取 {len(raw_actors)} 筆，去重後 {len(fetched)} 名角色。")

    # actors.jsonl 每次重抓會清空，沒有任何帳號持有的角色就不會出現；
    # 以現有 unique_actors.json 為底，本次抓到的覆蓋上去，避免角色從網站消失
    unique_path = args.output_dir / "unique_actors.json"
    previous = changelog.load_json(unique_path) if unique_path.exists() else None
    previous = previous if isinstance(previous, list) else []
    unique_actors = fetched
    if previous and not args.drop_missing:
        unique_actors = dedupe_latest(previous + fetched)
        fetched_keys = {actor_key(actor) for actor in fetched}
        kept = [actor_key(actor)[1] for actor in previous if actor_key(actor) not in fetched_keys]
        if kept:
            print(f"本次沒抓到、沿用舊資料的角色 {len(kept)} 名：{'、'.join(map(str, kept))}")

    parsed_actors = build_parsed_actors(unique_actors)
    parsed_skill = add_parsed_passive_skills(parsed_actors)
    visit_plots, missing = build_visit_plots(unique_actors)
    print(f"輸出 {len(unique_actors)} 名角色；取得拜訪資料：{len(visit_plots)} 名")
    if missing:
        print(f"缺少拜訪欄位（需以 3.0 API 重抓）：{len(missing)} 名，例如 {missing[:5]}")

    # 寫檔前先和現有的 unique_actors.json 比對，記錄給首頁「最近更新」
    changes = changelog.diff_actors(previous, unique_actors) if previous else []
    if changes:
        print(f"\n角色變動 {len(changes)} 項：")
        changelog.print_items(changes)
    else:
        print("\n角色資料沒有變動。")

    if args.dry_run:
        return 0

    write_json(args.output_dir / "parsed_actors.json", parsed_actors)
    write_json(args.output_dir / "parsed_actors_skill.json", parsed_skill)
    write_json(unique_path, unique_actors)
    write_json(args.output_dir / "visit_plots.json", visit_plots)
    print(f"\n已寫入 {args.output_dir}：parsed_actors.json、parsed_actors_skill.json、unique_actors.json、visit_plots.json")

    if changes and not args.no_changelog:
        changelog.record_changes(changes)
        print(f"已記錄到 {changelog.CHANGELOG_PATH.relative_to(changelog.ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
