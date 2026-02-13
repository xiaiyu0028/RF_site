# %%
from asyncio.log import logger
import requests

# API base URL (根據 iConfig 設定 level 選擇)
API_BASE = "https://api.komisureiya.com/api"

def login(email, password):
    
    # Step 1: 模擬登入（POST /users/log_in）
    login_url = f"{API_BASE}/users/log_in"
    payload = {
            "user[email]": email,
            "user[password]": password,
            "locale": "zh_TW",
            "key": "rfront2023",
            "app_version": "2.28"
    }


    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # 登入並取得 session
    login_response = requests.post(login_url, data=payload, headers=headers)

    login_response = login_response.json()
    if login_response.get("status") != "ok":
        print("❌ 登入失敗")
    else:
        print("✅ 登入成功")

    # 可能會回傳 token、user id、或 cookies
    print("登入回應:", login_response)
    return login_response


# %%
# 這裡可以使用 websocket 客戶端庫來連線
import asyncio
import websockets
import json
from datetime import datetime


output_file = "unions.jsonl"

member = 0

# ✨ 寫入訊息到檔案（每行一筆 JSON）
def save_message_to_file(data):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


# ❤️ 每 20 秒發送 heartbeat
async def send_heartbeat(websocket, start_ref):
    ref = start_ref
    while True:
        heartbeat_msg = [None, str(ref), "phoenix", "heartbeat", {}]
        await websocket.send(json.dumps(heartbeat_msg))
        print(f"❤️ 發送 heartbeat（ref={ref}）")

        # ref += 2
        await asyncio.sleep(20)

async def get_union_info(websocket, union_id, user_id):
    global member
    unions_msg = ["6", "19", f"player:{user_id}", "unions", {"body":""}]
    while True:

        await websocket.send(json.dumps(unions_msg))
        print(f"{union_id} ➡️ 發送 union_info: {unions_msg}")

        await asyncio.sleep(60)

# 📡 連線主流程
async def connect(ws_url, user_id):
    try:
        async with websockets.connect(ws_url, ping_interval=None, max_size=None) as websocket:
            print("✅ WebSocket 已連線")

            # 發送 phx_join
            join_ref = "6"
            topic = f"player:{user_id}"
            join_msg1 = [join_ref, join_ref, topic, "phx_join", {"fake": "ChannelPlayer", "fake2": 1}]
            join_msg2 = ["9", "9", "all_players", "phx_join", {"fake": "ChannelAllPlayer"}]
            join_msg3 = ["12", "12", "locale:zh_TW", "phx_join", {"fake": "locale"}]
            unions_msg = ["6", "19", f"player:{user_id}", "unions", {"body":""}]
            await websocket.send(json.dumps(join_msg1))
            # await websocket.send(json.dumps(join_msg2))
            # await websocket.send(json.dumps(join_msg3))
            
            print(f"➡️ 發送 phx_join: {join_msg1}")
            print(f"➡️ 發送 phx_join: {join_msg2}")
            print(f"➡️ 發送 phx_join: {join_msg3}")
            

            # 啟動 heartbeat
            heartbeat_task = asyncio.create_task(send_heartbeat(websocket, start_ref=20))
            union = asyncio.create_task(get_union_info(websocket, union_id=281, user_id=user_id))
            custom_msg = ["10", "10", "some_topic", "some_event", {"hello": "world"}]
            await websocket.send(json.dumps(custom_msg))
            
            await websocket.send(json.dumps(unions_msg))
            print(f"➡️ 發送 unions: {unions_msg}")
            # 持續接收訊息
            while True:
                raw_msg = await websocket.recv()
                print(f"⬅️ 收到訊息: {raw_msg}")

                try:
                    parsed = json.loads(raw_msg)
                    if(parsed[0] == "6" and parsed[1] == "19"):
                        save_message_to_file(parsed)
                        break
                except json.JSONDecodeError:
                    print("⚠️ 無法解析成 JSON")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ 連線中斷：{e}")

    except Exception as e:
        print(f"🚨 錯誤：{e}")




# %%
import argparse

def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--email", type=str, required=True, help="登入用的 email")
    arg_parser.add_argument("--password", type=str, required=True, help="登入用的 password")

    args = arg_parser.parse_args()
    login_response = login(args.email, args.password)
    if isinstance(login_response, dict):
        data = login_response.get("data", {})
        if isinstance(data, dict):
            user_token = data.get("user_token")
            user_id = data.get("user_id")
            print("✅ token:", user_token)
            print("✅ user_id:", user_id)
        else:
            print("⚠️ 'data' 欄位不是 dict，實際內容是:", data)
    else:
        print("❌ login_response 不是 dict，實際是:", type(login_response))

    ws_url = f"wss://api.komisureiya.com/socket/websocket?userToken={user_token}&locale=zh_TW&vsn=2.0.0"
    asyncio.run(connect(ws_url, user_id))

if __name__ == "__main__":
    main()

