import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_EXPORTER_SCRIPT = PROJECT_ROOT / "skills" / "sql-exporter" / "scripts" / "run_query.py"


def _load_sql_exporter_module():
    # 这里不是 subprocess 调脚本，而是把 skill 里的脚本当作模块动态加载，
    # 这样可以直接复用其中的校验、查询、导出函数。
    spec = importlib.util.spec_from_file_location("skill_sql_exporter_run_query", SQL_EXPORTER_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load sql exporter script: {SQL_EXPORTER_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_sql_exporter = _load_sql_exporter_module()


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
    """Execute a read-only SQL query and export the result set."""
    # 先统一加载 SQL，再复用 skill 里的只读校验规则。
    sql_text = _sql_exporter.load_sql(sql=sql, sql_file=sql_file)
    _sql_exporter.validate_read_only_sql(sql_text)

    normalized_params = params or {}
    output_path = Path(output).expanduser().resolve()
    # MCP tool 允许直接导出到文件，所以要先确保目标目录存在。
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if db_kind == "sqlite":
        if not db_path:
            raise ValueError("db_path is required when db_kind is sqlite")
        headers, rows = _sql_exporter.execute_sqlite(db_path, sql_text, normalized_params, max_rows)
    elif db_kind == "sqlalchemy":
        if not dsn:
            raise ValueError("dsn is required when db_kind is sqlalchemy")
        headers, rows = _sql_exporter.execute_sqlalchemy(dsn, sql_text, normalized_params, max_rows)
    else:
        raise ValueError("db_kind must be sqlite or sqlalchemy")

    # 导出格式和 skill/sql-exporter 的约束保持一致。
    if export == "csv":
        _sql_exporter.write_csv(output_path, headers, rows)
    elif export == "json":
        _sql_exporter.write_json(output_path, headers, rows)
    elif export == "xlsx":
        _sql_exporter.write_xlsx(output_path, headers, rows)
    else:
        raise ValueError("export must be csv, json, or xlsx")

    return {
        # 返回结构化元数据，前端和其他 agent 可以直接消费，不必自己解析控制台输出。
        "rows": len(rows),
        "columns": headers,
        "output": str(output_path),
        "export": export,
        "db_kind": db_kind,
        "sql": sql_text,
        "params": normalized_params,
    }
