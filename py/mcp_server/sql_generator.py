import importlib.util
from pathlib import Path
from typing import Any, Dict

from mcp_server.path_utils import find_repo_root

PROJECT_ROOT = find_repo_root(Path(__file__))
SKILL_GENERATOR_SCRIPT = PROJECT_ROOT / "skills" / "nl-to-sql-generator" / "scripts" / "generate_sql.py"


def _load_skill_sql_generator_module():
    spec = importlib.util.spec_from_file_location("skill_nl_to_sql_generator", SKILL_GENERATOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load nl-to-sql-generator script: {SKILL_GENERATOR_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_skill_sql_generator = _load_skill_sql_generator_module()


def generate_nl_sql(question: str, account: str = "") -> Dict[str, Any]:
    return _skill_sql_generator.generate_sql(question=question, account=account)
