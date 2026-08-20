# Sprint 7: the event backbone

Until this week, placing an order is one HTTP request. The service validates
it, fills it, writes it and answers. That works only because nothing real is
happening. Execution against a market takes time, fails part way, and has to
survive the process that requested it being restarted mid-flight. It also has
more than one interested party: the account has to be updated, the customer
told, the analytics estate loaded, and any strategy service informed.

Both problems have the same answer. The service that accepts the order records
it and publishes it. Something else executes it and publishes the result.
Everybody else subscribes. Your Sprint 6 service stops needing to know who
cares.

That answer has a price, and the price is the subject of this sprint. A
message bus that never loses a message will sometimes deliver one twice. Kafka
guarantees at-least-once, and the platform is built on it deliberately, because
the alternative is a broker that occasionally loses a trade. So the executor
will be handed the same order twice. Once during a rebalance, once after a
crash between the database commit and the offset commit, once when somebody
replays a topic to debug something. If handling that order twice debits an
account twice, the customer is out of pocket and nothing in the system reports
it. Nobody finds out until the cash is reconciled against the order history,
which in a real firm happens the following morning.

Every design decision in this sprint follows from that sentence. The
deliverable is not a consumer that works. It is a consumer that is correct when
the message arrives twice, and a team that can prove it on demand.

## What you deliver

| Deliverable | Where it lives |
|---|---|
| The three topics and their three dead-letter topics, created with the names, partition counts and retention the contract fixes | the broker; the commands go in `scripts/create-topics.sh` |
| The written justification of the partition counts and the key choices | `design/kafka.md`, which you create |
| A small change to your Sprint 6 service: publish to `orders`, answer `NEW` | `sprint-06-trade-api/` |
| The Trade Executor: consume, price, fill or reject, settle, publish | `executor/` |
| The market-data poller, scheduled inside the executor: batched quotes onto `market-data` | `executor/`, in its own package |
| The batch pipeline loading `FACT_TRADES`, with dead-letter handling | `etl-starter/`, refactored |
| Characterisation tests around the starter, committed before you change it | `etl-starter/tests/` |
| A SonarQube gate passing on the executor and the pipeline | your local SonarQube |

The scaffolds give you the Maven build, the executor's package tree, the
pipeline's project layout, and one loader that already works.
`scripts/create-topics.sh` is an empty file at a named path. Every class in the
executor, the poller's included, is yours to write.

## The three topics

`contracts/kafka-topics.md` is binding. It fixes the names, the keys, the
partition counts, the envelope and the payloads, because Sprint 10 extensions
consume these topics and some of them are written by another team.

| Topic | Carries | Key | Partitions | Retention |
|---|---|---|---|---|
| `orders` | Accepted orders awaiting execution. A work queue with exactly one consumer group | `accountId` as a string | 3 | 7 days |
| `trade-events` | Lifecycle outcomes: filled, rejected, cancelled. The platform's event log | `accountId` as a string | 3 | 30 days |
| `market-data` | Quotes polled from the Fauxnance API | `symbol` | 6 | 1 day |

Two of those columns are decisions rather than settings, and you are asked
about both at the review.

**The key decides the partition, and the partition decides the ordering.**
Kafka orders messages within a partition and promises nothing across
partitions. `orders` and `trade-events` are keyed by account because the
ordering that matters is per account: two orders on one account have to be
executed in the order they were accepted, or a sell is processed before the buy
that made it possible. `market-data` is keyed by symbol for the same reason at
instrument grain. Keying by order identifier puts every message on its own
partition and throws the guarantee away.

**Partitions can be increased and never decreased**, and increasing them
rehashes the keys, so an account's history splits across partitions from that
point onwards. Three on `orders` lets three executor instances share the work
and shows that a consumer group cannot usefully exceed the partition count. Six
on `market-data` reflects its higher rate.

Serialisation is JSON. Every message carries the same five-field envelope plus
a payload, on all three topics, so that one deserialiser and one dead-letter
handler cover the platform. Consumers ignore fields they do not recognise:
adding an optional field is not a breaking change, and a consumer that fails on
an unknown field turns an additive change into an outage.

### Creating them

The broker starts empty. Nothing in `docker-compose.yml` creates a topic, and
nothing above the broker process is provided. Running a single-node broker
teaches configuration rather than architecture, so the container is given to
you. Everything above that line is the deliverable: the topics, the partition
counts and keys with the reasoning behind them, and the producer and consumer
settings in the three services that use them.

