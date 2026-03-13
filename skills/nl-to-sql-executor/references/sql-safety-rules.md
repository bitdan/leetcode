# SQL Safety Rules

Apply these rules before execution.

## Allowed

- Single-statement `SELECT`
- Single-statement `WITH ... SELECT`
- Bound parameters for filter values

## Disallowed

- Multiple statements
- `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `REPLACE`
- `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `RENAME`
- `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`
- `GRANT`, `REVOKE`
- `CALL`, `EXEC`, `EXECUTE`
- SQLite admin commands such as `ATTACH`, `DETACH`, `PRAGMA`, `VACUUM`

## Review Checklist

Before execution, verify:

1. Every table exists in the supplied schema.
2. Every selected or filtered column exists in the supplied schema.
3. Join conditions use declared relationship keys.
4. Aggregations match the requested grain.
5. The query is read-only.
6. The export path is explicit.
