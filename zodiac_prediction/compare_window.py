import pandas as pd
import numpy as np
import requests
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler

# ====================== 配置 ======================
HISTORY_API = "https://history.macaumarksix.com/history/macaujc2/y/{year}"
LATEST_API = "https://macaumarksix.com/api/macaujc2.com"

zodiacs = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]
zodiac_to_idx = {z: i for i, z in enumerate(zodiacs)}
idx_to_zodiac = {i: z for i, z in enumerate(zodiacs)}

# ====================== 工具函数 ======================
def deduplicate_data(data_list):
    seen_expect = {}
    for item in data_list:
        expect = item[0]
        seen_expect[expect] = item
    unique_data = list(seen_expect.values())
    unique_data.sort(key=lambda x: x[0])
    return unique_data

def get_history_data(years=[2025, 2026]):
    all_data = []
    for year in years:
        try:
            url = HISTORY_API.format(year=year)
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data_json = resp.json()
                if data_json.get("result") and "data" in data_json:
                    for item in data_json["data"]:
                        expect = int(item["expect"])
                        zodiac_list = item["zodiac"].split(",")
                        if zodiac_list:
                            zodiac = zodiac_list[-1].strip()
                            all_data.append((expect, zodiac))
        except Exception as e:
            pass
    all_data = deduplicate_data(all_data)
    return all_data

def compute_features(df, window_size=10):
    """计算特征，可配置窗口期"""
    hist = df["编码"].values
    features = []
    for z in range(12):
        last = np.where(hist == z)[0]
        遗漏 = len(hist) - last[-1] if len(last) > 0 else len(hist)
        
        # 近N期出现次数
        recent = hist[-window_size:] if len(hist) >= window_size else hist
        近N次 = np.sum(recent == z)
        
        实际频率 = 近N次 / max(len(recent), 1)
        理论概率 = 1/12
        偏离度 = 实际频率 - 理论概率
        
        features.append([遗漏, 近N次, 偏离度])
    return np.array(features)

def train_and_predict(data, window_size, name):
    """训练并预测"""
    df = pd.DataFrame(data, columns=["期数", "生肖"])
    df["编码"] = df["生肖"].map(zodiac_to_idx)
    
    X = compute_features(df, window_size)
    
    train_X = []
    train_y = []
    for i in range(window_size, len(df)):
        window = df.iloc[:i]
        fx = compute_features(window, window_size)
        train_X.append(fx)
        train_y.append(df.iloc[i]["编码"])
    
    train_X = np.array(train_X)
    train_X = train_X.reshape(-1, 3)
    train_y = np.repeat(train_y, 12)
    
    scaler = StandardScaler()
    train_X = scaler.fit_transform(train_X)
    
    lr = LogisticRegression(max_iter=1000)
    lr.fit(train_X, train_y)
    
    xgb = XGBClassifier(eval_metric="mlogloss", n_estimators=50)
    xgb.fit(train_X, train_y)
    
    X_current = scaler.transform(X)
    prob_lr = lr.predict_proba(X_current)
    prob_xgb = xgb.predict_proba(X_current)
    
    final_prob = 0.6 * prob_lr + 0.4 * prob_xgb
    scores = final_prob.max(axis=1)
    
    rank = sorted(zip(zodiacs, scores), key=lambda x: x[1], reverse=True)
    
    top1_score = rank[0][1]
    top2_score = rank[1][1]
    分差 = top1_score - top2_score
    
    if 分差 >= 0.03:
        置信等级 = "S级（强信）"
    elif 分差 >= 0.015:
        置信等级 = "A级（中信）"
    else:
        置信等级 = "B级（观察级）"
    
    return {
        "名称": name,
        "窗口": window_size,
        "置信等级": 置信等级,
        "分差": 分差,
        "TOP1": rank[0][0],
        "TOP1概率": rank[0][1],
        "TOP2": rank[1][0],
        "TOP2概率": rank[1][1],
        "完整排名": rank
    }

# ====================== 主程序 ======================
print("="*80)
print("不同窗口期对比分析")
print("="*80)

# 获取数据
print("\n正在获取数据...")
data = get_history_data([2025, 2026])
print(f"获取到 {len(data)} 期数据")

# 测试不同窗口期
windows = [
    (10, "近10期"),
    (12, "近12期"),
    (15, "近15期"),
    (20, "近20期")
]

# 对每个窗口进行预测
results = []
for window, name in windows:
    print(f"\n正在训练 {name}...")
    result = train_and_predict(data, window, name)
    results.append(result)

# 打印对比
print("\n" + "="*80)
print("📊 各窗口期对比结果")
print("="*80)
print(f"{'窗口':<10} {'置信等级':<12} {'分差':<8} {'TOP1':<5} {'TOP1概率':<8}")
print("-"*80)

for res in results:
    print(f"{res['名称']:<10} {res['置信等级']:<12} {res['分差']:<8.4f} {res['TOP1']:<5} {res['TOP1概率']:<8.4f}")

print("\n" + "="*80)
print("🔝 各窗口期TOP5排名对比")
print("="*80)
for res in results:
    print(f"\n{res['名称']}（{res['置信等级']}）:")
    for i, (z, s) in enumerate(res['完整排名'][:5], 1):
        print(f"  {i}. {z} - {s:.4f}")

print("\n" + "="*80)
best_version = max(results, key=lambda x: x['分差'])
print(f"🏆 推荐窗口: {best_version['名称']}")
print(f"   置信等级: {best_version['置信等级']}")
print(f"   TOP1推荐: {best_version['TOP1']}")
print("="*80)
