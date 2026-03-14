#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union

FORBIDDEN_PATTERN = re.compile(
    r"\b("
    r"insert|update|delete|merge|replace|"
    r"create|alter|drop|truncate|rename|"
    r"begin|commit|rollback|savepoint|"
    r"grant|revoke|call|exec|execute|"
    r"attach|detach|pragma|vacuum"
    r")\b",
    re.IGNORECASE,
)


def strip_sql_comments(sql: str) -> str:
    sql = sql.lstrip("\ufeff")
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    sql = re.sub(r"--.*?$", " ", sql, flags=re.MULTILINE)
    return sql.strip()


def validate_read_only_sql(sql: str) -> None:
    normalized = strip_sql_comments(sql)
    if not normalized:
        raise ValueError("SQL is empty.")

    if normalized.count(";") > 1:
        raise ValueError("Multiple SQL statements are not allowed.")

    if ";" in normalized[:-1]:
        raise ValueError("Semicolons are only allowed at the end of a single statement.")

    if not re.match(r"^\s*(select|with)\b", normalized, re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries are allowed.")

    if FORBIDDEN_PATTERN.search(normalized):
        raise ValueError("SQL contains forbidden keywords for read-only execution.")


def load_sql(sql: str, sql_file: str) -> str:
    if sql:
        return sql
    if not sql_file:
        raise ValueError("Either --sql or --sql-file must be provided.")
    return Path(sql_file).read_text(encoding="utf-8")


def load_params(raw: str) -> Union[Sequence[Any], Dict[str, Any]]:
    if not raw:
        return {}
    data = json.loads(raw)
    if isinstance(data, (dict, list)):
        return data
    raise ValueError("--params must be a JSON object or array.")


def execute_sqlite(
    db_path: str,
    sql: str,
    params: Union[Sequence[Any], Dict[str, Any]],
    max_rows: int,
) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(sql, params)
        headers = [desc[0] for desc in cursor.description or []]
        rows = cursor.fetchmany(max_rows)
        return headers, rows
    finally:
        conn.close()


def execute_sqlalchemy(
    dsn: str,
    sql: str,
    params: Union[Sequence[Any], Dict[str, Any]],
    max_rows: int,
) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for --db-kind sqlalchemy.") from exc

    engine = create_engine(dsn)
    with engine.connect() as conn:
        result = conn.execute(text(sql), params if isinstance(params, dict) else {})
        headers = list(result.keys())
        rows = result.fetchmany(max_rows)
        return headers, rows


def write_csv(output: Path, headers: List[str], rows: Iterable[Tuple[Any, ...]]) -> None:
    with output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


def write_json(output: Path, headers: List[str], rows: Iterable[Tuple[Any, ...]]) -> None:
    payload = [dict(zip(headers, row)) for row in rows]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_excel_value(value: Any) -> Any:
    if isinstance(value, (datetime, date, int, float, bool)) or value is None:
        return value
    return str(value)


def write_xlsx(output: Path, headers: List[str], rows: Iterable[Tuple[Any, ...]]) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError as exc:
        raise RuntimeError("openpyxl is required for --export xlsx.") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "query_result"
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for row in rows:
        sheet.append([_normalize_excel_value(value) for value in row])

    for column_cells in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 40)

    workbook.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a read-only SQL query and export the result set.")
    parser.add_argument("--db-kind", choices=["sqlite", "sqlalchemy"], required=True)
    parser.add_argument("--db-path", help="SQLite database path.")
    parser.add_argument("--dsn", help="SQLAlchemy DSN for MySQL/PostgreSQL/others.")
    parser.add_argument("--sql", help="Inline SQL text.")
    parser.add_argument("--sql-file", help="Path to a .sql file.")
    parser.add_argument("--params", help="JSON object or array for query parameters.")
    parser.add_argument("--export", choices=["csv", "json", "xlsx"], required=True)
    parser.add_argument("--output", required=True, help="Export file path.")
    parser.add_argument("--max-rows", type=int, default=5000, help="Maximum rows to fetch and export.")
    args = parser.parse_args()

    sql = load_sql(args.sql, args.sql_file)
    validate_read_only_sql(sql)
    params = load_params(args.params)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.db_kind == "sqlite":
        if not args.db_path:
            raise ValueError("--db-path is required when --db-kind sqlite.")
        headers, rows = execute_sqlite(args.db_path, sql, params, args.max_rows)
    else:
        if not args.dsn:
            raise ValueError("--dsn is required when --db-kind sqlalchemy.")
        headers, rows = execute_sqlalchemy(args.dsn, sql, params, args.max_rows)

    if args.export == "csv":
        write_csv(output, headers, rows)
    elif args.export == "json":
        write_json(output, headers, rows)
    else:
        write_xlsx(output, headers, rows)

    print(json.dumps({
        "rows": len(rows),
        "columns": headers,
        "output": str(output.resolve()),
        "export": args.export,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
