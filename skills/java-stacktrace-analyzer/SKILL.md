---
name: java-stacktrace-analyzer
description: Analyze Java, Spring Boot, Maven, Gradle, and JDBC stack traces to identify the root cause and propose concrete fixes. Use when Codex is given Java exception output, startup logs, build failures, test failures, or nested Caused by chains and must explain what broke, where it broke, and how to fix it.
---

# Java Stacktrace Analyzer

## Overview

Analyze Java error output and convert it into a root-cause diagnosis plus concrete remediation steps. Focus on the
lowest meaningful failure, separate wrapper exceptions from the real cause, and call out missing context when the stack
trace alone is insufficient.

## Workflow

1. Find the real failure point.
   Scan for the deepest useful `Caused by:` entry, the first application-frame line, and the exception type that best
   explains the failure. Ignore high-level wrappers such as framework bootstrap exceptions unless no deeper cause exists.

2. Classify the failure.
   Decide whether the error is primarily:
   - application logic
   - dependency injection or Spring wiring
   - configuration or environment
   - database or SQL
   - serialization or deserialization
   - build or dependency resolution
   - concurrency or resource exhaustion

3. Map the stack to the code and runtime boundary.
   Identify the most relevant class, method, bean, property, SQL statement, or dependency edge. Prefer the user's code
   over framework internals when both appear in the trace.

4. Explain the root cause plainly.
   State what actually failed, why it failed, and which line or configuration entry is most likely responsible. If the
   evidence is incomplete, say so explicitly instead of guessing.

5. Propose fixes in priority order.
   Give the smallest likely fix first, then list alternative fixes only when multiple root causes are plausible.
   Include verification steps when the fix depends on runtime configuration or external systems.

## Operating Rules

- Prioritize the deepest actionable `Caused by` chain over top-level wrapper exceptions.
- Distinguish framework wrappers from user-code failures.
- Quote only the critical stack lines needed for explanation.
- Do not invent file names, line numbers, bean names, or configuration keys that are not present in the trace or user
  context.
- Ask for the full stack trace, relevant code, or configuration when the visible excerpt is too short to support a
  reliable diagnosis.
- When the error is a build failure, inspect plugin, module, and dependency coordinates before suggesting code changes.

## Response Pattern

Structure the answer in this order:

1. Root cause
2. Key evidence
3. Likely fix
4. Other plausible causes or follow-up checks
5. Missing context, if any

## References

- Read [references/common-failures.md](references/common-failures.md) for common exception families and what they
  usually mean.
- Read [references/spring-build-failures.md](references/spring-build-failures.md) for Spring Boot startup, bean
  creation, Maven, and Gradle failure patterns.
