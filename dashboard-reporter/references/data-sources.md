# 数据源参考

## 支持的平台

### 1. ocrm.sankuai.com（外卖直营数据）

**Cookie 域**：`ocrm.sankuai.com`  
**Cookie 字段**：`xianfu_waimai_ssoid`  
**数据接口**：`POST https://data.ocrm.sankuai.com/olap/query`

请求头：
```
Cookie: xianfu_waimai_ssoid=<value>
Content-Type: application/json
X-Requested-With: XMLHttpRequest
```

响应结构：
```json
{
  "rescode": 0,
  "data": { "list": [...] }
}
```

错误码：
- `rescode=30001`：ssoid 过期，需重新登录
- `rescode=10001`：未授权

**探测方式**：URL 含 `ocrm.sankuai.com` 或 `data.ocrm.sankuai.com`

---

### 2. data.sankuai.com（通用数据平台）

**Cookie 域**：`data.sankuai.com`  
**Cookie 字段**：`ssoid` 或 `sso_token`  
**数据接口**：参考看板页面 Network 请求

**探测方式**：URL 含 `data.sankuai.com`

---

### 3. 通用内网看板

对于未知平台：

1. 用 agent-browser 打开看板 URL
2. 打开 DevTools → Network 面板，找到数据请求（XHR/Fetch）
3. 记录：请求 URL、Method、Headers（含 Cookie 字段名）、请求体格式
4. 把这些信息填入配置文件的 `data_source.queries`

---

## Cookie 获取流程

```bash
# 通用 SSO 登录（已有脚本）
/app/skills/room-booking-helper/scripts/sso-login.sh <mis_account>

# 然后从 CDP 提取特定域 cookie
python3 ~/.openclaw/dashboard-reporter/scripts/extract_cookie.py --domain <domain>
```

或通过 agent-browser 导航到看板 URL，触发 SSO 登录后提取 cookie。

---

## 数据字段映射示例（ocrm 直营）

| 字段名 | 含义 | 格式化 |
|--------|------|--------|
| `fin_ord_num` | 消费订单量 | `/ 10000` → 万单 |
| `fin_actual_amt` | 实收GTV | `/ 10000` → 万元 |
| `ord_avg_fin_actual_amt` | 实收客单价 | 元，保留2位小数 |
| `net_mt_disc_rate` | 美补率 | `* 100` → % |
| `fin_ord_num_last_day_rate` | DoD 环比 | `* 100` → % + 箭头 |
| `fin_ord_num_last_week_rate` | WoW 周同比 | 同上 |
| `fin_ord_num_last_year_rate` | YoY 年同比 | 同上 |
