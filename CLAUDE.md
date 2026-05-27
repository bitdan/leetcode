# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

Full guidelines are in `AGENTS.md`. This file covers the commands and architecture you'll need most often.

## Build & Test Commands

```bash
# Main module (Spring Boot)
mvn -pl module -am clean package          # build
mvn -pl module -am test                   # run tests
mvn -pl module -am test -Dtest=ClassName  # run a single test class

# LeetCode editor module
mvn -pl leetcode-editor -am test

# Full build, skip tests
mvn -DskipTests package

# With profile
mvn -Pdev test
```

**Frontend** (`tool-hub/`): `npm run build` to verify.

**Python** (`py/`): Activate conda env `ai` first. Verify with `python -m py_compile` on changed modules, or `python -c "from app import create_app; create_app()"` for full app instantiation.

## Architecture Overview

This is a **multi-Maven-module Java 8 repository** (`pom.xml` is the parent POM):

| Module | Purpose |
|---|---|
| `module/` | Spring Boot 2.7 main application (Undertow, not Tomcat). Contains Redisson, PDFBox, Lock4j, AOP, and business logic across ~10 subpackages |
| `leetcode-editor/` | LeetCode solution practice code |

Additional non-Maven components:

| Path | Stack | Purpose |
|---|---|---|
| `py/` | FastAPI + SQLAlchemy 2.0 + Alembic | Python backend, assembled via `py/bootstrap.py` dependency container into `py/app.py`. Domain modules use `schemas.py` / `service.py` / `store.py` / `routes.py` pattern |
| `tool-hub/` | Vue 3 + Vite + Vuetify + Tailwind | Frontend SPA. API wrappers in `src/api/`, pages in `src/views/`, routing in `src/router/index.ts` |
| `script/` | Shell/helper scripts | Docker, Redis configs, utilities |
| `skills/` | Claude Code skill definitions | `nl-to-sql-generator`, `sql-exporter`, `java-stacktrace-analyzer`, `leetcode-coach`, `langgraph-workflow`, `resume-analyzer` |

**Spring Boot module subpackages** (`module/src/main/java/com/linger/module/`): `redisson`, `pdf`, `shorturl`, `totp`, `timeWheel`, `coupon`, `groupbuy`, `transaction`, `jackson`, `annotation`, `util`.

## Key Dependencies

- **Java**: Spring Boot 2.7.18, Redisson 3.21.3, PDFBox 2.0.30, Lock4j 2.2.7, Hutool 5.8.35, OkHttp 4.12, Lombok 1.18.20, Jackson 2.13.5
- **Python**: FastAPI, SQLAlchemy 2.0, Alembic — pinned in `py/requirements.txt`
- **Frontend**: Vue 3, Vite, Vuetify, Pinia, VueUse, Tailwind CSS

## Database

PostgreSQL via SQLAlchemy + Alembic. DSN in `POSTGRES_DSN` env var. Migration commands:

```powershell
conda activate ai
cd py
$env:POSTGRES_DSN="postgresql+psycopg2://user:password@localhost:5432/database"
python -m alembic upgrade head
```

Tables follow domain prefixes (`post_*`, `sys_*`). Use `TIMESTAMPTZ` with `created_at`/`updated_at` columns.

## Commit Style

Conventional Commits with scopes: `feat(redisson): ...`, `refactor(pdf): ...`, `fix(market): ...`
