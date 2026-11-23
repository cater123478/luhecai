import requests
from bs4 import BeautifulSoup
import re

url = "https://hcf14638dhx4.iugaub.com:31638/yjjy/ziliao.html"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, headers=headers, timeout=10)
response.encoding = 'gbk'
content = response.text

soup = BeautifulSoup(content, 'html.parser')

# 在HTML中搜索包含关键词的任意元素
keyword = "横财富【必中30码】"
target_element = soup.find_all(string=re.compile(keyword))

if target_element:
    for elem in target_element:
        parent = elem.parent
        table = parent.find('table') if parent else None
        
        if not table and parent:
            tables = parent.find_all('table')
            if tables:
                table = tables[-1]
        
        if not table:
            table = elem.find_next('table')
        
        if table:
            tbody = table.find('tbody')
            rows = tbody.find_all('tr') if tbody else table.find_all('tr')
            
            if rows:
                last_row = rows[-1]
                cells = last_row.find_all(['td', 'th'])
                row_text = [cell.get_text(strip=True) for cell in cells]
                
                # 🔑 只提取 【数字】 格式的内容，去掉文字
                all_text = ' '.join(row_text)
                pattern = r'【[\d.]+】'
                matches = re.findall(pattern, all_text)
                
                if matches:
                    print(' '.join(matches))
            break