FROM maven:3.9.9-eclipse-temurin-8 AS builder

WORKDIR /build

ARG APP_PROFILE=dev

COPY pom.xml ./pom.xml
COPY leetcode-editor/pom.xml ./leetcode-editor/pom.xml
COPY module/pom.xml ./module/pom.xml
COPY module/src ./module/src

RUN mvn -B -pl module -am clean package spring-boot:repackage -P${APP_PROFILE} -DskipTests \
    && cp "$(find /build/module/target -maxdepth 1 -type f -name '*.jar' ! -name '*.original' | head -n 1)" /build/app.jar

FROM eclipse-temurin:8-jre

WORKDIR /app

COPY --from=builder /build/app.jar /app/app.jar

EXPOSE 9999

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
