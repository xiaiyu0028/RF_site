import json
import os
import asyncio
import websockets
import datetime
import customtkinter as ctk

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
            "key": "t9cTpsbSCYcJgsrrC",
            "app_version": "3.00"
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


output_file = "history.jsonl"

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
async def connect(ws_url, user_id) -> list:
    parsed = None  # 新增：避免未賦值情況
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
            recruit_history_msg = ["6","40",f"player:{user_id}","used_recruit_coupons",{}]
            await websocket.send(json.dumps(join_msg1))
            # await websocket.send(json.dumps(join_msg2))
            # await websocket.send(json.dumps(join_msg3))
            
            print(f"➡️ 發送 phx_join: {join_msg1}")
            print(f"➡️ 發送 phx_join: {join_msg2}")
            print(f"➡️ 發送 phx_join: {join_msg3}")
            

            # 啟動 heartbeat
            heartbeat_task = asyncio.create_task(send_heartbeat(websocket, start_ref=20))
            # union = asyncio.create_task(get_union_info(websocket, union_id=281, user_id=user_id))
            # await websocket.send(json.dumps(custom_msg))

            await websocket.send(json.dumps(recruit_history_msg))
            print(f"➡️ 發送 recruit_history: {recruit_history_msg}")
            # 持續接收訊息
            while True:
                raw_msg = await websocket.recv()
                # print(f"⬅️ 收到訊息: {raw_msg}")

                try:
                    parsed = json.loads(raw_msg)
                    if(parsed[0] == "6" and parsed[1] == "40"):
                        # save_message_to_file(parsed)
                        break
                except json.JSONDecodeError:
                    print("⚠️ 無法解析成 JSON")
        return parsed

    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ 連線中斷：{e}")

    except Exception as e:
        print(f"🚨 錯誤：{e}")




# %%
import argparse
# 新增 import
import sys
import threading
from collections import Counter

def _extract_name(entry: dict) -> str:
    # 嘗試多個常見欄位名稱
    candidates = [
        "name"
    ]
    for key in candidates:
        v = entry.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # 最後用 id 兜底
    any_id = entry.get("character_id") or entry.get("card_id") or entry.get("id")
    return f"未知角色({any_id})" if any_id else "未知角色"

def _extract_rarity(entry: dict) -> str:
    rarity = entry.get("scarcity")
    rarity = str(rarity).upper()
    if rarity in {"SSR", "SR", "R"}:
        return rarity
    return "其他"

def compute_stats(entries: list) -> dict:
    total = len(entries)
    rarity_counter = Counter()
    char_counter = Counter()
    # 依稀有度分組的角色統計
    by_rarity = {
        "SSR": Counter(),
        "SR": Counter(),
        "R": Counter(),
        "其他": Counter(),
    }

    for e in entries:
        r = _extract_rarity(e)
        n = _extract_name(e)
        rarity_counter[r] += 1
        char_counter[n] += 1
        by_rarity[r][n] += 1

    # 保底：以總抽數 200 為一輪
    # 且從 2025 11 月 1 號得開始計算
    start_date = datetime(2025, 11, 1)
    total_after_nov = 0
    for e in entries:
        recruit_time = e.get("updated_at")
        if recruit_time:
            dt_object = datetime.fromisoformat(recruit_time)
            if dt_object >= start_date:
                total_after_nov += 1
    remainder = total_after_nov % 200
    pity_remaining = 0 if remainder == 0 and total_after_nov > 0 else (200 - remainder)

    # 百分比
    def pct(x): 
        return (x / total * 100) if total else 0.0

    stats = {
        "total": total,
        "pity_remaining": pity_remaining,
        "rarity_counts": {
            "SSR": rarity_counter.get("SSR", 0),
            "SR": rarity_counter.get("SR", 0),
            "R": rarity_counter.get("R", 0),
            "其他": rarity_counter.get("其他", 0),
        },
        "rarity_pct": {
            "SSR": pct(rarity_counter.get("SSR", 0)),
            "SR": pct(rarity_counter.get("SR", 0)),
            "R": pct(rarity_counter.get("R", 0)),
            "其他": pct(rarity_counter.get("其他", 0)),
        },
        "characters": dict(char_counter.most_common()),
        # 依稀有度輸出排序好的角色次數
        "characters_by_rarity": {
            "SSR": dict(by_rarity["SSR"].most_common()),
            "SR": dict(by_rarity["SR"].most_common()),
            "R": dict(by_rarity["R"].most_common()),
            "其他": dict(by_rarity["其他"].most_common()),
        },
    }
    return stats

