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

1. The query is read-only.
2. The statement count is exactly one.
3. Parameters are supplied in the correct shape.
4. The connection target is explicit.
5. The export path is explicit when export is requested.
