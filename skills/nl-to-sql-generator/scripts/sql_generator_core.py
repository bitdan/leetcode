import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PY_ROOT = PROJECT_ROOT / "py"
if str(PY_ROOT) not in sys.path:
    sys.path.append(str(PY_ROOT))


from config.config import OPENAI_API_BASE, OPENAI_API_KEY
from openai import OpenAI

DEFAULT_MODEL = os.getenv("SQL_GEN_MODEL", "gpt-4o-mini")
KNOWN_SITES = {
    "US", "CA", "MX", "BR", "DE", "FR", "IT", "ES", "UK", "NL", "PL", "SE", "CZ", "TR", "BE", "IE"
}

TABLES = {
    "order": {"name": "sale_amazon_order", "alias": "o"},
    "item": {"name": "sale_amazon_order_item", "alias": "i"},
}

DIMENSIONS = {
    "account": {"expr": "{a}.account", "label": "账号", "tables": ["order", "item"]},
    "site": {"expr": "{a}.site", "label": "站点", "tables": ["order", "item"]},
    "order_status": {"expr": "o.order_status", "label": "订单状态", "tables": ["order"]},
    "fulfillment_channel": {"expr": "o.fulfillment_channel", "label": "配送渠道", "tables": ["order"]},
    "sales_channel": {"expr": "o.sales_channel", "label": "销售渠道", "tables": ["order"]},
    "order_channel": {"expr": "o.order_channel", "label": "订单渠道", "tables": ["order"]},
    "ship_service_level": {"expr": "o.ship_service_level", "label": "运输服务级别", "tables": ["order"]},
    "payment_method": {"expr": "o.payment_method", "label": "付款方式", "tables": ["order"]},
    "marketplace_id": {"expr": "o.marketplace_id", "label": "市场ID", "tables": ["order"]},
    "order_type": {"expr": "o.order_type", "label": "订单类型", "tables": ["order"]},
    "refund_flag": {"expr": "o.refund_flag", "label": "退款标识", "tables": ["order"]},
    "seller_sku": {"expr": "i.seller_sku", "label": "SKU", "tables": ["item"]},
    "asin": {"expr": "i.asin", "label": "ASIN", "tables": ["item"]},
    "title": {"expr": "i.title", "label": "标题", "tables": ["item"]},
    "day": {"expr": "DATE({a}.create_time)", "label": "日期", "tables": ["order", "item"]},
}

METRICS = {
    "order_count": {"expr": "COUNT(DISTINCT o.amazon_order_id)", "label": "订单数", "alias": "order_count",
                    "tables": ["order"]},
    "row_count": {"expr": "COUNT(*)", "label": "记录数", "alias": "cnt", "tables": ["order", "item"]},
    "qty_ordered": {"expr": "SUM(i.quantity_ordered)", "label": "下单量", "alias": "qty_ordered", "tables": ["item"]},
    "qty_shipped": {"expr": "SUM(i.quantity_shipped)", "label": "已发货量", "alias": "qty_shipped", "tables": ["item"]},
    "items_total": {"expr": "SUM(i.number_of_items)", "label": "商品数量", "alias": "items_total", "tables": ["item"]},
    "order_amount": {
        "expr": "SUM(CAST(IFNULL(o.amount,'0') AS DECIMAL(18,2)))",
        "label": "销售额",
        "alias": "order_amount",
        "tables": ["order"],
    },
    "item_amount": {
        "expr": "SUM(CAST(IFNULL(i.item_price,'0') AS DECIMAL(18,2)))",
        "label": "商品金额",
        "alias": "item_amount",
        "tables": ["item"],
    },
    "shipping_amount": {
        "expr": "SUM(CAST(IFNULL(i.shipping_price,'0') AS DECIMAL(18,2)))",
        "label": "运费",
        "alias": "shipping_amount",
        "tables": ["item"],
    },
    "refund_amount": {
        "expr": "SUM(CAST(IFNULL(i.refund_amount,'0') AS DECIMAL(18,2)))",
        "label": "退款金额",
        "alias": "refund_amount",
        "tables": ["item"],
    },
    "sales_commission": {
        "expr": "SUM(CAST(IFNULL(i.sales_commission,'0') AS DECIMAL(18,2)))",
        "label": "销售佣金",
        "alias": "sales_commission",
        "tables": ["item"],
    },
}

