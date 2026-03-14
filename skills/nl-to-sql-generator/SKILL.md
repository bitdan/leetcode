---
name: nl-to-sql-generator
description: Convert a natural-language analytics or reporting request into schema-aware read-only SQL. Use when Codex is given a business question plus table, column, and join details and should return SQL only, without executing it or exporting data.
---

# NL To SQL Generator

## Overview

Turn a natural-language question plus user-provided schema details into a safe, read-only SQL query. Stop at SQL
generation. Do not execute the query and do not export results.

## Workflow

1. Gather the query intent.
   Infer the business metric, filters, grouping, ordering, date range, and expected output columns from the user's
   request.

2. Gather the schema context.
   Require table names, column names, join keys, date columns, and any code-value semantics from the user or an
   attached schema file before writing SQL. If the schema is incomplete, stop and ask for the missing fields instead of
   guessing. Use [references/schema-input-template.md](references/schema-input-template.md) as the intake format.

3. Map intent to schema.
   Resolve each requested metric or dimension to actual columns. State assumptions explicitly when multiple mappings are
   plausible. Refuse to invent columns, tables, or business rules that are not present in the supplied schema.

4. Generate read-only SQL.
   Produce a single query that starts with `SELECT` or `WITH`. Prefer explicit column lists over `SELECT *`. Keep joins
   and filters readable. Add a row limit when the user asks for a sample or when the result size is unclear.

5. Self-check the SQL.
   Verify the query uses only supplied tables and columns, has the intended grouping and filters, and does not contain
   write or admin statements. Apply the rules in [references/sql-safety-rules.md](references/sql-safety-rules.md).

## Operating Rules

- Require schema context before generating SQL. A natural-language question alone is not enough.
- Prefer parameterized SQL when values are user-provided.
- Return SQL only. Do not execute it.
- Restrict output to a single read-only statement.
- Reject multiple statements separated by semicolons.
- Reject DDL, DML, transaction control, and privilege management statements.

## Response Pattern

Structure the answer in this order:

1. Briefly restate the business question.
2. List the schema elements used.
3. Show the SQL.
4. State any assumptions or unresolved ambiguities.

## References

- Read [references/schema-input-template.md](references/schema-input-template.md) when the user has not provided
  structured schema information yet.
- Read [references/sql-safety-rules.md](references/sql-safety-rules.md) before returning SQL.
- Read [references/amazon-order-schema-example.md](references/amazon-order-schema-example.md) for a concrete two-table
  example when the user needs a sample schema format.
