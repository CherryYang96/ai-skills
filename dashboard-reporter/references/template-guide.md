# 报告模板指南

## 字体层级规范（大象 Markdown）

```
### 📊 报告大标题          ← 最大（### 三级标题）
#### 🔑 章节标题           ← 次大（#### 四级标题）
**粗体子节名称**           ← 与正文同级（加粗）
正文叙述段落               ← 普通文字
| Markdown 表格 |         ← 最小（渲染器原生小字）
```

**注意**：
- 大象不支持 `<sub>`、`<small>` 等 HTML 标签，会直接渲染为文本
- 发送必须用 `dx send markdown`，不能用普通 `dx send`
- 章节间用 `---` 分隔

---

## Jinja2 模板语法

模板文件存放在 `~/.openclaw/dashboard-reporter/templates/`，使用 Jinja2 语法：

```jinja2
### 📊 {{ report_title }} · {{ date_cn }}

#### 🔑 核心结论

> {{ core_summary }}

---

#### 📦 经营规模

**{{ city_name }}**

| 指标 | 数值 | DoD | WoW | YoY |
|------|------|-----|-----|-----|
| 消费订单量 | {{ data.ord_num | fmt_wan }}万单 | {{ data.ord_dod | fmt_arrow }} | {{ data.ord_wow | fmt_arrow }} | {{ data.ord_yoy | fmt_arrow }} |
| 实收GTV | {{ data.gtv | fmt_wan }}万元 | {{ data.gtv_dod | fmt_arrow }} | {{ data.gtv_wow | fmt_arrow }} | - |
```

---

## 内置格式化函数

| 函数 | 用途 | 示例输入 | 示例输出 |
|------|------|----------|----------|
| `fmt_wan(v)` | 转万单位 | `123456` | `12.35万` |
| `fmt_pct(v)` | 转百分比 | `0.0521` | `5.21%` |
| `fmt_arrow(v)` | 带箭头的环比 | `0.052` | `↑5.2%` |
| `fmt_yuan(v)` | 元，2位小数 | `38.567` | `38.57元` |
| `fmt_min(v)` | 分钟，2位小数 | `28.345` | `28.35分钟` |

`fmt_arrow` 规则：正数→`↑红色`，负数→`↓绿色`，零→`-`

---

## 默认模板结构（default）

适用于通用经营看板，包含以下章节：

1. **核心结论** - 用引用块 `>` 包裹 2~3 条跟踪项
2. **经营规模** - 订单量、GTV、客单价、补贴率
3. **流量及用户** - 消费用户、访购率、新老客
4. **商户及供给** - 品类分布、商家类型
5. **履约体验** - 配送时长、缺陷率

如果看板数据不包含某些字段，对应章节自动跳过。

---

## 自定义模板

1. 复制默认模板：
   ```bash
   cp ~/.openclaw/dashboard-reporter/templates/default.md.j2 \
      ~/.openclaw/dashboard-reporter/templates/my_report.md.j2
   ```

2. 编辑模板，修改章节结构和字段映射

3. 在配置文件 `reports/<name>.json` 中指定：
   ```json
   { "template": "my_report" }
   ```