Create the topics first. Every other piece of work this sprint produces to or
consumes from them, and a topic that does not exist is the first thing your
Sprint 6 service will fail on.

Auto-creation is switched off on the broker, in
`KAFKA_AUTO_CREATE_TOPICS_ENABLE`, and it stays off. An auto-created topic
arrives with one partition and the default retention, which is wrong for all
three of these, and it arrives silently on first use. With auto-creation off, a
producer writing to a topic nobody created gets an error. An error is something
you can act on. A platform that is quietly wrong is not.

A creation call carries six things, and each has exactly one source:

| What the call carries | Where the value comes from |
|---|---|
| The bootstrap address | `localhost:9092` from your machine, `kafka:29092` from inside the compose network |
| The topic name | The contract. A renamed topic breaks every consumer in the platform, including ones another team wrote |
| The partition count | The contract's table, and the justification you write for it |
| The replication factor | 1 locally, because there is one broker. A factor above the broker count is rejected |
| The retention | The contract, expressed in milliseconds. None of 7 days, 30 days or 1 day is the broker default |
| The cleanup policy | `delete` on all three. These are event streams, not keyed state to be compacted |

The local operation section of `contracts/kafka-topics.md` shows the flags those
map to. `kafka-topics.sh` ships inside the broker image, so the commands run in
that container rather than on your machine:

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --list
```

Then the three dead-letter topics. The contract names the pattern `<topic>.DLT`
and says nothing about their shape, because a dead-letter topic carries a small
fraction of its source's volume. Their partition count and retention are your
decision, and you are asked for the reasoning.

Confirm the result rather than assuming it. `--describe` prints the partition
count, the replication factor and every configuration you overrode:

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 --describe --topic market-data
```

One partition where the contract says six is the signature of a topic that a
producer created before anybody configured it. Partitions can never be
decreased, so the repair is to delete the topic and create it again. That is
cheap this week and expensive once a consumer group holds offsets on it.

`scripts/create-topics.sh` is an empty file at a named path. Put the commands in
it. Nothing forces you to. What is assessed is that the topics exist in the
contracted shape and that you can say how they got there, so a team that typed
the commands by hand and recorded them meets the criterion on the same terms.
The reason to write the script anyway is that
`docker compose down -v` removes the broker's volume and every topic on it, and
you will run that more than once before Friday.

### The justification

Commit `design/kafka.md`. It covers why `orders` and `trade-events` carry three
partitions and `market-data` six, why each topic is keyed the way it is, what
you chose for the dead-letter topics, and what breaks under the alternatives you
rejected.

The contract already states the reasoning, so repeating it back is not the
deliverable. Applying it to your own platform is: how many executor instances
you can usefully run at three partitions, what happens to per-account ordering
if somebody raises the count in Sprint 10, and which of your consumers would
notice. A team that cannot answer those has three numbers it copied.

## The change to your Sprint 6 service

Small, contained, and in your own code. Three things move.

The order is recorded and not filled. `POST /api/v1/orders` writes the order at
`NEW` and answers `NEW`. It no longer computes a fill, because there is no
price in that request and pricing is the executor's job.

After the transaction commits, publish an `ORDER_PLACED` message to `orders`,
keyed by the account. After, not inside. Publishing inside the transaction
risks an event for an order that then rolled back, and nothing can undo that.
Publishing after risks an order that committed and was never published, and
that is recoverable by replaying from the order table. Choose the recoverable
failure.

Nothing else changes. The validation, the layering, the error catalogue, the
optimistic lock and the token verification all stay as they are. The contract
already documents both behaviours, because the Angular application in Sprint 9
has to handle an order sitting at `NEW`.

Two consequences are worth expecting. Your Sprint 6 live checks that asserted a
terminal status now see `NEW`, which is correct. And your service acquires a
Kafka producer, which means producer configuration: `acks=all`,
`enable.idempotence=true`, a high retry count, and no more than five requests
in flight per connection. An idempotent producer removes the duplicates a
producer retry causes. It does not remove the duplicates an application retry
causes, which is why the executor still has work to do.

## The Trade Executor

This is the centre of the sprint. There is no broker simulator in this platform
and there will not be one: you build the execution venue, and it is the only
component that decides whether an order fills.

What it does with one order:

1. Consumes an `ORDER_PLACED` message from `orders`, in the consumer group
   `trade-executor`.
2. Loads the order from Postgres. A status other than `NEW` means a previous
   delivery already settled it.
3. Checks the instrument is still tradable, then fetches a quote from
   `GET /quotes/{symbol}`.
