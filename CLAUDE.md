# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概觀

RF（逆統戰）遊戲攻略網站：**沒有 build step 的靜態網站**，直接由 GitHub Pages 部署整個 repo 根目錄（`.github/workflows/deploy-pages.yml` 上傳 `path: .`）。HTML/CSS/JS 是手寫的原生檔案，沒有 npm、bundler、framework 或測試框架。搭配一組 Python 腳本，在**本機**登入遊戲 API 抓資料、轉成 JSON，再由前端 `fetch()` 讀取。

介面文字、註解、commit message 都使用繁體中文。

## 常用指令

```powershell
# 本地預覽（必須用 HTTP server，直接開 file:// 會因 CORS 無法 fetch JSON）
python -m http.server 8000        # http://localhost:8000

# 更新國策/城鎮公開資料（本機執行，需 RF_EMAIL / RF_PASSWORD 環境變數）
.\scripts\update_game_data.ps1 -DryRun   # 只驗證，不寫檔
.\scripts\update_game_data.ps1
.\scripts\commit_game_data.ps1           # 只 commit return_data_example/ 那幾個檔

# 抓角色原始資料（附加到 cal_power/actors.jsonl）
python cal_power/get_actors.py -a <email> -p <password>
python cal_power/run_all_get_actors.py           # 依 cal_power/config.json 批次跑多帳號

# 一併抓城內地點（逐城呼叫，較慢）
.\scripts\update_game_data.ps1 -CitySites visitable

# 重建角色圖片索引（掃描 passionfruit/images/actor/）
python generate_image_index.py
```

Python 依賴見 `requirements-data-update.txt`；`scripts/update_game_data.ps1` 會優先使用專案的 `.venv\Scripts\python.exe`。

## 資料流

遊戲 API (`api.komisureiya.com`) → Python 抓取 → JSON 檔 → 前端 `fetch()`：

- **國策 / 城鎮**：`scripts/update_game_data.py` 用 HTTP 登入取得 token，再開 WebSocket 送 Phoenix channel 訊息，寫入 `return_data_example/nation.json`、`cities.json`、`update_metadata.json`（原子寫入，且寫入前先 `validate_snapshots()`）。`.gitignore` 只放行這幾個檔，`return_data_example/` 其他內容都不進版控。
- **城內地點（選用）**：同一支腳本加 `--city-sites visitable|all` 會逐城送 `city_sites` 事件，寫入 `return_data_example/city_sites.json`（`{mode, requested, failed, sites}`）。因為是逐城呼叫（`all` 會打 271 次），預設 `off`，並以 `--city-sites-delay` 節流。`pages/cities.html` 的詳情視窗會自動讀取，缺檔則靜默略過。
- **city ↔ site 對照表**：`python scripts/build_city_site_index.py` 純本機轉檔（不連 API），讀 `city_sites.json` + `cities.json` 產出 `return_data_example/city_site_index.json`，內含 `cities`（city_id → 城市資訊 + site 清單）與 `sites`（site_id → 所屬城市，反查表）。city_sites.json 更新後要重跑。
- **角色**：`cal_power/get_actors.py` 把 WebSocket 回應**附加**到 `cal_power/actors.jsonl` → `cal_power/resolve_actors.ipynb` 逐 cell 解析，產出：
  - `parsed_actors.json`（基本資料 + 天賦）
  - `parsed_actors_skill.json`（多一層解析後的被動技能，依等級分段）← 兩個計算器都讀這個
  - `unique_actors.json`（去重後的原始角色資料）← characters.html 讀這個
  - `visit_plots.json`（角色可拜訪地點，3.0 新欄位）← characters.html 選用讀取，缺檔則不顯示該列。需先以 3.0 API 重跑 `get_actors.py`，舊的 `actors.jsonl` 不含 `has_visit_plot` / `visitable_city_id`
  
  這個轉檔步驟只存在於 notebook 裡，改解析邏輯就是改 notebook。
- **圖片**：`passionfruit/` 存放遊戲素材，大部分子目錄被 gitignore；`cal_power/image_index.json` 是檔名索引。

前端頁面各自 hardcode 相對路徑（例如 `../cal_power/parsed_actors_skill.json?t=${Date.now()}`，帶 timestamp 破 cache，失敗再 retry 不帶參數）。新增資料來源時沿用這個模式。

## 前端結構

- `index.html` 在根目錄，其他頁面在 `pages/`，共用 `css/style.css` + `css/design-system.css` + `js/app.js`。因為兩層目錄並存，路徑前綴要小心：`app.js` 的 `upgradeNavigation()` 靠 `/\/pages\//` 判斷目前深度來產生連結，圖片路徑則有 `getAssetPath()`（給 `pages/`）與 `getAssetPathFromRoot()`（給 `index.html`）兩個版本。
- **導覽列由 JS 產生**：`upgradeNavigation()` 會覆寫 `#navMenu` 的 innerHTML。頁面 HTML 裡的 `<ul id="navMenu">` 只是 fallback；要改選單項目請改 `js/app.js`，不要改各頁 HTML。
- `js/app.js` 提供共用工具：`loadJSON`、`showLoading/showError/showEmpty`、`parseMarkdown`、`initTabs/initAccordion/initSearch`、`storage`、`getNationName/getRoleName/getScarcityClass`、深色模式（`data-theme` attribute + localStorage）。頁面專屬邏輯則寫在各 HTML 的 inline `<script>`。
- `pages/guide.html` 在 client 端載入 `guides/*.md` 並用 `parseMarkdown()` 渲染，還會把 md 裡的 `src="images/` 改寫成 `src="../guides/images/`。新增教學章節要同時建立 md 檔並加進該頁的 `guideSections` 陣列。
- `pages/query.html` 直接在瀏覽器對遊戲 API 做登入 + WebSocket 查詢（帳號查詢、庫存、抽卡紀錄），不經過後端。

## 注意事項

- **不要把帳密進版控**。`cal_power/config.json` 內含明文帳密且**未被 .gitignore 涵蓋**——不要 `git add` 它，也不要把它的內容貼進輸出。Python 腳本一律從環境變數或 CLI 參數取得憑證。
- GitHub Actions 只做部署，**不會**登入遊戲或抓資料；所有資料更新都是本機執行後 commit。
- `cal_power/` 內另有一批離線分析腳本（`calculate_power.py`、`find_top_teams.py`、`generate_standalone.py`、`test_teams.json`、各種 `top_teams*.csv/json`），它們與網站無關，是自用的隊伍搜尋工具；`power_calculator_standalone.html` 是把資料內嵌的單檔版本，`generate_standalone.py` 產生。
