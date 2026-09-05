"""由 city_sites.json + cities.json 產生 city ↔ site 對照表。

輸出 return_data_example/city_site_index.json，內含：
  cities  city_id -> 城市資訊 + 該城 site 清單（正向表）
  sites   site_id -> 該 site 所屬城市 + 地點欄位（反查表）

純本機轉檔，不連線遊戲 API。
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class BuildError(RuntimeError):
    """來源資料不足以產生對照表時拋出。"""


# 保留在對照表裡的地點欄位（其餘如 emblem、workstation 對查表無用）
SITE_FIELDS = (
    "position",
    "reference_type",
    "ws_name",
    "prop_name",
    "side_label",
    "religious",
    "same_nation",
    "state",
    "energy_charge",
)


def load_json(path: Path) -> Any:
    if not path.exists():
        raise BuildError(f"找不到來源檔案：{path}")
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def build_index(city_sites: dict[str, Any], cities_payload: dict[str, Any]) -> dict[str, Any]:
    sites_by_city = city_sites.get("sites")
    if not isinstance(sites_by_city, dict) or not sites_by_city:
        raise BuildError("city_sites.json 沒有 sites 內容。")

    cities = cities_payload.get("cities")
    if not isinstance(cities, list) or not cities:
        raise BuildError("cities.json 沒有 cities 內容。")

    city_meta = {str(city["id"]): city for city in cities if isinstance(city, dict) and "id" in city}

    city_table: dict[str, Any] = {}
    site_table: dict[str, Any] = {}
    duplicate_site_ids: list[int] = []
    reference_types: Counter[str] = Counter()

    for city_id in sorted(sites_by_city, key=int):
        entry = sites_by_city[city_id]
        if not isinstance(entry, dict):
            continue
        meta = city_meta.get(city_id, {})
        nation = meta.get("control_nation") or {}
        chapter = meta.get("chapter") or {}
        city_row = {
            "city_id": int(city_id),
            "title": meta.get("title"),
            "nation_id": nation.get("id"),
            "nation_name": nation.get("name"),
            "chapter_name": chapter.get("name"),
            "status": meta.get("status"),
            "capital": meta.get("capital"),
            "workstation_count": entry.get("workstation_count"),
            "site_ids": [],
            "sites": [],
        }

        for site in entry.get("sites") or []:
            if not isinstance(site, dict) or "id" not in site:
                continue
            site_id = int(site["id"])
            row = {"site_id": site_id, **{key: site.get(key) for key in SITE_FIELDS}}
            city_row["site_ids"].append(site_id)
            city_row["sites"].append(row)
            reference_types[str(site.get("reference_type"))] += 1

            key = str(site_id)
            if key in site_table:
                duplicate_site_ids.append(site_id)
                continue
            site_table[key] = {
                **row,
                "city_id": int(city_id),
                "city_title": city_row["title"],
                "nation_name": city_row["nation_name"],
            }

        city_table[city_id] = city_row

    missing_cities = sorted((int(cid) for cid in city_meta if cid not in city_table))

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": {
            "city_sites": "return_data_example/city_sites.json",
            "cities": "return_data_example/cities.json",
            "mode": city_sites.get("mode"),
            "requested": city_sites.get("requested"),
            "failed": city_sites.get("failed"),
        },
        "stats": {
            "city_count": len(city_table),
            "site_count": len(site_table),
            "cities_without_sites": sum(1 for row in city_table.values() if not row["site_ids"]),
            "cities_missing_from_source": missing_cities,
            "duplicate_site_ids": sorted(set(duplicate_site_ids)),
            "reference_types": dict(sorted(reference_types.items())),
        },
        "cities": city_table,
        "sites": site_table,
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temp_path = Path(file.name)
    temp_path.replace(path)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="產生 city ↔ site 對照表")
    parser.add_argument("--data-root", type=Path, default=root / "return_data_example")
    parser.add_argument("--output", type=Path, default=None, help="預設寫入 <data-root>/city_site_index.json")
    parser.add_argument("--dry-run", action="store_true", help="只驗證與統計，不寫檔")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_root: Path = args.data_root
    output: Path = args.output or data_root / "city_site_index.json"

    try:
        index = build_index(
            load_json(data_root / "city_sites.json"),
            load_json(data_root / "cities.json"),
        )
    except BuildError as error:
        print(f"錯誤：{error}")
        return 1

    stats = index["stats"]
    print(f"城市 {stats['city_count']} 座、地點 {stats['site_count']} 個")
    print(f"無地點城市 {stats['cities_without_sites']} 座；來源未涵蓋 {len(stats['cities_missing_from_source'])} 座")
    if stats["duplicate_site_ids"]:
        print(f"警告：site id 重複 {stats['duplicate_site_ids']}")
    print(f"地點類型：{stats['reference_types']}")

    if args.dry_run:
        print("dry-run：未寫入檔案")
        return 0

    write_json_atomic(output, index)
    print(f"已寫入 {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
