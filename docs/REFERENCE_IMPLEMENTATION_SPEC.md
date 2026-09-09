# Reference implementation specification

Status: approved implementation specification. Backend restructuring starts once the
compliance matrix in Phase 1 is complete. Angular implementation waits for the screen
designs in Phase 2 to be accepted.

## Purpose

The `reference` branch is the worked example of the Enterprise Trading Platform.
It must demonstrate the same engineering outcomes that the graduate teams are
asked to deliver, rather than merely provide code that resembles the target
architecture.

The implementation is assessed against the union of the mandatory requirements on
`origin/us-ireland` and `origin/india`. The student branches remain specification
branches and do not receive reference implementation code.

This is not a greenfield build. The current `reference` branch contains substantial
working code, tests, infrastructure and deployment material. The work described here
restructures that code to match `TARGET_ARCHITECTURE.md`, completes the missing
India-mandatory features, and packages the result as a reproducible demonstration.

Two audiences set the quality bar. An instructor must be able to run the
demonstration and have it work every time. A graduate must be able to read any part
of it and copy the pattern safely. Where a choice trades reliability against
sophistication, take the reliable one and say why.

The reference is also upstream of the teaching material. `CURRICULUM_MAP.md` describes
the two cohort branches as derived from one reference implementation, and
`TARGET_ARCHITECTURE.md` places their regeneration after this rebuild. The rebuild
therefore has a downstream consumer, which is why the sprint mapping in Phase 1 is a
deliverable rather than a courtesy.

## Authoritative inputs

The implementation uses these sources in descending order of authority:

1. The acceptance criteria in the sprint README files on `origin/us-ireland` and
   `origin/india`, as mapped in `docs/CURRICULUM_MAP.md`.
2. The binding contracts under `docs/contracts/`.
3. `TARGET_ARCHITECTURE.md`, `ARCHITECTURE.md` and `DECISIONS.md`.
4. The existing implementation on `reference`.
5. The extension briefs under `extensions/briefs/` where no binding contract exists.

Where these sources disagree, the conflict is recorded in `DECISIONS.md` before the
implementation proceeds.

Where the two cohorts hold the same criterion at different depths, implement the
stricter one. The reference is assessed against the union, so an India reduction never
lowers the bar: the historical trade structures are built rather than only designed,
and a rotated refresh token stops working rather than merely being reissued.

Work that no acceptance criterion requires is out of scope unless it is recorded as a
decision with a stated reason. `TARGET_ARCHITECTURE.md` states the restraint that
governs this rebuild, and it is binding here: "No new framework, abstraction layer,
build tooling, CI system or service mesh enters the platform: the point of this
restructure is that there is less to run, not more."

## Branch policy

Implementation work starts on a short-lived branch from `reference`, provisionally
named `reference-rebuild`. The student branches are read as specifications and are not
merged, because their histories and contents are intentionally independent. They are
not, however, unrelated: the branches are regenerated from the rebuilt reference in a
later pass that this specification does not cover.

That makes regeneration a constraint on this work even though it is out of scope.
The reference is organised by component under `services/`, `analytics/`, `ui/` and
`extensions/`, while the student branches are organised by sprint under
`sprint-NN-slug/`. Record which reference paths supply which sprint folder, and avoid
restructuring that leaves a sprint deliverable with no coherent source.

Each completed phase is committed separately with its tests and evidence. Changes to
`main` are limited to shared programme documentation, and `gh-pages` is updated only
when the architecture diagrams have changed and been reviewed.

## Scope

The completed reference includes:

- the operational Postgres model and migrations;
- the Python analytics pipeline, DuckDB warehouse and dashboard;
- the Java trading domain inside the Trade REST API source tree;
- the Trade REST API and asynchronous order flow;
- Kafka topics, dead-letter behaviour and the Trade Executor;
- the scheduled Java market-data poller inside the Trade Executor;
- the NestJS Auth service;
- the Angular application;
- Customer Preferences;
- Customer Notifications;
- Watchlists and Price Alerts;
- Portfolio and P&L;
- local orchestration, quality checks, demonstration scripts and the static UI
  deployment flow.

The local reference is fully containerised. A clean machine needs Docker with the
Compose plugin and no host installation of Java, Maven, Node.js or Python. One
`docker compose up --build` starts the complete demonstration stack, including the
Angular application and analytics dashboard, and performs repeatable database seed
and Kafka topic initialisation.

The four named extensions are mandatory because the India specification requires all
four. Portfolio and P&L also serves as the completed elective example for the
US/Ireland specification, which asks each team to choose one extension.

