import json
import requests
from datetime import datetime

API_URL = "https://history.macaumarksix.com/history/macaujc2/y/2026"   # 换成你实际的接口

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

        if not expect or not open_code:
            continue

        # 号码必须是 7 个，逗号分隔，保留原格式
        nums = [x.strip() for x in open_code.split(",") if x.strip()]
        if len(nums) < 7:
            continue

        # 年份：优先 expect 前 4 位，否则 openTime 前 4 位
        year = expect[:4] if len(expect) >= 4 else (open_time[:4] if len(open_time) >= 4 else "")

        out.append({
            "qishu": expect,
            "year": year,
            "num": ",".join(nums),
            "date": open_time[:10] if open_time else ""
        })

    # 按期号倒序（最新在前）
    out.sort(key=lambda x: x["qishu"], reverse=True)

    with open("kj.json", "w", encoding="utf-8") as f:
        json.dump({"data": out}, f, ensure_ascii=False, indent=2)

    print(f"已写入 kj.json，共 {len(out)} 期，更新时间 {datetime.now()}")

if __name__ == "__main__":
    main()