PLAN_SYSTEM_PROMPT = """你是 Amazon 订单分析助手。你的任务不是直接写 SQL，而是把用户问题转成结构化查询计划。

你只能基于以下语义层进行理解：
1. 表：
- order: sale_amazon_order，订单级
- item: sale_amazon_order_item，商品级
- 当维度或指标跨表时，允许 order 与 item 通过 amazon_order_id 关联

2. 可用维度：
- account, site, order_status, fulfillment_channel, sales_channel, order_channel,
  ship_service_level, payment_method, marketplace_id, order_type, refund_flag,
  seller_sku, asin, title, day

3. 可用指标：
- order_count, row_count, qty_ordered, qty_shipped, items_total,
  order_amount, item_amount, shipping_amount, refund_amount, sales_commission

4. 时间规则：
- 默认时间字段使用 create_time
- 用户明确提到“按天趋势/每天/每日/趋势”时使用 day 维度
- 用户说“近7天/30天/90天”等，输出 time.days
- 用户说“2025年/2024年”等整年，输出 time.year

5. 意图：
- aggregation: 汇总
- distribution: 分布
- ranking: 排行
- trend: 趋势
- detail: 明细

输出要求：
1. 只输出一个 JSON 对象，不要输出其它文字。
2. 仅输出以下字段：
- intent: string
- base_table: string，可选 order/item/auto
- dimensions: string[]
- metrics: string[]
- time: object，可包含 days 或 year
- limit: int
- filters: object，可包含 account/site/order_status/refund_flag/seller_sku/asin 等等，但值只能是字符串或布尔
- orders: array，每项格式 {"field":"metric_or_dimension","direction":"asc|desc"}
- note: string，若无法回答则说明原因
3. 无法回答时，metrics 置空，并在 note 中说明原因。
4. 不要发明新维度、新指标、新字段。
"""

PLAN_FEW_SHOTS = [
    {
        "role": "user",
        "content": "近7天订单状态分布（按站点）",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "distribution",
                "base_table": "order",
                "dimensions": ["site", "order_status"],
                "metrics": ["row_count"],
                "time": {"days": 7},
                "limit": 200,
                "filters": {},
                "orders": [{"field": "row_count", "direction": "desc"}],
                "note": "",
            },
            ensure_ascii=False,
        ),
    },
    {
        "role": "user",
        "content": "近30天销量最高的10个SKU",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "ranking",
                "base_table": "item",
                "dimensions": ["seller_sku"],
                "metrics": ["qty_ordered", "qty_shipped"],
                "time": {"days": 30},
                "limit": 10,
                "filters": {},
                "orders": [{"field": "qty_ordered", "direction": "desc"}],
                "note": "",
            },
            ensure_ascii=False,
        ),
    },
    {
        "role": "user",
        "content": "2025年哪个账号卖得最好",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "ranking",
                "base_table": "item",
                "dimensions": ["account"],
                "metrics": ["qty_ordered"],
                "time": {"year": 2025},
                "limit": 10,
                "filters": {},
                "orders": [{"field": "qty_ordered", "direction": "desc"}],
                "note": "",
            },
            ensure_ascii=False,
        ),
    },
]


def _empty_result(reason: str) -> Dict[str, Any]:
    return {
        "sql": "",
        "preview_sql": "",
        "params": [],
        "result_columns": [],
        "explanation": f"原因：{reason}",
        "tables": [],
    }


def _extract_json(content: str) -> Dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return {}
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        return json.loads(content[start: end + 1])
    except json.JSONDecodeError:
        return {}


def _normalize_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if str(v).strip()]


