from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from bs4 import BeautifulSoup
import re
import json

TARGET_ROW = -1


def fetch_hengcai(row_index=-1):
    url = "https://hcf14638dhx4.iugaub.com:31638/yjjy/ziliao.html"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        print("正在抓取数据...")
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk'
        print("状态码:", response.status_code)
        soup = BeautifulSoup(response.text, 'html.parser')
        keyword = "横财富【必中30码】"
        target = soup.find_all(string=re.compile(keyword))
        if not target:
            return []
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
                    target_row = rows[row_index]
                    cells = target_row.find_all(['td', 'th'])
                    text = ' '.join(c.get_text(strip=True) for c in cells)
                    nums = []
                    for m in re.findall(r'【([\d.]+)】', text):
                        for p in m.split('.'):
                            n = int(p)
                            if 1 <= n <= 49 and n not in nums:
                                nums.append(n)
                    return nums[:30]
            break
        return []
    except Exception as e:
        print("抓取失败:", e)
        return []


class HengCaiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/hengcai'):
            print("收到请求:", self.path)
            row = TARGET_ROW
            parts = self.path.split('/')
            if len(parts) >= 3 and parts[2].lstrip('-').isdigit():
                row = int(parts[2])

            nums = fetch_hengcai(row)
            result = {
                'code': 0,
                'data': nums,
                'count': len(nums),
                'row': row,
                'desc': f'第{row}行' if row >= 0 else f'倒数第{abs(row)}行'
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    port = 5000
    desc = f'第{TARGET_ROW}行' if TARGET_ROW >= 0 else f'倒数第{abs(TARGET_ROW)}行'
    print(f"🚀 横财富服务启动: http://127.0.0.1:{port}/hengcai")
    print(f"📌 当前配置: {desc}")

    # ⭐ 新增：启动时写入 hcf.json
    nums = fetch_hengcai(TARGET_ROW)
    with open('hcf.json', 'w', encoding='utf-8') as f:
        json.dump({'code': 0, 'data': nums, 'count': len(nums), 'fetch_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, f)
    print(f"✅ hcf.json 已写入，共 {len(nums)} 个号码")

    server = HTTPServer(('0.0.0.0', port), HengCaiHandler)
    server.serve_forever()