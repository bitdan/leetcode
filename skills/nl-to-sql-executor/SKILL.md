---
name: nl-to-sql-executor
description: Convert a natural-language analytics request into a schema-aware SQL query, then run the query and export the result set. Use when Codex is given business questions plus table or column information and must produce read-only SQL, validate it against the supplied schema, execute it safely, and export the data as CSV or JSON.
---

# NL To SQL Executor

## Overview

Turn a natural-language question plus user-provided schema details into a safe, read-only SQL workflow. Require explicit
table and column information before generating SQL, then execute only `SELECT` or `WITH ... SELECT` queries and export
the result set.

## Workflow

1. Gather the query intent.
   Infer the business metric, filters, grouping, ordering, date range, and expected output columns from the user's
   natural-language request.

2. Gather the schema context.
   Require table names, column names, join keys, and any code-value semantics from the user or an attached schema file
   before writing SQL. If the schema is incomplete, stop and ask for the missing fields instead of guessing.
   Use [references/schema-input-template.md](references/schema-input-template.md) as the intake format.

3. Map intent to schema.
   Resolve each requested metric or dimension to actual columns. State assumptions explicitly when multiple mappings are
   plausible. Refuse to invent columns, tables, or business rules that are not present in the supplied schema.

4. Generate read-only SQL.
   Produce a single query that starts with `SELECT` or `WITH`. Prefer explicit column lists over `SELECT *`. Keep joins
   and filters readable. Add a row limit when the user asks for a sample or when the result size is unclear.

5. Self-check the SQL.
   Verify the query uses only supplied tables and columns, has the intended grouping and filters, and does not contain
   write or admin statements. Apply the rules in [references/sql-safety-rules.md](references/sql-safety-rules.md).

6. Execute and export.
   Use `scripts/run_query.py` to run the query when local execution is possible. Export to CSV, JSON, or XLSX. Report
   the SQL, parameter values, output path, and row count.

## Operating Rules

- Require schema context before generating SQL. A natural-language question alone is not enough.
- Prefer parameterized execution when values are user-provided.
- Restrict execution to read-only statements.
- Reject multiple statements separated by semicolons.
- Reject DDL, DML, transaction control, and privilege management statements.
- Tell the user when execution cannot proceed because a connection string, database file, or schema is missing.

## Execution

Run the helper script for local execution:

```bash
python scripts/run_query.py --db-kind sqlite --db-path ./demo.sqlite --sql-file ./query.sql --export csv --output ./result.csv
```

Named parameters can be passed as JSON:

```bash
python scripts/run_query.py --db-kind sqlite --db-path ./demo.sqlite --sql-file ./query.sql --params "{\"start\":\"2026-01-01\",\"end\":\"2026-01-31\"}" --export json --output ./result.json
```

For non-SQLite databases, use a SQLAlchemy URL:

```bash
python scripts/run_query.py --db-kind sqlalchemy --dsn "mysql+pymysql://user:pass@host:3306/db" --sql-file ./query.sql --export csv --output ./result.csv
```

## Response Pattern

When using this skill, structure the answer in this order:

1. Briefly restate the business question.
2. List the schema elements used.
3. Show the SQL.
4. State any assumptions or unresolved ambiguities.
5. If executed, report row count and export file path.

## References

- Read [references/schema-input-template.md](references/schema-input-template.md) when the user has not provided
  structured schema information yet.
- Read [references/sql-safety-rules.md](references/sql-safety-rules.md) before executing any query.
- Read [references/amazon-order-schema-example.md](references/amazon-order-schema-example.md) for a concrete two-table
  Amazon order schema example.
- Read [references/acceptance-tests.md](references/acceptance-tests.md) for validation prompts and expected review
  points.