def _parse_limit(sql: str) -> Optional[int]:
    m = re.search(r"\blimit\s+(\d+)\s*,\s*(\d+)\b", sql, re.IGNORECASE)
    if m:
        return int(m.group(2))
    m = re.search(r"\blimit\s+(\d+)\b", sql, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _infer_days(question: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*天", question or "")
    return int(m.group(1)) if m else None


def _infer_year(question: str) -> Optional[int]:
    m = re.search(r"\b(20\d{2})\s*年", question or "")
    return int(m.group(1)) if m else None


def _parse_account_site(account_token: str) -> Tuple[str, str]:
    token = (account_token or "").strip()
    if "-" not in token:
        return token, ""
    account, site = token.rsplit("-", 1)
    site_upper = site.strip().upper()
    if site_upper in KNOWN_SITES:
        return account.strip(), site_upper
    return token, ""


def _extract_account_site_from_question(question: str) -> Tuple[str, str]:
    text = question or ""
    patterns = [
        r"账号站点(?:是|为|:|：)\s*([A-Za-z][A-Za-z0-9-]+)",
        r"(?<![A-Za-z0-9-])([A-Za-z][A-Za-z0-9-]+)(?![A-Za-z0-9-])",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            token = match.group(1).strip()
            account, site = _parse_account_site(token)
            if account and site:
                return account, site
    return "", ""


def _to_sql_literal(value: str) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        return text
    return "'" + text.replace("'", "''") + "'"


def _build_preview_sql(sql: str, params: List[str], account: str, site: str, question: str) -> str:
    if not sql:
        return ""
    days_value = _infer_days(question)
    year_value = _infer_year(question)
    value_map = {
        "account": account,
        "site": site,
        "days": "" if days_value is None else str(days_value),
        "year_start": "" if year_value is None else f"{year_value}-01-01 00:00:00",
        "year_end": "" if year_value is None else f"{year_value + 1}-01-01 00:00:00",
    }
    idx = 0

    def repl(_: re.Match) -> str:
        nonlocal idx
        key = params[idx].lower() if idx < len(params) else ""
        idx += 1
        if not key:
            return "?"
        value = value_map.get(key, "")
        return "?" if value == "" else _to_sql_literal(value)

    return re.sub(r"\?", repl, sql)


def _format_dimension_expr(name: str, base_table: str) -> Optional[str]:
    config = DIMENSIONS.get(name)
    if not config:
        return None
    if "{a}" in config["expr"]:
        alias = TABLES[base_table]["alias"]
        return config["expr"].format(a=alias)
    return config["expr"]


def _metric_expr(name: str) -> Optional[str]:
    config = METRICS.get(name)
    return config["expr"] if config else None


def _metric_alias(name: str) -> Optional[str]:
    config = METRICS.get(name)
    return config["alias"] if config else None


def _detect_tables_from_sql(sql: str) -> List[str]:
    tables: List[str] = []
    if re.search(r"\bsale_amazon_order_item\b", sql, re.IGNORECASE):
        tables.append("sale_amazon_order_item")
    if re.search(r"\bsale_amazon_order\b", sql, re.IGNORECASE):
        tables.append("sale_amazon_order")
    return tables


def _resolve_base_table(dimensions: List[str], metrics: List[str], preferred: str) -> Optional[str]:
    candidates = {"order", "item"}
    used = dimensions + metrics
    if not used:
        return None
    for name in dimensions:
        config = DIMENSIONS.get(name)
        if not config:
            return None
        candidates &= set(config["tables"])
    for name in metrics:
        config = METRICS.get(name)
        if not config:
            return None
        candidates &= set(config["tables"])
    if preferred in candidates:
        return preferred
    if "item" in candidates:
        return "item"
    if "order" in candidates:
        return "order"
    return None


def _should_join_order(dimensions: List[str], metrics: List[str], base_table: str) -> bool:
    if base_table != "item":
        return False
    for name in dimensions:
        config = DIMENSIONS.get(name)
        if config and "item" not in config["tables"]:
            return True
    for name in metrics:
        config = METRICS.get(name)
        if config and "item" not in config["tables"]:
            return True
    return False


def _normalize_orders(value: Any) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    if not isinstance(value, list):
        return result
    for item in value:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field", "") or "").strip()
        direction = str(item.get("direction", "desc") or "desc").lower()
        if not field:
            continue
        if direction not in {"asc", "desc"}:
            direction = "desc"
        result.append({"field": field, "direction": direction})
    return result


def _normalize_filters(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: Dict[str, Any] = {}
    for key, val in value.items():
        if isinstance(val, (str, bool)):
            result[str(key)] = val
    return result


def _build_user_prompt(account_token: str, account: str, site: str, question: str) -> str:
    token_text = account_token if account_token else "(未传)"
    return (
        "【上下文】\n"
        f"- 输入 account 参数 = {token_text}\n"
        f"- 解析结果：account = {account or '(空)'}，site = {site or '(空)'}\n"
        "- 若上下文已有 account/site，不必重复从问题中提取\n"
        "- 若用户要求按天趋势，请使用 day 维度\n"
        "- 若用户问销量/卖得最好，优先使用 qty_ordered\n\n"
        "【用户问题】\n"
        f"{question}"
    )


def _call_llm_for_plan(account_token: str, account: str, site: str, question: str) -> Dict[str, Any]:
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE or None)
    messages: List[Dict[str, str]] = [{"role": "system", "content": PLAN_SYSTEM_PROMPT}]
    messages.extend(PLAN_FEW_SHOTS)
    messages.append(
        {
            "role": "user",
            "content": _build_user_prompt(
                account_token=account_token,
                account=account,
                site=site,
                question=question,
            ),
        }
    )
    completion = client.chat.completions.create(
        model=DEFAULT_MODEL,
        temperature=0,
        messages=messages,
        response_format={"type": "json_object"},
    )
    content = ""
    if completion.choices and completion.choices[0].message:
        content = completion.choices[0].message.content or ""
    return _extract_json(content)


def _normalize_plan(question: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    time_info = payload.get("time", {})
    if not isinstance(time_info, dict):
        time_info = {}
    days = time_info.get("days")
    year = time_info.get("year")
    if not isinstance(days, int):
        days = _infer_days(question)
    if not isinstance(year, int):
        year = _infer_year(question)

    limit = payload.get("limit", 200)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 200
    limit = max(1, min(limit, 200))

    plan = {
        "intent": str(payload.get("intent", "") or "aggregation").lower(),
        "base_table": str(payload.get("base_table", "") or "auto").lower(),
        "dimensions": [name for name in _normalize_list(payload.get("dimensions", [])) if name in DIMENSIONS],
        "metrics": [name for name in _normalize_list(payload.get("metrics", [])) if name in METRICS],
        "time": {},
        "limit": limit,
        "filters": _normalize_filters(payload.get("filters", {})),
        "orders": _normalize_orders(payload.get("orders", [])),
        "note": str(payload.get("note", "") or "").strip(),
    }
    if isinstance(days, int) and days > 0:
        plan["time"]["days"] = days
    if isinstance(year, int) and 2000 <= year <= 2100:
        plan["time"]["year"] = year

    if not plan["metrics"]:
        if "销量" in question or "卖得最好" in question or "销量最高" in question:
            plan["metrics"] = ["qty_ordered"]
        elif "退款" in question:
            plan["metrics"] = ["refund_amount"]
        elif "金额" in question or "销售额" in question or "销售金额" in question:
            plan["metrics"] = ["order_amount"]
        elif "订单数" in question:
            plan["metrics"] = ["order_count"]
        elif "分布" in question or "数量" in question:
            plan["metrics"] = ["row_count"]

    if not plan["dimensions"]:
        if "SKU" in question.upper():
            plan["dimensions"] = ["seller_sku"]
        elif "ASIN" in question.upper():
            plan["dimensions"] = ["asin"]
        elif "账号" in question:
            plan["dimensions"] = ["account"]
        elif "站点" in question:
            plan["dimensions"] = ["site"]
        elif "订单状态" in question:
            plan["dimensions"] = ["order_status"]

    if any(token in question for token in ["趋势", "每天", "每日", "按天"]):
        if "day" not in plan["dimensions"]:
            plan["dimensions"].insert(0, "day")
        if plan["intent"] == "aggregation":
            plan["intent"] = "trend"

    if not plan["orders"] and plan["metrics"]:
        plan["orders"] = [{"field": _metric_alias(plan["metrics"][0]) or plan["metrics"][0], "direction": "desc"}]

    return plan


def _apply_context_to_plan(plan: Dict[str, Any], account: str, site: str) -> None:
    if account:
        plan["filters"]["account"] = True
    if site:
        plan["filters"]["site"] = True


def _render_sql_from_plan(plan: Dict[str, Any], require_account: bool, require_site: bool) -> Dict[str, Any]:
    dimensions = plan["dimensions"]
    metrics = plan["metrics"]
    preferred = plan["base_table"] if plan["base_table"] in {"order", "item"} else "item"
    base_table = _resolve_base_table(dimensions, metrics, preferred)
    if not base_table:
        return _empty_result("当前问题超出已支持的维度/指标范围")

    need_join_order = _should_join_order(dimensions, metrics, base_table)
    select_parts: List[str] = []
    group_parts: List[str] = []
    result_columns: List[str] = []
    order_map: Dict[str, str] = {}

    for dimension in dimensions:
        expr = _format_dimension_expr(dimension, base_table)
        if not expr:
            return _empty_result(f"不支持维度 {dimension}")
        alias = dimension
        select_parts.append(f"{expr} AS {alias}")
        group_parts.append(expr)
        result_columns.append(alias)
        order_map[alias] = alias

    for metric in metrics:
        expr = _metric_expr(metric)
        alias = _metric_alias(metric)
        if not expr or not alias:
            return _empty_result(f"不支持指标 {metric}")
        select_parts.append(f"{expr} AS {alias}")
        result_columns.append(alias)
        order_map[metric] = alias
        order_map[alias] = alias

    if not select_parts:
        return _empty_result("未识别到可查询的维度或指标")

    from_clause = f"FROM {TABLES[base_table]['name']} {TABLES[base_table]['alias']}"
    if need_join_order:
        from_clause += " JOIN sale_amazon_order o ON i.amazon_order_id = o.amazon_order_id"

    where_parts: List[str] = []
    params: List[str] = []

    if base_table == "order":
        where_parts.append("o.deleted = 0")
    else:
        where_parts.append("i.deleted = 0")
    if need_join_order:
        where_parts.append("o.deleted = 0")

    if require_account:
        if base_table == "order":
            where_parts.append("o.account = ?")
        else:
            where_parts.append("i.account = ?")
        params.append("account")
        if need_join_order:
            where_parts.append("o.account = ?")
            params.append("account")

    if require_site:
        if base_table == "order":
            where_parts.append("o.site = ?")
        else:
            where_parts.append("i.site = ?")
        params.append("site")
        if need_join_order:
            where_parts.append("o.site = ?")
            params.append("site")

    time_info = plan["time"]
    time_alias = "o" if base_table == "order" else "i"
    if "days" in time_info:
        where_parts.append(f"{time_alias}.create_time >= DATE_SUB(NOW(), INTERVAL ? DAY)")
        params.append("days")
    elif "year" in time_info:
        where_parts.append(f"{time_alias}.create_time >= ?")
        where_parts.append(f"{time_alias}.create_time < ?")
        params.extend(["year_start", "year_end"])

    for key, val in plan["filters"].items():
        if key in {"account", "site"}:
            continue
        if key not in DIMENSIONS or not isinstance(val, str) or not val.strip():
            continue
        expr = _format_dimension_expr(key, base_table)
        if not expr:
            continue
        where_parts.append(f"{expr} = ?")
        params.append(key)

    sql = "SELECT " + ", ".join(select_parts) + " " + from_clause + " WHERE " + " AND ".join(where_parts)
    if group_parts:
        sql += " GROUP BY " + ", ".join(group_parts)

    order_parts: List[str] = []
    for item in plan["orders"]:
        field = order_map.get(item["field"], order_map.get(_metric_alias(item["field"]) or "", ""))
        if not field:
            continue
        order_parts.append(f"{field} {item['direction'].upper()}")
    if not order_parts and metrics:
        order_parts.append(f"{_metric_alias(metrics[0])} DESC")
    if order_parts:
        sql += " ORDER BY " + ", ".join(order_parts)
    sql += f" LIMIT {plan['limit']}"

    return {
        "sql": sql,
        "preview_sql": "",
        "params": params,
        "result_columns": result_columns,
        "explanation": "",
        "tables": _detect_tables_from_sql(sql),
    }


def _build_explanation(plan: Dict[str, Any]) -> str:
    dim_labels = [DIMENSIONS[name]["label"] for name in plan["dimensions"] if name in DIMENSIONS]
    metric_labels = [METRICS[name]["label"] for name in plan["metrics"] if name in METRICS]
    time_text = ""
    if "days" in plan["time"]:
        time_text = f"近{plan['time']['days']}天"
    elif "year" in plan["time"]:
        time_text = f"{plan['time']['year']}年"
    metric_text = "、".join(metric_labels) if metric_labels else "指标"
    dim_text = "、".join(dim_labels)
    if dim_text:
        return f"统计{time_text}{dim_text}维度的{metric_text}".replace("统计维度", "统计")
    return f"统计{time_text}{metric_text}".strip()


def _validate_sql(sql: str, tables: List[str], require_account: bool, require_site: bool) -> Optional[str]:
    normalized = sql.strip()
    lowered = normalized.lower()
    if not re.match(r"^\s*select\b", normalized, re.IGNORECASE):
        return "只允许 SELECT 查询"
    if ";" in normalized:
        return "SQL 不允许分号"
    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        return "SQL 不允许注释"
    if re.search(r"\b(insert|update|delete|replace|truncate|drop|alter|create)\b", lowered, re.IGNORECASE):
        return "SQL 包含被禁止的写操作或DDL关键字"
    if not re.search(r"\bdeleted\s*=\s*0\b", normalized, re.IGNORECASE):
        return "必须包含 deleted = 0 过滤"
    if require_account and not re.search(r"\baccount\s*=\s*\?", normalized, re.IGNORECASE):
        return "必须使用 account = ? 过滤"
    if require_site and not re.search(r"\bsite\s*=\s*\?", normalized, re.IGNORECASE):
        return "必须使用 site = ? 过滤"

    limit_value = _parse_limit(normalized)
    if limit_value is None:
        return "必须包含 LIMIT"
    if limit_value > 500:
        return "LIMIT 不能大于 500"

    has_order = "sale_amazon_order" in set(tables)
    has_item = "sale_amazon_order_item" in set(tables)
    if has_order and has_item and not re.search(
            r"\bi\.amazon_order_id\s*=\s*o\.amazon_order_id\b", normalized, re.IGNORECASE
    ):
        return "两表 JOIN 仅允许 i.amazon_order_id = o.amazon_order_id"
    return None


def _validate_params(sql: str, params: List[str], require_account: bool, require_site: bool) -> Optional[str]:
    placeholders = len(re.findall(r"\?", sql))
    if placeholders != len(params):
        return "params 数量必须与 SQL 占位符数量一致"
    lowered = [p.lower() for p in params]
    if require_account and "account" not in lowered:
        return "params 必须包含 account"
    if require_site and "site" not in lowered:
        return "params 必须包含 site"
    if re.search(r"date_sub\s*\(\s*now\(\)\s*,\s*interval\s*\?\s*day\s*\)", sql,
                 re.IGNORECASE) and "days" not in lowered:
        return "存在近N天条件时，params 必须包含 days"
    return None


def generate_sql_payload(account_token: str, question: str) -> Dict[str, Any]:
    if not question or not question.strip():
        return _empty_result("问题不能为空")

    parsed_account, parsed_site = _parse_account_site(account_token)
    if not parsed_account and not parsed_site:
        inferred_account, inferred_site = _extract_account_site_from_question(question)
        parsed_account = inferred_account
        parsed_site = inferred_site
        if inferred_account and inferred_site and not account_token:
            account_token = f"{inferred_account}-{inferred_site}"

    if parsed_site and not parsed_account:
        return _empty_result("account 格式无效")
    if not OPENAI_API_KEY:
        return _empty_result("未配置 OPENAI_API_KEY")

    raw_plan = _call_llm_for_plan(
        account_token=account_token,
        account=parsed_account,
        site=parsed_site,
        question=question,
    )
    if not raw_plan:
        return _empty_result("模型返回结果不是合法 JSON")

    plan = _normalize_plan(question, raw_plan)
    _apply_context_to_plan(plan, parsed_account, parsed_site)
    if not plan["metrics"]:
        return _empty_result(plan["note"] or "无法识别查询指标")

    result = _render_sql_from_plan(
        plan=plan,
        require_account=bool(parsed_account),
        require_site=bool(parsed_site),
    )
    if not result["sql"]:
        return result

    err = _validate_sql(
        result["sql"],
        result["tables"],
        require_account=bool(parsed_account),
        require_site=bool(parsed_site),
    )
    if err:
        return _empty_result(f"生成 SQL 未通过安全校验，{err}")

    params_err = _validate_params(
        result["sql"],
        result["params"],
        require_account=bool(parsed_account),
        require_site=bool(parsed_site),
    )
    if params_err:
        return _empty_result(params_err)

    result["explanation"] = _build_explanation(plan)
    result["preview_sql"] = _build_preview_sql(
        sql=result["sql"],
        params=result["params"],
        account=parsed_account,
        site=parsed_site,
        question=question,
    )
    return result
