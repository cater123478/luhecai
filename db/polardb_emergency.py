#!/usr/bin/env python3
"""
PolarDB 应急改密 + 账号指纹预警工具（完整版）

模式：
  测试模式 --test-mode：自建 MySQL，本地 ALTER USER 改密
  生产模式：阿里云 OpenAPI 改密

功能：
  1. 指纹 diff：高权限账号直连查 mysql.user，与指纹库比对，新增账号告警
  2. 批量改密：测试模式走 ALTER USER，生产模式走 ModifyAccountPassword
     改密范围由凭据文件里的 rotate_accounts 白名单决定，未配置则改所有非高权限账号（不推荐）
  3. 钉钉告警：新增账号和不可达集群汇总后发钉钉
  4. 灰度：--first-only 只跑第一台，--limit N 跑前 N 台
  5. 凭据文件：--cred-file 指定，按集群 ID 取账号密码和白名单

用法：
  # 初始化指纹库
  python polardb_emergency.py --region cn-hangzhou --cred-file creds.json --test-mode --init-baseline

  # 日常预警（定时任务用这个）
  python polardb_emergency.py --region cn-hangzhou --cred-file creds.json --test-mode

  # 灰度改密：先跑第一台
  python polardb_emergency.py --region cn-hangzhou --cred-file creds.json --test-mode --rotate --first-only --yes

  # 全量改密
  python polardb_emergency.py --region cn-hangzhou --cred-file creds.json --test-mode --rotate --exclude-accounts dts_user --yes

  # 人工确认后更新基线
  python polardb_emergency.py --region cn-hangzhou --cred-file creds.json --test-mode --update-baseline
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import string
import sys
import time
import urllib.parse
from typing import List, Dict, Optional, Tuple

import pymysql
import requests

from alibabacloud_polardb20170801.client import Client as PolardbClient
from alibabacloud_polardb20170801 import models as polardb_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.exceptions import (
    ClientException, ServerException, ThrottlingException
)
from alibabacloud_credentials.client import Client as CredentialClient
from darabonba.exceptions import UnretryableException


# ==================== 配置 ====================
FINGERPRINT_FILE = "polardb_fingerprint.json"
PASSWORD_STORE_FILE = "polardb_passwords.jsonl"
SPECIAL_CHARS = "!@#$%^&*()_+-="

DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=47c06a936824931ef9b4fba4b0b8669fa025e7fc1b964608073fb6a951de8904"
DINGTALK_SECRET = os.environ.get("DINGTALK_SECRET", "")


# ==================== 密码生成 ====================
def generate_password(length: int = 32) -> str:
    length = max(8, min(32, length))
    pools = [string.ascii_uppercase, string.ascii_lowercase, string.digits, SPECIAL_CHARS]
    selected = random.sample(pools, 3)
    chars = [random.choice(p) for p in selected]
    all_chars = "".join(pools)
    chars.extend(random.choice(all_chars) for _ in range(length - len(chars)))
    random.shuffle(chars)
    return "".join(chars)


# ==================== 密码存储 ====================
def store_password(cluster_id: str, account_name: str, password: str) -> None:
    record = {"cluster": cluster_id, "account": account_name, "password": password}
    with open(PASSWORD_STORE_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"    [STORED] 密码已写入 {PASSWORD_STORE_FILE}")


# ==================== 钉钉 ====================
def send_dingtalk(title: str, content: str) -> None:
    if not DINGTALK_WEBHOOK:
        print("    [DINGTALK] 未配置 Webhook，跳过")
        return
    url = DINGTALK_WEBHOOK
    if DINGTALK_SECRET:
        ts = str(round(time.time() * 1000))
        sign_str = f"{ts}\n{DINGTALK_SECRET}"
        sign = base64.b64encode(
            hmac.new(DINGTALK_SECRET.encode(), sign_str.encode(), hashlib.sha256).digest()
        ).decode()
        url += f"&timestamp={ts}&sign={urllib.parse.quote_plus(sign)}"
    payload = {"msgtype": "markdown", "markdown": {"title": title, "text": content}}
    try:
        requests.post(url, json=payload, timeout=5)
        print("    [DINGTALK] 发送成功")
    except Exception as e:
        print(f"    [DINGTALK_ERR] {e}")


def send_new_accounts_alert(new_accounts: List[Dict], unreachable: List[str]) -> None:
    if not new_accounts and not unreachable:
        return
    lines = ["### PolarDB 账号巡检告警", ""]
    if new_accounts:
        lines.append(f"**新增账号 {len(new_accounts)} 个：**")
        for a in new_accounts:
            lines.append(f"- `{a['cluster']}`: **{a['user']}@{a['host']}**")
        lines.append("")
    if unreachable:
        lines.append(f"**不可达集群 {len(unreachable)} 个：**")
        for c in unreachable:
            lines.append(f"- `{c}`")
        lines.append("")
    lines.append("请人工确认合法性，合法账号运行 --update-baseline。")
    send_dingtalk("PolarDB 账号告警", "\n".join(lines))


# ==================== 指纹库 ====================
def load_fingerprint() -> Dict[str, List[Dict]]:
    if not os.path.exists(FINGERPRINT_FILE):
        return {}
    with open(FINGERPRINT_FILE, "r") as f:
        return json.load(f)


def save_fingerprint(fp: Dict[str, List[Dict]]) -> None:
    with open(FINGERPRINT_FILE, "w") as f:
        json.dump(fp, f, indent=2, ensure_ascii=False)


def accounts_to_set(accounts: List[Dict]) -> set:
    return {(a["user"].lower(), a["host"].lower()) for a in accounts}


# ==================== 凭据文件 ====================
def load_credentials(path: str) -> Dict[str, Dict]:
    if not os.path.exists(path):
        print(f"[ERR] 凭据文件不存在: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        return json.load(f)


# ==================== 阿里云客户端 ====================
def create_client(region_id: str) -> PolardbClient:
    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        endpoint=f"polardb.{region_id}.aliyuncs.com",
    )
    return PolardbClient(config)


def call_with_retry(func, max_retries: int = 3, initial_delay: float = 1.0):
    for attempt in range(max_retries + 1):
        try:
            return func()
        except ThrottlingException:
            if attempt == max_retries:
                raise
            delay = (2 ** attempt) * initial_delay
            print(f"    [THROTTLED] {delay:.1f}s 后重试...")
            time.sleep(delay)
        except ServerException as e:
            if attempt == max_retries:
                raise
            delay = (2 ** attempt) * initial_delay
            print(f"    [SERVER_ERR] {e.message}，{delay:.1f}s 后重试...")
            time.sleep(delay)
        except (ClientException, UnretryableException):
            raise


# ==================== 集群列表 ====================
def get_clusters(args, client, creds: Dict[str, Dict]) -> List[Dict]:
    if args.test_mode:
        return [
            {"cluster_id": cid, "description": "local-test", "local": True,
             "host": cfg.get("host", "127.0.0.1"), "port": cfg.get("port", 3306)}
            for cid, cfg in creds.items() if cfg.get("local")
        ]
    clusters = []
    page = 1
    while True:
        req = polardb_models.DescribeDBClustersRequest(
            region_id=args.region, page_number=page, page_size=100
        )
        resp = call_with_retry(lambda: client.describe_dbclusters(req))
        items = resp.body.items or []
        for item in items:
            clusters.append({
                "cluster_id": item.dbcluster_id,
                "description": item.dbcluster_description or "",
                "local": False,
            })
        if len(items) < 100:
            break
        page += 1
    return clusters


def get_connection_string(client, cluster_id: str) -> Optional[str]:
    req = polardb_models.DescribeDBClusterEndpointsRequest(dbcluster_id=cluster_id)
    try:
        resp = call_with_retry(lambda: client.describe_dbcluster_endpoints(req))
        for ep in (resp.body.items or []):
            if ep.endpoint_type == "Primary":
                return ep.address
    except Exception as e:
        print(f"    [ERR] 获取连接地址失败: {e}")
    return None


# ==================== 直连查账号 ====================
def query_mysql_user(host: str, port: int, user: str, password: str) -> Optional[List[Dict]]:
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            connect_timeout=10, read_timeout=30,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT User, Host FROM mysql.user")
            rows = cur.fetchall()
        conn.close()
        return [{"user": r[0], "host": r[1]} for r in rows]
    except Exception as e:
        print(f"    [ERR] 查询 mysql.user 失败: {e}")
        return None


# ==================== 改密：本地 ====================
def local_alter_password(host: str, port: int, admin_user: str, admin_pwd: str,
                         target_user: str, target_host: str, new_pwd: str) -> bool:
    try:
        conn = pymysql.connect(
            host=host, port=port, user=admin_user, password=admin_pwd,
            connect_timeout=10,
        )
        with conn.cursor() as cur:
            escaped_pwd = new_pwd.replace("'", "''")
            cur.execute(f"ALTER USER '{target_user}'@'{target_host}' IDENTIFIED BY '{escaped_pwd}'")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"    [FAIL] ALTER USER 失败: {e}")
        return False


# ==================== 改密：OpenAPI ====================
def openapi_modify_password(client, cluster_id: str, account_name: str, new_pwd: str) -> Tuple[bool, Optional[str]]:
    req = polardb_models.ModifyAccountPasswordRequest(
        dbcluster_id=cluster_id,
        account_name=account_name,
        new_account_password=new_pwd,
    )
    try:
        resp = call_with_retry(lambda: client.modify_account_password(req))
        return True, resp.body.request_id
    except Exception as e:
        print(f"    [FAIL] {type(e).__name__}: {e}")
        return False, None


# ==================== 主流程 ====================
def main():
    parser = argparse.ArgumentParser(description="PolarDB 应急改密 + 账号指纹预警")
    parser.add_argument("--region", required=True)
    parser.add_argument("--cred-file", required=True, help="凭据文件路径")
    parser.add_argument("--test-mode", action="store_true", help="自建 MySQL 测试模式")
    parser.add_argument("--rotate", action="store_true", help="执行改密")
    parser.add_argument("--password-length", type=int, default=32)
    parser.add_argument("--exclude-accounts", nargs="*", default=[])
    parser.add_argument("--init-baseline", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--first-only", action="store_true", help="只处理第一台")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 台")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--cluster-ids", nargs="*", help="仅处理指定集群")
    args = parser.parse_args()

    print("=" * 60)
    print(f"模式: {'测试(自建MySQL)' if args.test_mode else '生产(OpenAPI)'}")
    print(f"地域: {args.region}")
    print(f"操作: {'改密+预警' if args.rotate else '仅预警'}"
          f"{' | 初始化基线' if args.init_baseline else ''}"
          f"{' | 更新基线' if args.update_baseline else ''}")
    print("=" * 60)

    creds = load_credentials(args.cred_file)
    client = None if args.test_mode else create_client(args.region)
    fingerprint = load_fingerprint()

    # 集群列表
    print("\n[1/3] 获取集群列表...")
    clusters = get_clusters(args, client, creds)
    if args.cluster_ids:
        clusters = [c for c in clusters if c["cluster_id"] in args.cluster_ids]
    if not clusters:
        print("未找到目标集群，退出。")
        sys.exit(0)
    if args.first_only:
        clusters = clusters[:1]
        print(f"  [FIRST-ONLY] 只处理第一台")
    elif args.limit > 0:
        clusters = clusters[:args.limit]
        print(f"  [LIMIT] 只处理前 {args.limit} 台")
    print(f"  发现 {len(clusters)} 个集群")

    # 指纹比对
    print("\n[2/3] 账号指纹比对...")
    all_new_accounts = []
    unreachable = []
    rotate_plan = []

    for c in clusters:
        cid = c["cluster_id"]
        print(f"\n  [集群] {cid} ({c['description']})({c['host']})")

        cfg = creds.get(cid)
        if not cfg:
            print(f"    [WARN] 凭据文件无此集群配置，跳过")
            unreachable.append(cid)
            continue

        if c.get("local"):
            host, port = c["host"], c["port"]
        else:
            host = get_connection_string(client, cid)
            port = 3306
        if not host:
            print(f"    [WARN] 无法获取连接地址，跳过")
            unreachable.append(cid)
            continue

        current = query_mysql_user(host, port, cfg["user"], cfg["password"])
        if current is None:
            unreachable.append(cid)
            continue
        print(f"    当前账号数: {len(current)}")

        # diff
        if args.init_baseline or args.update_baseline:
            fingerprint[cid] = current
            print(f"    [BASELINE] 已写入/更新")
        elif cid not in fingerprint:
            print(f"    [WARN] 指纹库无此集群，请先 --init-baseline")
        else:
            cur_set = accounts_to_set(current)
            base_set = accounts_to_set(fingerprint[cid])
            new_accs = cur_set - base_set
            gone_accs = base_set - cur_set
            if new_accs:
                print(f"    [ALERT] 新增 {len(new_accs)} 个账号:")
                for u, h in sorted(new_accs):
                    print(f"      + {u}@{h}")
                    all_new_accounts.append({"cluster": cid, "user": u, "host": h})
            if gone_accs:
                print(f"    [INFO] 消失 {len(gone_accs)} 个账号:")
                for u, h in sorted(gone_accs):
                    print(f"      - {u}@{h}")
            if not new_accs and not gone_accs:
                print(f"    [OK] 与基线一致")

        # 准备改密（白名单过滤）
        if args.rotate:
            allowed = cfg.get("rotate_accounts")  # None 表示不限制
            for acc in current:
                name, acc_host = acc["user"], acc["host"]
                if name.lower() == cfg["user"].lower():
                    print(f"    [SKIP] 高权限账号 {name} 不改密")
                    continue
                if name in args.exclude_accounts:
                    print(f"    [SKIP] 排除账号 {name} 不改密")
                    continue
                if allowed is not None and name not in allowed:
                    print(f"    [SKIP] {name} 不在业务账号白名单")
                    continue
                rotate_plan.append({
                    "cluster": cid, "host": host, "port": port,
                    "account": name, "acc_host": acc_host,
                    "admin_user": cfg["user"], "admin_pwd": cfg["password"],
                    "local": c.get("local", False),
                })

    # 保存基线
    if args.init_baseline or args.update_baseline:
        save_fingerprint(fingerprint)
        print(f"\n指纹库已保存到 {FINGERPRINT_FILE}")
        if not args.rotate:
            send_new_accounts_alert([], unreachable)
            sys.exit(0)

    # 改密
    if args.rotate and rotate_plan:
        print(f"\n[3/3] 执行改密，共 {len(rotate_plan)} 个账号...")
        if not args.yes:
            print("旧密码将立即失效。输入 'YES' 确认: ", end="")
            if input() != "YES":
                print("已取消。")
                sys.exit(0)

        success, failed = 0, 0
        for item in rotate_plan:
            new_pwd = generate_password(args.password_length)
            print(f"\n  [{item['cluster']}] {item['account']}@{item['acc_host']}")
            if item["local"]:
                ok = local_alter_password(
                    item["host"], item["port"], item["admin_user"], item["admin_pwd"],
                    item["account"], item["acc_host"], new_pwd,
                )
                request_id = "local"
            else:
                ok, request_id = openapi_modify_password(
                    client, item["cluster"], item["account"], new_pwd
                )
            if ok:
                store_password(item["cluster"], item["account"], new_pwd)
                print(f"    [OK] {request_id}")
                success += 1
            else:
                failed += 1
        print(f"\n改密完成: 成功 {success}, 失败 {failed}")
        print("注意：仅白名单内业务账号被改密，系统账号未改动。")

    # 告警
    send_new_accounts_alert(all_new_accounts, unreachable)

    # 汇总
    print("\n" + "=" * 60)
    if all_new_accounts:
        print(f"[!] 新增账号: {len(all_new_accounts)} 个")
        for a in all_new_accounts:
            print(f"    {a['cluster']}: {a['user']}@{a['host']}")
    else:
        print("未发现新增账号。")
    if unreachable:
        print(f"[!] 不可达集群: {len(unreachable)} 个")
        for c in unreachable:
            print(f"    {c}")
    print("=" * 60)


if __name__ == "__main__":
    main()