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
