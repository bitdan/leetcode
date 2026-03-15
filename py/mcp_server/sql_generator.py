from typing import Any, Dict

from sql_generator.service import generate_sql_payload


def generate_nl_sql(question: str, account: str = "") -> Dict[str, Any]:
    """Generate SQL from a natural-language question using the repository's Amazon order SQL generator."""
    payload = generate_sql_payload(account_token=account, question=question)
    return payload