4. Applies the fill rules to the quote and the order's limit price.
5. Settles in one transaction: the order's status, the account's cash, and the
   position.
6. Publishes `ORDER_FILLED` or `ORDER_REJECTED` to `trade-events`, keyed by the
   account.
7. Acknowledges the offset.

Steps 5, 6 and 7 are in that order for a reason. Publishing before the commit
risks an event for a transaction that rolled back. Acknowledging before
publishing risks an order that settled in Postgres and told nobody.

### The fill rule

The rule is a design decision, constrained by the business rules you
implemented in Sprint 5. A workable default, and the one to start from:

> Fill the whole order at the current quoted price when a BUY's limit price is
> at or above the quote, or a SELL's limit price is at or below it. Reject
> otherwise.

Partial fills are out of scope, because the order status enumeration has no
state to represent one. There is also no working state between `NEW` and a
terminal status, so an unmarketable order is rejected rather than rested.

Four details decide whether that rule survives contact with real prices, and
each is yours to settle and defend.

| Question | Why it matters |
|---|---|
| What price is stored | The quote carries more decimal places than the column holds. Round before the comparison, or an order can fill at a price that failed its own check |
| Which rules are re-checked here | Rules 6 and 7 were checked at acceptance against a limit price and an older balance. Both have moved while the order sat on the topic |
| What a suspended account does | An account suspended after the order was accepted should not trade, including on orders accepted before the suspension |
| What happens when there is no price | Fauxnance can be down or out of quota. Leaving the order at `NEW` for ever is worse than rejecting it: the customer sees an order that never resolves and the blotter cannot explain it |

Write the rule as a function of an order and a quote, returning a decision. It
touches no database and no socket, which is the only reason its interesting
cases will actually get tested.

### One transaction, three writes

The status change, the cash movement and the position write are one
transaction. If any of the three fails, none of them happened. An order marked
filled beside cash that did not move leaves the audit trail disagreeing with
the balance, and nothing in the platform reconciles the two for you.

Two guards sit inside that transaction and they answer different questions.

The **guarded state transition** answers "has this order already been
executed". It is the first write in the transaction, not a read before it:

```sql
UPDATE orders SET status = ?, executed_price = ?, executed_on = ?
 WHERE id = ? AND status = 'NEW'
```

Zero rows affected means another delivery got there first. The transaction
returns having changed nothing and published nothing. A read, then a decision,
then a write can be run twice by two deliveries; a write conditioned on the
state it expects cannot, because the database serialises the two updates.

The **optimistic lock** answers "has anybody else moved this account's cash".
It is the same mechanism you built in Sprint 6, on the same version column, and
it is needed here because the Trade REST API is still writing to the account
row and the Sprint 10 portfolio service will be. Zero rows affected is not a
failure: re-read and try again, up to a bounded number of attempts, and treat
only an exhausted budget as an error.

### The demonstration you have to be able to give

The acceptance criterion is that replaying a duplicate message does not
double-debit an account, and that the team can demonstrate it. On demand, in
front of an assessor, at any point in the review.

Read one message off `orders` and produce it back:

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server kafka:29092 --topic orders \
  --from-beginning --max-messages 1 \
  --property print.key=true --property key.separator=$'\t' > order.txt

docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server kafka:29092 --topic orders \
  --property parse.key=true --property key.separator=$'\t' < order.txt
