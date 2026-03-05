import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from config.config import OPENAI_API_BASE, OPENAI_API_KEY
from openai import OpenAI

DEFAULT_MODEL = os.getenv("SQL_GEN_MODEL", "gpt-4o-mini")
KNOWN_SITES = {
    "US", "CA", "MX", "BR", "DE", "FR", "IT", "ES", "UK", "NL", "PL", "SE", "CZ", "TR", "BE", "IE"
}

SYSTEM_PROMPT = """你是资深 MySQL 5.7 数据分析 SQL 专家。你的任务是把用户的自然语言问题转换为一条“可执行且安全”的 SQL 查询语句。

【硬性安全规则】
1) 只能输出 1 条 SQL，并且必须是 SELECT（禁止 INSERT/UPDATE/DELETE/REPLACE/TRUNCATE/DROP/ALTER/CREATE）。
2) 禁止多语句：SQL 中不允许出现分号 “;”。
3) 禁止注释：不允许出现 “--” 或 “/* */”。
4) 必须使用占位符参数（?）传入动态条件（例如 account/site/时间范围等），禁止多语句拼接。
5) 必须包含 deleted 过滤：涉及到的每张表都必须加 deleted = 0。
6) 如果上下文给出了 account（非空），涉及到的每张表都必须加 account = ?。
7) 如果上下文给出了 site（非空），涉及到的每张表都必须加 site = ?。
8) 必须包含 LIMIT，且 LIMIT <= 200（除非用户明确要求更大，但最大也不能超过 500）。
9) 默认时间范围使用 create_time（datetime）；除非用户明确要求使用 purchase_date/last_update_date（varchar）。
10) 金额字段为 varchar：凡是 SUM/比较/排序涉及金额，必须 CAST 为 DECIMAL：
   CAST(IFNULL(field,'0') AS DECIMAL(18,2))

【可用数据表与字段白名单（只能用这些）】
表 sale_amazon_order 作为 o：
- id, amazon_order_id, seller_order_id, purchase_date, last_update_date, order_status,
  fulfillment_channel, sales_channel, order_channel, ship_service_level, currency_code, amount,
  number_of_items_shipped, number_of_items_unshipped, payment_method, marketplace_id,
  shipment_service_level_category, easy_ship_shipment_status, order_type,
  earliest_ship_date, latest_ship_date, earliest_delivery_date, latest_delivery_date,
  is_business_order, is_prime, is_premium_order,
  buyer_name, buyer_email,
  sync_items, sync_buyer_info, sync_address,
  shop_id, account, site, refund_flag, create_time, update_time, deleted

表 sale_amazon_order_item 作为 i：
- id, amazon_order_id, asin, seller_sku, order_item_id, title,
  quantity_ordered, quantity_shipped, number_of_items,
  item_price, shipping_price, item_tax, shipping_tax,
  shipping_discount, shipping_discount_tax,
  promotion_discount, promotion_discount_tax,
  fba_unit_fulfillment_fee, refund_commission_fee, sales_commission, refund_amount,
  promotion_ids, cod_fee, cod_fee_discount,
  shop_id, account, site, create_time, update_time, deleted

【JOIN 规则】
- 如果同时用到两个表，只允许用以下 JOIN：
  i.amazon_order_id = o.amazon_order_id

【输出格式（必须严格遵守）】
只输出一个 JSON 对象，不能输出其它文字。
JSON 字段：
- sql: string（SQL 语句，必须含 ? 占位符）
- params: array（按 ? 出现顺序给出参数含义说明，例如 ["account","site","days"]，不要给具体值）
- result_columns: array（结果列名列表）
- explanation: string（用中文，简短说明 SQL 在查什么）
- tables: array（使用到的表名）

如果用户的问题无法仅靠白名单字段回答，返回：
{
  "sql": "",
  "params": [],
  "result_columns": [],
  "explanation": "原因：…（中文）",
  "tables": []
}

【额外约束】
- 如果用户问“近7天/30天/90天”，统一用 create_time 做时间过滤：
  create_time >= DATE_SUB(NOW(), INTERVAL ? DAY)
  并把 days 放到 params 里。
- 如果用户问“2025年哪个账号卖得最好/销量最高”等年度账号对比问题：
  使用 create_time 年度范围过滤（建议 create_time >= ? AND create_time < ?，params 使用 ["year_start","year_end"]），
  按 account 分组并按销量降序，LIMIT 1~20。
- 如果用户要求“按天趋势”，用 DATE(create_time) 分组。
- 尽量不要 SELECT *，只返回必要字段。
"""

