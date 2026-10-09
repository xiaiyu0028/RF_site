"""比對新舊資料快照，產生首頁「最近更新」使用的 changelog.json。

國策 / 城鎮 / 城內地點的比對由 update_game_data.py 在寫檔前呼叫；
角色的比對則在 notebook 產出 unique_actors.json 後手動執行：

    python scripts/changelog.py actors            # 與 git HEAD 版本比對並寫入
    python scripts/changelog.py actors --dry-run  # 只印出差異
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = ROOT / "return_data_example" / "changelog.json"
ACTORS_PATH = ROOT / "cal_power" / "unique_actors.json"
MAX_ENTRIES = 30
MAX_DETAILS = 12

SITE_TYPE_LABELS = {"Workstation": "工作站", "Visit": "拜訪", "Explore": "探索", "Access": "通道"}


def today() -> date:
    return datetime.now().astimezone().date()


def load_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def clean_text(value: Any) -> str:
    text = re.sub(r"<br\s*/?>", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def make_item(
    category: str, kind: str, title: str, details: list[str] | None = None, name: str | None = None
) -> dict[str, Any]:
    details = details or []
    if len(details) > MAX_DETAILS:
        details = details[:MAX_DETAILS] + [f"…另有 {len(details) - MAX_DETAILS} 項"]
    item = {"category": category, "kind": kind, "title": title, "details": details}
    if name:
        item["name"] = name  # 首頁用來連到角色 / 城鎮頁面
    return item


# ---------- 國策 ----------

def strategy_names(nations: dict[str, Any]) -> tuple[dict[int, str], dict[int, str]]:
    diplomatic = {item["id"]: item["name"] for item in nations.get("diplomatic_strategies") or [] if item}
    general: dict[int, str] = {}
    for group in nations.get("general_strategies") or []:
        if group.get("id") is not None:
            general[group["id"]] = group["name"]
        for route in group.get("general_strategy_routes") or []:
            for strategy in route.values():
                if isinstance(strategy, dict) and strategy.get("id") is not None:
                    general[strategy["id"]] = strategy["name"]
    return diplomatic, general


def diff_nations(old: Any, new: dict[str, Any], on: date) -> list[dict[str, Any]]:
    if not isinstance(old, dict):
        return []
    diplomatic, general = strategy_names(new)
    old_diplomatic, old_general = strategy_names(old)
    diplomatic = {**old_diplomatic, **diplomatic}
    general = {**old_general, **general}
    old_by_id = {item["id"]: item for item in old.get("nations") or []}

    details = []
    for nation in new.get("nations") or []:
        before = old_by_id.get(nation["id"])
        if not before:
            continue
        changes = []
        old_dip, new_dip = before.get("diplomatic_strategy_id"), nation.get("diplomatic_strategy_id")
        if old_dip != new_dip:
            changes.append(f"外交「{diplomatic.get(old_dip, '無')}」→「{diplomatic.get(new_dip, '無')}」")
        old_set = set(before.get("general_strategy_ids") or [])
        new_set = set(nation.get("general_strategy_ids") or [])
        added = [general.get(i, str(i)) for i in sorted(new_set - old_set)]
        removed = [general.get(i, str(i)) for i in sorted(old_set - new_set)]
        if added:
            changes.append("新增 " + "、".join(added))
        if removed:
            changes.append("移除 " + "、".join(removed))
        if changes:
            details.append(f"{nation['name']}：" + "；".join(changes))

    if not details:
        return []
    return [make_item("nation", "updated", f"更新本週（{on.month}/{on.day}）國策", details)]


# ---------- 城鎮與城內地點 ----------

def site_label(site: dict[str, Any]) -> str:
    kind = site.get("reference_type")
    if kind == "Workstation":
        name = site.get("ws_name") or "工作站"
        side = site.get("side_label")
        return f"{side}「{name}」" if side and side != "工作站" else f"工作站「{name}」"
    return f"{SITE_TYPE_LABELS.get(kind, kind or '地點')}「{site.get('name') or '—'}」"


def site_keys(city_sites: dict[str, Any]) -> dict[tuple[Any, Any], dict[str, Any]]:
    return {(site.get("reference_type"), site.get("id")): site for site in city_sites.get("sites") or []}


def diff_cities(
    old_cities: Any,
    new_cities: dict[str, Any],
    old_sites: Any,
    new_sites: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(old_cities, dict):
        return []
    items = []
    old_ids = {city["id"] for city in old_cities.get("cities") or []}
    names = {str(city["id"]): city["name"] for city in new_cities.get("cities") or []}
    new_site_map = (new_sites or {}).get("sites") or {}

    for city in new_cities.get("cities") or []:
        if city["id"] in old_ids:
            continue
        details = []
        chapter = (city.get("chapter") or {}).get("name")
        if chapter:
            details.append(f"章節：{chapter}")
        details += [site_label(site) for site in (new_site_map.get(str(city["id"])) or {}).get("sites") or []]
        items.append(make_item("city", "new", f"新城鎮：{city['name']}", details, city["name"]))

    # 只比對新舊兩次都有抓到的城市，避免上次查詢失敗的城市被誤判成整批新增
    old_site_map = (old_sites or {}).get("sites") if isinstance(old_sites, dict) else None
    if not old_site_map or not new_site_map:
        return items
    for city_id, city_sites in new_site_map.items():
        before = old_site_map.get(city_id)
        if not before:
            continue
        old_keys = site_keys(before)
        added = [site for key, site in site_keys(city_sites).items() if key not in old_keys]
        if added:
            city_name = names.get(city_id, f"城市 {city_id}")
            items.append(make_item("site", "new", f"{city_name} 新增地點", [site_label(site) for site in added], city_name))
    return items


# ---------- 角色 ----------

def wears_outfit(actor: dict[str, Any]) -> bool:
    """角色是否穿著 ★ 造型。穿著時天賦與被動數值會 ×1.2，不能代表角色本身的數值。

    基本造型是 outfits 裡與角色同名的那一個；目前立繪（gif_image）不是它就代表穿著其他造型。
    """
    name = (actor.get("actor_prototype") or {}).get("name") or actor.get("name")
    base = next((outfit for outfit in actor.get("outfits") or [] if outfit.get("name") == name), None)
    return bool(base and actor.get("gif_image") and actor["gif_image"] != base.get("image"))


def actor_profile(actor: dict[str, Any]) -> dict[str, Any]:
    proto = actor.get("actor_prototype") or {}
    return {
        "wears_outfit": wears_outfit(actor),
        "name": proto.get("name") or actor.get("name"),
        "scarcity": actor.get("scarcity"),
        "nation": actor.get("nation"),
        "category": (proto.get("actor_category") or {}).get("name"),
        "offense_base_value": proto.get("offense_base_value"),
        "offense_elevation_value": proto.get("offense_elevation_value"),
        "blood_base_value": proto.get("blood_base_value"),
        "blood_elevation_value": proto.get("blood_elevation_value"),
        "talent_1": clean_text(proto.get("talent_1")),
        "talent_2": clean_text(proto.get("talent_2")),
        "visitable_city": (proto.get("visitable_city") or {}).get("name"),
        "active_skills": [
            {
                "name": skill.get("name"),
                "level": skill.get("level"),
                "point": skill.get("activate_skill_point"),
                "description": clean_text(skill.get("description")),
            }
            for skill in proto.get("active_skills") or []
        ],
        "passive_skills": {
            str(skill.get("level")): clean_text(skill.get("description"))
            for skill in actor.get("passive_skills") or []
        },
    }


ACTOR_FIELD_LABELS = {
    "name": "名稱",
    "scarcity": "稀有度",
    "nation": "陣營",
    "category": "職業",
    "offense_base_value": "ATK 基礎值",
    "offense_elevation_value": "ATK 成長值",
    "blood_base_value": "HP 基礎值",
    "blood_elevation_value": "HP 成長值",
    "talent_1": "天賦 1",
    "talent_2": "天賦 2",
    "visitable_city": "可拜訪城市",
}


def diff_actor(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    changes = []
    # 只有一邊穿著造型時，天賦 / 被動的差異是造型加成造成的，不算角色調整
    comparable = before["wears_outfit"] == after["wears_outfit"]
    for field, label in ACTOR_FIELD_LABELS.items():
        if field in ("talent_1", "talent_2") and not comparable:
            continue
        if before[field] != after[field]:
            changes.append(f"{label}：{before[field] or '無'} → {after[field] or '無'}")

    old_skills = {(skill["name"], skill["level"]): skill for skill in before["active_skills"]}
    new_skills = {(skill["name"], skill["level"]): skill for skill in after["active_skills"]}
    for key, skill in new_skills.items():
        title = f"主動技「{skill['name']}」{skill['level'] or ''}"
        old = old_skills.get(key)
        if not old:
            changes.append(f"新增{title}：{skill['description']}")
            continue
        if old["description"] != skill["description"]:
            changes.append(f"{title}：{old['description']} → {skill['description']}")
        if old["point"] != skill["point"]:
            changes.append(f"{title} 技能點：{old['point']} → {skill['point']}")
    for key, skill in old_skills.items():
        if key not in new_skills:
            changes.append(f"移除主動技「{skill['name']}」{skill['level'] or ''}")

    if not comparable:
        return changes
    levels = sorted(set(before["passive_skills"]) | set(after["passive_skills"]), key=lambda v: int(v) if v.isdigit() else 0)
    for level in levels:
        old, new = before["passive_skills"].get(level), after["passive_skills"].get(level)
        if old != new:
            changes.append(f"被動 Lv{level}：{old or '無'} → {new or '無'}")
    return changes


def actor_map(data: Any) -> dict[Any, dict[str, Any]]:
    actors = data if isinstance(data, list) else list((data or {}).values())
    result = {}
    for actor in actors:
        key = (actor.get("actor_prototype") or {}).get("id") or actor.get("name")
        if key is not None:
            result[key] = actor_profile(actor)
    return result


def diff_actors(old: Any, new: Any) -> list[dict[str, Any]]:
    old_map, new_map = actor_map(old), actor_map(new)
    items = []
    for key, actor in new_map.items():
        before = old_map.get(key)
        if before is None:
            info = " / ".join(filter(None, [actor["scarcity"], actor["nation"], actor["category"]]))
            details = [info] if info else []
            details += [f"天賦：{t}" for t in (actor["talent_1"], actor["talent_2"]) if t]
            items.append(make_item("actor", "new", f"新角色：{actor['name']}", details, actor["name"]))
            continue
        changes = diff_actor(before, actor)
        if changes:
            items.append(make_item("actor", "changed", f"角色調整：{actor['name']}", changes, actor["name"]))
    return items


# ---------- changelog.json ----------

def record_changes(items: list[dict[str, Any]], on: date | None = None, path: Path = CHANGELOG_PATH) -> bool:
    """把變動併入當天的紀錄；同一天重跑時以標題去重，後寫的覆蓋先寫的。"""
    if not items:
        return False
    on_text = (on or today()).isoformat()
    data = load_json(path)
    entries = data.get("entries", []) if isinstance(data, dict) else []
    entry = next((e for e in entries if e.get("date") == on_text), None)
    if entry is None:
        entry = {"date": on_text, "items": []}
        entries.append(entry)
    titles = {item["title"] for item in items}
    entry["items"] = [item for item in entry.get("items", []) if item.get("title") not in titles] + items
    entries.sort(key=lambda e: e.get("date", ""), reverse=True)

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as file:
        json.dump({"entries": entries[:MAX_ENTRIES]}, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temp_path = Path(file.name)
    temp_path.replace(path)
    return True


def print_items(items: list[dict[str, Any]]) -> None:
    for item in items:
        print(f"- {item['title']}")
        for detail in item["details"]:
            print(f"    {detail}")


def git_show(revision: str, relative_path: str) -> Any:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative_path}"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise SystemExit(f"無法讀取 {revision}:{relative_path}：{result.stderr.strip()}")
    return json.loads(result.stdout)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="產生首頁「最近更新」紀錄")
    sub = parser.add_subparsers(dest="command", required=True)
    actors = sub.add_parser("actors", help="比對角色資料（unique_actors.json）")
    actors.add_argument("--base", default="HEAD", help="比對基準的 git revision（預設 HEAD）")
    actors.add_argument("--dry-run", action="store_true", help="只印出差異，不寫入 changelog.json")
    args = parser.parse_args()

    old = git_show(args.base, "cal_power/unique_actors.json")
    new = load_json(ACTORS_PATH)
    if new is None:
        raise SystemExit(f"無法讀取 {ACTORS_PATH}")
    items = diff_actors(old, new)
    if not items:
        print("角色資料沒有變動。")
        return 0
    print_items(items)
    if not args.dry_run:
        record_changes(items)
        print(f"已寫入 {CHANGELOG_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
