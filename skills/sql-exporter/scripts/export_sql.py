from pathlib import Path
import sys
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PY_ROOT = PROJECT_ROOT / "py"

if str(PY_ROOT) not in sys.path:
    sys.path.append(str(PY_ROOT))

from mcp_server.sql_exporter_core import run_sql_export


def export_sql(
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
    """Skill entrypoint for read-only SQL execution and export."""
    return run_sql_export(
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
