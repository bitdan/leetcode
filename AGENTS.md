# Repository Guidelines

## Project Structure & Module Organization

This is a Maven multi-module Java repository. The parent `pom.xml` defines shared dependency versions and profiles.

Key paths:

- `module/src/main/java` and `module/src/main/resources`: primary Spring Boot module code and resources.
- `module/src/test/java`: tests for the `module` module.
- `leetcode-editor/src/main/java`: LeetCode solution implementations.
- `script/`, `py/`, `tool-hub/`: helper scripts and tooling (not part of the main build).

## Build, Test, and Development Commands

Use Maven from the repo root:

1. `mvn -pl module -am clean package` — build the main module and its dependencies.
2. `mvn -pl module -am test` — run tests for the main module.
3. `mvn -pl leetcode-editor -am test` — run tests (if any) for the LeetCode editor module.
4. `mvn -DskipTests package` — full build without tests.

## Coding Style & Naming Conventions

- Language level: Java 8 (`maven.compiler.source/target` set to 8).
- Indentation: 4 spaces, no tabs.
- Packages follow reverse-domain naming (e.g., `com.linger...`).
- Class names: `PascalCase`; methods/fields: `camelCase`; constants: `UPPER_SNAKE_CASE`.
- Lombok is used in the `module` module—prefer Lombok annotations over boilerplate.

## Testing Guidelines

- Testing stack: Spring Boot Test (JUnit 5 via `spring-boot-starter-test`).
- Place tests under `module/src/test/java` and name them `*Test`.
- Keep unit tests fast; add integration tests only when needed.
- Use `@Slf4j` in tests and log key assertions/results so test runs emit useful output.
- No explicit coverage threshold is configured.

## Commit & Pull Request Guidelines

Commit history follows Conventional Commits with scopes, for example:

- `feat(redisson): add like service`
- `refactor(pdf): optimize text removal`

For PRs:

1. Provide a clear description of the change and rationale.
2. Link related issues or requirements.
3. Include test evidence (commands run and results).

## Configuration & Profiles

The parent POM defines `dev` and `local` profiles. Use them for environment-specific overrides when needed (e.g.,
`mvn -Pdev test`).

## Tool Hub Frontend Guidelines

The `tool-hub/` app is a Vue 3 + Vite + Vuetify frontend.

- API wrappers live under `tool-hub/src/api`. Use the existing `tool-hub/src/utils/request.ts` axios wrapper so
  authentication headers, cookies, timeout handling, and global error behavior stay consistent.
- Feature pages live under `tool-hub/src/views`. Group larger product areas by domain, such as
  `tool-hub/src/views/community`.
- Register navigable pages in `tool-hub/src/router/index.ts`. Add `requiresAuth: true` only for pages that actually
  require login; keep read-only public pages public when possible.
- The side navigation is built from grouped router records in `tool-hub/src/components/AppNavigation.vue`. Add new
  top-level product areas as route groups, then include that group in the navigation filter.
- Prefer Vuetify components and Material Design Icons (`mdi-*`) for controls. Keep pages usable as the first screen;
  do not add marketing-style landing pages for internal tools or app features.
- For frontend verification, run `npm run build` from `tool-hub/`.

## Python Backend Guidelines

The `py/` app is a FastAPI backend assembled in `py/app.py` through a dependency container from `py/bootstrap.py`.

- Add new backend features as domain modules under `py/<domain>/`, typically with `schemas.py`, `service.py`,
  `store.py`, and `routes.py`.
- Route factories should expose `create_router(container)` and be registered in `py/app.py`.
- Reuse the existing auth dependency pattern from `auth.routes`: `create_auth_router` stores `get_current_user` on the
  auth router, and other routers can retrieve it through `container._auth_router`.
- Keep API responses aligned with `auth.schemas.ApiResponse` unless there is a strong reason to use a different
  contract.
- Configuration belongs in `py/core/settings.py` and should be loaded from environment variables or `py/.env`.
- Runtime dependencies used by the deployed Python service must be added to `py/requirements.txt`.
- For backend verification, at minimum run `python -m py_compile` on changed Python modules. If dependencies and
  services are available, also instantiate the app with `python -c "from app import create_app; create_app()"`.

## Database Guidelines

PostgreSQL is the preferred persistent store for new Tool Hub business features that need durable relational data.

- Put schema files in `py/` with clear names, such as `py/posts_schema.sql`.
- Use table names prefixed by the feature domain. For the post feature, use `post_` tables such as `post_posts`,
  `post_comments`, and `post_likes`.
- Use `sys_` table names for authentication, users, roles, permissions, and other system-level account data, such as
  `sys_users`.
- Name indexes and constraints with the same feature prefix, for example `idx_post_posts_status_created` and
  `uq_post_likes_post_user`.
- Use `TIMESTAMPTZ` for persisted timestamps, with `created_at` and `updated_at` columns on mutable business tables.
- Prefer soft delete for user-generated content by using a `status` column such as `published`, `deleted`, or `hidden`.
- The Python backend reads PostgreSQL through `POSTGRES_DSN`. In URL-style DSNs, URL-encode reserved characters in
  passwords; for example `@` must be written as `%40`.
- In Docker Compose, services on `linger-net` should connect to PostgreSQL by container name, for example
  `postgres-db:5432`, not by public IP.
- When adding or changing deployed database requirements, update both the SQL schema file and any Docker/runtime
  configuration needed to reach the database.

## Dependency & Deployment Notes

- When adding new runtime components or protocols, update the actual deployment dependency files, not only local
  environment exports. For the Python Docker backend, `py/Dockerfile` installs from `py/requirements.txt`; packages
  listed only in `py/ai.yaml` are not included in the deployed image.
- Pay special attention to optional runtime extras required by new components. For example, FastAPI WebSocket routes
  served by Uvicorn require `uvicorn[standard]`, `websockets`, or `wsproto`; otherwise upgrade requests can be logged as
  unsupported and handled as plain HTTP requests.
- After introducing frontend features that depend on backend protocols such as WebSocket or SSE, verify both the
  browser request and the container logs in the deployed environment.

## Skill Routing

Use the local skills under `skills/` when the request clearly matches one of the workflows below. Prefer the most
specific skill that fits the task. If the user explicitly names a skill, use that skill.

- `nl-to-sql-generator`
  Use for natural language plus schema input when the task is to generate read-only SQL only. Do not execute SQL in
  this skill.

- `sql-exporter`
  Use for an existing SQL statement plus database connection details when the task is to validate, execute, or export
  query results. Do not invent SQL from a business question in this skill.

- `java-stacktrace-analyzer`
  Use for Java, Spring Boot, Maven, Gradle, JDBC, or test stack traces when the task is to identify the root cause and
  propose fixes.

## Skill Usage Notes

- Ask for missing schema details before using `nl-to-sql-generator`.
- Ask for missing SQL or connection details before using `sql-exporter`.
- For Java error analysis, prioritize the deepest actionable `Caused by` chain instead of top-level wrapper exceptions.
- Keep skill responsibilities separate. Do not let `sql-exporter` generate SQL, and do not let
  `java-stacktrace-analyzer` modify code unless the user asks for code changes after the diagnosis.
