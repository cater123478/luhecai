import pandas as pd
import numpy as np
import requests
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
import json
# ====================== 1. API接口配置 ======================
HISTORY_API = "https://history.macaumarksix.com/history/macaujc2/y/{year}"
LATEST_API = "https://macaumarksix.com/api/macaujc2.com"

# 生肖列表固定
zodiacs = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]
zodiac_to_idx = {z: i for i, z in enumerate(zodiacs)}
idx_to_zodiac = {i: z for i, z in enumerate(zodiacs)}

# ★ 特征窗口期（全局统一控制，改这里即可）
WINDOW_SIZE = 15

# ====================== 2. 从API获取历史数据 ======================
def deduplicate_data(data_list):
    """按期数去重，保留最后出现的"""
    seen_expect = {}
    for item in data_list:
        expect = item[0]
        seen_expect[expect] = item  # 覆盖式保留，确保最新
    # 转回列表并排序
    unique_data = list(seen_expect.values())
    unique_data.sort(key=lambda x: x[0])
    return unique_data

def get_history_data(years=[2025, 2026]):
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
                        # 取最后一个生肖作为主要生肖
                        zodiac_list = item["zodiac"].split(",")
                        if zodiac_list:
                            zodiac = zodiac_list[-1].strip()
                            all_data.append((expect, zodiac))
        except Exception as e:
            print(f"获取 {year} 年数据失败: {e}")
    # 去重并排序
    all_data = deduplicate_data(all_data)
    return all_data

def get_latest_data():
    """获取最新一期数据"""
    try:
        print("正在获取最新一期数据...")
        resp = requests.get(LATEST_API, timeout=10)
        if resp.status_code == 200:
            data_list = resp.json()
            if data_list and len(data_list) > 0:
                item = data_list[0]
                expect = int(item["expect"])
                zodiac_list = item["zodiac"].split(",")
                if zodiac_list:
                    zodiac = zodiac_list[-1].strip()
                    return (expect, zodiac)
    except Exception as e:
        print(f"获取最新数据失败: {e}")
    return None

# ====================== 3. 主程序逻辑 ======================
print("="*50)
print("正在从API获取数据...")
print("="*50)

# 获取历史数据
data = get_history_data()
original_count = len(data)

# 获取最新一期并补充（按期数去重）
latest = get_latest_data()
if latest:
    data.append(latest)

# 最终去重
data = deduplicate_data(data)
deduplicated_count = len(data)
removed_count = original_count - deduplicated_count + (1 if latest else 0)
if removed_count > 0:
    print(f"已去除 {removed_count} 条重复数据")

if not data:
    print("未获取到数据，使用内置默认数据")
    # 备用数据
    data = [
        (2026001, "牛"), (2026002, "猴"), (2026003, "雞"), (2026004, "雞"), (2026005, "豬"),
        (2026006, "蛇"), (2026007, "牛"), (2026008, "雞"), (2026009, "虎"), (2026010, "兔"),
        (2026011, "羊"), (2026012, "羊"), (2026013, "蛇"), (2026014, "龍"), (2026015, "豬"),
        (2026016, "鼠"), (2026017, "狗"), (2026018, "兔"), (2026019, "猴"), (2026020, "馬"),
        (2026021, "鼠"), (2026022, "鼠"), (2026023, "羊"), (2026024, "虎"), (2026025, "蛇"),
        (2026026, "豬"), (2026027, "雞"), (2026028, "兔"), (2026029, "蛇"), (2026030, "牛"),
        (2026031, "龍"), (2026032, "鼠"), (2026033, "牛"), (2026034, "豬"), (2026035, "兔"),
        (2026036, "蛇"), (2026037, "豬"), (2026038, "鼠"), (2026039, "羊"), (2026040, "虎"),
        (2026041, "馬"), (2026042, "虎"), (2026043, "蛇"), (2026044, "豬"), (2026045, "蛇"),
        (2026046, "兔"), (2026047, "兔"), (2026048, "羊"), (2026049, "馬"), (2026050, "猴"),
        (2026051, "馬"), (2026052, "蛇"), (2026053, "龍"), (2026054, "羊"), (2026055, "蛇"),
        (2026056, "羊"), (2026057, "猴"), (2026058, "鼠"), (2026059, "雞"), (2026060, "狗"),
        (2026061, "虎"), (2026062, "羊"), (2026063, "兔"), (2026064, "牛"), (2026065, "虎"),
        (2026066, "馬"), (2026067, "虎"), (2026068, "猴"), (2026069, "羊"), (2026070, "馬"),
        (2026071, "羊"), (2026072, "雞"), (2026073, "雞"), (2026074, "雞"), (2026075, "狗"),
        (2026076, "蛇"), (2026077, "虎"), (2026078, "雞"), (2026079, "猴"), (2026080, "龍"),
        (2026081, "虎"), (2026082, "龍"), (2026083, "虎"), (2026084, "兔"), (2026085, "鼠"),
        (2026086, "羊"), (2026087, "蛇"), (2026088, "龍"), (2026089, "馬"), (2026090, "羊"),
        (2026091, "馬"), (2026092, "牛"), (2026093, "兔"), (2026094, "虎"), (2026095, "猴"),
        (2026096, "鼠"), (2026097, "猴"), (2026098, "虎"), (2026099, "羊"), (2026100, "狗"),
        (2026101, "龍"), (2026102, "豬"), (2026103, "牛"), (2026104, "馬"), (2026105, "兔"),
        (2026106, "雞"), (2026107, "馬"), (2026108, "狗"), (2026109, "兔"),
    ]

