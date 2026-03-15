from pathlib import Path
import sys
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PY_ROOT = PROJECT_ROOT / "py"

if str(PY_ROOT) not in sys.path:
    sys.path.append(str(PY_ROOT))

from sql_generator.service import generate_sql_payload


def generate_sql(question: str, account: str = "") -> Dict[str, Any]:
    """Skill entrypoint for NL-to-SQL generation."""
    return generate_sql_payload(account_token=account, question=question)
