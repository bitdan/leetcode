from pathlib import Path
import sys
from typing import Any, Dict


# 这个文件是 skill 的“程序入口”。
# 外部代码应该调用这里，而不是直接跳到 core 实现里。
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from sql_generator_core import generate_sql_payload


def generate_sql(question: str, account: str = "") -> Dict[str, Any]:
    """Skill entrypoint for NL-to-SQL generation."""
    # 核心逻辑仍然在 sql_generator_core.py，这里只负责暴露稳定入口。
    return generate_sql_payload(account_token=account, question=question)
