---
name: dashboard-reporter
description: 从内网看板阅数（dashboard.example.com、data.example.com 等）自动获取 SSO cookie，拉取 OLAP 数据，调用 LLM subagent 基于知识库生成经营解读（Markdown 格式），发送到指定大象群聊。无 subagent 时自动降级为 Python 模板模式。内含通用外卖经营分析知识库模板（指标口径/归因框架/业务规律）。触发词：自动日报、定时发送经营数据、从看板读数据发群、dashboard-reporter、看板数据发大象、创建日报任务、生成经营解读。

metadata:
  skillhub.creator: "<YOUR_MIS_ACCOUNT>"
  skillhub.updater: "<YOUR_MIS_ACCOUNT>"
  skillhub.version: "V3"
  skillhub.source: "FRIDAY Skillhub"
  skillhub.skill_id: "16002"
---

# Dashboard Reporter V3

从内网看板自动拉取数据，调用墨客（LLM subagent）基于知识库生成经营解读，发送到大象群聊。每日自动归档到案例库，为周报积累数据。

---

## 整体架构

**内部实例（作者实际在跑的版本，含墨客与大象）**：

```
daily_report.py（Python）
  ├── 1. 读取 SSO Cookie → dashboard.example.com OLAPQuery 拉取数据
  ├── 2. 构建结构化数据 JSON + 表格框架（纯数字部分）
  ├── 3. sessions_send → 墨客（label=moke）生成分析文字
  ├── 4. 组装完整 Markdown 日报 → /tmp/daily_report_output.txt
  ├── 5. 归档到 knowledge-base/daily-reports/YYYY-MM-DD.md
  └── 6. npx <internal-im-cli> send markdown → 大象群
```

**本仓库发布的通用框架（与上面对应的可复用部分）**：

```
fetch_data.py --config <report>.json        # 读 cookie + 拉 OLAP → /tmp/dashboard_data_<name>.json
  └── --from-file <sample>.json             # 演示模式：跳过 cookie 与网络，直接用本地样例数据

render_report.py --config <report>.json     # 默认模板 / 自定义 Jinja2 模板
  └── → /tmp/report_output.txt（Markdown）

（可选）LLM 解读：把数据 JSON 交给你的 agent / subagent，并挂上 knowledge-base 里的口径与归因规则
（可选）发送：交给平台自带的消息工具，或自行接 webhook
```

**关键设计原则**：
- 取数脚本只负责取数和拼表格，**不写任何分析文字**
- 分析文字交给 LLM（内部用墨客）基于知识库生成，解读质量远优于模板；没有 LLM 时自动降级为模板模式
- Cookie 失效时可告警或打印 `[ALERT]`，等用户手动更新后重试

---

## 核心文件路径

> ⚠️ **两套路径要分清**：下面第一张表是**本仓库随 Skill 一起发布的通用框架**（任何人 clone 下来就能用）；
> 第二张表是**作者在美团内部跑的那套实例**（写死的某特区日报流程），里面的 `daily_report.py`、墨客 session、群 GID 等**不在本仓库内**（具体值已打码），外部环境没有这些文件。

### A. 本仓库提供的文件（通用框架，可离线演示）

| 文件 | 路径 | 说明 |
|------|------|------|
| 取数脚本 | `scripts/fetch_data.py` | 按 JSON 配置拉 OLAP / REST 数据，输出 `/tmp/dashboard_data_<name>.json` |
| 渲染脚本 | `scripts/render_report.py` | 用 Jinja2 模板或内置默认模板渲染 Markdown |
| Cookie 获取 | `scripts/fetch_cookie.sh` | 为指定域名获取/刷新 SSO cookie（依赖内网 SSO，见「前置条件」） |
| 初始化 | `scripts/setup.sh` | 建 `~/.openclaw/dashboard-reporter/` 目录并生成示例配置 |
| 演示配置 | `scripts/config.example.json` | 离线演示用的报告配置 |
| 演示数据 | `scripts/sample_data.example.json` | 虚构样例数据，不含任何真实业务数据 |
| 知识库模板 | `knowledge-base-templates/*.md` | 指标口径 / 解读规则与归因 / 业务规律，需替换占位符 |
| 参考文档 | `references/data-sources.md`、`references/template-guide.md` | 数据源适配与模板写法 |

### B. 内部实例路径（仅供参考，仓库内没有这些文件）

