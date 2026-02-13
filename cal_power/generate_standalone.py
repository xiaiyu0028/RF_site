import json

# 讀取 JSON 資料
with open('parsed_actors_skill.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 讀取 HTML 模板
with open('power_calculator.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# 將資料內嵌到 HTML 中
# 找到 loadActorData 函數並替換
standalone_html = html_content.replace(
    '''        // 載入角色資料
        async function loadActorData() {
            try {
                const response = await fetch('parsed_actors_skill.json');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                parsedActors = await response.json();
                actorNames = Object.keys(parsedActors).sort();
                console.log(`載入 ${actorNames.length} 個角色資料`);
                
                // 自動新增第一個角色選擇
                addActorSelection();
            } catch (error) {
                console.error('載入角色資料失敗:', error);
                document.getElementById('results').innerHTML = 
                    `<div class="error">
                        ⚠️ 無法載入角色資料<br><br>
                        <strong>可能的原因：</strong><br>
                        1. 請使用本地伺服器開啟此檔案（不要直接雙擊開啟）<br>
                        2. 請確認 parsed_actors_skill.json 檔案在同一目錄下<br><br>
                        <strong>解決方法：</strong><br>
                        在此目錄下執行以下指令啟動本地伺服器：<br>
                        <code style="background:#f8f9fa;padding:5px;border-radius:3px;display:block;margin:10px 0;">
                        python -m http.server 8000
                        </code>
                        然後在瀏覽器開啟：<code style="background:#f8f9fa;padding:5px;border-radius:3px;">
                        http://localhost:8000/power_calculator.html
                        </code>
                    </div>`;
            }
        }''',
    f'''        // 內嵌角色資料（獨立版本）
        const EMBEDDED_DATA = {json.dumps(data, ensure_ascii=False)};
        
        // 載入角色資料
        async function loadActorData() {{
            try {{
                parsedActors = EMBEDDED_DATA;
                actorNames = Object.keys(parsedActors).sort();
                console.log(`載入 ${{actorNames.length}} 個角色資料 (內嵌版本)`);
                
                // 自動新增第一個角色選擇
                addActorSelection();
            }} catch (error) {{
                console.error('載入角色資料失敗:', error);
                document.getElementById('results').innerHTML = 
                    '<div class="error">⚠️ 載入角色資料時發生錯誤: ' + error.message + '</div>';
            }}
        }}'''
)

# 修改標題，標示為獨立版本
standalone_html = standalone_html.replace(
    '<title>角色戰力計算器</title>',
    '<title>角色戰力計算器 (獨立版)</title>'
)

standalone_html = standalone_html.replace(
    '<h1>⚔️ 角色戰力計算器 ⚔️</h1>',
    '<h1>⚔️ 角色戰力計算器 ⚔️</h1>\n        <p style="text-align:center;color:#666;margin-top:-20px;margin-bottom:20px;">📦 獨立版本 - 可直接開啟使用</p>'
)

# 寫入新檔案
with open('power_calculator_standalone.html', 'w', encoding='utf-8') as f:
    f.write(standalone_html)

print("✅ 已生成獨立版本: power_calculator_standalone.html")
print(f"📊 檔案大小: {len(standalone_html) / 1024 / 1024:.2f} MB")
print("🎯 此版本可以直接用瀏覽器開啟，無需啟動伺服器！")
