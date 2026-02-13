"""
掃描 passionfruit/images/actor/ 下所有圖片檔案，
生成 image_index.json 供角色頁面載入使用。
"""
import json, os

IMAGE_BASE = 'passionfruit/images/actor'
OUTPUT = 'cal_power/image_index.json'

index = {}

for subdir in ['head', 'half', 'gif', 'half_full']:
    full_path = os.path.join(IMAGE_BASE, subdir)
    if not os.path.exists(full_path):
        continue
    files = sorted(os.listdir(full_path))
    index[subdir] = [f for f in files if f.lower().endswith(('.png', '.gif', '.jpg', '.webp'))]

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"Generated {OUTPUT}")
for k, v in index.items():
    print(f"  {k}: {len(v)} files")
