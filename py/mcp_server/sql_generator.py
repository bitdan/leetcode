from typing import Any, Dict

from sql_generator.service import generate_sql_payload


def generate_nl_sql(question: str, account: str = "") -> Dict[str, Any]:
    """Generate SQL from a natural-language question using the repository's Amazon order SQL generator."""
    # 这里复用的是仓库已有的 Amazon 订单 SQL 生成器，
    # 所以当前 MCP tool 的能力边界也和它保持一致。
    payload = generate_sql_payload(account_token=account, question=question)
    return payload