Trade Advice and Signals and Automated Strategy Execution remain fully specified
extension briefs but are not part of the first reference release. Implementing every
elective alternative is a separate scope decision; it is not required to demonstrate
the US/Ireland requirement to choose and complete one.

## Delivery order

Phase 1 comes first because every later phase is judged against it. Phases 2 and 3
then run in parallel: the screen designs constrain the Angular work in Phase 6 and
nothing else, while the restructuring in Phase 3 is backend-only and has no dependency
on screen design. Phases 4 to 8 are sequential.

A phase does not close while it has unresolved acceptance issues. An acceptance issue
is a mandatory criterion in `REFERENCE_COMPLIANCE.md` that the phase claimed to
satisfy and does not, or a test that fails from a clean checkout.

## Phase 1: create the compliance matrix and the missing contracts

### Compliance matrix

Create `docs/REFERENCE_COMPLIANCE.md`. It lists every acceptance criterion from both
student branches and maps each criterion to:

- the code or document that satisfies it;
- the automated test that protects it;
- the command or scenario that demonstrates it;
- its current status;
- any cohort-specific difference, and where the cohorts differ in depth, the stricter
  reading the reference implements;
- the sprint folder the criterion belongs to, so that the later regeneration pass has
  the component-to-sprint mapping it needs.

The matrix is maintained with the implementation. A feature is not complete when its
code merges; it is complete when its evidence is recorded in the matrix.

The matrix also carries a row per planted flaw. `docs/PLANTED_STARTER_FLAWS.md`
records nine deliberate defects in the Sprint 7 starter loader on `us-ireland`, and
the reference analytics pipeline is the worked answer to them. Map each flaw to the
reference code and test that resolves it. That file is instructor-only: cite it from
the matrix, and never copy its content into a student branch.

This phase is first because it is the requirement set that Phase 2 designs against
and that the definition of done is measured against. It is also the cheapest way to
find a genuine conflict between the two cohorts before any code depends on it.

### Extension contracts

Portfolio and P&L has a binding contract at `docs/contracts/portfolio-api.yaml`.
Customer Preferences, Customer Notifications, and Watchlists and Price Alerts have
briefs only. Write an OpenAPI contract for each of those three now, and review it
before Phase 5 implements it.

Read the briefs, not the surrounding folder history. `extensions/README.md` described
extensions as separate deployable services with their own ports until it was corrected
alongside this specification; it was missed in the restructure pass that updated the
other documents. The five briefs themselves are consistent with the target
architecture.

The platform is contract-governed everywhere else, and Phase 6 generates its API
clients from contracts. Writing these three after the code would record whatever was
built rather than what was agreed, and would teach the reverse of the pattern the
graduates are asked to follow. Keep them to paths, schemas and error codes. They do
not need the prose depth of `trade-api.yaml`.

## Phase 2: design the screens

Screen design constrains Phase 6. It does not gate Phase 3, 4 or 5, which are backend
work with no dependency on it.

The designs define the user journey before the extension API shapes are fixed. They
must show how the core platform and the four mandatory extensions form one product
rather than a collection of disconnected demos.

### Required screens

1. Sign in.
2. Account dashboard.
3. Order ticket.
4. Order history or blotter.
5. Portfolio summary and priced positions.
6. Profit and loss detail.
7. Customer preferences.
8. Notification inbox and delivery state.
9. Watchlist detail with current prices.
10. Price-alert creation and alert history.

Design these at desktop width. The Angular application stays usable on a narrow
viewport, but no acceptance criterion asks for a mobile design and separate mobile
layouts for ten screens are not worth the time they cost.

### Required states

The state matrix is the part of this phase that carries real weight. The states below
are where an order management UI is normally wrong, and a graduate reading the
reference needs to see them handled:

- loading, empty, populated and failure;
- field validation and readable platform error messages;
- unauthenticated and forbidden behaviour;
- an order remaining at `NEW` while execution is pending;
- stale and partially unavailable prices;
- a notification that identifies the preference-selected channel;
- a triggered, acknowledged and disabled price alert;
- clear currency, timestamp and market-data freshness labels.

Record the matrix once, as a table of screen against state, rather than drawing every
cell.

### Navigation and journey requirements

The designs must demonstrate these journeys:

1. Sign in, land on the preferred account, inspect balances and positions, place an
   order, and follow it from `NEW` to its final state.
2. Change the notification channel, place or execute an order, and see the resulting
   notification use the new channel.
