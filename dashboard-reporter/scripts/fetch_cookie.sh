#!/usr/bin/env bash
# fetch_cookie.sh - 为指定域名获取/刷新 SSO cookie
# 用法：./fetch_cookie.sh <domain> [mis_account]
# 输出：cookie 值写入 ~/.openclaw/dashboard-reporter/cookies/<domain>.txt
#
# 支持域名：dashboard.example.com, data.example.com, 等 *.example.com 域名

set -euo pipefail

DOMAIN="${1:-}"
MIS="${2:-<YOUR_MIS_ACCOUNT>}"
COOKIE_DIR="${HOME}/.openclaw/dashboard-reporter/cookies"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$DOMAIN" ]]; then
  echo "用法: $0 <domain> [mis_account]" >&2
  exit 1
fi

mkdir -p "$COOKIE_DIR"
COOKIE_FILE="$COOKIE_DIR/${DOMAIN}.txt"

# 1. 先检查现有 cookie 是否有效（通过 HEAD 请求）
check_cookie_valid() {
  local cookie_val="$1"
  # 用 curl 访问域名首页，检查是否被重定向到 SSO
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Cookie: <SSO_COOKIE_NAME>=${cookie_val}" \
    --max-time 5 \
    "https://${DOMAIN}/" 2>/dev/null || echo "000")
  [[ "$http_code" != "302" && "$http_code" != "401" && "$http_code" != "000" ]]
}

if [[ -f "$COOKIE_FILE" ]]; then
  existing_cookie=$(cat "$COOKIE_FILE" | tr -d '[:space:]')
  if [[ -n "$existing_cookie" ]] && check_cookie_valid "$existing_cookie"; then
    echo "✅ Cookie 有效，跳过登录：$COOKIE_FILE"
    exit 0
  fi
  echo "⚠️  Cookie 已过期，重新登录..."
fi

# 2. 执行 SSO 登录
echo "🔐 执行 SSO 登录（mis: $MIS）..."
SSO_SCRIPT="<内网>/sso-login.sh"
if [[ ! -f "$SSO_SCRIPT" ]]; then
  echo "❌ 找不到 SSO 登录脚本: $SSO_SCRIPT" >&2
  exit 1
fi
bash "$SSO_SCRIPT" "$MIS"

# 3. 从 CDP 提取目标域的 cookie
echo "🍪 从浏览器提取 cookie（domain: $DOMAIN）..."
COOKIE_VAL=$(python3 - "$DOMAIN" <<'PYEOF'
import sys, json, urllib.request, urllib.error

domain = sys.argv[1]
CDP_URL = "http://127.0.0.1:9222"

# 获取 tab 列表
try:
    tabs_resp = urllib.request.urlopen(f"{CDP_URL}/json", timeout=5)
    tabs = json.load(tabs_resp)
except Exception as e:
    print(f"[ERROR] CDP 不可用: {e}", file=sys.stderr)
    sys.exit(1)

# 找到第一个可用 tab
tab = next((t for t in tabs if t.get("type") == "page"), None)
if not tab:
    print("[ERROR] 没有可用的 tab", file=sys.stderr)
    sys.exit(1)

ws_url = tab["webSocketDebuggerUrl"]

import websocket, threading, time, uuid

result_cookies = []
done = threading.Event()

def on_message(ws, message):
    data = json.loads(message)
    if data.get("id") == 1:
        cookies = data.get("result", {}).get("cookies", [])
        for c in cookies:
            if domain in c.get("domain", ""):
                # 优先找常见 ssoid 字段
                if c["name"] in ("<SSO_COOKIE_NAME>", "ssoid", "sso_token", "SSOID"):
                    result_cookies.append(c)
        done.set()

def on_open(ws):
    ws.send(json.dumps({
        "id": 1,
        "method": "Network.getAllCookies"
    }))

ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_open=on_open)
t = threading.Thread(target=ws.run_forever)
t.daemon = True
t.start()
done.wait(timeout=10)
ws.close()

if result_cookies:
    # 取最新的 ssoid
    best = sorted(result_cookies, key=lambda c: c.get("expires", 0), reverse=True)[0]
    print(best["value"])
else:
    print("[ERROR] 未找到目标 cookie", file=sys.stderr)
    sys.exit(1)
PYEOF
)

if [[ -z "$COOKIE_VAL" || "$COOKIE_VAL" == "[ERROR]"* ]]; then
  echo "❌ 提取 cookie 失败: $COOKIE_VAL" >&2
  exit 1
fi

echo "$COOKIE_VAL" > "$COOKIE_FILE"
echo "✅ Cookie 已保存到 $COOKIE_FILE"
