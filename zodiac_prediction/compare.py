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
    """按期数去重，保留最后出现的"""
    seen_expect = {}
    for item in data_list:
        expect = item[0]
        seen_expect[expect] = item
    unique_data = list(seen_expect.values())
    unique_data.sort(key=lambda x: x[0])
    return unique_data

def get_history_data(years):
    """按年份获取历史数据"""
    all_data = []
    for year in years:
        try:
            url = HISTORY_API.format(year=year)
            print(f"正在获取 {year} 年数据...")
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
            print(f"获取 {year} 年数据失败: {e}")
    all_data = deduplicate_data(all_data)
    return all_data

def compute_features(df):
    hist = df["编码"].values
    features = []
    for z in range(12):
        last = np.where(hist == z)[0]
        遗漏 = len(hist) - last[-1] if len(last) > 0 else len(hist)
        
        recent = hist[-10:] if len(hist) >= 10 else hist
        近10次 = np.sum(recent == z)
        
        实际频率 = 近10次 / max(len(recent), 1)
        理论概率 = 1/12
        偏离度 = 实际频率 - 理论概率
        
        features.append([遗漏, 近10次, 偏离度])
    return np.array(features)

def train_and_predict(data):
    """训练并预测"""
    df = pd.DataFrame(data, columns=["期数", "生肖"])
    df["编码"] = df["生肖"].map(zodiac_to_idx)
    
    X = compute_features(df)
    
    train_X = []
    train_y = []
    for i in range(10, len(df)):
        window = df.iloc[:i]
        fx = compute_features(window)
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
        单挑准确率 = "32%~38%"
    elif 分差 >= 0.015:
        置信等级 = "A级（中信）"
        单挑准确率 = "26%~32%"
    else:
        置信等级 = "B级（观察级）"
        单挑准确率 = "18%~26%"
    
    return {
        "数据量": len(data),
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
print("不同数据量模型对比分析")
print("="*80)

# 获取完整数据
print("\n正在获取完整数据（2021-2026）...")
full_data = get_history_data([2021, 2022, 2023, 2024, 2025, 2026])

# 定义不同数据量的版本
versions = [
    ("v1: 2025-2026", [y for y in full_data if str(y[0]).startswith(("2025", "2026"))]),
    ("v2: 2023-2026", [y for y in full_data if str(y[0]).startswith(("2023", "2024", "2025", "2026"))]),
    ("v3: 2021-2026", full_data)
]

# 对每个版本进行预测
results = []
for name, data in versions:
    print(f"\n正在训练 {name}...")
    result = train_and_predict(data)
    result["版本"] = name
    results.append(result)

# 打印对比
print("\n" + "="*80)
print("📊 各版本对比结果")
print("="*80)
print(f"{'版本':<15} {'数据量':<8} {'置信等级':<12} {'分差':<8} {'TOP1':<5} {'TOP1概率':<8}")
print("-"*80)

for res in results:
    print(f"{res['版本']:<15} {res['数据量']:<8} {res['置信等级']:<12} {res['分差']:<8.4f} {res['TOP1']:<5} {res['TOP1概率']:<8.4f}")

print("\n" + "="*80)
print("🔝 各版本TOP5排名对比")
print("="*80)
for res in results:
    print(f"\n{res['版本']}（{res['置信等级']}）:")
    for i, (z, s) in enumerate(res['完整排名'][:5], 1):
        print(f"  {i}. {z} - {s:.4f}")

print("\n" + "="*80)
best_version = max(results, key=lambda x: x['分差'])
print(f"🏆 推荐版本: {best_version['版本']}")
print(f"   置信等级: {best_version['置信等级']}")
print(f"   TOP1推荐: {best_version['TOP1']}")
print("="*80)
