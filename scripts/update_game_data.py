"""Fetch the public nation and city snapshots used by the static site.

Credentials are supplied only through environment variables.  The script never
prints credentials, user IDs, or session tokens so it is safe to run in CI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import websockets

API_BASE = "https://api.komisureiya.com/api"
WS_BASE = "wss://api.komisureiya.com/socket/websocket"
APP_VERSION = os.environ.get("RF_APP_VERSION", "3.00")
APP_KEY = os.environ.get("RF_APP_KEY", "t9cTpsbSCYcJgsrrC")


class UpdateError(RuntimeError):
    """Raised when the remote response cannot safely replace local data."""


def login(email: str, password: str, timeout: int) -> tuple[str, str]:
    response = requests.post(
        f"{API_BASE}/users/log_in",
        data={
            "user[email]": email,
            "user[password]": password,
            "locale": "zh_TW",
            "key": APP_KEY,
            "app_version": APP_VERSION,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise UpdateError("遊戲登入回應格式不正確。")
    data = payload.get("data")
    if payload.get("status") != "ok" or not isinstance(data, dict):
        raise UpdateError("遊戲登入失敗，請確認 CI Secrets 與帳號狀態。")
    token, user_id = data.get("user_token"), data.get("user_id")
    if not token or not user_id:
        raise UpdateError("登入回應缺少建立資料連線所需的資訊。")
    return str(token), str(user_id)


async def request_snapshot(
    token: str,
    user_id: str,
    timeout: int,
    city_sites_mode: str = "off",
    city_sites_delay: float = 0.35,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    ws_url = f"{WS_BASE}?userToken={quote(token, safe='')}&locale=zh_TW&vsn=2.0.0"
    topic = f"player:{user_id}"
    async with websockets.connect(
        ws_url,
        ping_interval=15,
        ping_timeout=30,
        close_timeout=timeout,
        max_size=10 * 1024 * 1024,
        max_queue=32,
    ) as websocket:

        async def wait_for_reply(ref: str) -> dict[str, Any]:
            while True:
                raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                message = json.loads(raw)
                if not (isinstance(message, list) and len(message) >= 5 and str(message[1]) == ref and message[3] == "phx_reply"):
                    continue
                reply = message[4]
                if not isinstance(reply, dict) or reply.get("status") != "ok" or not isinstance(reply.get("response"), dict):
                    raise UpdateError("遊戲資料連線請求未成功。")
                return reply["response"]

        await websocket.send(json.dumps(["6", "6", topic, "phx_join", {"fake": "ChannelPlayer", "fake2": 1}]))
        await wait_for_reply("6")

        async def request(event: str, payload: dict[str, Any], ref: str) -> dict[str, Any]:
            await websocket.send(json.dumps(["6", ref, topic, event, payload]))
            return await wait_for_reply(ref)

        nations = await request("nations", {"body": ""}, "14")
        cities = await request("cities", {"body": ""}, "15")

        city_sites: dict[str, Any] | None = None
        if city_sites_mode != "off":
            city_sites = await request_city_sites(
                request,
                cities.get("cities") or [],
                city_sites_mode,
                city_sites_delay,
            )

        return nations, cities, city_sites


async def request_city_sites(
    request: Any,
    city_items: list[dict[str, Any]],
    mode: str,
    delay: float,
) -> dict[str, Any]:
    """逐城查詢 city_sites。預設只抓可進入的城市，避免 271 次呼叫。"""
    if mode == "all":
        targets = [city for city in city_items if isinstance(city, dict) and city.get("id") is not None]
    else:
        targets = [
            city
            for city in city_items
            if isinstance(city, dict)
            and city.get("id") is not None
            and (city.get("movable") or city.get("visitable"))
        ]

    sites: dict[str, Any] = {}
    failed: list[int] = []
    ref = 100
    for index, city in enumerate(targets, start=1):
        city_id = city["id"]
        ref += 1
        try:
            response = await request("city_sites", {"city_id": city_id}, str(ref))
        except (UpdateError, asyncio.TimeoutError, json.JSONDecodeError):
            failed.append(city_id)
            continue
        sites[str(city_id)] = response
        if index % 25 == 0:
            print(f"  城內地點進度：{index} / {len(targets)}")
        if delay > 0:
            await asyncio.sleep(delay)

    if failed:
        print(f"  有 {len(failed)} 座城市的地點查詢失敗，已略過。")

    return {"mode": mode, "requested": len(targets), "failed": failed, "sites": sites}


def validate_snapshots(nations: dict[str, Any], cities: dict[str, Any]) -> None:
    nation_items = nations.get("nations")
    city_items = cities.get("cities")
    if not isinstance(nation_items, list) or len(nation_items) < 3:
        raise UpdateError("國策資料格式不完整，已取消更新。")
    if not isinstance(nations.get("diplomatic_strategies"), list) or not isinstance(nations.get("general_strategies"), list):
        raise UpdateError("國策策略資料格式不完整，已取消更新。")
    if not isinstance(city_items, list) or len(city_items) < 10:
        raise UpdateError("城鎮資料格式不完整，已取消更新。")
    if not all(
        isinstance(item, dict) and item.get("id") is not None and item.get("name")
        for item in nation_items
    ):
        raise UpdateError("國策資料缺少必要欄位，已取消更新。")
    if not all(
        isinstance(item, dict) and item.get("id") is not None and item.get("name")
        for item in city_items
    ):
        raise UpdateError("城鎮資料缺少必要欄位，已取消更新。")


def validate_city_sites(city_sites: dict[str, Any]) -> None:
    sites = city_sites.get("sites")
    if not isinstance(sites, dict) or not sites:
        raise UpdateError("城內地點資料為空，已取消更新。")
    if not all(isinstance(value, dict) for value in sites.values()):
        raise UpdateError("城內地點資料格式不完整，已取消更新。")
    requested = city_sites.get("requested") or 0
    if requested and len(sites) < requested * 0.5:
        raise UpdateError("城內地點資料缺漏過半，已取消更新。")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
        temp_path = Path(file.name)
    temp_path.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新 RF 國策與城鎮公開資料")
    parser.add_argument("--dry-run", action="store_true", help="只抓取與驗證資料，不寫入檔案")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP 與 WebSocket 單次逾時秒數")
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--city-sites",
        choices=("off", "visitable", "all"),
        default="off",
        help="是否逐城抓取城內地點：off 不抓；visitable 只抓可進入城市；all 抓全部（呼叫次數最多）",
    )
    parser.add_argument(
        "--city-sites-delay",
        type=float,
        default=0.35,
        help="逐城查詢之間的間隔秒數，避免對伺服器造成瞬間壓力",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    email = os.environ.get("RF_EMAIL") or os.environ.get("RF_ACCOUNT_EMAIL")
    password = os.environ.get("RF_PASSWORD") or os.environ.get("RF_ACCOUNT_PASSWORD")
    if not email or not password:
        raise UpdateError("缺少 RF_EMAIL 或 RF_PASSWORD 環境變數。")

    token, user_id = login(email, password, args.timeout)
    nations, cities, city_sites = asyncio.run(
        request_snapshot(
            token,
            user_id,
            args.timeout,
            city_sites_mode=args.city_sites,
            city_sites_delay=args.city_sites_delay,
        )
    )
    validate_snapshots(nations, cities)
    if city_sites is not None:
        validate_city_sites(city_sites)

    site_summary = f"、{len(city_sites['sites'])} 座城市的地點" if city_sites is not None else ""

    if args.dry_run:
        print(f"驗證成功：{len(nations['nations'])} 個陣營、{len(cities['cities'])} 個城鎮{site_summary}。")
        return 0

    updated_at = datetime.now(UTC).isoformat()
    root = args.output_root
    write_json_atomic(root / "return_data_example" / "nation.json", nations)
    write_json_atomic(root / "return_data_example" / "cities.json", {"cities": cities["cities"]})

    datasets = {"nations": "available", "cities": "available"}
    counts = {"nations": len(nations["nations"]), "cities": len(cities["cities"])}
    if city_sites is not None:
        write_json_atomic(root / "return_data_example" / "city_sites.json", city_sites)
        datasets["city_sites"] = "available"
        counts["city_sites"] = len(city_sites["sites"])

    write_json_atomic(
        root / "return_data_example" / "update_metadata.json",
        {"updated_at": updated_at, "datasets": datasets, "counts": counts},
    )
    print(f"更新完成：{len(nations['nations'])} 個陣營、{len(cities['cities'])} 個城鎮{site_summary}。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (UpdateError, requests.RequestException, websockets.WebSocketException, json.JSONDecodeError) as error:
        print(f"資料更新失敗：{error}")
        raise SystemExit(1)
