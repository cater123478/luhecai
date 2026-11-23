import requests
import random
from collections import defaultdict

NUM_RANGE = list(range(1, 50))
NUM_TM = 5  # 推荐特码数量
NUM_ZM = 6  # 正码组合数量（示例）

# ================== 获取历史数据 ==================
def fetch_history(limit=50):
    # 示例：尝试抓取某个网页API
    url = "https://api.example.com/lottery/hk"  # 替换为可用数据源
    try:
        data = requests.get(url, timeout=5).json()
        history_raw = data.get("history", [])
        history = []
        for row in history_raw[:limit]:
            nums = row["numbers"]  # 取前6个号码
            history.append(nums[:6])
        return history
    except Exception as e:
        print("❌ 获取数据失败:", e)
        return []

# ================== 半量化策略 ==================
def calc_features(history):
    freq = defaultdict(int)
    last_seen = {n: None for n in NUM_RANGE}
    for i, draw in enumerate(history):
        for n in draw:
            freq[n] += 1
            last_seen[n] = i
    features = {}
    for n in NUM_RANGE:
        miss = (len(history) - last_seen[n]) if last_seen[n] is not None else len(history)
        features[n] = {"freq": freq[n], "miss": miss}
    return features

def score_numbers(features, miss_weight=0.6, freq_weight=0.3):
    scores = {}
    for n, f in features.items():
        scores[n] = miss_weight * f["miss"] - freq_weight * f["freq"]
    return scores

def pick_numbers(scores, count):
    sorted_nums = sorted(scores, key=scores.get, reverse=True)
    pool = sorted_nums[:count*2]  # 多选一些随机化
    return sorted(random.sample(pool, count))

# ================== 主流程 ==================
def main():
    choice = input("选择数据来源（1=自动获取，2=手动输入）：")
    history = []
    if choice == "1":
        history = fetch_history()
        if not history:
            print("❌ 自动获取数据失败，请选择手动输入")
    if choice == "2" or not history:
        print("请输入最近50期历史数据，每行6个号码，用空格分隔：")
        while True:
            line = input("输入一行号码（空行结束）：")
            if not line.strip():
                break
            nums = list(map(int, line.strip().split()))
            if len(nums) != 6:
                print("每行必须输入6个号码！")
                continue
            history.append(nums)
        if not history:
            print("❌ 没有输入有效数据，退出")
            return

    features = calc_features(history)
    scores = score_numbers(features)

    recommended_tm = pick_numbers(scores, NUM_TM)
    recommended_zm = pick_numbers(scores, NUM_ZM)

    print("=== 半量化推荐号码 ===")
    print("正码组合:", recommended_zm)
    print("特码组合:", recommended_tm)

if __name__ == "__main__":
    main()