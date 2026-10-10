# Dashboard Reporter · 经营看板日报自动化

把「打开内网看板 → 复制数据 → 手写经营解读 → 发到群里」这条每天重复的链路，做成一条可配置、可定时、可降级的自动化流水线。

- **取数**：按 JSON 配置调用看板 OLAP / REST 接口，输出结构化数据
- **解读**：把数据 + 指标口径/归因规则交给 LLM（内部实例用墨客），生成经营解读；没有 LLM 时自动降级为模板渲染
- **交付**：产出 Markdown 报告，可定时推送到群聊（内部实例用大象）
- **沉淀**：每日归档到知识库，为周报积累趋势数据

---

## 目录结构

```
dashboard-reporter/
├── SKILL.md                        # 技能说明（加载器读这个文件）
├── README.md                       # 本文件：安装、演示、生产部署
├── scripts/
│   ├── fetch_data.py               # 取数（--from-file 支持离线演示）
│   ├── render_report.py            # 渲染 Markdown（默认模板 / 自定义 Jinja2）
│   ├── fetch_cookie.sh             # 刷新 SSO cookie（内网环境）
│   ├── setup.sh                    # 初始化目录 + 生成示例配置
│   ├── config.example.json         # 演示配置
│   └── sample_data.example.json    # 虚构演示数据（不含真实业务数据）
├── knowledge-base-templates/       # 指标口径 / 解读规则与归因 / 业务规律（带占位符）
└── references/
    ├── data-sources.md             # 数据源适配说明
    └── template-guide.md           # 自定义模板写法
```

---

## 一、30 秒离线演示（不需要任何内网权限）

只需要 Python 3（标准库即可）：

```bash
cd dashboard-reporter/scripts

python3 fetch_data.py    --config config.example.json \
                         --from-file sample_data.example.json \
                         --output /tmp/demo_data.json

python3 render_report.py --config config.example.json \
                         --data /tmp/demo_data.json \
                         --output /tmp/demo_report.md

cat /tmp/demo_report.md
```

预期看到 `[DATA_READY]`、`[REPORT_READY]` 两行标记，以及一份「核心数据概览」Markdown 表格 —— 这就是取数→渲染的完整链路。

---

## 二、接入你自己的看板

1. **写配置**（可参考 `scripts/config.example.json`）：

```json
{
  "name": "我的看板日报",
  "data_source": {
    "platform": "generic",
    "base_url": "https://your-dashboard.example.com",
    "cookie_file": "~/.openclaw/dashboard-reporter/cookies/your-domain.txt",
    "queries": [
      { "name": "overview", "endpoint": "/api/query", "body": { "date": "__DATE__" } }
    ]
  },
  "template": "default",
  "schedule": "0 3 * * *"
}
```

- `platform` 支持 `generic`（通用 REST）与 `ocrm`（阅数/OCRM OLAP，内部实例用的适配器）
- body 里的 `__DATE__` 会被替换成目标日期的时间戳
- 取数结果默认落在 `/tmp/dashboard_data_<name>.json`

2. **准备 cookie**（若接口需要登录）：

```bash
mkdir -p ~/.openclaw/dashboard-reporter/cookies
echo "<你的 cookie 值>" > ~/.openclaw/dashboard-reporter/cookies/your-domain.txt
```

3. **自定义报告模板**（可选）：把 `<template>.md.j2` 放进 `~/.openclaw/dashboard-reporter/templates/`，用 `--template-dir` 指定其他目录也可以。模板里可用过滤器：`fmt_wan` / `fmt_pct` / `fmt_arrow` / `fmt_yuan` / `fmt_min`。

---

## 三、前置条件与边界（重要）

| 依赖 | 是否必需 | 说明 |
|------|---------|------|
| 内网看板域名 | 生产必需 | 默认适配 `*.example.com` 的阅数/OCRM；其他数据源走 `generic` 适配器 |
| SSO Cookie | 生产必需 | 内部实例用 `<SSO_COOKIE_NAME>`；也可手动从浏览器 F12 复制 |
| 内网 SSO 登录能力 | **仅内部** | `fetch_cookie.sh` 依赖同环境的 `sso-login.sh` 与本机 9222 端口 CDP，外部请手动提供 cookie |
| Python 3 | 必需 | 标准库即可跑通；`jinja2` 用于自定义模板，`websocket-client` 仅自动取 cookie 时需要 |
| LLM / subagent | 可选 | 有则生成解读，没有则走模板模式 |
| 群消息发送 CLI | 可选 | 内部实例用 `<internal-im-cli>`（大象），外部可换成任意 webhook / 平台消息工具 |

**结论**：这个 Skill 的**通用骨架（取数 + 渲染 + 归档）在任意环境都能跑**，只要你有可访问的数据接口和一个 cookie；
**原始内部实例**（写死某特区 7 个 OLAP 请求、墨客 session、大象群 GID）无法在外部复现，本仓库只保留了它的配置思路。

---

## 四、知识库模板（首次使用必读）

`knowledge-base-templates/` 里是通用外卖经营分析口径，含大量占位符，用前请替换：

```bash
cp knowledge-base-templates/*.md ~/.openclaw/workspace/knowledge-base/
grep -rn "\[示例值\|\[请\|\[目标城市\]" ~/.openclaw/workspace/knowledge-base/
# 把 [目标城市] / [竞对平台] / [示例值，请替换...] 换成本业务真实数据
```

---

## 五、常见问题

- **`[ALERT] Cookie 文件不存在`**：还没放 cookie 文件。只想验证链路请用 `--from-file` 演示模式。
- **`[ALERT] Cookie 可能已过期`**：接口返回 401/403 或 `rescode=30001/10001`，重新获取 cookie。
- **渲染出来是英文指标名**：默认模板直接使用接口返回的字段名，建议改用自定义 Jinja2 模板把字段映射成业务口径名。
- **`avg_delivery_dur` 箭头方向看着反了**：默认模板对所有环比统一用正↑负↓，配送时长这类「越低越好」的指标请用自定义模板反转箭头。