```

Then show three things: the balance before, the balance after, and the log line
where the executor recognised the duplicate and did nothing. Show also that no
second message appeared on `trade-events`, because a consumer that believes the
order happened twice is the same bug one service further downstream.

### Failure handling

Two classes of failure, handled differently, and telling them apart is the
assessed part.

| Class | Examples | Handling |
|---|---|---|
| Will never succeed | Malformed JSON, a missing `orderId`, an order identifier that is not in Postgres, an unexpected `eventType` | Dead-letter it on the first attempt |
| Will succeed later | The broker briefly unreachable, a lost database connection, an exhausted optimistic-lock budget | Retry with a backoff that grows, dead-letter once the budget is spent |

Do not retry a poison message indefinitely. One bad message blocking a
partition stops every account keyed to that partition.

A Fauxnance outage belongs in neither row. It is retried inside the quote
client, and if the budget is spent the order is rejected with a reason that
says so. A price feed being down is a business outcome, not a message-processing
failure, and dead-lettering the order would leave it at `NEW` for ever.

### Schema additions

The executor writes three columns your Sprint 3 schema may not have yet:
the price a fill happened at, when it happened, and why an order was rejected.
Add them as a migration, in the same folder and the same style as your Sprint 3
migrations. The analytical model needs the executed price too, so this is not a
change you can defer.

## The market-data poller

The curriculum promises a real-time price stream. Fauxnance does not have one:
it serves end-of-day candles and delayed quotes over HTTP, with no WebSocket
and no server-sent events. The poller is what manufactures the stream, and its
existence is the reason the Sprint 10 extensions that read prices have anything
to consume.

It calls `GET /quotes?symbols=A,B,C` on an interval and publishes one message
per symbol to `market-data`. One message per symbol, never one per batch:
batching the HTTP call is a quota optimisation and it is correct, but batching
the Kafka message puts several symbols behind one key and destroys the
per-symbol ordering the contract promises.

### Where it lives

Inside the Trade Executor, as a scheduled component in Java, in its own package
under the executor's base package. Not a service of its own, not Python, and not
a second container.

The reason is the key. The executor already calls Fauxnance to price every fill.
A separate poller means a second process holding the same credential, spending
the same 2000 requests with no idea what the other one has spent, and an
argument about which of the two owns the retry policy. One component calls
Fauxnance, so one component holds the key and one component divides the budget.

What follows from the placement is worth stating, because it is where teams go
wrong. The poller runs on its own schedule and is not on the order path. It does
not start a poll because an order arrived, and the consumer does not wait for a
poll to finish. They share a quote client and nothing else. Sharing a process is
not sharing a lifecycle: a scheduled method that throws is not necessarily
rescheduled, and a poller that quietly stopped in a running container is harder
to notice than one whose container exited.

The executor scaffold ships the package with a `package-info.java` stating what
belongs in it. Scheduling has to be switched on for it, and Fauxnance has to be
asked for the batch endpoint rather than one symbol at a time.

### The quota arithmetic

The batch endpoint takes at most 25 symbols and costs one request whatever the
symbol count. The quota is 2000 requests per day per key, resetting at 00:00
UTC, and the poller shares it with every fill the executor prices.

| Interval | Requests in 24 hours | How long 2000 requests last |
|---|---|---|
| 15s | 5760 | 8 hours 20 minutes |
| 30s | 2880 | 16 hours 40 minutes |
| 60s | 1440 | A full day, with 560 to spare |
| 120s | 720 | A full day, with 1280 to spare |

Three conclusions follow, and the arithmetic is the assessed part rather than
the code.

Batch, or lose the day before lunch. Eight symbols fetched one at a time every
30 seconds is 23040 requests, and the key is gone in a little over two hours.
The same data batched is 2880.

Nothing at a 30 second interval survives being left running overnight. Thirty
seconds is right for a taught day and costs about 960 requests over eight
hours, which leaves the rest for pricing fills. Stop the executor at the end of
the session, or run at 60 seconds.

The key is shared inside one process now, which makes the arithmetic easier to
get right and no less important. A poller that spends the whole allowance leaves
the fill path with nothing, and the first symptom is orders rejected because no
price could be obtained. Give the poller a budget that is its share rather than
the whole quota, and give the two callers one place that counts what has been
spent.

The key is read from `FAUXNANCE_API_KEY` and appears nowhere in the repository,
in this folder or any other. A key that reaches a commit has to be revoked, and
the history keeps it whether or not you revoke it.

Poll only the symbols you hold or watch. Enforce a floor on the interval in the
code rather than documenting one and hoping. Check `GET /usage` before assuming
the API is broken, and `GET /health`, which needs no key, before assuming
anything at all.

## The batch pipeline

`contracts/analytics-schema.sql` is the model the pipeline loads: a star with
`FACT_TRADES` at the centre and three dimensions around it. The grain is one
order, in whatever status it reached. Rejected and cancelled orders are loaded
rather than filtered out, because fill rate is one of the analytics the model
has to answer and it cannot be computed from fills alone.

Four properties are assessed.

**Load order.** Dimensions before facts, or a fact row references a key that
does not exist yet. `dim_date` first, covering the whole range, then
`dim_instrument`, then `dim_account`, then `fact_trades`.

**Incremental, not full.** A watermark on the order's creation timestamp, so
that a scheduled run reads what is new rather than the whole table.

**Idempotent.** Re-running yesterday's load must not double-count. Merge on the
natural key rather than inserting: `source_order_id` is unique per order, and
the unique constraint on it in the contract is what makes that enforceable in
the store as well as in the pipeline. This is the same property the executor
needs, arrived at from the other direction.

**Dead-lettered, not dropped.** Every check named in the contract's load and
data quality section runs before a row reaches the fact table: referential
integrity into all three dimensions, positive quantity and price, a valid side
and status, and a `trade_value` recomputed rather than trusted. A row that
fails goes somewhere with the reason it failed and the batch it came from.
Dropping it silently and dead-lettering it produce the same fact table, and only
one of them can be investigated on Monday morning.

Do not insert a placeholder dimension row to make an unresolved key pass. That
hides the fault, which is almost always that the dimension load was skipped.

The contract also asks for a reconciliation after the load: the row count and
the summed `trade_value` in the fact table for a day have to equal the same
figures computed against Postgres for that day. A pipeline nobody reconciles is
a pipeline nobody can trust.

## The starter you are given

`etl-starter/` holds a working batch loader. It reads accounts, instruments and
orders out of Postgres and writes the star schema into a DuckDB file. Run it
against the seeded stack and it produces a warehouse the Sprint 4 dashboard can
read. `etl-starter/README.md` says how.

It is also flawed by design. Somebody wrote it under pressure, it went into
service, and it has been running ever since. The flaws are structural rather
than cosmetic, they are the kind that a passing test suite would not have
caught because there is no test suite, and the list of them is not published.
It is not in this repository and you will not be given it. Finding them is the
exercise.

That shapes the deliverable, and the order is not negotiable.

**First, characterisation tests.** A characterisation test does not assert what
the loader should do. It records what it does now, including the parts you
disagree with, so that a change which alters behaviour by accident fails
loudly instead of quietly. You cannot write one after the change, because a
test written against refactored code records the behaviour of the refactored
code, which is the one thing it cannot then be used to check.

Start where the behaviour is observable. What warehouse does a known set of
source rows produce. What happens to a row that cannot be placed. What does a
second run do to a warehouse that already holds the first.
`etl-starter/fixtures/source-rows.json` is one snapshot of the three reads, so
a test can put rows through the loader without a Postgres container.

**Then refactor.** Separate what does not belong together, make the load
idempotent, give bad rows somewhere to go, and keep the tests green while you
do it. When you decide a behaviour was wrong and you are changing it
deliberately, change the test in the same commit and say so in the message.
That is a different act from the tests silently going green again.

### The rule on ordering, exactly

The first commit that adds a test file under `etl-starter/tests/` has to be an
ancestor of the first commit after the scaffold that touches
`etl-starter/src/`.

Tests and a change to the loader in the same commit do not satisfy it. Neither
does a history where the loader was tidied first and pinned afterwards. Your
instructor reads `git log` for those two commits, so make them easy to find.

Commit in small pieces. A history of one commit per week cannot show this and
cannot show anything else either.

## SonarQube

The gate has to pass on the executor and on the pipeline. Run it locally rather
than reading about it.

```bash
docker run -d --name sonarqube-<yourteam> -p 9000:9000 sonarqube:community
```

Give the container a name that is yours. Several of these run on one machine
during the sprint and a second `docker run --name sonarqube` fails against the
first team's container rather than starting yours.

Open `http://localhost:9000`, sign in as `admin` with the password `admin`,
change it when asked, create a project and generate a token. The token is a
credential: export it, never commit it.

