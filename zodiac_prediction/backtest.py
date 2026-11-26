import pandas as pd
import numpy as np
import requests
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler

# ====================== 配置 ======================
HISTORY_API = "https://history.macaumarksix.com/history/macaujc2/y/{year}"
zodiacs = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]
zodiac_to_idx = {z: i for i, z in enumerate(zodiacs)}

WINDOW = 15          # 特征窗口（与 open.py 一致）
MIN_TRAIN = 150      # 最少训练期数，从第151期开始回测
RETRAIN_STEP = 5     # 每5期重训一次模型（模拟实战：每周更新一次）


def get_history_data(years):
    all_data = {}
    for year in years:
        try:
            resp = requests.get(HISTORY_API.format(year=year), timeout=10)
            if resp.status_code == 200:
                for item in resp.json().get("data", []):
                    zs = item["zodiac"].split(",")
                    if zs:
                        all_data[int(item["expect"])] = zs[-1].strip()
        except Exception as e:
            print(f"获取{year}年数据失败: {e}")
    data = sorted(all_data.items())
    return data


def compute_features(hist, window=WINDOW):
    """输入编码序列，输出12个生肖的特征矩阵 (12, 3)"""
    features = []
    for z in range(12):
        last = np.where(hist == z)[0]
        miss = len(hist) - last[-1] if len(last) > 0 else len(hist)
        recent = hist[-window:] if len(hist) >= window else hist
        cnt = int(np.sum(recent == z))
        freq = cnt / max(len(recent), 1)
        features.append([miss, cnt, freq - 1 / 12])
    return np.array(features, dtype=float)


def build_train_set(codes, upto, mode="binary"):
    """
    用 [0, upto) 的数据构造训练集
    mode='binary': 每行一个生肖，标签=该生肖当期是否开出（修正版）
    mode='wrong' : 复现原脚本 train_y=repeat 的错误标签
    """
    X, y = [], []
    for i in range(WINDOW, upto):
        feats = compute_features(codes[:i])
        actual = codes[i]
        if mode == "binary":
            for z in range(12):
                X.append(feats[z])
                y.append(1 if z == actual else 0)
        else:
            for z in range(12):
                X.append(feats[z])
                y.append(actual)
    return np.array(X), np.array(y)


def fit_predict(codes, upto, mode="binary", use_xgb=False):
    """训练模型并返回当期的12个生肖概率"""
    X, y = build_train_set(codes, upto, mode)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    lr = LogisticRegression(max_iter=1000)
    lr.fit(Xs, y)
    cur = scaler.transform(compute_features(codes[:upto]))
    p_lr = lr.predict_proba(cur)[:, 1] if mode == "binary" else lr.predict_proba(cur)[:, 1]
    if use_xgb:
        xgb = XGBClassifier(eval_metric="logloss", n_estimators=50, verbosity=0)
        xgb.fit(Xs, y)
        p_xgb = xgb.predict_proba(cur)[:, 1]
        return 0.6 * p_lr + 0.4 * p_xgb
    return p_lr


def rank_of(probs, actual):
    order = np.argsort(-probs)
    return int(np.where(order == actual)[0][0]) + 1


def main():
    print("=" * 60)
    print("生肖模型 Walk-Forward 回测（滚动训练，无未来数据泄漏）")
    print("=" * 60)

    years = list(range(2021, 2027))
    data = get_history_data(years)
    codes = np.array([zodiac_to_idx.get(z, -1) for _, z in data])
    valid = codes >= 0
    codes = codes[valid]
    print(f"有效数据: {len(codes)} 期（{data[0][0]} ~ {data[-1][0]}）")
    print(f"回测区间: 第 {MIN_TRAIN + 1} ~ {len(codes)} 期，共 {len(codes) - MIN_TRAIN} 期")
    print(f"参数: window={WINDOW}, 每{RETRAIN_STEP}期重训\n")

    total = len(codes) - MIN_TRAIN
    stats = {k: {"top1": 0, "top3": 0, "top6": 0} for k in ["binary_lr", "binary_mix", "wrong_lr"]}
    baselines = {"随机猜": {"top1": 0, "top3": 0, "top6": 0},
                 "近15期高频": {"top1": 0, "top3": 0, "top6": 0},
                 "遗漏最大": {"top1": 0, "top3": 0, "top6": 0}}

    cache = {}
    for i in range(MIN_TRAIN, len(codes)):
        actual = codes[i]
        hist = codes[:i]
        feats = compute_features(hist)

        # 每 RETRAIN_STEP 期重训一次，中间复用模型（只更新特征）
        if (i - MIN_TRAIN) % RETRAIN_STEP == 0:
            cache["binary_lr"] = fit_predict(codes, i, "binary", False)
            cache["binary_mix"] = fit_predict(codes, i, "binary", True)
            cache["wrong_lr"] = fit_predict(codes, i, "wrong", False)

        for key in stats:
            r = rank_of(cache[key], actual)
            if r == 1: stats[key]["top1"] += 1
            if r <= 3: stats[key]["top3"] += 1
            if r <= 6: stats[key]["top6"] += 1

        # 基线1：按近15期出现次数排序
        r_freq = rank_of(feats[:, 1].astype(float), actual)
        if r_freq == 1: baselines["近15期高频"]["top1"] += 1
        if r_freq <= 3: baselines["近15期高频"]["top3"] += 1
        if r_freq <= 6: baselines["近15期高频"]["top6"] += 1

        # 基线2：按遗漏最大排序（追冷）
        r_miss = rank_of(feats[:, 0].astype(float), actual)
        if r_miss == 1: baselines["遗漏最大"]["top1"] += 1
        if r_miss <= 3: baselines["遗漏最大"]["top3"] += 1
        if r_miss <= 6: baselines["遗漏最大"]["top6"] += 1

        baselines["随机猜"]["top1"] += 1 / 12
        baselines["随机猜"]["top3"] += 3 / 12
        baselines["随机猜"]["top6"] += 6 / 12

        if (i - MIN_TRAIN + 1) % 100 == 0:
            print(f"  已回测 {i - MIN_TRAIN + 1}/{total} 期...")

    print("\n" + "=" * 60)
    print("📊 命中率对比（理论随机基线: TOP1=8.3% TOP3=25% TOP6=50%）")
    print("=" * 60)
    print(f"{'方法':<16} {'TOP1':>8} {'TOP3':>8} {'TOP6':>8}")
    print("-" * 60)
    for name, s in {**stats, **baselines}.items():
        print(f"{name:<16} {s['top1']/total*100:>7.2f}% {s['top3']/total*100:>7.2f}% {s['top6']/total*100:>7.2f}%")
    print("=" * 60)

    best = max(stats.items(), key=lambda kv: kv[1]["top1"] / total)
    best_rate = best[1]["top1"] / total * 100
    print(f"\n模型最佳: {best[0]}  TOP1命中率 {best_rate:.2f}%")
    if best_rate < 8.3:
        print("⚠️ 结论：模型不如随机猜，当前算法不具备实战价值")
    elif best_rate < 12:
        print("⚠️ 结论：略优于随机，但优势微弱，不足以覆盖投注成本")
    else:
        print("✅ 结论：明显优于随机，可进一步做参数优化验证")


if __name__ == "__main__":
    main()
