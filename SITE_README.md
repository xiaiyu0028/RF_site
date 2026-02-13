# RF 攻略網站

這是一個使用 GitHub Pages 建置的 RF 遊戲攻略網站。

## 功能特色

- 🏰 **城鎮資訊** - 查看城鎮詳細資料、劇情標題、通關獎勵與掉落物資訊
- 👤 **角色資訊** - 完整角色數據，包含職業、陣營、天賦表、符文類型、等級數值
- ⚔️ **戰力計算器** - 自由編隊計算角色與隊伍戰力，規劃最強陣容
- 📖 **新手教學** - 詳細的遊戲入門指南，幫助新手快速上手
- 🔍 **查詢功能** - 查詢已擁有角色、庫存道具、符文裝備與抽獎歷史
- 🏴 **國策資訊** - 各陣營國策一覽，查看戰力加成與本地援助效果

## 網站結構

```
rf_site/
├── index.html          # 首頁
├── css/
│   └── style.css       # 共用樣式
├── js/
│   └── app.js          # 共用 JavaScript
├── pages/
│   ├── cities.html     # 城鎮資訊
│   ├── characters.html # 角色資訊
│   ├── calculator.html # 戰力計算器
│   ├── guide.html      # 新手教學
│   ├── query.html      # 查詢功能
│   └── nations.html    # 國策資訊
├── guides/             # Markdown 教學文件
│   └── basic-guide.md
└── cal_power/          # 角色資料與計算工具
    ├── parsed_actors.json
    └── parsed_actors_skill.json
```

## 本地開發

由於網站使用 fetch API 載入 JSON 資料，直接開啟 HTML 檔案會遇到 CORS 限制。
請使用本地 HTTP 伺服器：

### Python 方式

```bash
# Python 3
python -m http.server 8000

# 然後在瀏覽器開啟 http://localhost:8000
```

### Node.js 方式

```bash
# 安裝 http-server
npm install -g http-server

# 啟動伺服器
http-server -p 8000
```

### VS Code Live Server

安裝 VS Code 的 Live Server 擴充套件，右鍵點擊 index.html 選擇「Open with Live Server」。

## 部署到 GitHub Pages

1. 將此專案推送到 GitHub 倉庫
2. 進入倉庫設定 → Pages
3. 選擇 Source 為「Deploy from a branch」
4. 選擇 Branch 為「main」和「/ (root)」
5. 點擊 Save，等待部署完成

部署後，網站將可透過 `https://[你的用戶名].github.io/[倉庫名稱]/` 存取。

## 更新內容

### 更新教學文件

教學文件存放在 `guides/` 資料夾，使用 Markdown 格式撰寫。
直接編輯 `.md` 檔案並提交即可更新。

### 更新角色資料

角色資料存放在 `cal_power/` 資料夾：
- `parsed_actors.json` - 角色基本資料與天賦
- `parsed_actors_skill.json` - 包含解析後的被動技能效果

## API 參考

網站使用以下 API 格式查詢遊戲資料：

| 功能 | API 格式 |
|------|----------|
| 角色查詢 | `["6","39","player:{ID}","actors",{"body":""}]` |
| 庫存查詢 | `["6","32","player:{ID}","backpack",{}]` |
| 抽獎歷史 | `["6","37","player:{ID}","used_recruit_coupons",{}]` |
| 城鎮資訊 | `["6","15","player:{ID}","cities",{"body":""}]` |
| 國策資訊 | `["6","14","player:{ID}","nations",{"body":""}]` |
| 符文資訊 | `["6","18","player:{ID}","weapon_prototypes",{}]` |

## 授權

此專案僅供學習與個人使用。
