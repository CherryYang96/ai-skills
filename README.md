# AI Skills Collection

基于 OpenClaw / CatPaw 平台构建的 AI Skill 合集。这些 Skill 是在美团实际业务场景中打磨出来的，覆盖**认知蒸馏**、**分析能力提升**和**数据自动化**三个方向。

---

## 📂 Skill 列表

### 1. [Cyber-MaoMao（虚拟毛毛）](./cyber-maomao/)

> 基于真实业务负责人 194 篇周度工作笔记的**认知蒸馏**，将一个人的思维方式产品化为可交互的 AI 人格。

- **定位**：不是聊天机器人，是一个有立场、有认知边界的思维型对话者
- **核心能力**：把「人的问题」还原为「结构问题」，用跨域类比（经济学/博弈论/认知心理学）发现洞见
- **适用场景**：拆解复杂业务问题、压力测试判断、寻找杠杆点
- **方法论**：五维认知模型（D1-D5）+ 演化轨迹 + 认知边界自省
- **Friday 广场下载量**：2,300+

### 2. [分析师炼金术（Sharp Analyst）](./sharp-analyst/)

> 面向商业分析师的 **AI 分析教练**，用严厉但精确的反馈帮你提升分析质量。

- **Review 模式**：三维度评分（认知价值/归因质量/行动指向）+ 相关方预问模拟 + 关键改进点
- **学习模式**：将优秀分析拆解为可复用的写作模式和模板
- **核心价值**：让你在上会前就知道哪里会被追问，提前补好防线
- **Friday 广场下载量**：500+

### 3. [Dashboard Reporter（经营日报自动化播报）](./dashboard-reporter/)

> 从内网看板自动拉取数据，结合 LLM 知识库生成**经营解读**，定时推送到群聊。

- **V3 架构**：Python 取数 → LLM SubAgent（墨客）生成解读 → 大象群发送
- **内置知识库模板**：指标口径 / 解读规则与归因框架 / 业务规律（通用外卖经营分析）
- **支持降级**：无 SubAgent 时自动降级为 Python 模板模式
- **已验证**：连续数月稳定运行，覆盖日报/周报场景

---

## 🧠 背后的方法论

这三个 Skill 代表了三种不同的 AI 应用思路：

| Skill | 思路 | 核心问题 |
|-------|------|---------|
| Cyber-MaoMao | **认知蒸馏** | 能不能把一个人的判断力变成可复用的 AI 能力？ |
| 分析师炼金术 | **能力放大** | 能不能让 AI 当教练，加速人的成长？ |
| Dashboard Reporter | **流程自动化** | 能不能让重复性知识工作全自动运行？ |

---

## 📖 使用方式

每个 Skill 目录下都有完整的 `SKILL.md`，可直接用于 OpenClaw / CatPaw / Friday 平台：

```bash
# 在 OpenClaw 中安装（将 SKILL.md 放入 ~/.openclaw/skills/<skill-name>/ 目录）
cp -r cyber-maomao ~/.openclaw/skills/
cp -r sharp-analyst ~/.openclaw/skills/
cp -r dashboard-reporter ~/.openclaw/skills/
```

> 目录名与 `SKILL.md` 里的 `name:` 字段保持一致，便于加载器按目录名查找：
> `cyber-maomao` / `sharp-analyst`（原名 good-analyst，已对齐） / `dashboard-reporter`。

---

## 🚦 环境依赖（装之前先看这张表）

| Skill | 依赖 | 外部环境能否直接用 |
|-------|------|------------------|
| **Cyber-MaoMao** | 无（纯 Markdown + examples） | ✅ 可以，任何支持 SKILL.md 的加载器 |
| **分析师炼金术** | 无（纯 Markdown + references） | ✅ 可以 |
| **Dashboard Reporter** | 数据接口 + 登录 cookie；原始实例还依赖内网 SSO、墨客 subagent、大象群 CLI | ⚠️ 通用骨架可跑，原始内部实例不可复现 |

Dashboard Reporter 的**离线演示**（不需要任何内网权限，只要 Python 3）：

```bash
cd dashboard-reporter/scripts
python3 fetch_data.py    --config config.example.json --from-file sample_data.example.json --output /tmp/demo_data.json
python3 render_report.py --config config.example.json --data /tmp/demo_data.json --output /tmp/demo_report.md
cat /tmp/demo_report.md
```

更多部署说明见 [`dashboard-reporter/README.md`](./dashboard-reporter/README.md)。

也可以在 [Friday Skill 广场](https://skills.example.com) 搜索安装（仅内网可访问）。

---

## 👤 作者

**<YOUR_MIS_ACCOUNT>** — 战略分析 × AI 实践者

---

## License

MIT（见 [LICENSE](./LICENSE)）
