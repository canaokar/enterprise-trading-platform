FROM maven:3.9-eclipse-temurin-21 AS build

WORKDIR /app

COPY pom.xml .
COPY src src

RUN mvn -B -Dmaven.test.skip=true package

FROM eclipse-temurin:21-jre-alpine AS runtime

RUN addgroup -S trading && adduser -S -G trading trading

WORKDIR /app
COPY --from=build /app/target/trade-api-1.0.0.jar app.jar
USER trading

EXPOSE 8080

ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0 -XX:+ExitOnOutOfMemoryError"

HEALTHCHECK --interval=15s --timeout=3s --start-period=40s --retries=5 \
  CMD wget -qO- http://localhost:8080/actuator/health | grep -q '"status":"UP"' || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
