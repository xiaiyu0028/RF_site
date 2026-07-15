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

import requests
import websockets

API_BASE = "https://api.komisureiya.com/api"
WS_BASE = "wss://api.komisureiya.com/socket/websocket"
APP_VERSION = "2.28"
APP_KEY = "rfront2023"


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
        headers={"Content-Type": "application/x-www-form-urlencoded"},
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


async def request_snapshot(token: str, user_id: str, timeout: int) -> tuple[dict[str, Any], dict[str, Any]]:
    ws_url = f"{WS_BASE}?userToken={token}&locale=zh_TW&vsn=2.0.0"
    topic = f"player:{user_id}"
    async with websockets.connect(ws_url, ping_interval=20, close_timeout=timeout, max_size=None) as websocket:
        await websocket.send(json.dumps(["1", "1", topic, "phx_join", {"fake": "ChannelPlayer", "fake2": 1}]))

        async def request(event: str, payload: dict[str, Any], ref: str) -> dict[str, Any]:
            await websocket.send(json.dumps(["1", ref, topic, event, payload]))
            while True:
                raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                message = json.loads(raw)
                if not (isinstance(message, list) and len(message) >= 5 and message[1] == ref and message[3] == "phx_reply"):
                    continue
                reply = message[4]
                if not isinstance(reply, dict) or reply.get("status") != "ok" or not isinstance(reply.get("response"), dict):
                    raise UpdateError(f"{event} 資料請求未成功。")
                return reply["response"]

        nations = await request("nations", {"body": ""}, "14")
        cities = await request("cities", {"body": ""}, "15")
        return nations, cities


def validate_snapshots(nations: dict[str, Any], cities: dict[str, Any]) -> None:
    nation_items = nations.get("nations")
    city_items = cities.get("cities")
    if not isinstance(nation_items, list) or len(nation_items) < 3:
        raise UpdateError("國策資料格式不完整，已取消更新。")
    if not isinstance(nations.get("diplomatic_strategies"), list) or not isinstance(nations.get("general_strategies"), list):
        raise UpdateError("國策策略資料格式不完整，已取消更新。")
    if not isinstance(city_items, list) or len(city_items) < 10:
        raise UpdateError("城鎮資料格式不完整，已取消更新。")
    if not all(isinstance(item, dict) and item.get("id") and item.get("name") for item in nation_items):
        raise UpdateError("國策資料缺少必要欄位，已取消更新。")
    if not all(isinstance(item, dict) and item.get("id") and item.get("name") for item in city_items):
        raise UpdateError("城鎮資料缺少必要欄位，已取消更新。")


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    email = os.environ.get("RF_ACCOUNT_EMAIL")
    password = os.environ.get("RF_ACCOUNT_PASSWORD")
    if not email or not password:
        raise UpdateError("缺少 RF_ACCOUNT_EMAIL 或 RF_ACCOUNT_PASSWORD Secret。")

    token, user_id = login(email, password, args.timeout)
    nations, cities = asyncio.run(request_snapshot(token, user_id, args.timeout))
    validate_snapshots(nations, cities)

    if args.dry_run:
        print(f"驗證成功：{len(nations['nations'])} 個陣營、{len(cities['cities'])} 個城鎮。")
        return 0

    updated_at = datetime.now(UTC).isoformat()
    root = args.output_root
    write_json_atomic(root / "return_data_example" / "nation.json", nations)
    write_json_atomic(root / "return_data_example" / "cities.json", {"cities": cities["cities"]})
    write_json_atomic(
        root / "return_data_example" / "update_metadata.json",
        {
            "updated_at": updated_at,
            "datasets": {"nations": "available", "cities": "available"},
            "counts": {"nations": len(nations["nations"]), "cities": len(cities["cities"])},
        },
    )
    print(f"更新完成：{len(nations['nations'])} 個陣營、{len(cities['cities'])} 個城鎮。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (UpdateError, requests.RequestException, websockets.WebSocketException, json.JSONDecodeError) as error:
        print(f"資料更新失敗：{error}")
        raise SystemExit(1)