3. Create a watchlist and threshold alert, observe a crossing market quote, and see
   the alert delivered through Customer Notifications.
4. Open Portfolio and P&L, distinguish realised from unrealised profit and loss, and
   understand stale or partial pricing without reading implementation notes.

### Design deliverables

This phase produces:

- a screen inventory;
- a navigation map;
- annotated desktop designs for the ten screens;
- the state matrix described above;
- written review decisions for any behaviour not already fixed by a contract.

Designs are reviewed against usability, accessibility, contract feasibility and the
graduate acceptance criteria. Acceptance of this phase is the gate for Phase 6.

## Phase 3: rebuild the implementation to the target architecture

### Trading domain

Move the Sprint 5 domain source and tests into `services/trade-api`. Remove the
separate `trading-engine` build prerequisite and the locally installed Maven
dependency. The domain remains free of Spring, HTTP and database concerns even
though its source now lives inside the Trade REST API project.

### Market-data poller

Replace the standalone Python poller with a scheduled Java component inside
`services/trade-executor`. Confirm what the running stack does before planning this
work: `docker-compose.yml` already omits `services/market-data-poller` and already
describes the Trade Executor as running the poller, while the Python source is still
on disk. Record the true starting position in `DECISIONS.md`.

Preserve the required behaviour:

- discover held and watched symbols;
- batch no more than 25 symbols per Fauxnance API request;
- enforce quota-aware polling intervals and bounded retries, against the documented
  quota of 2000 requests per day;
- publish one Kafka message per symbol, keyed by symbol;
- preserve quote timestamp and staleness;
- isolate a failed symbol or batch without silently stopping the poller;
- expose health and observable failure information through the executor.

### Portfolio and P&L

Move the existing Portfolio and P&L implementation into a dedicated package inside
the Trade REST API. Reuse the API's authentication, authorisation, error handling and
database configuration rather than carrying duplicate copies. Serve
`docs/contracts/portfolio-api.yaml` on port 8080 and move its schema into the normal
platform migration sequence.

### Residual cleanup

`TARGET_ARCHITECTURE.md` names two further items that complete the rebuild. Remove the
Snowflake wording from the docstrings in `analytics/src/analytics/config.py` and
`analytics/src/analytics/db/warehouse.py`, including the claim that the same DDL runs
unchanged on Snowflake, DuckDB and SQLite. Then delete `services/trading-engine`,
`services/market-data-poller` and `extensions/portfolio-pnl` once they are empty.

Those three directories are removed only after their replacement behaviour and tests
pass.

### Runtime topology

The mature reference is one Docker Compose stack. Its long-running containers are
Postgres, Kafka, the Trade REST API, the Trade Executor, the real Auth service, the
Angular application served by nginx, and the Python analytics dashboard and Kafka
sink. DuckDB is an embedded file owned by the analytics container and persisted on a
named volume; it is not presented as a separate database server.

One-shot initialisation containers create the contracted Kafka topics and apply any
database migrations or seed data that cannot be handled safely by the owning service.
Initialisation is idempotent. `docker compose up --build` from a clean checkout waits
on health checks and starts a usable, seeded demonstration without requiring Java,
Maven, Node.js or Python on the host.

The auth stub is reachable only through an explicit `stub` profile and never starts
alongside the real Auth service by default. The trading domain, Customer Preferences,
Customer Notifications, Watchlists and Price Alerts, and Portfolio and P&L remain
modules inside the Trade REST API rather than gaining containers of their own.

## Phase 4: close the core sprint acceptance criteria

### Database

- Maintain ordered, repeatable migrations and one-command seed data.
- Add the ER diagram and operational data design record.
- Provide executable demonstrations for unique and foreign-key violations.
- Document index justification.
- Build the historical trade-data structures, not only a design record. India reduces
  this to a documented design; US and Ireland require the implementation, and the
  reference takes the stricter reading.

### Analytics

- Preserve separated extract, transform and load steps.
- Demonstrate incremental and idempotent loads.
- Quarantine bad rows and provide source-to-warehouse reconciliation.
- Include NSE or BSE instruments as required by the India specification.
- Retain at least three understandable business claims and their charts.

This pipeline is read as the answer to the Sprint 7 refactoring exercise, so the nine
flaws in `docs/PLANTED_STARTER_FLAWS.md` must each be visibly absent. Five are precise
enough to test directly:

- `trade_value` is quantity multiplied by `executed_price` where the order filled, not
  by the limit price. The starter gets this wrong and a first refactor usually leaves
  it wrong, so it carries a test of its own.
