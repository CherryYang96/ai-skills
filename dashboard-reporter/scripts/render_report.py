#!/usr/bin/env python3
"""
render_report.py - 通用经营报告渲染脚本（Jinja2 模板引擎）

用法：
  python3 render_report.py --config my_report.json --data /tmp/dashboard_data_xxx.json
  python3 render_report.py --config my_report.json  # 自动找数据文件

输出：Markdown 报告写入 /tmp/report_output.txt，打印 [REPORT_READY]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── 格式化工具函数 ─────────────────────────────────────────────────────────────

def fmt_wan(v, decimals=2):
    """转万单位"""
    try:
        return f"{float(v)/10000:.{decimals}f}万"
    except (TypeError, ValueError):
        return "-"

def fmt_pct(v, decimals=1):
    """转百分比"""
    try:
        return f"{float(v)*100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "-"

def fmt_arrow(v, decimals=1):
    """带箭头的环比，正红负绿"""
    try:
        f = float(v)
        if abs(f) < 1e-6:
            return "-"
        sign = "↑" if f > 0 else "↓"
        return f"{sign}{abs(f)*100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "-"

def fmt_yuan(v, decimals=2):
    """元，保留小数"""
    try:
        return f"{float(v):.{decimals}f}元"
    except (TypeError, ValueError):
        return "-"

def fmt_min(v, decimals=2):
    """分钟"""
    try:
        return f"{float(v):.{decimals}f}分钟"
    except (TypeError, ValueError):
        return "-"

def safe_get(d: dict, key: str, default=0):
    return d.get(key, default) or default

# ─── 模板渲染 ──────────────────────────────────────────────────────────────────

def render_with_jinja2(template_str: str, context: dict) -> str:
    try:
        from jinja2 import Environment
    except ImportError:
        # 降级：简单字符串替换
        result = template_str
        for k, v in context.items():
            result = result.replace("{{ " + k + " }}", str(v))
        return result
    
    env = Environment()
    env.filters["fmt_wan"] = fmt_wan
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_arrow"] = fmt_arrow
    env.filters["fmt_yuan"] = fmt_yuan
    env.filters["fmt_min"] = fmt_min
    
    tmpl = env.from_string(template_str)
    return tmpl.render(**context)

def render_default(data_payload: dict, config: dict) -> str:
    """使用内置默认模板渲染（仿直营日报格式）"""
    data = data_payload["data"]
    date_iso = data_payload["date"]
    report_name = config.get("name", "经营日报")
    
    tz_sh = timezone(timedelta(hours=8))
    dt = datetime.fromisoformat(date_iso).replace(tzinfo=tz_sh)
    date_cn = f"{dt.year}年{dt.month}月{dt.day}日"
    date_slash = dt.strftime("%Y/%m/%d")
    
    # 尝试从 data 中提取通用字段（overview 查询结果）
    overview = data.get("overview", [{}])
    row = overview[0] if overview else {}
    
    def p(key):
        return fmt_arrow(row.get(key))
    
    def fv(key):
        return row.get(key, 0) or 0
    
    lines = [
        f"### 📊 {report_name} · {date_slash}",
        "",
        "---",
        "",
        "#### 🔑 核心数据概览",
        "",
    ]
    
    # 动态生成表格（遍历所有数值字段）
    if row:
        # 过滤出数值字段和环比字段
        metrics = {}
        rates = {}
        for k, v in row.items():
            if k.endswith(("_last_day_rate", "_last_week_rate", "_last_year_rate")):
                rates[k] = v
            elif isinstance(v, (int, float)) and v != 0:
                metrics[k] = v
        
        if metrics:
            lines += [
                "| 指标 | 数值 | DoD |",
                "|------|------|-----|",
            ]
            for k, v in list(metrics.items())[:20]:  # 最多显示20个指标
                dod_key = k + "_last_day_rate"
                dod = fmt_arrow(rates.get(dod_key))
                # 格式化数值
                if "rate" in k or "ratio" in k:
                    val_str = fmt_pct(v)
                elif v > 10000:
                    val_str = fmt_wan(v)
                elif "dur" in k or "time" in k:
                    val_str = fmt_min(v)
                else:
                    val_str = f"{v:.2f}"
                lines.append(f"| {k} | {val_str} | {dod} |")
    else:
        lines.append("> ⚠️ 暂无数据，请检查数据源配置")
    
    lines += [
        "",
        "---",
        "",
        f"*——来自自动日报系统*",
    ]
    
    return "\n".join(lines)

# ─── 主逻辑 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="经营报告渲染")
    parser.add_argument("--config", required=True, help="报告配置文件路径")
    parser.add_argument("--data", help="数据文件路径（fetch_data.py 的输出）")
    parser.add_argument("--output", default="/tmp/report_output.txt", help="输出文件路径")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()
    with open(config_path) as f:
        config = json.load(f)
    
    report_name = config["name"].replace(" ", "_")
    
    # 找数据文件
    data_file = args.data or f"/tmp/dashboard_data_{report_name}.json"
    if not Path(data_file).exists():
        print(f"[ALERT] 数据文件不存在: {data_file}，请先运行 fetch_data.py", file=sys.stderr)
        sys.exit(1)
    
    with open(data_file) as f:
        data_payload = json.load(f)
    
    # 选择模板
    template_name = config.get("template", "default")
    template_dir = Path("~/.openclaw/dashboard-reporter/templates").expanduser()
    template_file = template_dir / f"{template_name}.md.j2"
    
    if template_file.exists():
        template_str = template_file.read_text()
        # 构建 context
        context = {
            "data": data_payload["data"],
            "date": data_payload["date"],
            "report_name": config["name"],
            "config": config,
        }
        report = render_with_jinja2(template_str, context)
    else:
        # 使用内置默认模板
        report = render_default(data_payload, config)
    
    with open(args.output, "w") as f:
        f.write(report)
    
    print(f"[REPORT_READY] {args.output}")


if __name__ == "__main__":
    main()
