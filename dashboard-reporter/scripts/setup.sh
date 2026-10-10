#!/usr/bin/env bash
# setup.sh - 初始化 dashboard-reporter 目录结构
# 用法：bash setup.sh [mis_account]

set -euo pipefail

BASE_DIR="${HOME}/.openclaw/dashboard-reporter"
MIS="${1:-}"

echo "📦 初始化 dashboard-reporter..."

mkdir -p "$BASE_DIR/reports"
mkdir -p "$BASE_DIR/cookies"
mkdir -p "$BASE_DIR/templates"
mkdir -p "$BASE_DIR/logs"

# 安装 Python 依赖（jinja2 可选，降级模式不需要）
if python3 -c "import jinja2" 2>/dev/null; then
  echo "✅ jinja2 已安装"
else
  echo "📥 安装 jinja2..."
  pip3 install jinja2 --quiet || echo "⚠️  jinja2 安装失败，将使用降级渲染模式"
fi

if python3 -c "import websocket" 2>/dev/null; then
  echo "✅ websocket-client 已安装"
else
  echo "📥 安装 websocket-client..."
  pip3 install websocket-client --quiet || echo "⚠️  websocket-client 安装失败"
fi

echo ""
echo "✅ 初始化完成！目录结构："
echo "   $BASE_DIR/"
echo "   ├── reports/     # 看板配置文件（*.json）"
echo "   ├── cookies/     # SSO cookie 缓存"
echo "   ├── templates/   # 自定义 Jinja2 模板（*.md.j2）"
echo "   └── logs/        # 运行日志"
echo ""
echo "下一步：创建第一个报告配置"
echo "  参考示例：~/.openclaw/dashboard-reporter/reports/example.json"

# 生成示例配置
cat > "$BASE_DIR/reports/example.json" << 'EOF'
{
  "name": "示例看板日报",
  "data_source": {
    "platform": "ocrm",
    "base_url": "https://dashboard.example.com",
    "cookie_domain": "dashboard.example.com",
    "cookie_file": "~/.openclaw/dashboard-reporter/cookies/dashboard.example.com.txt",
    "queries": [
      {
        "name": "overview",
        "endpoint": "/olap/query",
        "body": {
          "注释": "把看板的 OLAP 请求体粘贴到这里，用 __DATE__ 替换日期时间戳"
        }
      }
    ]
  },
  "template": "default",
  "schedule": "0 3 * * *",
  "delivery": {
    "test_gid": "",
    "prod_gid": "",
    "notify_uid": ""
  }
}
EOF

echo "📄 示例配置已生成：$BASE_DIR/reports/example.json"
