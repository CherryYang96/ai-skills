#!/usr/bin/env python3
"""
fetch_data.py - 通用看板数据拉取脚本

用法：
  python3 fetch_data.py --config ~/.openclaw/dashboard-reporter/reports/my_report.json
  python3 fetch_data.py --config my_report.json --date 2026-03-24

  # 演示模式（离线，不需要内网与 cookie，用随仓库提供的样例数据跑通全链路）
  python3 fetch_data.py --config config.example.json --from-file sample_data.example.json

输出：JSON 数据写入 /tmp/dashboard_data_<name>.json
"""

import argparse
import json
import http.client
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Cookie 读取 ───────────────────────────────────────────────────────────────

def load_cookie(cookie_file: str, field_name: str = None) -> str:
    path = Path(cookie_file).expanduser()
    if not path.exists():
        raise PermissionError(f"Cookie 文件不存在: {path}\n请先运行 fetch_cookie.sh {field_name or ''}")
    val = path.read_text().strip()
    if not val:
        raise PermissionError(f"Cookie 文件为空: {path}")
    return val

# ─── HTTP 请求 ─────────────────────────────────────────────────────────────────

def do_post(host: str, path: str, body: dict, headers: dict) -> dict:
    payload = json.dumps(body).encode("utf-8")
    conn = http.client.HTTPSConnection(host, timeout=30)
    conn.request("POST", path, payload, headers)
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8")
    conn.close()
    if resp.status in (401, 403):
        raise PermissionError(f"HTTP {resp.status}：Cookie 可能已过期")
    data = json.loads(raw)
    # 通用错误码检测
    rescode = data.get("rescode", data.get("code", 0))
    if rescode in (30001, 10001, 401):
        raise PermissionError(f"接口返回 rescode={rescode}：Cookie 已过期")
    return data

# ─── 平台适配器 ────────────────────────────────────────────────────────────────

def fetch_ocrm(source_cfg: dict, cookie_val: str, date_ts: int) -> dict:
    """dashboard.example.com OLAP Query 适配器"""
    base_url = source_cfg["base_url"]
    host = base_url.replace("https://", "").replace("http://", "").split("/")[0]
    
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"<SSO_COOKIE_NAME>={cookie_val}",
        "X-Requested-With": "XMLHttpRequest",
        "M-UserContext": "eyJsb2NhbGUiOiJ6aCIsInRpbWVab25lIjoiQXNpYS9TaGFuZ2hhaSJ9",
    }
    
    results = {}
    for query in source_cfg.get("queries", []):
        name = query["name"]
        endpoint = query.get("endpoint", "/olap/query")
        body = dict(query.get("body", {}))
        # 注入日期（如果 body 模板里有 __DATE__ 占位符）
        body_str = json.dumps(body).replace('"__DATE__"', str(date_ts))
        body = json.loads(body_str)
        
        resp = do_post(host, endpoint, body, headers)
        results[name] = resp.get("data", {}).get("list", resp.get("data", {}))
    
    return results

def fetch_generic(source_cfg: dict, cookie_val: str, date_ts: int) -> dict:
    """通用 REST API 适配器"""
    base_url = source_cfg["base_url"]
    host = base_url.replace("https://", "").replace("http://", "").split("/")[0]
    cookie_field = source_cfg.get("cookie_field", "ssoid")
    
    headers = {
        "Content-Type": "application/json",
        "Cookie": f"{cookie_field}={cookie_val}",
    }
    headers.update(source_cfg.get("extra_headers", {}))
    
    results = {}
    for query in source_cfg.get("queries", []):
        name = query["name"]
        endpoint = query.get("endpoint", "/api/query")
        body = dict(query.get("body", {}))
        body_str = json.dumps(body).replace('"__DATE__"', str(date_ts))
        body = json.loads(body_str)
        
        resp = do_post(host, endpoint, body, headers)
        # 尝试通用数据提取
        data = resp.get("data", resp)
        if isinstance(data, dict):
            data = data.get("list", data.get("rows", data.get("result", data)))
        results[name] = data
    
    return results

# ─── 主逻辑 ────────────────────────────────────────────────────────────────────

PLATFORM_ADAPTERS = {
    "ocrm": fetch_ocrm,
    "generic": fetch_generic,
}

def main():
    parser = argparse.ArgumentParser(description="通用看板数据拉取")
    parser.add_argument("--config", required=True, help="报告配置文件路径")
    parser.add_argument("--date", help="数据日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--output", help="输出文件路径（默认 /tmp/dashboard_data_<name>.json）")
    parser.add_argument("--from-file", dest="from_file",
                        help="演示模式：直接读取本地样例数据 JSON，不联网、不需要 cookie")
    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config).expanduser()
    with open(config_path) as f:
        config = json.load(f)

    report_name = config["name"].replace(" ", "_")
    source_cfg = config["data_source"]
    platform = source_cfg.get("platform", "generic")

    # 日期处理
    tz_shanghai = timezone(timedelta(hours=8))
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=tz_shanghai)
    else:
        now = datetime.now(tz_shanghai)
        target_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    date_ts = int(target_date.timestamp() * 1000)
    date_iso = target_date.strftime("%Y-%m-%d")

    # ─── 演示模式：本地样例数据，跳过 cookie 与网络 ──────────────────────────────
    if args.from_file:
        sample_path = Path(args.from_file).expanduser()
        if not sample_path.exists():
            print(f"[ALERT] 样例数据文件不存在: {sample_path}", file=sys.stderr)
            sys.exit(1)
        with open(sample_path) as f:
            sample = json.load(f)
        # 允许两种写法：完整 payload（含 data/date）或只给 data 内容
        if isinstance(sample, dict) and "data" in sample:
            payload = dict(sample)
            payload.setdefault("report_name", config["name"])
            payload.setdefault("date", date_iso)
            payload.setdefault("date_ts", date_ts)
        else:
            payload = {
                "report_name": config["name"],
                "date": date_iso,
                "date_ts": date_ts,
                "data": sample,
            }
        output_file = args.output or f"/tmp/dashboard_data_{report_name}.json"
        with open(output_file, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[DATA_READY] {output_file} (demo/offline)")
        return

    # 加载 cookie
    cookie_file = Path(source_cfg["cookie_file"]).expanduser()
    try:
        cookie_val = load_cookie(str(cookie_file))
    except PermissionError as e:
        print(f"[ALERT] {e}", file=sys.stderr)
        sys.exit(1)

    # 拉取数据
    adapter = PLATFORM_ADAPTERS.get(platform, fetch_generic)
    try:
        data = adapter(source_cfg, cookie_val, date_ts)
    except PermissionError as e:
        print(f"[ALERT] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ALERT] 数据拉取异常: {e}", file=sys.stderr)
        raise

    # 输出
    output = {
        "report_name": config["name"],
        "date": date_iso,
        "date_ts": date_ts,
        "data": data,
    }
    output_file = args.output or f"/tmp/dashboard_data_{report_name}.json"
    with open(output_file, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"[DATA_READY] {output_file}")


if __name__ == "__main__":
    main()
