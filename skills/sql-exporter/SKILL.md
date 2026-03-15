---
name: sql-exporter
description: Execute an existing read-only SQL query against SQLite or SQLAlchemy-supported databases and optionally export the result set. Use when Codex is given SQL plus connection details and must validate, run, and write results as CSV, JSON, or XLSX.
---

# SQL Exporter

## Overview

Run an existing read-only SQL query and optionally export the result set. Do not generate SQL from natural language in
this skill. Require the SQL text or SQL file first.

## Workflow

1. Gather execution inputs.
   Require the SQL statement or SQL file, the database kind, connection details, optional parameters, and the desired
   output format when export is requested.

2. Validate read-only SQL.
   Apply the checks in [references/sql-safety-rules.md](references/sql-safety-rules.md). Reject write statements,
   multi-statement SQL, and hidden admin commands before execution.

3. Execute locally when possible.
   Use `scripts/run_query.py` for SQLite or SQLAlchemy-backed databases such as MySQL and PostgreSQL.

4. Export only when requested.
   Write CSV, JSON, or XLSX when the user asks for a file. If the user only wants execution, report row count and
   columns without creating an output file unless the script requires one.

## Operating Rules

- Require explicit SQL input. Do not infer SQL from a natural-language request.
- Restrict execution to read-only statements.
- Reject multiple statements separated by semicolons.
- Reject DDL, DML, transaction control, and privilege management statements.
- Tell the user when execution cannot proceed because the SQL, connection string, database file, or parameters are
  missing.

## Execution

Run the helper script for local execution:

```bash
python scripts/run_query.py --db-kind sqlite --db-path ./demo.sqlite --sql-file ./query.sql --export csv --output ./result.csv
```

Named parameters can be passed as JSON:

```bash
python scripts/run_query.py --db-kind sqlite --db-path ./demo.sqlite --sql-file ./query.sql --params "{\"start\":\"2026-01-01\",\"end\":\"2026-01-31\"}" --export json --output ./result.json
```

For MySQL or other non-SQLite databases, use a SQLAlchemy URL:

```bash
python scripts/run_query.py --db-kind sqlalchemy --dsn "mysql+pymysql://user:pass@host:3306/db" --sql-file ./query.sql --export csv --output ./result.csv
```

## Response Pattern

Structure the answer in this order:

1. Briefly restate the SQL task.
2. Show or confirm the SQL being executed.
3. List connection inputs and parameters.
4. If executed, report row count and output path.

## References

- Read [references/sql-safety-rules.md](references/sql-safety-rules.md) before executing any query.

## Scripts

- Use scripts/export_sql.py as the local execution entrypoint when code needs to invoke this skill programmatically.