| 文件 | 路径 |
|------|------|
| 主脚本 | `~/.openclaw/workspace/scripts/daily_report.py` |
| 看板 OLAP 请求体模板 | `~/.openclaw/workspace/memory/*_olap_body_template.json`（打码，示例） |
| Cookie 文件 | `~/.openclaw/workspace/scripts/ocrm_cookie.txt`（只存 ssoid 值） |
| 细分维度请求体模板 | `~/.openclaw/workspace/memory/*_body_templates.json`（打码，示例） |
| 案例库目录 | `~/.openclaw/workspace/knowledge-base/daily-reports/` |
| 案例库索引 | `~/.openclaw/workspace/knowledge-base/04-案例库.md` |
| 临时输出 | `/tmp/daily_report_output.txt`（每次重新生成，不持久）|

---

## 前置条件（重要：这个 Skill 不能"装完就跑"）

| 依赖 | 是否必需 | 说明 |
|------|---------|------|
| 内网看板域名 | 生产必需 | 默认 `*.example.com`（阅数/OCRM）；换其他数据源需改 `config.data_source` |
| SSO Cookie | 生产必需 | `<SSO_COOKIE_NAME>` 的值；也可手动 F12 复制后写入 cookie 文件 |
| 内网 SSO 登录能力 | 生产必需 | `fetch_cookie.sh` 依赖同环境的 `sso-login.sh` 与本地 9222 端口 CDP，非内网用户请手动提供 cookie |
| Python 3 | 必需 | 仅标准库即可跑通；装了 `jinja2` 可用自定义模板，装了 `websocket-client` 才能自动取 cookie |
| 墨客（LLM subagent） | 可选 | 有则生成 LLM 解读；没有则自动降级为模板渲染 |
| 大象群发送 | 可选 | 需要内部 CLI `<internal-im-cli>`；没有则只产出 Markdown 文件 |

**离线验证（不需要任何内网权限）**：

```bash
cd dashboard-reporter/scripts
python3 fetch_data.py   --config config.example.json --from-file sample_data.example.json --output /tmp/demo_data.json
python3 render_report.py --config config.example.json --data /tmp/demo_data.json --output /tmp/demo_report.md
cat /tmp/demo_report.md
```

预期输出：一张「核心数据概览」Markdown 表格 + `[DATA_READY]` / `[REPORT_READY]` 两行标记。

---

## 定时任务配置（内部实例，示例）

- **触发时间**：每天北京时间 11:00（UTC 03:00）
- **Schedule**：`0 11 * * * @ Asia/Shanghai`
- **测试群 / 正式群**：`<TEST_GID>` / `<PROD_GID>`（具体值已打码）
- **Cron Job ID**：`<CRON_JOB_ID>`（具体值已打码）
- **执行命令**：`python3 ~/.openclaw/workspace/scripts/daily_report.py`（该文件不在本仓库，用 `fetch_data.py` + `render_report.py` 替代即可）

---

## 数据源

- **平台**：内部阅数/OCRM 看板（`https://data.ocrm.<内部域名>`，已打码）
- **接口**：`POST /<internal>/OLAPQuery`
- **认证**：Cookie `<SSO_COOKIE_NAME>=<value>`（内部 cookie 名已打码）
- **拉取维度**（共 7 个请求）：
  1. 特区总览（城市编码已打码）
  2. 全国直营白领总览（无城市过滤）
  3. 品类细分（美食 / 甜点 / 饮品）
  4. 商家类型细分（城市商家 / 区域KA / 全国KA）
  5. 餐饮用户类型（新客 / 老客）
  6. 订单实付单均价区间
  7. 餐饮用户分层（成熟 / 过渡 / 尝鲜）

---

## 墨客（LLM subagent）调用

```python
# Gateway HTTP 直调墨客持久 session
GW_URL = "http://127.0.0.1:18789/tools/invoke"
MOKE_SESSION_KEY = "agent:moke:main"

# 调用方式
POST /tools/invoke
{"tool": "sessions_send", "args": {"sessionKey": "agent:moke:main", "message": <数据JSON>, "timeoutSeconds": 150}}

# 取回复
reply = resp["result"]["details"]["reply"]
```

**注意**：`sessions_send` 返回 `ok=true` 但 `details.status` 可能是 `"forbidden"`，需单独检查。

墨客的知识库：
- `knowledge-base/01-指标口径.md`
- `knowledge-base/02-解读规则与归因.md`
- `knowledge-base/03-业务规律.md`
- `knowledge-base/04-案例库.md`（含历史日报案例）

---

## 大象发送

```bash
# 发送命令
npx <internal-im-cli> send markdown --gid <gid> --json -- "<内容>"

# 成功判断：ok=true 且 status="confirmed"
# status="queued" = session 断开，需 login 后重试
# login 命令：npx <internal-im-cli> login --timeout-sec 60 --json
```

**重要**：只有 `confirmed` + `msgId` 才算真正送达，`queued` 视为失败需重试。

---

## Cookie 管理

Cookie 只需存储 `<SSO_COOKIE_NAME>` 的值（不含 key 名）：

