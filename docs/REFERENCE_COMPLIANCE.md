# Reference implementation evidence

Status recorded after the local Compose verification on 2 September 2026. “Complete” means
implemented and exercised in the local reference. External cloud/live-data evidence is kept
separate so a fixture-backed laptop run is not misrepresented as production evidence.

## Platform matrix

| Criterion | Implementation or document | Automated protection | Demonstration | Status |
|---|---|---|---|---|
| One seeded multi-container stack | `docker-compose.yml`, `infra/postgres`, `infra/kafka` | Container health checks | `docker compose up --build` and `docker compose ps --all` | Complete |
| Seven-container runtime topology | `docs/TARGET_ARCHITECTURE.md`, Compose | `docker compose config` | Postgres, Kafka, API, executor, Auth, UI and Analytics healthy | Complete |
| Core trading domain inside Trade API | `services/trade-api/src/main/java/com/tradingplatform/domain` | Trade API unit/application/persistence suite | Build API without a local Maven install | Complete |
| Six Trade API routes and error envelope | `docs/contracts/trade-api.yaml`, API controllers | Controller and service tests | Place, read and cancel with bearer token | Complete |
| Parameterised SQL, transactions and locking | API mappers and services | `MapperIntegrationTest`, `OrderServiceTest` | Place and asynchronously settle an order | Complete |
| Contracted Kafka topics and DLTs | `docs/contracts/kafka-topics.md`, `infra/kafka/create-topics.sh` | Idempotency tests in API/executor/analytics | List topics from the Kafka container | Complete |
| Asynchronous execution with fixture pricing | Trade Executor | Executor unit tests | Order transitions `NEW` to `FILLED` | Complete |
| Scheduled Java market-data poller | Executor `marketdata` package | Executor build and health indicator | Logs show discovered/published symbols | Complete |
| Real Auth and configuration-only stub | `services/auth-service`, Compose `stub` profile | Auth contract test | Login as `demo1`; optional stub on port 3001 | Complete |
| Incremental analytics and DuckDB dashboard | `analytics/src/analytics` | Analytics pytest suite | Trade event appears at `localhost:8000` | Complete |
| Customer preferences | Trade API `extensions/preferences` | Validation and route security through common API tests | Read and change the selected channel | Complete |
| Preference-driven notifications | Trade API `extensions/notifications` | Event-id uniqueness in Postgres | Fill creates one inbox row using selected channel | Complete |
| Market board, watchlists and current prices | Trade API `extensions/market` and `extensions/watchlists` | Market event deduplication constraint; Angular market-price test | Ticket and seeded list show feed mode, quote time and freshness | Complete |
| Threshold alert delivery | Watchlist consumer plus notification service | Atomic status update and event-id deduplication | Crossing quote triggers once and creates inbox row | Complete |
| Portfolio and P&L | Trade API `extensions/portfolio` | Core order/position tests | Summary, priced positions and symbol P&L endpoints | Complete |
| Plain Angular experience | `ui/src/app/features`, `docs/UI_DESIGN.md` | Angular build and existing unit/Playwright suite | Sign in and navigate all protected routes | Complete |
| Fixture mode without external network | `FAUXNANCE_MODE=fixture`, executor fixture client | Java and UI production builds | Default Compose startup with no API key | Complete |
| Live Fauxnance path | `FAUXNANCE_MODE=live`, root README pre-flight | Not run without a participant key | `/health`, `/usage`, then Compose in live mode | Ready, not evidenced |
| S3/CloudFront deployment evidence | Existing curriculum requirement | Not part of local verification | Requires an AWS account and scoped credentials | Not evidenced |

The India extension requirements are implemented in full. Portfolio and P&L is also the
US/Ireland elective. The reference takes the stricter refresh-token, historical-data and
analytics readings where the cohorts differ.

## Starter-loader flaw mapping

The descriptions remain in the instructor-only `docs/PLANTED_STARTER_FLAWS.md`; this table only
maps each numbered flaw to the worked reference.

| Flaw | Reference resolution | Test evidence |
|---|---|---|
| 1 | Separate `analytics/etl/extract.py`, `transform.py` and `load.py` | `test_transform.py`, `test_load_idempotency.py` |
| 2 | Canonical constraints in `analytics/db/schema.sql` and the analytics contract | `test_load_idempotency.py` |
| 3 | Loader-owned watermark in `analytics/etl/watermark.py` | `test_load_idempotency.py` |
| 4 | Type 2 account change handling in `analytics/etl/load.py` | `test_load_idempotency.py` |
| 5 | Quarantine and validation modules | `test_validate.py` |
| 6 | Filled value uses executed price in `analytics/etl/transform.py` | `test_transform.py` |
| 7 | Central settings in `analytics/config.py` | Analytics configuration fixtures |
| 8 | Bound extraction parameters in `analytics/etl/extract.py` | Analytics extract exercised through load tests |
| 9 | Reconciliation in `analytics/etl/pipeline.py` and maintained tests | `test_load_idempotency.py`, `test_validate.py` |

The historical “characterisation tests committed before refactor” criterion is a commit-order
teaching artifact from the cohort branches. It cannot be recreated honestly after the fact in
this consolidated repository; the final corrected behavior and its tests are present.