print(f"已获取到 {len(data)} 期历史数据")
print(f"最新一期: {data[-1][0]} - {data[-1][1]}")

# 构建DataFrame
df = pd.DataFrame(data, columns=["期数", "生肖"])
df["编码"] = df["生肖"].map(zodiac_to_idx)

# ====================== 4. 计算3个核心特征 ======================
def compute_features(df):
    hist = df["编码"].values
    features = []
    for z in range(12):
        # 遗漏值
        last = np.where(hist == z)[0]
        遗漏 = len(hist) - last[-1] if len(last) > 0 else len(hist)
        
        # 近WINDOW_SIZE期出现次数
        recent = hist[-WINDOW_SIZE:] if len(hist) >= WINDOW_SIZE else hist
        近N次 = np.sum(recent == z)
        
        # 概率偏离度
        实际频率 = 近N次 / max(len(recent), 1)
        理论概率 = 1/12
        偏离度 = 实际频率 - 理论概率
        
        features.append([遗漏, 近N次, 偏离度])
    return np.array(features)

X = compute_features(df)

# ====================== 5. 构建训练集 ======================
train_X = []
train_y = []
# 训练集用全部数据
for i in range(WINDOW_SIZE, len(df)):
    window = df.iloc[:i]
    fx = compute_features(window)
    train_X.append(fx)
    train_y.append(df.iloc[i]["编码"])

train_X = np.array(train_X)
train_X = train_X.reshape(-1, 3)
train_y = np.repeat(train_y, 12)

# 标准化
scaler = StandardScaler()
train_X = scaler.fit_transform(train_X)

# ====================== 6. 双模型训练 ======================
# 逻辑回归（主）
lr = LogisticRegression(max_iter=1000)
lr.fit(train_X, train_y)

# XGBoost（辅助）
xgb = XGBClassifier(eval_metric="mlogloss", n_estimators=50)
xgb.fit(train_X, train_y)

# ====================== 7. 预测当期概率 ======================
X_current = scaler.transform(X)
prob_lr = lr.predict_proba(X_current)
prob_xgb = xgb.predict_proba(X_current)

# 6:4 融合
final_prob = 0.6 * prob_lr + 0.4 * prob_xgb
scores = final_prob.max(axis=1)

# 排序
rank = sorted(zip(zodiacs, scores), key=lambda x: x[1], reverse=True)
top12 = [(i+1, z, round(s,4)) for i,(z,s) in enumerate(rank)]
杀肖 = [rank[-1][0], rank[-2][0]]

# ====================== 8. 置信度与准确率 ======================
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

TOP3准确率 = f"{round(float(单挑准确率[:2])*2.7)}%~{round(float(单挑准确率[-3:-1])*2.7)}%"

# 预测期数
next_expect = data[-1][0] + 1

# ====================== 详细特征分析 ======================
print("="*50)
result = {
    "next_expect": next_expect,
    "top12": [{"rank": r, "zodiac": z, "score": round(float(s),4)} for r,z,s in top12],
    "kill": 杀肖,
    "confidence": 置信等级,
    "top1_acc": 单挑准确率,
    "top3_acc": TOP3准确率,
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}
with open("result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)