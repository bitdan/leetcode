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