FEW_SHOT_MESSAGES = [
    {
        "role": "user",
        "content": "近7天订单状态分布（按站点）",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "sql": "SELECT o.site, o.order_status, COUNT(*) AS cnt FROM sale_amazon_order o WHERE o.deleted = 0 AND o.account = ? AND o.site = ? AND o.create_time >= DATE_SUB(NOW(), INTERVAL ? DAY) GROUP BY o.site, o.order_status ORDER BY cnt DESC LIMIT 200",
                "params": ["account", "site", "days"],
                "result_columns": ["site", "order_status", "cnt"],
                "explanation": "统计指定店铺近N天各站点的订单状态数量分布",
                "tables": ["sale_amazon_order"],
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
                "sql": "SELECT i.seller_sku, SUM(i.quantity_ordered) AS qty_ordered, SUM(i.quantity_shipped) AS qty_shipped FROM sale_amazon_order_item i WHERE i.deleted = 0 AND i.account = ? AND i.site = ? AND i.create_time >= DATE_SUB(NOW(), INTERVAL ? DAY) GROUP BY i.seller_sku ORDER BY qty_ordered DESC LIMIT 10",
                "params": ["account", "site", "days"],
                "result_columns": ["seller_sku", "qty_ordered", "qty_shipped"],
                "explanation": "统计指定店铺近N天按SKU汇总的下单量与已发货量，并取销量最高的前10个SKU",
                "tables": ["sale_amazon_order_item"],
            },
            ensure_ascii=False,
        ),
    },
    {
        "role": "user",
        "content": "账号站点是QD-US，近30天销量最高的10个SKU",
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "sql": "SELECT i.seller_sku, SUM(i.quantity_ordered) AS qty_ordered, SUM(i.quantity_shipped) AS qty_shipped FROM sale_amazon_order_item i WHERE i.deleted = 0 AND i.account = ? AND i.site = ? AND i.create_time >= DATE_SUB(NOW(), INTERVAL ? DAY) GROUP BY i.seller_sku ORDER BY qty_ordered DESC LIMIT 10",
                "params": ["account", "site", "days"],
                "result_columns": ["seller_sku", "qty_ordered", "qty_shipped"],
                "explanation": "按指定账号站点统计近30天销量最高的10个SKU",
                "tables": ["sale_amazon_order_item"],
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
                "sql": "SELECT i.account, SUM(i.quantity_ordered) AS qty_ordered FROM sale_amazon_order_item i WHERE i.deleted = 0 AND i.create_time >= ? AND i.create_time < ? GROUP BY i.account ORDER BY qty_ordered DESC LIMIT 10",
                "params": ["year_start", "year_end"],
                "result_columns": ["account", "qty_ordered"],
                "explanation": "统计2025年各账号销量并按销量降序返回前10名账号",
                "tables": ["sale_amazon_order_item"],
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
    return [str(v) for v in value]


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
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _infer_year(question: str) -> Optional[int]:
    m = re.search(r"\b(20\d{2})\s*年", question or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


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
        for m in re.finditer(pattern, text, re.IGNORECASE):
            token = m.group(1).strip()
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
    escaped = text.replace("'", "''")
    return f"'{escaped}'"


def _build_preview_sql(
        sql: str,
        params: List[str],
        account: str,
        site: str,
        question: str,
) -> str:
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
        if value == "":
            return "?"
        return _to_sql_literal(value)

    return re.sub(r"\?", repl, sql)


def _inject_filters_for_alias(sql: str, alias: str, need_account: bool, need_site: bool) -> str:
    add_parts: List[str] = []
    if need_account and not re.search(rf"\b{alias}\.account\s*=\s*\?", sql, re.IGNORECASE):
        add_parts.append(f"{alias}.account = ?")
    if need_site and not re.search(rf"\b{alias}\.site\s*=\s*\?", sql, re.IGNORECASE):
        add_parts.append(f"{alias}.site = ?")
    if not add_parts:
        return sql

    m = re.search(r"\b(group\s+by|order\s+by|limit)\b", sql, re.IGNORECASE)
    if m:
        head = sql[:m.start()].rstrip()
        tail = sql[m.start():]
    else:
        head = sql.rstrip()
        tail = ""

    if re.search(r"\bwhere\b", head, re.IGNORECASE):
        head = f"{head} AND " + " AND ".join(add_parts)
    else:
        head = f"{head} WHERE " + " AND ".join(add_parts)

    return f"{head} {tail}".strip()


def _enforce_context_filters(sql: str, params: List[str], tables: List[str], require_account: bool,
                             require_site: bool) -> Tuple[str, List[str]]:
    if not sql or (not require_account and not require_site):
        return sql, params

    table_set = set(tables)
    has_order = "sale_amazon_order" in table_set
    has_item = "sale_amazon_order_item" in table_set

    fixed_sql = sql
    fixed_params = list(params)

    if has_item and not has_order:
        before = fixed_sql
        fixed_sql = _inject_filters_for_alias(fixed_sql, "i", require_account, require_site)
        if fixed_sql != before:
            if require_account and "account" not in [p.lower() for p in fixed_params]:
                fixed_params.append("account")
            if require_site and "site" not in [p.lower() for p in fixed_params]:
                fixed_params.append("site")
        return fixed_sql, fixed_params

    if has_order and not has_item:
        before = fixed_sql
        fixed_sql = _inject_filters_for_alias(fixed_sql, "o", require_account, require_site)
        if fixed_sql != before:
            if require_account and "account" not in [p.lower() for p in fixed_params]:
                fixed_params.append("account")
            if require_site and "site" not in [p.lower() for p in fixed_params]:
                fixed_params.append("site")
        return fixed_sql, fixed_params

    return fixed_sql, fixed_params


def _validate_sql(sql: str, tables: List[str], require_account: bool, require_site: bool) -> Optional[str]:
    normalized = sql.strip()
    lowered = normalized.lower()

    if not re.match(r"^\s*select\b", normalized, re.IGNORECASE):
        return "只允许 SELECT 查询"

    if ";" in normalized:
        return "SQL 不允许分号"

    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        return "SQL 不允许注释"

    forbidden = re.search(
        r"\b(insert|update|delete|replace|truncate|drop|alter|create)\b",
        lowered,
        re.IGNORECASE,
    )
    if forbidden:
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

    table_set = set(tables)
    has_order = "sale_amazon_order" in table_set
    has_item = "sale_amazon_order_item" in table_set

    if has_order and not has_item:
        if require_account and not re.search(r"\bo\.account\s*=\s*\?", normalized, re.IGNORECASE):
            return "订单表必须包含 o.account = ?"
        if require_site and not re.search(r"\bo\.site\s*=\s*\?", normalized, re.IGNORECASE):
            return "订单表必须包含 o.site = ?"
        if not re.search(r"\bo\.deleted\s*=\s*0\b", normalized, re.IGNORECASE):
            return "订单表必须包含 o.deleted = 0"

    if has_item and not has_order:
        if require_account and not re.search(r"\bi\.account\s*=\s*\?", normalized, re.IGNORECASE):
            return "明细表必须包含 i.account = ?"
        if require_site and not re.search(r"\bi\.site\s*=\s*\?", normalized, re.IGNORECASE):
            return "明细表必须包含 i.site = ?"
        if not re.search(r"\bi\.deleted\s*=\s*0\b", normalized, re.IGNORECASE):
            return "明细表必须包含 i.deleted = 0"

    if has_order and has_item:
        if not re.search(r"\bi\.amazon_order_id\s*=\s*o\.amazon_order_id\b", normalized, re.IGNORECASE):
            return "两表 JOIN 仅允许 i.amazon_order_id = o.amazon_order_id"
        if require_account and not re.search(r"\bo\.account\s*=\s*\?", normalized, re.IGNORECASE):
            return "订单表必须包含 o.account = ?"
        if require_account and not re.search(r"\bi\.account\s*=\s*\?", normalized, re.IGNORECASE):
            return "明细表必须包含 i.account = ?"
        if require_site and not re.search(r"\bo\.site\s*=\s*\?", normalized, re.IGNORECASE):
            return "订单表必须包含 o.site = ?"
        if require_site and not re.search(r"\bi\.site\s*=\s*\?", normalized, re.IGNORECASE):
            return "明细表必须包含 i.site = ?"
        if not re.search(r"\bo\.deleted\s*=\s*0\b", normalized, re.IGNORECASE):
            return "订单表必须包含 o.deleted = 0"
        if not re.search(r"\bi\.deleted\s*=\s*0\b", normalized, re.IGNORECASE):
            return "明细表必须包含 i.deleted = 0"

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
    if re.search(r"date_sub\s*\(\s*now\(\)\s*,\s*interval\s*\?\s*day\s*\)", sql, re.IGNORECASE):
        if "days" not in lowered:
            return "存在近N天条件时，params 必须包含 days"

    return None


def _build_user_prompt(account_token: str, account: str, site: str, question: str) -> str:
    site_text = site if site else ""
    account_text = account if account else ""
    token_text = account_token if account_token else "(未传)"
    return (
        "【上下文】\n"
        f"- 输入 account 参数 = {token_text}\n"
        f"- 解析结果：account = {account_text or '(空)'}，site = {site_text or '(空)'}\n"
        "- 规则：只有在 account/site 非空时才添加对应过滤\n"
        "- 必须使用 ? 占位符，禁止把 account/site 直接写常量\n\n"
        "【用户问题】\n"
        f"{question}"
    )


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

    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE or None)

    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(FEW_SHOT_MESSAGES)
    messages.append(
        {
            "role": "user",
            "content": _build_user_prompt(
                account_token=account_token,
                account=parsed_account,
                site=parsed_site,
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

    payload = _extract_json(content)
    if not payload:
        return _empty_result("模型返回结果不是合法 JSON")

    result = {
        "sql": str(payload.get("sql", "") or ""),
        "preview_sql": "",
        "params": _normalize_list(payload.get("params", [])),
        "result_columns": _normalize_list(payload.get("result_columns", [])),
        "explanation": str(payload.get("explanation", "") or ""),
        "tables": _normalize_list(payload.get("tables", [])),
    }

    if not result["sql"]:
        if not result["explanation"]:
            result["explanation"] = "原因：无法使用白名单字段生成 SQL"
        return result

    require_account = bool(parsed_account)
    require_site = bool(parsed_site)

    original_sql = result["sql"]
    original_params = list(result["params"])
    fixed_sql, fixed_params = _enforce_context_filters(
        sql=result["sql"],
        params=result["params"],
        tables=result["tables"],
        require_account=require_account,
        require_site=require_site,
    )
    result["sql"] = fixed_sql
    result["params"] = fixed_params

    err = _validate_sql(
        result["sql"],
        result["tables"],
        require_account=require_account,
        require_site=require_site,
    )
    if err:
        return _empty_result(f"生成 SQL 未通过安全校验，{err}")

    params_err = _validate_params(
        result["sql"],
        result["params"],
        require_account=require_account,
        require_site=require_site,
    )
    if params_err:
        return _empty_result(params_err)

    if not result["explanation"]:
        result["explanation"] = "已根据问题生成安全查询 SQL"
    if (result["sql"] != original_sql or result["params"] != original_params) and (parsed_account or parsed_site):
        result["explanation"] += f"；已按上下文自动补全过滤(account={parsed_account or '-'}, site={parsed_site or '-'})"

    result["preview_sql"] = _build_preview_sql(
        sql=result["sql"],
        params=result["params"],
        account=parsed_account,
        site=parsed_site,
        question=question,
    )

    return result
