# Enterprise Trading Platform reference

The reference platform runs as one Docker Compose stack. Docker Desktop or Docker
Engine with the Compose plugin is the only host prerequisite.

## Start

```bash
docker compose up --build
```

The first build downloads the service dependencies. Compose then creates the database,
loads the demo trading data, creates the Kafka topics, migrates the auth schema and
creates the demo users.

The default stack has seven long-running containers: Postgres, Kafka, Trade API,
Trade Executor, Auth, Angular/nginx and Analytics/DuckDB. `db-init` and `kafka-init`
are one-shot containers and should finish with exit code 0.

| Component | URL |
|---|---|
| Angular application | http://localhost:4200 |
| Trade API health | http://localhost:8080/actuator/health |
| Trade API contract | http://localhost:8080/swagger-ui |
| Auth API contract | http://localhost:3000/docs |
| Analytics report | http://localhost:8000 |

The Angular application includes a Kafka-fed market board, order entry/history,
portfolio and P&amp;L, preferences, notification inbox, watchlists and price alerts.
Every quote is labeled as either `LIVE FEED` or `DEMO FEED`; the browser never receives
the Fauxnance key.

Sign in with `demo1` and `Trainee#2026`. Users `demo2` through `demo5` use the same
password and map to the corresponding seeded accounts.

Fixture quotes are the default, so placing an order does not need network access or an
API key. To exercise live pricing, set `FAUXNANCE_MODE=live` and
`FAUXNANCE_API_KEY` in a local `.env` before starting the stack.

Before a live demonstration, check the upstream independently:

```bash
curl -fsS https://y4t9nq2bqf.execute-api.eu-west-2.amazonaws.com/v1/health
curl -fsS -H "x-api-key: $FAUXNANCE_API_KEY" \
  https://y4t9nq2bqf.execute-api.eu-west-2.amazonaws.com/v1/usage
```

## Check and stop

```bash
docker compose ps
docker compose logs -f trade-api trade-executor
docker compose down
```

To discard all local data and recreate the canonical seed set:

```bash
docker compose down --volumes
docker compose up --build
```

The auth stub is not part of the normal stack. Start it only for the replacement
demonstration with `docker compose --profile stub up auth-stub`.
