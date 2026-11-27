import json
import numpy as np
from collections import Counter
from math import comb

ZODIACS = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
ZIDX = {z:i for i,z in enumerate(ZODIACS)}
ZODIAC_KEYS = ["shengxiao","生肖","zodiac","animal"]
ISSUE_KEYS  = ["qishu","期号","issue","period","id"]

def load_json(path, target_pos=-1):
    with open(path,"r",encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        for v in raw.values():
            if isinstance(v, list): raw = v; break
    seq, issues = [], []
    for item in raw:
        zstr = next((item[k] for k in ZODIAC_KEYS if k in item), None)
        if zstr is None: raise ValueError(f"找不到生肖字段: {item}")
        zlist = [z.strip() for z in str(zstr).split(",") if z.strip()]
        seq.append(zlist[target_pos])
        issues.append(next((item[k] for k in ISSUE_KEYS if k in item), None))
    pairs = sorted(zip(issues, seq), key=lambda x: str(x[0]))
    return [p[1] for p in pairs], [p[0] for p in pairs]

def strat_uniform(hist, k):
    return ZODIACS[:k]

def strat_freq(hist, k):
    cnt = Counter(hist)
    return sorted(ZODIACS, key=lambda z: (-cnt.get(z,0), ZIDX[z]))[:k]

def strat_rotate(hist, k):
    """轮换均匀：按历史长度滑动取k个，长期覆盖均匀"""
    start = len(hist) % len(ZODIACS)
    return [ZODIACS[(start+i) % len(ZODIACS)] for i in range(k)]

def backtest(seq, strategy, k, start=50):
    hits = []
    for t in range(start, len(seq)):
        pred = strategy(seq[:t], k)
        hits.append(1 if seq[t] in pred else 0)
    return np.array(hits)

def binom_p(hits, p0):
    n=len(hits); x=int(hits.sum())
    return sum(comb(n,i)*p0**i*(1-p0)**(n-i) for i in range(x,n+1))

def report(name, hits, k):
    n=len(hits); r=hits.mean(); p0=k/12; p=binom_p(hits,p0)
    print(f"{name:12s} k={k} n={n:4d} 命中率={r:.4f} 基准={p0:.4f} p={p:.4f}")

if __name__ == "__main__":
    PATH = "../kj.json"
    seq, issues = load_json(PATH, target_pos=-1)
    print(f"共{len(seq)}期，最近5期：{list(zip(issues[-5:],seq[-5:]))}\n")

    for k in (2,3):
        print(f"===== 回测：输出{k}个生肖 =====")
        report("均匀", backtest(seq, strat_uniform, k), k)
        report("全量频率", backtest(seq, strat_freq, k), k)
        report("轮换均匀", backtest(seq, strat_rotate, k), k)
        print()

    print("===== 下一期（326期）预测 =====")
    for k in (2,3):
        print(f"\n-- 输出{k}个 --")
        print("均匀       ->", strat_uniform(seq, k))
        print("全量频率   ->", strat_freq(seq, k))
        print("轮换均匀   ->", strat_rotate(seq, k))