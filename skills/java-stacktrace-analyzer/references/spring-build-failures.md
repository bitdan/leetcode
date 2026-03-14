# Spring And Build Failures

Use this file when the stack trace involves Spring Boot startup, bean creation, property binding, Maven, or Gradle.

## Spring Boot Startup

- `ApplicationContextException`
  - Usually a wrapper. Keep digging for `Caused by`.
  - Check embedded server startup, missing configuration, and bean graph failures.

- `BeanCreationException`
  - Identify the bean name, factory method, and nested cause.
  - Common checks:
    - constructor parameters not satisfiable
    - `@Value` placeholder missing
    - init method throws
    - circular dependency

- `UnsatisfiedDependencyException`
  - Usually missing bean, ambiguous bean, or failure while creating a dependency.
  - Check component scanning, `@Bean` methods, qualifiers, and profile conditions.

- `NoSuchBeanDefinitionException`
  - Check whether the bean is annotated, scanned, conditionally excluded, or in another module not loaded.

- `ConfigurationPropertiesBindException`
  - Check property names, formats, nested object fields, and active profiles.

- `PortInUseException`
  - Check which process owns the port or change `server.port`.

## JDBC And Datasource Startup

- `Communications link failure`, `ConnectException`, `UnknownHostException`
  - Check database host, port, DNS, firewall, VPN, and credentials.

- `Access denied for user`
  - Check username, password, host-based grants, and auth plugin compatibility.

- `CannotGetJdbcConnectionException`
  - Usually a wrapper around connectivity or driver issues.
  - Check the nested JDBC exception and datasource URL.

- `Driver class not found`
  - Check JDBC driver dependency and runtime scope.

## Maven And Gradle

- Compilation failures
  - Focus on the first compiler error, not the summary footer.
  - Check source/target level, missing imports, generated sources, and annotation processors.

- Test failures
  - Separate assertion failures from application startup failures in test context.
  - If Spring tests fail before assertions run, treat them as startup issues first.

- Dependency resolution failures
  - Check repository reachability, credentials, mirror settings, and artifact coordinates.

- `NoSuchMethodError` during tests or startup
  - Treat as dependency version conflict unless proven otherwise.
  - Recommend checking `mvn dependency:tree` or Gradle dependency insight.

## Suggested Diagnostic Order

1. Find the deepest nested cause.
2. Locate the first user-controlled class or configuration entry.
3. Decide whether the failure is code, configuration, dependency, or environment.
4. Suggest the smallest verification step that can confirm the diagnosis.
