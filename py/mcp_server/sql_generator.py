import importlib.util
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_GENERATOR_SCRIPT = PROJECT_ROOT / "skills" / "nl-to-sql-generator" / "scripts" / "generate_sql.py"


def _load_skill_sql_generator_module():
    # 统一从 skill 目录加载执行入口，这样 MCP 的实现路径和 skill 定义保持一致。
    spec = importlib.util.spec_from_file_location("skill_nl_to_sql_generator", SKILL_GENERATOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load nl-to-sql-generator script: {SKILL_GENERATOR_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_skill_sql_generator = _load_skill_sql_generator_module()


def generate_nl_sql(question: str, account: str = "") -> Dict[str, Any]:
    """Generate SQL from a natural-language question through the nl-to-sql-generator skill entrypoint."""
    return _skill_sql_generator.generate_sql(question=question, account=account)
