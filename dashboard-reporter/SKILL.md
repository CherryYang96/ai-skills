---
name: dashboard-reporter
description: 从美团内网看板阅数（ocrm.sankuai.com、data.sankuai.com 等）自动获取 SSO cookie，拉取 OLAP 数据，调用 LLM subagent 基于知识库生成经营解读（Markdown 格式），发送到指定大象群聊。无 subagent 时自动降级为 Python 模板模式。内含通用外卖经营分析知识库模板（指标口径/归因框架/业务规律）。触发词：自动日报、定时发送经营数据、从看板读数据发群、dashboard-reporter、看板数据发大象、创建日报任务、生成经营解读。

metadata:
  skillhub.creator: "yangchengling"
  skillhub.updater: "yangchengling"
  skillhub.version: "V3"
  skillhub.source: "FRIDAY Skillhub"
  skillhub.skill_id: "16002"
---

# Dashboard Reporter V3

从美团内网看板自动拉取数据，调用墨客（LLM subagent）基于知识库生成经营解读，发送到大象群聊。每日自动归档到案例库，为周报积累数据。

---

## 整体架构

```
daily_report.py（Python）
  ├── 1. 读取 SSO Cookie → data.ocrm.sankuai.com OLAPQuery 拉取数据
  ├── 2. 构建结构化数据 JSON + 表格框架（纯数字部分）
  ├── 3. sessions_send → 墨客（label=moke）生成分析文字
  ├── 4. 组装完整 Markdown 日报 → /tmp/daily_report_output.txt
  ├── 5. 归档到 knowledge-base/daily-reports/YYYY-MM-DD.md
  └── 6. npx @waimai/meituan-local-xm-cli send markdown → 大象群
```

**关键设计原则**：
- Python 只负责取数和拼表格，**不写任何分析文字**
- 分析文字全部由墨客基于知识库生成，LLM 解读质量远优于模板
- Cookie 失效时通过大象私信告警，等用户手动更新后自动重试

---

## 核心文件路径

| 文件 | 路径 |
|------|------|
| 主脚本 | `~/.openclaw/workspace/scripts/daily_report.py` |
| Cookie 文件 | `~/.openclaw/workspace/scripts/ocrm_cookie.txt`（只存 ssoid 值） |
| 杭州 OLAP 请求体模板 | `~/.openclaw/workspace/memory/ocrm_olap_body_template.json` |
| 全国 OLAP 请求体模板 | `~/.openclaw/workspace/memory/national_olap_body_template.json` |
| 细分维度请求体模板 | `~/.openclaw/workspace/memory/subdivision_body_templates.json` |
| 案例库目录 | `~/.openclaw/workspace/knowledge-base/daily-reports/` |
| 案例库索引 | `~/.openclaw/workspace/knowledge-base/04-案例库.md` |
| 临时输出 | `/tmp/daily_report_output.txt`（每次重新生成，不持久）|

---

## 定时任务配置

- **Cron Job ID**：`a682bfc9-0594-4643-85e8-6175c9b7af13`
- **触发时间**：每天北京时间 11:00（UTC 03:00）
- **Schedule**：`0 11 * * * @ Asia/Shanghai`
- **测试群 GID**：`70454604015`
- **正式群 GID**：`69793911869`
- **执行命令**：`python3 ~/.openclaw/workspace/scripts/daily_report.py`

---

## 数据源

- **平台**：`data.ocrm.sankuai.com`（阅数/OCRM）
- **接口**：`POST /igate/mapinsight/dashBoard/v2/OLAPQuery?ssoprotect=1&...`
- **认证**：Cookie `xianfu_waimai_ssoid=<value>`
- **拉取维度**（共 7 个请求）：
  1. 杭州特区总览（`map_second_district=330100`）
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
npx @waimai/meituan-local-xm-cli send markdown --gid <gid> --json -- "<内容>"

# 成功判断：ok=true 且 status="confirmed"
# status="queued" = session 断开，需 login 后重试
# login 命令：npx @waimai/meituan-local-xm-cli login --timeout-sec 60 --json
```

**重要**：只有 `confirmed` + `msgId` 才算真正送达，`queued` 视为失败需重试。

---

## Cookie 管理

Cookie 只需存储 `xianfu_waimai_ssoid` 的值（不含 key 名）：

```bash
echo "<ssoid值>" > ~/.openclaw/workspace/scripts/ocrm_cookie.txt
```

**Cookie 失效处理流程**（脚本自动执行）：
1. 检测到 HTTP 401 或 `rescode=10001/10003`
2. 大象私信告警杨同学，提示登录 `https://data.ocrm.sankuai.com` 后 F12 → Application → Cookies 复制 `xianfu_waimai_ssoid`
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
### 📊 杭州特区直营日报 · YYYY/MM/DD

#### 🔑 核心结论
（3条加粗结论 + ⚠️ 持续跟踪项）

#### 📦 经营规模
（文字叙述 + 杭州特区表格 + 全国基准表格）

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

## 降级模式（无 subagent 时自动生效）

若未配置 LLM subagent（`MOKE_SESSION_KEY` 为空或调用失败），脚本自动降级为 **Python 模板模式**：

- 使用内置 Jinja2 模板生成固定格式报告
- 只含数据表格和简单文字说明，无深度归因解读
- 所有数字正常展示，发送流程不受影响

**配置 subagent**（可选，开启 LLM 解读）：
```python
# 在 daily_report.py 顶部配置区修改：
MOKE_SESSION_KEY = "agent:moke:main"  # 你的 LLM subagent session key
# 留空则自动降级：
# MOKE_SESSION_KEY = ""
```

---

## 新增日报任务流程

用户说"帮我把 XXX 看板的数据每天发到 YYY 群"时：

1. **收集配置**：看板 URL、发送时间（北京时间）、目标群 GID
2. **获取 Cookie**：引导用户登录看板，F12 复制 ssoid，写入对应 cookie 文件
3. **调试取数**：直接运行脚本，确认数据正常
4. **测试发送**：先发测试群（`--test-only` 参数），等用户确认
5. **创建定时任务**：`openclaw cron add`，确认时间和命令
6. **正式运行**：首次定时触发后确认送达

---

## 注意事项

- 大象不支持 `<sub>` 等 HTML 标签，只用标准 Markdown
- `/tmp/` 不持久，报告每次运行重新生成；持久化存档在 `knowledge-base/daily-reports/`
- 墨客 subagent 需处于运行状态（`sessions_list` 确认 `label=moke` 存在）
- 首次部署需确认 Gateway `tools.agentToAgent.enabled: true`，否则 sessions_send 会报 forbidden
