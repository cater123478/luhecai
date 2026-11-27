import json
import requests
from datetime import datetime

API_URL = "https://history.macaumarksix.com/history/macaujc2/y/2026"

# 繁体 → 简体生肖
TRAD_TO_SIMP = {
    "馬": "马", "龍": "龙", "豬": "猪", "雞": "鸡", "牛": "牛", "猴": "猴",
    "兔": "兔", "蛇": "蛇", "虎": "虎", "鼠": "鼠", "狗": "狗", "羊": "羊"
}

def main():
    res = requests.get(API_URL, timeout=20)
    res.raise_for_status()
    raw = res.json()

    data = raw.get("data", [])
    if not isinstance(data, list):
        data = []

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue

        expect = str(item.get("expect", "")).strip()
        open_code = str(item.get("openCode", "")).strip()
        open_time = str(item.get("openTime", "")).strip()
        zodiac_str = str(item.get("zodiac", "")).strip()

        if not expect or not open_code:
            continue

        nums = [x.strip() for x in open_code.split(",") if x.strip()]
        if len(nums) < 7:
            continue

        # 全部 7 个生肖，转简体，与 num 一一对应
        zodiac_list = [x.strip() for x in zodiac_str.split(",") if x.strip()]
        zodiac_simplified = [TRAD_TO_SIMP.get(z, z) for z in zodiac_list]

        # 保证生肖数量与号码一致；不够就留空
        if len(zodiac_simplified) < 7:
            zodiac_simplified = zodiac_simplified + [""] * (7 - len(zodiac_simplified))

        year = expect[:4] if len(expect) >= 4 else (open_time[:4] if len(open_time) >= 4 else "")

        out.append({
            "qishu": expect,
            "year": year,
            "num": ",".join(nums),
            "zodiac": ",".join(zodiac_simplified[:7]),
            "date": open_time[:10] if open_time else ""
        })

    out.sort(key=lambda x: x["qishu"], reverse=True)

    with open("kj.json", "w", encoding="utf-8") as f:
        json.dump({"data": out}, f, ensure_ascii=False, indent=2)

    print(f"已写入 kj.json，共 {len(out)} 期，更新时间 {datetime.now()}")

if __name__ == "__main__":
    main()