Java, from `executor/`:

```bash
export SONAR_TOKEN=the-token-you-generated

mvn -B verify org.sonarsource.scanner.maven:sonar-maven-plugin:sonar \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.projectKey=trade-executor \
  -Dsonar.token="${SONAR_TOKEN}"
```

Python, from the project folder, using the scanner image so that nothing has to
be installed:

```bash
docker run --rm -v "${PWD}:/usr/src" \
  -e SONAR_HOST_URL=http://host.docker.internal:9000 \
  -e SONAR_TOKEN="${SONAR_TOKEN}" \
  sonarsource/sonar-scanner-cli \
  -Dsonar.projectKey=analytics-pipeline \
  -Dsonar.sources=src -Dsonar.tests=tests
```

On Linux, `host.docker.internal` does not resolve. Add `--network host` and use
`http://localhost:9000`.

The expectation is the default Sonar way gate, passing: no new blocker or
critical issue, no new security hotspot left unreviewed, and duplication and
coverage on new code inside the gate's thresholds. Passing by marking findings
as "won't fix" is visible in the dashboard and is not passing.

Nothing runs SonarQube for you. The gate is checked at the review, on your
screen, on the project you scanned.

## The toolchain

Java 21 and Maven 3.9 or later, Python 3.12 or later, Docker, and the stack
from `docker-compose.yml`.

