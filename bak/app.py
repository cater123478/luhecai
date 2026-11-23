import streamlit as st
import random
from collections import defaultdict
from datetime import date

# ================= 参数 =================
NUM_RANGE = list(range(1, 50))
NUM_COUNT = 6          # 正码数量
TE_COUNT = 5           # 特码数量
DEFAULT_FIXED_DAY = 7
FIXED_BET = 30
RANDOM_BET = 10

# ================= session_state 初始化 =================
for key in ["fixed_group", "fixed_te", "fixed_day", "fixed_total_days",
            "random_high", "random_high_te", "random_bal", "random_bal_te",
            "history", "last_date"]:
    if key not in st.session_state:
        if "group" in key or "random" in key or "te" in key:
            st.session_state[key] = []
        elif key=="fixed_total_days":
            st.session_state[key] = DEFAULT_FIXED_DAY
        elif key=="last_date":
            st.session_state[key] = None
        else:
            st.session_state[key] = 1

# ================= 历史数据处理 =================
def parse_manual_history(text):
    history = []
    for line in text.strip().split("\n"):
        nums = list(map(int, line.strip().split()))
        if len(nums) >= 6:
            history.append(nums[:7])  # 前6正码+1特码
    return history

def calc_weighted_features(history, te=False):
    total = len(history)
    freq = defaultdict(float)
    last_seen = {n: None for n in NUM_RANGE}
    for idx, draw in enumerate(history):
        weight = (idx + 1) / total
        for i, n in enumerate(draw):
            if te and i==6:
                freq[n] += weight
                last_seen[n] = idx
            elif not te and i<6:
                freq[n] += weight
                last_seen[n] = idx
    features = {}
    for n in NUM_RANGE:
        miss = (total - last_seen[n]) if last_seen[n] is not None else total
        features[n] = {"freq": freq[n], "miss": miss}
    return features

def score_cold(features):
    return {n: 0.7*f["miss"] - 0.2*f["freq"] for n,f in features.items()}

def score_balanced(features):
    return {n: 0.5*f["miss"] - 0.5*f["freq"] for n,f in features.items()}

def pick_top_with_noise(scores, count, noise=0.02):
    noisy_scores = {n: s + random.random()*noise for n,s in scores.items()}
    sorted_nums = sorted(noisy_scores, key=noisy_scores.get, reverse=True)
    return sorted(sorted_nums[:count])

def format_line(nums):
    return " ".join(str(n) for n in nums)

# ================= 页面 =================
st.title("玩彩职业版")

# --- 输入历史数据 ---
text = st.text_area("输入历史数据，每行7个号码（前6正码 + 最后1特码）")
st.session_state.history = parse_manual_history(text) if text else []

# ================= 刷新函数 =================
def refresh_fixed():
    if st.session_state.history:
        features = calc_weighted_features(st.session_state.history)
        features_te = calc_weighted_features(st.session_state.history, te=True)
        st.session_state.fixed_group = pick_top_with_noise(score_cold(features), NUM_COUNT)
        st.session_state.fixed_te = pick_top_with_noise(score_cold(features_te), TE_COUNT)
    else:
        st.session_state.fixed_group = random.sample(NUM_RANGE, NUM_COUNT)
        st.session_state.fixed_te = random.sample(NUM_RANGE, TE_COUNT)
    st.session_state.fixed_day = 1
    st.session_state.last_date = date.today()

def refresh_random():
    if st.session_state.history:
        features = calc_weighted_features(st.session_state.history)
        features_te = calc_weighted_features(st.session_state.history, te=True)
        st.session_state.random_high = pick_top_with_noise(score_cold(features), NUM_COUNT)
        st.session_state.random_high_te = pick_top_with_noise(score_cold(features_te), TE_COUNT)
        st.session_state.random_bal = pick_top_with_noise(score_balanced(features), NUM_COUNT)  # 平衡组现在会变
        st.session_state.random_bal_te = pick_top_with_noise(score_balanced(features_te), TE_COUNT)
    else:
        st.session_state.random_high = random.sample(NUM_RANGE, NUM_COUNT)
        st.session_state.random_high_te = random.sample(NUM_RANGE, TE_COUNT)
        st.session_state.random_bal = random.sample(NUM_RANGE, NUM_COUNT)
        st.session_state.random_bal_te = random.sample(NUM_RANGE, TE_COUNT)

# ================= 页面加载自动生成 =================
if not st.session_state.fixed_group:
    refresh_fixed()
if not st.session_state.random_high or not st.session_state.random_bal:
    refresh_random()

# ================= 自动增加固定组天数 =================
today = date.today()
if st.session_state.last_date != today:
    st.session_state.fixed_day += 1
    if st.session_state.fixed_day > st.session_state.fixed_total_days:
        st.session_state.fixed_day = 1
    st.session_state.last_date = today

# --- 固定组 ---
st.subheader("固定追号组")
fixed_days = st.number_input("追号总天数", min_value=1, value=st.session_state.fixed_total_days)
st.session_state.fixed_total_days = fixed_days
st.text(f"固定组（第 {st.session_state.fixed_day}/{st.session_state.fixed_total_days} 天）：")
st.text("正码：" + format_line(st.session_state.fixed_group))
st.text("推荐5个特码：" + format_line(st.session_state.fixed_te))
st.button("换固定组", on_click=refresh_fixed)

# --- 随机推荐组 ---
st.subheader("随机推荐组")
st.text("高评分组 正码：" + format_line(st.session_state.random_high))
st.text("高评分组 特码：" + format_line(st.session_state.random_high_te))
st.text("平衡组 正码：" + format_line(st.session_state.random_bal))
st.text("平衡组 特码：" + format_line(st.session_state.random_bal_te))
st.button("生成随机组", on_click=refresh_random)

# --- 投入建议 ---
st.subheader("投入建议")
total_invest = FIXED_BET + RANDOM_BET*2
st.text(f"固定组投入：{FIXED_BET}元")
st.text(f"随机组投入：{RANDOM_BET}元 × 2组")
st.text(f"总投入：{total_invest}元")