import re

# ================= 数据字典区 =================
CATEGORIES = {
    "吃肉": {"虎", "蛇", "龙", "狗"},
    "吃菜": {"猪", "鼠", "鸡", "猴"},
    "吃草": {"牛", "羊", "马", "兔"},
    "肉菜": {"虎", "蛇", "龙", "狗", "牛", "羊", "马", "兔"},
    "肉草": {"虎", "蛇", "龙", "狗", "牛", "羊", "马", "兔"},
    "菜草": {"猪", "鼠", "鸡", "猴", "牛", "羊", "马", "兔"},
    "天肖": {"兔", "马", "猴", "猪", "牛", "龙"},
    "地肖": {"蛇", "羊", "鸡", "狗", "鼠", "虎"},
    "左肖": {"牛", "鼠", "鸡", "猴", "蛇", "龙"},
    "右肖": {"猪", "狗", "兔", "虎", "羊", "马"},
    "前肖": {"鼠", "牛", "虎", "兔", "龙", "蛇"},
    "后肖": {"猪", "狗", "鸡", "猴", "羊", "马"},
    "野兽": {"猴", "蛇", "龙", "兔", "虎", "鼠"},
    "家禽": {"羊", "马", "牛", "猪", "狗", "鸡"}
}

ZODIAC_NUMS = {
    "马": [1, 13, 25, 37, 49], "蛇": [2, 14, 26, 38], "龙": [3, 15, 27, 39], "兔": [4, 16, 28, 40],
    "虎": [5, 17, 29, 41], "牛": [6, 18, 30, 42], "鼠": [7, 19, 31, 43], "猪": [8, 20, 32, 44],
    "狗": [9, 21, 33, 45], "鸡": [10, 22, 34, 46], "猴": [11, 23, 35, 47], "羊": [12, 24, 36, 48]
}

WUXING = {
    "金": [4, 5, 12, 13, 26, 27, 34, 35, 42, 43],
    "木": [8, 9, 16, 17, 24, 25, 38, 39, 46, 47],
    "水": [1, 14, 15, 22, 23, 30, 31, 44, 45],
    "火": [2, 3, 10, 11, 18, 19, 32, 33, 40, 41, 48, 49],
    "土": [6, 7, 20, 21, 28, 29, 36, 37]
}

BOSE = {
    "红": [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46],
    "蓝": [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48],
    "绿": [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]
}

NUM_TO_ZODIAC = {n: z for z, nums in ZODIAC_NUMS.items() for n in nums}
NUM_TO_WUXING = {n: w for w, nums in WUXING.items() for n in nums}
NUM_TO_BOSE = {n: b for b, nums in BOSE.items() for n in nums}


# ================= 核心逻辑 =================
def find_intersection(input_str):
    # 1. 提取分类标签
    tags = [t for t in CATEGORIES.keys() if t in input_str]

    # 2. 提取输入的号码
    # 匹配所有的数字，支持 . , 或者空格分隔
    input_nums = set(int(n) for n in re.findall(r'\b\d{1,2}\b', input_str) if 1 <= int(n) <= 49)

    if not tags and not input_nums:
        return "未识别到有效标签或号码，请重新输入（例：26.31.32、天肖、家禽）。"

    # 3. 先求标签的生肖交集
    tag_animals = None
    for tag in tags:
        if tag_animals is None:
            tag_animals = CATEGORIES[tag]
        else:
            tag_animals = tag_animals.intersection(CATEGORIES[tag])

    # 如果标签有交集，就把交集生肖对应的号码提取出来
    if tag_animals is not None:
        if not tag_animals:
            return f"条件：[{' + '.join(tags)}] 无交集！"
        # 这些分类对应的所有号码集合
        tag_nums_set = set()
        for a in tag_animals:
            tag_nums_set.update(ZODIAC_NUMS[a])
    else:
        # 如果没有输入标签，只输入了号码
        tag_nums_set = None
        tag_animals = set()

    # 4. 计算最终号码交集
    if tag_nums_set is not None and input_nums:
        # 既分类标签，又有指定号码 → 取两者交集
        final_nums = tag_nums_set.intersection(input_nums)
    elif tag_nums_set is not None:
        # 只有分类标签
        final_nums = tag_nums_set
    else:
        # 只有号码
        final_nums = input_nums

    final_nums = sorted(list(final_nums))

    if not final_nums:
        return "号码无交集！"

    # 5. 提取最终号码包含的生肖
    final_animals = set(NUM_TO_ZODIAC[n] for n in final_nums)

    # 6. 组装输出明细
    num_details = []
    for n in final_nums:
        z = NUM_TO_ZODIAC.get(n, "?")
        w = NUM_TO_WUXING.get(n, "?")
        b = NUM_TO_BOSE.get(n, "?")
        num_details.append(f"{n:02d}{z}/{w}/{b}")

    # 组装条件显示字符串
    condition_str = []
    if tags: condition_str.append(" + ".join(tags))
    if input_nums: condition_str.append("号码 " + " ".join(f"{n:02d}" for n in sorted(list(input_nums))))

    out = f"【输入条件】：{' | '.join(condition_str)}\n"
    out += f"【交集生肖】：{'，'.join(final_animals)}（共 {len(final_animals)} 肖）\n"
    out += f"【号码明细】（共 {len(final_nums)} 码）：\n" + "、".join(num_details)

    return out


# ================= 交互式输入 =================
if __name__ == "__main__":
    print("========================================")
    print("请输入分类标签和/或号码（支持顿号、逗号、点分隔）")
    print("可用标签：吃肉、吃菜、吃草、肉菜、肉草、菜草、天肖、地肖、左肖、右肖、前肖、后肖、野兽、家禽")
    print("例如：26.31.32.33.37.42、天肖、家禽")
    print("========================================\n")

    while True:
        user_input = input("请输入条件 (输入 q 退出)：")
        if user_input.lower() == 'q':
            print("已退出。")
            break

        if not user_input.strip():
            continue

        print("\n" + find_intersection(user_input) + "\n")