```bash
docker compose --profile platform up -d --build   # infrastructure and the stub

sprint-07-event-backbone/scripts/create-topics.sh # the topics, once you have
                                                  # written the commands

cd sprint-07-event-backbone/executor
mvn clean verify                                  # build and test the executor

cd ..
python3 -m venv .venv
.venv/bin/python -m pip install -e 'etl-starter[dev]'
.venv/bin/python -m pytest etl-starter
```

That install has to work from an empty environment on a teammate's machine, not
only on the laptop the code was written on.

Add the executor to `docker-compose.yml` under the `platform` profile, as you
did with the Trade REST API in Sprint 6. It needs `KAFKA_BOOTSTRAP_SERVERS`
pointing at `kafka:29092`, `FAUXNANCE_API_KEY` and `POLL_INTERVAL_SECONDS`
passed through from `.env`, the database variables, and a `depends_on` for
Postgres on its health condition. `localhost` inside a container is the
container. There is no separate poller service to add, and nothing in the
compose file creates a topic: they are on the broker because you put them
there.

The executor's package tree ships as empty packages, each with a
`package-info.java` stating what belongs in it, including the one the poller
goes in. Rename or reorganise them if your design says something else.

## Acceptance criteria

These are the criteria your instructor assesses against.

1. The three topics and their dead-letter topics exist, created by the team,
   with the contracted names, keys, partition counts and retention, and the
   partition and key choices are justified in writing.
2. The Trade REST API publishes to `orders` and returns `NEW`.
3. The Trade Executor consumes, prices against a live Fauxnance quote, applies
   fill or reject rules, updates order, cash and position in one transaction,
   and publishes to `trade-events`.
4. Replaying a duplicate message does not double-debit an account, and the team
   can demonstrate that.
5. The poller runs on a schedule inside the executor, batches up to 25 symbols
   per call and stays inside the daily quota.
6. Batch ETL loads `FACT_TRADES` with dead-letter handling for bad rows.
7. SonarQube gate passing on the pipeline and the executor.
8. Characterisation tests written before any refactoring of the starter code.

## Evaluation

This sprint contributes 10 marks to the 100-mark Capstone assessment. The
executor scaffold, the empty `scripts/create-topics.sh` and the supplied
`etl-starter/` carry no marks unchanged. Your instructor reads the
implementation, the correction of the starter, the integration and the evidence
you add against the criteria above.

| Criterion | Marks |
|---|---:|
| Topic configuration and the Trade REST API publishing change | 2 |
| Trade Executor pricing, settlement transaction and event publication | 2 |
| Duplicate safety, retries and dead-letter handling | 2 |
| Quota-aware market-data polling and the incremental analytical load | 2 |
| Characterisation history, tests, SonarQube gate and live demonstration | 2 |
| **Total** | **10** |

## The review

Your instructor assesses this sprint by reading the code against the criteria
above and by watching the platform run. A green suite proves less here than
anywhere else in the programme. A duplicate that moved no money once says
nothing about whether the mechanism holds under load, and a row that was
dead-lettered says nothing about whether the reason recorded with it is usable
on Monday morning.

Read or demonstrated, never counted:

- the partition counts and the key choices, and whether the team can defend
  them against the alternatives rather than recite the contract
- how the topics came to exist, and why they are shaped the way they are
- the fill rule, and what it does at the boundaries: an equal price, a stale
  quote, a market that is closed
- whether the transaction encloses the three writes and nothing more
- whether the retry and dead-letter split genuinely distinguishes a poison
  message from a transient failure
- the quota arithmetic, the cap of 25 symbols per call, and whether your
  interval and symbol list agree with it
- the SonarQube gate, on your screen, on the project you scanned
- whether the characterisation tests pin behaviour worth pinning, and whether
  the refactoring left the loader better than it found it

Bring to the review: the running stack, `--describe` output for the topics you
created and `design/kafka.md` beside it, one order traced from the HTTP request
through the topic to the committed rows and the published event, the duplicate
replay performed live, a quote arriving on `market-data` inside one polling
interval, a bad row landing in the dead-letter path rather than in
`FACT_TRADES`, a second pipeline run over the same data that adds nothing, your
fill rule and the reasoning behind it, the quota arithmetic for your
configuration, the SonarQube dashboard, and the `git log` showing the tests
arriving before the refactoring.