- The warehouse DDL keeps `uq_fact_trades_source`, `uq_dim_instrument_symbol` and all
  three foreign keys, matching `docs/contracts/analytics-schema.sql`.
- The loader holds its own watermark rather than depending on an operator remembering
  a `--since` argument.
- `dim_account` performs real Type 2 change detection, closing off the previous
  version rather than inserting a fresh current row per run.
- The orders query binds its parameters.

### Trade REST API and event backbone

- Preserve all six Trade REST API contract endpoints and the common error envelope.
- Preserve parameterised MyBatis access, transactions and optimistic locking.
- Publish new orders to `orders` and return `NEW` in asynchronous mode.
- Demonstrate that duplicate Kafka delivery cannot debit an account twice.
- Document and create the contracted topics and dead-letter topics.
- Run the batch and Kafka analytics ingestion paths without double loading.

### Authentication

- Preserve the four Auth API endpoints and exact JWT claims contract.
- Demonstrate configuration-only replacement of the auth stub.
- Preserve password hashing and uniform login failure behaviour.
- Rotate refresh tokens so that the previous token stops working. India makes
  revocation optional; the reference takes the stricter US and Ireland reading.
- Serve the OpenAPI document and complete the OWASP authentication review.

## Phase 5: implement the mandatory extension modules

Implement the extensions inside the Trade REST API in dependency order, against the
contracts written in Phase 1.

Every consumer in this phase deduplicates on the `eventId` envelope field, which
`docs/contracts/kafka-topics.md` already defines as the idempotency key for
consumers. Do not invent a second scheme.

### Customer Preferences

Persist one customer's default account, notification channel and display preferences.
Apply the default account at the customer's next UI login. Every account-addressed
route compares the account to the verified JWT claim.

### Customer Notifications

Consume `trade-events` using its own consumer group. Create idempotent notification
records for filled, rejected and cancelled orders and resolve the delivery channel
through Customer Preferences. Duplicate event delivery must not create a second
notification.

Delivery is an outbox table plus the in-app inbox screen. The notification row records
the resolved channel and its delivery state; no email, SMS or push message leaves the
platform. Real outbound delivery would add credentials, an external dependency and a
failure mode that is invisible during a demonstration, and it would not demonstrate
anything the outbox does not. A graduate team that wants real delivery adds an adapter
behind the same table.

### Watchlists and Price Alerts

Persist customer-owned watchlists, instruments, thresholds and trigger history.
Consume `market-data` using a distinct consumer group. A threshold crossing must
call Customer Notifications and must therefore use the channel held by Customer
Preferences; logging an alert alone does not meet the requirement.

### Portfolio and P&L

Complete the integrated Portfolio contract using batched live quotes. Correctly
distinguish cost basis, market value, realised profit and loss and unrealised profit
and loss. Partial or stale prices remain visible and do not block order placement.

Each extension owns its tables and service boundary inside the shared application,
has route-level authorisation, has isolated tests and contributes to one combined
OWASP security review and architecture decision log.

## Phase 6: implement the approved user experience

Build the Angular screens from the accepted Phase 2 designs. Changes to interaction or
navigation discovered during implementation return to the designs for review before
the code diverges from them.

Generate API clients from the binding contracts, including the three extension
contracts written in Phase 1, rather than maintaining handwritten transport models.

Keep the Angular presentation deliberately plain. Use standalone Angular components,
reactive forms and ordinary CSS with a small shared set of cards, tables, badges,
buttons and form controls. Do not add a state-management framework, a second UI
framework, animation system or bespoke design-system abstraction. Related capabilities
may share a screen where that makes the demonstration easier to follow; the required
screen inventory describes capabilities, not a requirement for ten unrelated layouts.

The UI must:

- attach the bearer token only to platform API requests;
- guard authenticated routes;
- validate orders and extension forms before submission;
- render the complete error catalogue in user-facing language;
- handle asynchronous `NEW` orders;
- expose all four mandatory extensions;
- display loading, empty, stale, partial and failure states from the state matrix;
- contain no Fauxnance API key or other secret in its source or built bundle.

## Phase 7: quality and automated verification

Verification is script-driven; this project does not introduce GitHub CI.

The verification suite includes:

- Java unit, application and persistence tests;
- Jest tests for Auth service security and contract behaviour;
- pytest coverage for analytics, malformed data, idempotency and reconciliation;
- a characterisation suite pinning the starter loader's behaviour before its refactor;
- Angular component and service tests;
- integration tests for the four extension flows, including preference-driven channel
  resolution and threshold-crossing alert delivery;