async def fetch_recruit_history(email: str, password: str) -> dict:
    login_response = login(email, password)
    if not isinstance(login_response, dict) or login_response.get("status") != "ok":
        raise RuntimeError("登入失敗，請確認帳號密碼")

    data = login_response.get("data") or {}
    user_token = data.get("user_token")
    user_id = data.get("user_id")
    if not user_token or not user_id:
        raise RuntimeError("登入成功但缺少 user_token 或 user_id")

    ws_url = f"wss://api.komisureiya.com/socket/websocket?userToken={user_token}&locale=zh_TW&vsn=2.0.0"
    parsed = await connect(ws_url, user_id)
    if not parsed or not isinstance(parsed, list) or not isinstance(parsed[-1], dict):
        raise RuntimeError("WebSocket 回傳資料格式不正確")

    response_list = parsed[-1].get("response", [])
    if not isinstance(response_list, list):
        raise RuntimeError("未取得招募歷史列表")

    # 計算統計
    stats = compute_stats(response_list)
    return stats

# ------- customtkinter UI -------
class RecruitHistoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self.title("招募歷史查詢 by 夏夏子")
        self.geometry("820x640")

        # 上方輸入區
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=12, pady=12)

        self.email_var = ctk.StringVar()
        self.pwd_var = ctk.StringVar()

        ctk.CTkLabel(input_frame, text="帳號").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.email_entry = ctk.CTkEntry(input_frame, width=280, textvariable=self.email_var)
        self.email_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ctk.CTkLabel(input_frame, text="密碼").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.pwd_entry = ctk.CTkEntry(input_frame, width=220, show="*", textvariable=self.pwd_var)
        self.pwd_entry.grid(row=0, column=3, padx=6, pady=6, sticky="w")

        self.query_btn = ctk.CTkButton(input_frame, text="查詢", command=self.on_query)
        self.query_btn.grid(row=0, column=4, padx=10, pady=6)

        self.status_label = ctk.CTkLabel(input_frame, text="", text_color=("gray20", "gray80"))
        self.status_label.grid(row=1, column=0, columnspan=5, sticky="w", padx=6, pady=(0,6))

        # 統計區
        stats_frame = ctk.CTkFrame(self)
        stats_frame.pack(fill="x", padx=12, pady=6)

        self.pity_label = ctk.CTkLabel(stats_frame, text="距離下一次保底還有 - 抽")
        self.pity_label.grid(row=0, column=0, padx=6, pady=6, sticky="w")

        self.total_label = ctk.CTkLabel(stats_frame, text="總抽數：-")
        self.total_label.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        self.rarity_label = ctk.CTkLabel(stats_frame, justify="left", text="稀有度統計：-")
        self.rarity_label.grid(row=1, column=0, columnspan=2, padx=6, pady=6, sticky="w")

        # 角色統計
        char_frame = ctk.CTkFrame(self)
        char_frame.pack(fill="both", expand=True, padx=12, pady=6)

        ctk.CTkLabel(char_frame, text="每個角色抽到次數").pack(anchor="w", padx=6, pady=(8,4))
        self.char_text = ctk.CTkTextbox(char_frame, height=380)
        self.char_text.pack(fill="both", expand=True, padx=6, pady=6)

    def on_query(self):
        email = self.email_var.get().strip()
        pwd = self.pwd_var.get().strip()
        if not email or not pwd:
            self.set_status("請輸入 Email 與 Password")
            return

        self.query_btn.configure(state="disabled")
        self.set_status("查詢中，請稍候...")

        def worker():
            try:
                stats = asyncio.run(fetch_recruit_history(email, pwd))
                self.after(0, lambda: self.update_stats(stats))
            except Exception as e:
                self.after(0, lambda: self.set_status(f"發生錯誤：{e}"))
            finally:
                self.after(0, lambda: self.query_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def set_status(self, msg: str):
        self.status_label.configure(text=msg)

    def update_stats(self, stats: dict):
        self.set_status("查詢完成")
        pity = stats.get("pity_remaining", 0)
        total = stats.get("total", 0)
        rc = stats.get("rarity_counts", {})
        rp = stats.get("rarity_pct", {})
        chars = stats.get("characters", {})
        chars_by_r = stats.get("characters_by_rarity", {})

        self.pity_label.configure(text=f"距離下一次保底還有 {pity} 抽")
        self.total_label.configure(text=f"總抽數：{total}")

        rarity_lines = [
            f"SSR：{rc.get('SSR',0)} 次（{rp.get('SSR',0):.2f}%）",
            f"SR：{rc.get('SR',0)} 次（{rp.get('SR',0):.2f}%）",
            f"R：{rc.get('R',0)} 次（{rp.get('R',0):.2f}%）",
        ]
        # 若有其他分類
        if rc.get("其他", 0) > 0:
            rarity_lines.append(f"其他：{rc.get('其他',0)} 次（{rp.get('其他',0):.2f}%）")
        self.rarity_label.configure(text="稀有度統計：\n" + "\n".join(rarity_lines))

        self.char_text.configure(state="normal")
        self.char_text.delete("1.0", "end")
        # 以稀有度順序顯示：SSR -> SR -> R -> 其他，並在不同稀有度間加入分隔線
        order = ["SSR", "SR", "R", "其他"]
        printed_any = False
        if isinstance(chars_by_r, dict) and any(chars_by_r.get(r) for r in order):
            non_empty_groups = [r for r in order if chars_by_r.get(r)]
            for idx, r in enumerate(non_empty_groups):
                group = chars_by_r.get(r, {})
                if idx > 0:
                    self.char_text.insert("end", "\n-----------------------\n")
                # 可選：顯示稀有度標題
                self.char_text.insert("end", f"{r}\n")
                for name, cnt in group.items():
                    self.char_text.insert("end", f"{name}：{cnt}\n")
                printed_any = True
        else:
            # 後備：若沒有分組資訊，就用原本的平面清單
            if not chars:
                self.char_text.insert("end", "無角色資料")
            else:
                for name, cnt in chars.items():
                    self.char_text.insert("end", f"{name}：{cnt}\n")
                printed_any = True
        self.char_text.configure(state="disabled")


async def main():
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
    data = await connect(ws_url, user_id)
    # print("✅ 連線成功，收到資料:", data)
    
    if data[-1].get("response") is not None:
        print("🎉 招募歷史資料已儲存到", output_file)
    else:
        print("❌ 未收到招募歷史資料")
        return
    
    data = data[-1].get("response", [])
    counts = 0
    rare_counts = {"SSR": 0, "SR": 0, "R": 0}
    for entry in data:
        recruit_time = entry.get("updated_at")
        if recruit_time:
            # recruit_time: 2025-11-02T03:46:48
            dt_object = datetime.fromisoformat(recruit_time)
            if dt_object >= datetime(2025, 11, 1):
                counts += 1
        rarity = entry.get("scarcity")
        if rarity in rare_counts:
            rare_counts[rarity] += 1

    print(f"📅 2025年11月1日以後的招募次數: {counts} 次")
    print(f"📊 總招募次數: {len(data)} 次")
    print(f"距離下一次保底還有 {200 - (counts % 200)} 次招募")
    print("⭐ 各稀有度招募統計:")
    for rarity, count in rare_counts.items():
        print(f"⭐ {rarity} 總共招募到 {count} 次")
    for rarity, count in rare_counts.items():
        if count > 0:
            print(f"⭐ {rarity} 機率為 {count / len(data) * 100:.2f}%")

if __name__ == "__main__":
    # 若有帶參數，沿用 CLI；否則啟動 UI
    if len(sys.argv) > 1:
        asyncio.run(main())
    else:
        app = RecruitHistoryApp()
        app.mainloop()

