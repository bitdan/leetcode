from pathlib import Path
import sys
from typing import Any, Dict


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from sql_generator_core import generate_sql_payload


def generate_sql(question: str, account: str = "") -> Dict[str, Any]:
    """Skill entrypoint for NL-to-SQL generation."""
    return generate_sql_payload(account_token=account, question=question)