- Playwright journeys for sign-in, order placement and order history;
- OpenAPI contract-parity checks;
- Kafka duplicate replay and dead-letter tests;
- SonarQube scans for the pipeline, executor and integrated Trade REST API;
- a built-bundle secret scan;
- a clean-checkout build test with no prior local Maven installation step.

Playwright covers the three journeys the Sprint 9 criteria name and no more. The
extension flows are verified at the integration layer instead, because an end-to-end
browser test over a Kafka-driven alert pipeline is the least stable test in the suite
and a reference implementation with an intermittently red suite is worse than no
suite for both audiences.

Both cohorts are assessed on writing characterisation tests before refactoring, and it
is a technique graduates get wrong more often than any other in Sprint 7. The
reference therefore carries a worked example rather than only the refactored result.
The suite pins what the starter loader does today, including the wrong `trade_value`
recorded as today's output with a note that it is wrong, and it is committed ahead of
the refactor so that the commit order itself demonstrates the practice.
`docs/PLANTED_STARTER_FLAWS.md` lists what a good suite pins.

All automated tests use a controlled pricing fixture and must pass with no network
access to the Fauxnance API. This makes the checks reproducible; it does not replace
the live demonstration, which is a separate mandatory criterion covered in Phase 8.

## Phase 8: local demonstration and deployment evidence

Add a root README and a reproducible demonstration runbook. From a clean checkout an
instructor runs `docker compose up --build`; the stack creates its topics, applies its
migrations, loads its demo data and starts every UI and service needed for the
principal user journeys. The runbook records the URLs, seeded credentials, health
checks, checks and reset command without requiring the reader to reconstruct commands
from service-specific documents.

The demonstration has two paths and both are first class.

The live path is mandatory evidence for the curriculum. It is opt-in at runtime rather
than the default local mode. The Sprint 10 criteria require a team to demonstrate the
feature working against live data rather than fixtures, and Sprint 7 requires the
Trade Executor to price against a live Fauxnance API quote. A reference that only ever
ran on fixtures would not evidence the criterion it exists to model, so the live path
is tracked in `REFERENCE_COMPLIANCE.md` as a criterion in its own right.

The fixture path exists because the live one can fail for reasons that have nothing to
do with the platform. The Fauxnance API is a hosted external service with a
per-participant key and a quota of 2000 requests per day, so an exhausted quota, an
expired key or a blocked network can take the demonstration down in front of an
audience. The Compose stack and scripted checks therefore default to the recorded
fixture, and the
runbook opens with a pre-flight: call `GET /usage` for the remaining quota and
`GET /health`, which needs no key, to separate a platform fault from an API fault
before anyone is watching. If the pre-flight fails, the fixture path carries the
session and the failure is reported rather than worked around.

The final demonstration covers:

1. authentication and protected routes;
2. order placement and asynchronous execution;
3. duplicate-delivery safety;
4. operational-to-analytical data movement and dashboard claims;
5. preference-driven trade notification;
6. market-data-driven watchlist alert delivery;
7. Portfolio and P&L with stale and partial-price behaviour;
8. the architecture decisions, security findings and quality results.

The existing S3 and CloudFront flow is retained for the Angular build. Deployment
evidence must show HTTPS access, a private S3 origin using origin access control, one
build/upload/invalidation script, scoped IAM and authenticated flow verification.

## Definition of done

The reference implementation is complete when:

- every mandatory criterion in `REFERENCE_COMPLIANCE.md` has implementation, test
  and demonstration evidence;
- the Phase 2 designs were accepted before the Angular work began and the final UI
  remains traceable to them;
- the runtime structure matches `TARGET_ARCHITECTURE.md`;
- `docker compose up --build` starts a healthy, seeded stack from a clean checkout,
  including the Angular UI and analytics, with Docker as the only host prerequisite;
- all four India-mandatory extensions work together end to end;
- Portfolio and P&L supplies the completed US/Ireland elective example;
- all automated checks pass from a clean checkout with no network access to the
  Fauxnance API;
- the scripted demonstration is reproducible on fixture data, and the mandatory
  live-data demonstration passes with its pre-flight;
- the nine planted starter flaws each map to reference code and a test that resolves
  them, and the characterisation suite is committed ahead of the refactor;
- documentation describes the code that actually runs;
- no secrets are present in the repository, history-facing examples or UI bundle.
