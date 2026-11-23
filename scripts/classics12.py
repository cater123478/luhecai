import requests
import re

API_URL = "https://zlkj-a1.kj54228cmw.xyz:54358/api/kjdata.php?g=am"
BET_FILE = "classics12.txt"
OUT_FILE = "classics12_result.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


def fetch_kj_data():
    res = requests.get(API_URL, headers=HEADERS, timeout=15)
    res.raise_for_status()
    raw = res.json().get("data", [])

    # ★ 扁平化嵌套数组，不要切片
    flat = []
    for item in raw:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)

    return flat


def build_open_map(kj_data):
    # ★ 先找出最大年份
    years = [int(item.get("year", 0)) for item in kj_data if item.get("year")]
    if not years:
        return {}
    max_year = max(years)

    result = {}
    for item in kj_data:
        year = int(item.get("year", 0))
        if year != max_year:  # ★ 只取最新年份
            continue

        qishu = str(item.get("qishu", "")).strip()
        num_str = str(item.get("num", "")).strip()
        if not qishu or not num_str:
            continue

        nums = [int(x) for x in num_str.split(",") if x.strip().isdigit()]
        if len(nums) < 7:
            continue

        open_num = nums[-1]
        result[qishu] = open_num
        try:
            result[str(int(qishu))] = open_num
        except ValueError:
            pass

    return result


def parse_bet_line(line):
    match = re.match(r"(\d{3})期.*?【([\d\s]+)】", line)
    if not match:
        return None, None
    qishu = match.group(1)
    nums = [int(x) for x in match.group(2).split() if x.isdigit()]
    return qishu, nums

def main1():
    print("正在拉取开奖数据...")
    kj_data = fetch_kj_data()
    print("总期数:", len(kj_data))

    # 打印所有 300 期的 num
    for item in kj_data:
        if str(item.get("qishu")) == "300":
            print("300期:", item.get("num"))

    # 先 return，不处理投注
    return

def main():
    print("正在拉取开奖数据...")
    kj_data = fetch_kj_data()
    open_map = build_open_map(kj_data)
    print(f"拉取到 {len(kj_data)} 期，映射 {len(open_map)} 条")

    # ★ 调试：打印 300 期
    # for item in kj_data:
        # if str(item.get("qishu")) == "300":
        #     print("300期接口num:", item.get("num"))
        #     break

    with open(BET_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = []
    hit_count = miss_count = unknown_count = 0

    for line in lines:
        line = line.rstrip("\n")
        if not line.strip():
            out_lines.append(line)
            continue

        qishu, nums = parse_bet_line(line)
        if qishu is None or nums is None:
            out_lines.append(line + "  ⚠️ 无法解析")
            unknown_count += 1
            continue

        open_num = None
        for q in [qishu, str(int(qishu))]:
            if q in open_map:
                open_num = open_map[q]
                break

        if open_num is None:
            out_lines.append(line + "  ⏳ 未找到开奖")
            unknown_count += 1
            continue

        if open_num in nums:
            out_lines.append(line + f"  ✅ 中奖（特码{open_num}）")
            hit_count += 1
        else:
            out_lines.append(line + f"  ❌ 未中（特码{open_num}）")
            miss_count += 1

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

    print(f"\n完成：中 {hit_count}，未中 {miss_count}，未知 {unknown_count}")
    print(f"结果：{OUT_FILE}")


if __name__ == "__main__":
    main()