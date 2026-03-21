import importlib.util
from pathlib import Path
from typing import Any, Dict, Optional

from mcp_server.path_utils import find_repo_root

PROJECT_ROOT = find_repo_root(Path(__file__))
SKILL_EXPORTER_SCRIPT = PROJECT_ROOT / "skills" / "sql-exporter" / "scripts" / "export_sql.py"


def _load_skill_sql_exporter_module():
    spec = importlib.util.spec_from_file_location("skill_sql_exporter", SKILL_EXPORTER_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load sql-exporter script: {SKILL_EXPORTER_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_skill_sql_exporter = _load_skill_sql_exporter_module()


def run_sql_export(
    db_kind: str,
    sql: str = "",
    sql_file: str = "",
    params: Optional[Dict[str, Any]] = None,
    export: str = "json",
    output: str = "",
    max_rows: int = 5000,
    db_path: str = "",
    dsn: str = "",
) -> Dict[str, Any]:
    return _skill_sql_exporter.export_sql(
        db_kind=db_kind,
        sql=sql,
        sql_file=sql_file,
        params=params,
        export=export,
        output=output,
        max_rows=max_rows,
        db_path=db_path,
        dsn=dsn,
    )