```bash
echo "<ssoid值>" > ~/.openclaw/workspace/scripts/ocrm_cookie.txt
```

**Cookie 失效处理流程**（脚本自动执行）：
1. 检测到 HTTP 401 或 `rescode=10001/10003`
2. 大象私信告警杨同学，提示登录 `https://dashboard.example.com` 后 F12 → Application → Cookies 复制 `<SSO_COOKIE_NAME>`
3. 用户更新 cookie 文件后，下次定时任务自动恢复

若需立即重跑：
```bash
python3 ~/.openclaw/workspace/scripts/daily_report.py
```

---

## 案例库归档

每次生成日报后自动执行：
1. 写入 `knowledge-base/daily-reports/YYYY-MM-DD.md`（完整日报）
2. 更新 `04-案例库.md` 索引表格（新增当日摘要行）

归档数据支持后续周报生成：读取 7 天 `daily-reports/*.md` → 墨客提炼趋势 → 生成周报。

---

## 日报格式（V6 Markdown）

```
### 📊 某特区直营日报 · YYYY/MM/DD

#### 🔑 核心结论
（3条加粗结论 + ⚠️ 持续跟踪项）

#### 📦 经营规模
（文字叙述 + 某特区表格 + 全国基准表格）

#### 👤 流量及用户
（文字叙述 + 用户分层表格）

#### 🏪 商户及供给
（文字叙述 + 品类/商家类型表格）

#### 🚴 履约体验
（文字叙述 + 配送时长/缺陷率表格）

---
*——来自杨铖灵的助理小王子Bot，欢迎私信~*
```

---

## 知识库模板（首次使用必读）

skill 内置了 `knowledge-base-templates/` 目录，包含通用外卖经营分析知识库模板：

| 模板文件 | 内容 |
|---------|------|
| `01-指标口径-template.md` | GTV/订单/流量/补贴/M值/天气等核心指标定义与口径 |
| `02-解读规则与归因-template.md` | 解读红线规则、归因框架、优秀/及格标准 |
| `03-业务规律-template.md` | 周内/季节/竞争/收补期规律，排除正常波动找真异动 |

**初始化步骤**：
```bash
# 1. 复制模板到你的知识库目录
cp knowledge-base-templates/*.md ~/.openclaw/workspace/knowledge-base/

# 2. 搜索并替换所有占位符
grep -rn "\[示例值\|\[请\|\[目标城市\]" knowledge-base/

# 3. 替换为你业务的真实数据：
#    - [目标城市] → 你负责的城市
#    - [竞对平台] → 竞争对手名称
#    - [示例值，请替换...] → 填入历史实测数据
```

---

## 降级模式（无 LLM 时自动生效）

不接 LLM subagent 时，流程自动降级为 **模板渲染模式**：

- `render_report.py` 使用内置默认模板（或 `~/.openclaw/dashboard-reporter/templates/<name>.md.j2`）生成固定格式报告
- 只含数据表格和简单文字说明，无深度归因解读
- 所有数字正常展示，发送流程不受影响

**离线自测**（验证取数→渲染链路，不需要内网）：

```bash
python3 fetch_data.py    --config config.example.json --from-file sample_data.example.json --output /tmp/demo_data.json
python3 render_report.py --config config.example.json --data /tmp/demo_data.json --output /tmp/demo_report.md
```

**接你自己的 LLM**（可选，开启解读）：
把取数输出（`/tmp/dashboard_data_*.json`）连同 `knowledge-base/01~03` 的口径与归因规则交给任意 agent / subagent，让它产出解读文字，再拼到模板报告前面即可；内部实例用的 session key 配置（`MOKE_SESSION_KEY`）属于作者内网环境，不在本仓库。

---

## 新增日报任务流程

用户说"帮我把 XXX 看板的数据每天发到 YYY 群"时：

1. **收集配置**：看板 URL、发送时间（北京时间）、目标群 GID
2. **获取 Cookie**：引导用户登录看板，F12 复制 ssoid，写入对应 cookie 文件
3. **调试取数**：先跑 `fetch_data.py --config ...` 确认数据正常，再跑 `render_report.py` 确认排版
4. **测试发送**：只发测试群，等用户确认（发送步骤按平台自带的消息工具实现）
5. **创建定时任务**：`openclaw cron add`，确认时间和命令
6. **正式运行**：首次定时触发后确认送达

---

## 注意事项

- 大象不支持 `<sub>` 等 HTML 标签，只用标准 Markdown
- `/tmp/` 不持久，报告每次运行重新生成；持久化存档在 `knowledge-base/daily-reports/`
- 墨客 subagent 需处于运行状态（`sessions_list` 确认 `label=moke` 存在）
- 首次部署需确认 Gateway `tools.agentToAgent.enabled: true`，否则 sessions_send 会报 forbidden
