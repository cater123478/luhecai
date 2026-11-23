import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime


def fetch_hengcai():
    url = "https://hcf14638dhx4.iugaub.com:31638/yjjy/ziliao.html"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        print("正在抓取数据...")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk'
        # print("状态码:", response.status_code)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        keyword = "横财富【必中30码】"
        target = soup.find_all(string=re.compile(keyword))
        if not target:
            return {'nums': [], 'expect': '', 'raw_groups': []}

        for elem in target:
            parent = elem.parent
            table = parent.find('table') if parent else None
            if not table and parent:
                tables = parent.find_all('table')
                table = tables[-1] if tables else None
            if not table:
                table = elem.find_next('table')
            if table:
                tbody = table.find('tbody')
                rows = tbody.find_all('tr') if tbody else table.find_all('tr')
                if rows:
                    # ⭐ 从最后一行开始往前迭代
                    for idx in range(len(rows) - 1, -1, -1):
                        row = rows[idx]
                        cells = row.find_all(['td', 'th'])
                        text = ' '.join(c.get_text(strip=True) for c in cells)
                        
                        # 提取号码
                        nums = []
                        for m in re.findall(r'【([\d.]+)】', text):
                            for p in m.split('.'):
                                n = int(p)
                                if 1 <= n <= 49 and n not in nums:
                                    nums.append(n)
                        
                        # ⭐ 如果号码数量 >= 30，说明是有效行
                        if len(nums) >= 30:
                            raw_groups = []
                            for m in re.findall(r'【([\d.]+)】', text):
                                raw_groups.append(m)
                            
                            expect = ''
                            expect_match = re.search(r'(\d{2,4})期', text)
                            if expect_match:
                                expect = expect_match.group(1)
                            
                            print(f"✅ 找到有效行: {expect}期，{len(nums)} 个号码")
                            return {'nums': nums[:30], 'expect': expect, 'raw_groups': raw_groups[:3]}
                    
                    # 如果所有行都没有30个号码，取最后一个
                    target_row = rows[-1]
                    cells = target_row.find_all(['td', 'th'])
                    text = ' '.join(c.get_text(strip=True) for c in cells)
                    raw_groups = []
                    for m in re.findall(r'【([\d.]+)】', text):
                        raw_groups.append(m)
                    nums = []
                    for m in re.findall(r'【([\d.]+)】', text):
                        for p in m.split('.'):
                            n = int(p)
                            if 1 <= n <= 49 and n not in nums:
                                nums.append(n)
                    expect = ''
                    expect_match = re.search(r'(\d{2,4})期', text)
                    if expect_match:
                        expect = expect_match.group(1)
                    return {'nums': nums[:30], 'expect': expect, 'raw_groups': raw_groups[:3]}

        return {'nums': [], 'expect': '', 'raw_groups': []}
    except Exception as e:
        print("抓取失败:", e)
        return {'nums': [], 'expect': '', 'raw_groups': []}


if __name__ == '__main__':
    file_path = os.path.join(os.path.dirname(__file__), 'hcf.json')
    result = fetch_hengcai()
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({
            'code': 0,
            'data': result['raw_groups'],
            'count': len(result['nums']),
            'expect': result['expect'],
            'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, f)
    print(f"✅ hcf.json 已写入，{result['expect']}期，共 {len(result['nums'])} 个号码")