# final_app.py
import streamlit as st
import requests
from collections import defaultdict
import random
import plotly.graph_objs as go

# ================== 参数设置 ==================
NUM_RANGE = list(range(1, 50))
TOTAL_BUDGET = 50
UNIT_PRICE = 10
ODDS_ZM = 10
ODDS_TM = 20

# ================== 数据获取 ==================
def fetch_history(limit=50):
    url = "https://marksix6.net/api/lottery_api.php"
    try:
        data = requests.get(url, timeout=5).json()
        for item in data["lottery_data"]:
            if "香港" in item["name"]:
                history_raw = item.get("history", [])
                history = []
                for row in history_raw[:limit]:
                    nums = row["numbers"]
                    history.append(nums[:6])
                return history
    except:
        return []

def fetch_latest_draw():
    url = "https://marksix6.net/api/lottery_api.php"
    try:
        data = requests.get(url, timeout=5).json()
        for item in data["lottery_data"]:
            if "香港" in item["name"]:
                history_raw = item.get("history", [])
                if history_raw:
                    latest = history_raw[0]["numbers"][:6]
                    return latest
    except:
        return None

# ================== 策略计算 ==================
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
        score = miss_weight*f["miss"] - freq_weight*f["freq"]
        scores[n] = score
    return scores

def pick_by_score(scores, pool_size=20):
    sorted_nums = sorted(scores, key=scores.get, reverse=True)
    pool = sorted_nums[:pool_size]
    return sorted(random.sample(pool, 6))

def decide_mode(hit_history):
    if len(hit_history) < 3:
        return "balanced"
    if all(h == 0 for h in hit_history[-3:]):
        return "stable"
    if sum(hit_history[-3:]) >= 2:
        return "aggressive"
    return "balanced"

def generate_plan(history, hit_history, miss_weight=0.6, freq_weight=0.3):
    features = calc_features(history)
    scores = score_numbers(features, miss_weight, freq_weight)
    mode = decide_mode(hit_history)
    if mode == "stable":
        zm, tm = 3, 2
    elif mode == "balanced":
        zm, tm = 2, 3
    else:
        zm, tm = 1, 4

    zm_list = []
    for _ in range(zm):
        nums = pick_by_score(scores)
        zm_list.append(nums)

    tm_list = []
    top_nums = sorted(scores, key=scores.get, reverse=True)[:15]
    for _ in range(tm):
        sp = random.choice(top_nums)
        tm_list.append(sp)

    return zm_list, tm_list, mode

def check_hit(picks, actual):
    hits = 0
    for p in picks:
        hits += len(set(p) & set(actual))
    return hits

# ================== 回测 & 实时 ==================
def simulate(history, periods=100, miss_weight=0.6, freq_weight=0.3, real_draws=None):
    cash_history = []
    hit_history = []
    mode_history = []
    capital = 0
    history = history.copy()
    if real_draws is None:
        real_draws = history.copy()

    for i in range(periods):
        zm, tm, mode = generate_plan(history, hit_history, miss_weight, freq_weight)
        mode_history.append(mode)
        actual = real_draws[i % len(real_draws)]
        hits_zm = check_hit(zm, actual)
        hits_tm = check_hit([tm], actual)
        profit = hits_zm*UNIT_PRICE*ODDS_ZM + hits_tm*UNIT_PRICE*ODDS_TM - TOTAL_BUDGET
        capital += profit
        cash_history.append(capital)
        hit_history.append(hits_zm + hits_tm)
        history.insert(0, actual)
        history = history[:50]

    return cash_history, hit_history, mode_history

# ================== 自动调参 ==================
def auto_tune(history):
    best_profit = -float('inf')
    best_params = (0.6, 0.3)
    for mw in [0.4,0.5,0.6,0.7,0.8]:
        for fw in [0.2,0.3,0.4]:
            cash_history, _, _ = simulate(history, miss_weight=mw, freq_weight=fw)
            final_profit = cash_history[-1]
            if final_profit > best_profit:
                best_profit = final_profit
                best_params = (mw, fw)
    return best_params

# ================== 可视化 ==================
def plot_results(cash_history, hit_history, mode_history):
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(y=cash_history, mode='lines', name='累计盈亏'))
    fig1.update_layout(title='资金变化曲线', xaxis_title='期数', yaxis_title='盈亏')

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(y=hit_history, name='每期命中数'))
    fig2.update_layout(title='每期命中数', xaxis_title='期数', yaxis_title='命中数')

    mode_color = {'stable':'blue','balanced':'green','aggressive':'red'}
    mode_numeric = [1 if m=='stable' else 2 if m=='balanced' else 3 for m in mode_history]
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(y=mode_numeric, mode='markers', marker=dict(color=[mode_color[m] for m in mode_history], size=10), name='策略模式'))
    fig3.update_layout(title='每期策略模式', yaxis=dict(tickvals=[1,2,3], ticktext=['stable','balanced','aggressive']))

    st.plotly_chart(fig1, use_container_width=True)
    st.plotly_chart(fig2, use_container_width=True)
    st.plotly_chart(fig3, use_container_width=True)

# ================== Streamlit 界面 ==================
st.title("半量化职业玩家选号系统（实时+回测）")
st.markdown("支持自动获取最新开奖数据，每期自动生成投注组合，并记录盈亏，可自动调参优化策略权重。")

option = st.radio("数据来源", ["自动获取", "手动输入"])
history = []
if option=="自动获取":
    history = fetch_history()
if option=="手动输入" or not history:
    st.info("手动输入历史数据，每行6个正码，用空格分隔")
    text_input = st.text_area("输入历史数据（每行6个数字）：")
    if text_input:
        for line in text_input.strip().split("\n"):
            nums = list(map(int, line.strip().split()))
            if len(nums)==6:
                history.append(nums)

periods = st.slider("回测期数", 10, 500, 100, 10)

if st.button("运行回测 + 实时模拟"):
    if len(history)==0:
        st.error("❌ 无有效历史数据")
    else:
        st.info("正在自动调参优化权重...")
        miss_weight, freq_weight = auto_tune(history)
        st.success(f"最佳权重：miss_weight={miss_weight}, freq_weight={freq_weight}")

        latest_draw = fetch_latest_draw()
        if latest_draw:
            st.info(f"最新开奖：{latest_draw}")
            real_draws = history + [latest_draw]
        else:
            real_draws = history

        cash_history, hit_history, mode_history = simulate(history, periods, miss_weight, freq_weight, real_draws)
        zm, tm, mode = generate_plan(history, hit_history, miss_weight, freq_weight)
        st.write("✅ 本期自动生成投注组合")
        st.write("正码组合：", zm)
        st.write("特码组合：", tm)
        st.write("当前策略模式：", mode)

        plot_results(cash_history, hit_history, mode_history)