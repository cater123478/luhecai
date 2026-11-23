import requests
import json

API_URL = "https://zlkj-a1.kj54228cmw.xyz:54358/api/kjdata.php?g=am"
OUT_FILE = "meatVeg_result.txt"

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

# 分类
MEAT = ['虎','蛇','龙','狗']   # 吃肉
VEG  = ['猪','鼠','鸡','猴']   # 吃菜
GRASS = ['牛','羊','马','兔']  # 吃草


def get_category(zodiac):
    if zodiac in MEAT:
        return '肉'
    if zodiac in VEG:
        return '菜'
    if zodiac in GRASS:
        return '草'
    return '未知'


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

def main():
    print("正在拉取开奖数据...")
    kj_data = fetch_kj_data()
    print(f"总期数: {len(kj_data)}")

    # 只取最新年份
    years = [int(item.get("year", 0)) for item in kj_data if item.get("year")]
    max_year = max(years) if years else 0
    kj_data = [item for item in kj_data if int(item.get("year", 0)) == max_year]

    # 分类说明
    lines = []
    lines.append("吃肉:虎蛇龙狗 吃菜:猪鼠鸡猴 吃草:牛羊马兔")
    lines.append("天肖：兔.马.猴.猪.牛.龙    地肖：蛇.羊.鸡.狗.鼠.虎")
    lines.append("左肖：牛鼠鸡猴蛇龙         右肖：猪狗兔虎羊马")
    lines.append("前肖：鼠牛虎兔龙蛇         后肖：猪狗鸡猴羊马")
    lines.append("野兽：猴蛇龙兔虎鼠         家禽：羊马牛猪狗鸡")
    lines.append("")

    for item in kj_data:
        qishu = str(item.get("qishu", "")).strip()
        num_str = str(item.get("num", "")).strip()
        if not qishu or not num_str:
            continue

        nums = [int(x) for x in num_str.split(",") if x.strip().isdigit()]
        if len(nums) < 7:
            continue

        open_num = nums[-1]
        zodiac = ZODIAC_MAP.get(open_num, '')
        if not zodiac:
            continue

        tags = []

        # 1. 吃肉/吃菜/吃草
        tags.append(get_category(zodiac))

        # 2. 天肖 / 地肖
        if zodiac in ['兔','马','猴','猪','牛','龙']:
            tags.append('天')
        elif zodiac in ['蛇','羊','鸡','狗','鼠','虎']:
            tags.append('地')

        # 3. 左肖 / 右肖
        if zodiac in ['牛','鼠','鸡','猴','蛇','龙']:
            tags.append('左')
        elif zodiac in ['猪','狗','兔','虎','羊','马']:
            tags.append('右')

        # 4. 前肖 / 后肖
        if zodiac in ['鼠','牛','虎','兔','龙','蛇']:
            tags.append('前')
        elif zodiac in ['猪','狗','鸡','猴','羊','马']:
            tags.append('后')

        # 5. 野兽 / 家禽
        if zodiac in ['猴','蛇','龙','兔','虎','鼠']:
            tags.append('野')
        elif zodiac in ['羊','马','牛','猪','狗','鸡']:
            tags.append('家')

        lines.append(f"{qishu}期：特码 {open_num:02d}（{zodiac}）→ {' '.join(tags)}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"结果已写入：{OUT_FILE}，共 {len(lines) - 6} 期")

# def main():
#     print("正在拉取开奖数据...")
#     kj_data = fetch_kj_data()
#     print(f"总期数: {len(kj_data)}")
#
#     # 只取最新年份
#     years = [int(item.get("year", 0)) for item in kj_data if item.get("year")]
#     max_year = max(years) if years else 0
#     kj_data = [item for item in kj_data if int(item.get("year", 0)) == max_year]
#
#     # 按期号排序（从新到旧或旧到新都行，这里用接口顺序）
#     lines = []
#     lines.append("吃肉:虎蛇龙狗 吃菜:猪鼠鸡猴 吃草:牛羊马兔")
#     lines.append("")
#     for item in kj_data:
#         qishu = str(item.get("qishu", "")).strip()
#         num_str = str(item.get("num", "")).strip()
#         if not qishu or not num_str:
#             continue
#
#         nums = [int(x) for x in num_str.split(",") if x.strip().isdigit()]
#         if len(nums) < 7:
#             continue
#
#         open_num = nums[-1]
#         zodiac = ZODIAC_MAP.get(open_num, '')
#         category = get_category(zodiac)
#         lines.append(f"{qishu}期：特码 {open_num:02d}（{zodiac}）→ {category}")
#
#     for item in kj_data:
#         if str(item.get("qishu")) == "312":
#             print("312:", json.dumps(item, ensure_ascii=False))
#             break
#
#     with open(OUT_FILE, "w", encoding="utf-8") as f:
#         f.write("\n".join(lines))
#
#     print(f"结果已写入：{OUT_FILE}，共 {len(lines)} 期")


if __name__ == "__main__":
    main()