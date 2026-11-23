import requests
import re

API_URL = "https://zlkj-a1.kj54228cmw.xyz:54358/api/kjdata.php?g=am"
BET_FILE = "formula6.txt"
OUT_FILE = "formula6_result.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# 2026马年生肖映射
ZODIAC_MAP = {
    1:'马',2:'蛇',3:'龙',4:'兔',5:'虎',6:'牛',7:'鼠',8:'猪',9:'狗',10:'鸡',11:'猴',12:'羊',
    13:'马',14:'蛇',15:'龙',16:'兔',17:'虎',18:'牛',19:'鼠',20:'猪',21:'狗',22:'鸡',23:'猴',24:'羊',
    25:'马',26:'蛇',27:'龙',28:'兔',29:'虎',30:'牛',31:'鼠',32:'猪',33:'狗',34:'鸡',35:'猴',36:'羊',
    37:'马',38:'蛇',39:'龙',40:'兔',41:'虎',42:'牛',43:'鼠',44:'猪',45:'狗',46:'鸡',47:'猴',48:'羊',
    49:'马'
}


def get_zodiac(num):
    return ZODIAC_MAP.get(num, '')


def fetch_kj_data():
    res = requests.get(API_URL, headers=HEADERS, timeout=15)
    res.raise_for_status()
    raw = res.json().get("data", [])

    flat = []
    for item in raw:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)

    return flat


def build_open_map(kj_data):
    years = [int(item.get("year", 0)) for item in kj_data if item.get("year")]
    if not years:
        return {}
    max_year = max(years)

    result = {}
    for item in kj_data:
        year = int(item.get("year", 0))
        if year != max_year:
            continue

        qishu = str(item.get("qishu", "")).strip()
        num_str = str(item.get("num", "")).strip()
        if not qishu or not num_str:
            continue

        nums = [int(x) for x in num_str.split(",") if x.strip().isdigit()]
        if len(nums) < 7:
            continue

        open_num = nums[-1]
        open_zodiac = get_zodiac(open_num)

        result[qishu] = {"num": open_num, "zodiac": open_zodiac}
        try:
            result[str(int(qishu))] = {"num": open_num, "zodiac": open_zodiac}
        except ValueError:
            pass

    return result


def parse_bet_line(line):
    """解析：001期：公式⑥肖【牛鸡蛇猪龙羊】"""
    match = re.search(r"(\d{3})\s*期.*?【\s*([\u4e00-\u9fa5\s]+?)\s*】", line)
    if not match:
        return None, None
    qishu = match.group(1)
    zodiacs = list(re.sub(r"\s+", "", match.group(2)))
    return qishu, zodiacs


def main():
    print("正在拉取开奖数据...")
    kj_data = fetch_kj_data()
    open_map = build_open_map(kj_data)
    print(f"拉取到 {len(kj_data)} 期，映射 {len(open_map)} 条")

    with open(BET_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = []
    hit_count = 0
    miss_count = 0
    unknown_count = 0

    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            out_lines.append(line)
            continue

        # ★ 跳过标题行（不含"期"或"【"）
        if "期" not in line or "【" not in line:
            out_lines.append(line)
            continue

        qishu, zodiacs = parse_bet_line(line)
        if qishu is None or zodiacs is None:
            out_lines.append(line + "  ⚠️ 无法解析")
            unknown_count += 1
            continue

        open_info = None
        for q in [qishu, str(int(qishu))]:
            if q in open_map:
                open_info = open_map[q]
                break

        if open_info is None:
            out_lines.append(line + "  ⏳ 未找到开奖")
            unknown_count += 1
            continue

        open_num = open_info["num"]
        open_zodiac = open_info["zodiac"]

        if open_zodiac in zodiacs:
            out_lines.append(line + f"  ✅ 中奖（特码{open_num}/{open_zodiac}）")
            hit_count += 1
        else:
            out_lines.append(line + f"  ❌ 未中（特码{open_num}/{open_zodiac}）")
            miss_count += 1

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

    print(f"\n完成：中 {hit_count}，未中 {miss_count}，未知 {unknown_count}")
    print(f"结果：{OUT_FILE}")


if __name__ == "__main__":
    main()