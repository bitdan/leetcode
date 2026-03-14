# Common Failures

Use this file to map common Java exception families to likely root causes and checks.

## Null And Type Errors

- `NullPointerException`
  - Check which variable is null at the first user-code frame.
  - In Java 14+, helpful NPE messages may name the null expression.
  - Common fixes: initialize dependency, validate input, guard optional values, fix bean wiring.

- `ClassCastException`
  - Check the source and target types in the message.
  - Common fixes: correct generic types, remove unsafe casts, align serializer/deserializer contracts.

- `NumberFormatException`
  - Check the offending input string and where parsing occurs.
  - Common fixes: validate input, trim whitespace, handle empty strings, use safe parsing rules.

- `IndexOutOfBoundsException` or `ArrayIndexOutOfBoundsException`
  - Check collection length and caller assumptions.
  - Common fixes: guard indexes, fix loop bounds, validate external input.

## Reflection And Class Loading

- `ClassNotFoundException`
  - Usually means the class is absent from the runtime classpath.
  - Check dependency scope, shading, module boundaries, and classloader differences.

- `NoClassDefFoundError`
  - The class existed at compile time but is unavailable or failed during initialization at runtime.
  - Check transitive dependency conflicts, packaging, and static initializer failures.

- `NoSuchMethodError` or `NoSuchFieldError`
  - Usually indicates binary incompatibility between library versions.
  - Check dependency tree and jar version skew first.

## SQL And Persistence

- `SQLException`
  - Read vendor-specific message text first.
  - Check SQL syntax, schema drift, permissions, network connectivity, and transaction state.

- `SQLSyntaxErrorException`
  - Check generated SQL, reserved words, column names, and database dialect.

- `DataIntegrityViolationException`
  - Usually wraps unique key, foreign key, or not-null violations.
  - Check the nested SQL exception and the exact constraint name.

- `LazyInitializationException`
  - Usually means ORM access happened outside an active session.
  - Check transaction boundaries, fetch strategy, and DTO mapping.

## HTTP And Serialization

- `HttpMessageNotReadableException`
  - Usually malformed JSON, wrong field type, or missing constructor.
  - Check request body shape against DTO fields and Jackson annotations.

- `MismatchedInputException`
  - Usually JSON token type does not match the target field type.
  - Check arrays vs objects, numbers vs strings, and enum values.

## Concurrency And Resource Problems

- `OutOfMemoryError`
  - Distinguish heap, metaspace, direct buffer, and GC overhead variants.
  - Check recent load changes, leaks, large caches, and batch sizes.

- `StackOverflowError`
  - Usually uncontrolled recursion or cyclic object serialization.
  - Check recursive method calls, Lombok-generated `toString`, and entity graph cycles.

- `RejectedExecutionException`
  - Usually thread pool saturation or executor shutdown.
  - Check pool sizing, queue policy, and lifecycle management.
