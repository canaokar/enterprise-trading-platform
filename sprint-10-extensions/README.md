# Sprint 10: extensions

For seven sprints the work has been specified for you. A contract said what the
Trade REST API returned, `kafka-topics.md` said what the envelope looked like, a
brief said which eight business rules the domain engine enforced, and the
acceptance criteria said when you were finished. That was deliberate: a platform
built by four teams to four different designs cannot be assessed against itself,
and the fastest way to teach a convention is to hand it over and make people
build to it.

This week nothing is handed over. You choose a feature, decide what it is worth
building in five days, design its API, agree its integration surface, build it,
secure it, and demonstrate it against a running platform. The technology is
technology you already have. What is new is that the decisions are yours, and
that the way you took them is part of what is assessed.

That is why the folder is thin. There is no scaffold in here, because there is
nothing to scaffold until you have chosen. What is here is the catalogue and the
shape of the two documents you have to produce.

## The extension is not a new service

It is a set of packages and routes inside the Trade REST API you built in
Sprint 6. Its routes answer on 8080, beside `/api/v1/orders`. Its consumers run
in that process. It has no Dockerfile, no compose entry, no port of its own and
no second copy of token verification.

The reason is arithmetic about your week. A sixth container costs a Dockerfile,
a port allocation, a compose entry, a set of environment variables and a second
JWT verifier, and none of that is the feature. A team that starts there
demonstrates something on Friday morning if at all. A team writing a package
inside a service that already boots, already verifies tokens and already holds a
database connection starts on the feature on Monday afternoon.

The integration lesson a separate service was supposed to teach is already
taught. Five services and a broker speak to each other across the platform you
have built, the JWT crosses every one of those boundaries, and Sprint 7 made you
configure both ends of a topic. Nothing is lost by not doing it a sixth time.

What gets harder is authorisation, and that is the trade you are being asked to
make. In a separate service you could lean on the boundary: whatever reached
you came through your own verification. Inside a shared service, a route that
returns another customer's data is a defect in the same application that holds
the order book. Every route you add enforces its own authorisation. The security
review this week has more to find, not less.

## What changes this week

No new technology is taught. Every tool this sprint needs, you have used: Java
and Spring Boot for the code, Kafka for the events, Postgres for the state,
Angular for the screen, SonarQube for the quality gate, JUnit for the tests.

You run the sprint. Plan it, split it, track it, review each other's pull
requests, and hold whatever ceremonies your team has settled into. Instructors
are available all week and will not be assigning work.

Process is assessed alongside product. A team that ships a working feature with
no backlog, no decision log and a security review written on the Thursday
evening scores below a team that ships something narrower and can show how it
was decided. The two documents in this folder are not paperwork attached to the
build; they are half of the deliverable.

## Day one

Three things happen before any code is written, and they happen on the Monday.

**Choose the extension.** One from the catalogue below. Six briefs, one file
each, and they are written to be picked between rather than ranked. Read all six
before arguing about any of them. Every one of them is written as a set of
routes and packages inside the Trade REST API, whatever the brief calls it.

**Confirm the scope with an instructor.** Bring what you intend to build by
Friday, what you have decided not to build, and the API you propose to expose.
For five of the six extensions the API design is yours, and this is the review it
gets. For Portfolio and P&L the contract is already written and the conversation
is about everything around it. Scope confirmed on day one is an acceptance
criterion, not a courtesy.

**Write the backlog before you write code.** Stories with acceptance criteria, in
whatever tracker your team has been using. A backlog assembled on Friday morning
from the commits is visible as one, and it is worth less to you than to anybody
marking it: the point of writing it first is that it tells you on Wednesday
whether the scope you agreed is still the scope you are building.

## The catalogue

| Extension | Identifier | Brief | Integrates through |
|---|---|---|---|
| Portfolio and P&L | `portfolio-pnl` | [catalogue/portfolio-pnl.md](catalogue/portfolio-pnl.md) | Postgres, Fauxnance quotes, optionally `trade-events` and `market-data` |
| Trade advice and signals | `trade-advice-signals` | [catalogue/trade-advice-signals.md](catalogue/trade-advice-signals.md) | `market-data`, Fauxnance candles, optionally `trade-events` |
| Watchlists and price alerts | `watchlists-price-alerts` | [catalogue/watchlists-price-alerts.md](catalogue/watchlists-price-alerts.md) | `market-data`, and a delivery route to the customer |
| Customer notifications | `customer-notifications` | [catalogue/customer-notifications.md](catalogue/customer-notifications.md) | `trade-events`, and an outbound channel |
| Customer preferences and personalisation | `customer-preferences` | [catalogue/customer-preferences.md](catalogue/customer-preferences.md) | The Angular application, and the platform's own data |
| Automated strategy execution | `automated-strategy-execution` | [catalogue/automated-strategy-execution.md](catalogue/automated-strategy-execution.md) | `market-data`, `trade-events`, and `POST /api/v1/orders` |

The identifier is the name to give the package your module lives in, inside the
Trade REST API. Use it unchanged, so that the brief and the code agree.

One extension is the deliverable. The assessment is depth, integration quality
and the security review for that one module, so a narrow extension built
properly is worth more than a wide one built thinly. Two half-built extensions
are worth less than either of them finished.

## What every extension has to do

The feature is your choice. Five properties are not, and they are the same five
whichever brief you pick.

**It is a module, and the boundary is yours to hold.** One package under the
service's base package, named for the extension, with its own layers inside it:
its own controllers, its own service classes, its own mappers, its own tables.
Nothing outside that package imports anything inside it. Your module reads the
trading tables and calls the domain, and it does not reach into the order
placement path to do it, because the day it does, a change to how orders are
recorded breaks a portfolio screen.

A compiler enforces none of this now. That is the point of assessing it: in a
separate service the boundary was a network hop nobody could get past by
accident, and here it is a decision you make every time you write an import.

**Every route enforces its own authorisation.** The Trade REST API already
verifies the signature, the expiry and the algorithm on every route under
`/api/v1/`, so a route you add under that prefix is authenticated the moment it
exists, and you write no second verifier. What is not decided for you is whether
this caller may reach this resource. Compare the `accountId` claim against the
account in the path, on every route you add, and refuse a mismatch with
`ACC-403`. A route that returns another customer's data to a valid token is the
finding this sprint's security review exists to catch, and it is now a finding
inside the service that holds the order book.

Mapping a route out of the verified prefix, to make a demonstration easier,
publishes it. If a route has to be public, say so in the decision log and bring
the reasoning to the review.

**It integrates with the platform, and it is reachable from the Angular UI.**
Consuming a topic, producing to one, or reading and writing the trading data
through the layers this service already has all count. A module that only talks
to its own tables has not been integrated into the platform. Reachable from the
UI means a screen in the Sprint 9 application that a customer can use,
generating its client from your OpenAPI document the way the other clients are
generated. A route that answers only to `curl` does not meet the criterion.

**It does not regress Sprint 6.** The six contract endpoints answer exactly as
they did on Friday of week 6, the service's own tests are still green, and the
image still builds and starts. You are adding to a service other people's work
depends on: the Angular application calls it, the Trade Executor reads what it
wrote, and the analytics extract reads the same tables. A module that breaks
order placement has cost more than it added.

**It runs on live data at the demonstration.** Real quotes from the Fauxnance
API, real messages from the topics your poller and executor are producing, real
rows from your Postgres. Not fixtures, not a seeded response, not a recorded
payload replayed from a file. Fixtures belong in the test suite, and a
demonstration that runs on them is demonstrating the fixture.

Two platform rules carry over unchanged. The Fauxnance key is read from the
environment and never reaches the browser. Every consumer sets an explicit
`group.id`, named for the module and written down where your team keeps
operational detail, and does not share it with another consumer. A group id names a logical consumer rather than a
process, and separate ids are what keep your module's offsets independent of the
rest of the service.

## The decision log

Committed in `decision-log/`, one file per decision, using the shape in
[decision-log/TEMPLATE.md](decision-log/TEMPLATE.md). It is an acceptance
criterion for this sprint and it is read at the final showcase in Sprint 11.

Write entries as you take the decisions. A log assembled in the last hour of the
sprint records what you built, which everyone can already see, and loses the
thing that makes it worth reading: what you nearly did instead, and why you did
not. It also reads exactly like what it is.

An entry is worth writing when reversing the choice later would cost more than an
afternoon, when a competent engineer would have chosen the other option, or when
somebody on the team asked why and the answer took a paragraph. Four to six
entries is a normal week. Twenty is a changelog and one is not a log.

### A worked entry

Neutral subject, so that the shape is visible without the content doing the work
for you.

````markdown
# 0003 One consumer group for the module, sized to the partition count

| Field | Value |
|---|---|
| Status | accepted |
| Date | 2026-11-17 |
| Decided by | the whole team, at the Tuesday stand-up |

## Context

Our module consumes `market-data`, which `contracts/kafka-topics.md` fixes at
six partitions because it carries the highest message rate on the platform. We
intend to run more than one instance of the Trade REST API in Docker Compose so
that we can show what happens when one is killed. Kafka assigns partitions to
consumers within a group, so how we set `group.id` decides whether a second
instance shares the work or duplicates it.

## Options considered

| Option | For | Against |
|---|---|---|
| One group for the module, one consumer per instance | Partitions are split across instances, so work is shared and a lost instance is rebalanced onto the others | Only useful up to six instances, since a consumer beyond the partition count is idle |
| A group per instance | Every instance sees every message, which is simple to reason about | Every instance does the same work, and every alert would be evaluated and delivered as many times as we have instances |
| One consumer, no scaling | Nothing to configure | A single point of failure, and no way to demonstrate a rebalance |

## Decision

One group, `watchlist-service`, with each instance running one consumer, and no
more than six instances. The second option is not a scaling design at all: with
this module the duplicate work is a duplicate customer notification, which is a
defect a customer sees rather than wasted CPU.

## Consequences

Scaling past six instances buys nothing, and we have written that in the module
README next to the compose entry for the Trade REST API. A rebalance pauses
consumption briefly when an instance joins or leaves, so the alert evaluation has
to be idempotent on `eventId` anyway, which we were going to need for
at-least-once delivery. The group identifier is now part of our operational
surface: another consumer adopting the same name would silently take half our
messages, which is why it is listed in the README.
````

What makes that entry useful is not its length. It states what was true when the
decision was taken, gives an option that was genuinely considered and rejected,
names the thing that decided it, and admits a cost. An entry with one option in
it is a record of what you did.

## The security review

An OWASP review of what you added, committed in this folder, using the shape of
the template from Sprint 8 at
`../sprint-08-auth-service/security-review/TEMPLATE.md`. Copy it into
`security-review/` in this folder and retitle it for your extension.

The subject of the review is the module and the routes it adds, not the whole of
the Trade REST API. Where your module changes something the service already did,
say so: a filter you altered, a route you exempted, a table you granted access
to. Those are the rows that matter this week, because they are the ones where a
new feature reaches into an application that was already holding a customer's
money.

Two things change from Sprint 8. The categories are the ones that bear on your
extension rather than on an authentication service, and the set is the full Top
Ten, because an extension that consumes events, calls a third party and serves a
customer touches more of the list than the Auth service did. A category that
genuinely does not apply is dispositioned as out of scope with the reason, not
deleted: a category with nothing in it is the one worth asking about.

The second change is that findings have to be addressed. The criterion is not a
review that exists, it is a review whose findings were dealt with. Fixed, with
the commit. Mitigated, with what limits the exposure. Accepted, with the residual
risk stated and named as a decision the team took. A finding still open on Friday
belongs in the outstanding items table with an owner against it, and it will be
asked about.

Start with the access-control row. Every brief in the catalogue names the same
first risk, because every one of these extensions holds data belonging to one
customer and reachable with a token belonging to another. Broken access control
is A01 for a reason, and this year your route sits in the same application as
the order book rather than behind a boundary of its own.

## The quality gate

SonarQube passing on the Trade REST API with your module in it, on the same
terms as Sprint 7. Run it during the week rather than on Friday: a gate run
once, at the end, against a week of code produces a list nobody has time to act
on, which is how a quality gate turns into a formality.

The gate now reads a codebase somebody else on your team wrote most of. Bring
the new-code result, not only the overall one: a gate that was green in week 6
and is red now is red because of what you added this week.

Bring the gate result to the review, with the analysis date and the project key,
and be ready to talk about anything you marked as won't fix.

## What is in this folder

```
README.md              this brief
catalogue/             six briefs, one per extension
decision-log/          TEMPLATE.md, and your entries beside it
security-review/       your OWASP review of the extension
```

Your code does not live here. It lives in the Trade REST API, under
`sprint-06-trade-api/src/main/java`, in a package named for the extension. There
is nothing to add to `docker-compose.yml`: the service it goes into is already
there. This folder holds the sprint's documents.

## Acceptance criteria

These are the criteria your instructor assesses against.

1. The extension is chosen and its scope is confirmed with an instructor on day
   one.
2. It is built as a module inside the Trade REST API, in its own package, with
   its own routes and its own tables.
3. Every route it adds enforces authorisation on the account it addresses, on
   the token the service already verifies.
4. It is integrated with the platform through Kafka or the trading data, and it
   is reachable from the Angular application.
5. Nothing built in Sprint 6 regressed: the six contract endpoints answer as
   they did and the service's tests are green.
6. An OWASP security review of the extension is completed and its findings are
   addressed.
7. The SonarQube quality gate passes.
8. An architecture decision log is committed, giving the reasoning for each
   significant choice.
9. The team can demonstrate the feature working against live data, not fixtures.

## Evaluation

This sprint contributes 8 marks to the 100-mark Capstone assessment. Every
extension in the catalogue is eligible. The same rubric applies whichever
extension is selected, and selecting more than one does not increase the
8-mark maximum. The catalogue briefs and `decision-log/TEMPLATE.md` carry no
marks unchanged.

| Criterion | Marks |
|---|---:|
| Confirmed scope, backlog and architecture decisions | 1 |
| Functional depth of the selected extension | 2 |
| Module boundary inside the Trade REST API, JWT authorisation, Angular route and live data | 2 |
| Security review and closure of its findings | 1 |
| Tests, SonarQube gate and demonstrated behaviour | 2 |
| **Total** | **8** |

## The review

Every criterion this week is read or demonstrated. There is nothing countable to
hide behind, and that is deliberate: five of the six extensions have no contract
to be checked against, because the feature is your team's design.

Read or demonstrated: whether the scope
you agreed on Monday is the scope you delivered, whether the module boundary
holds or your code reached into the order placement path, whether the decision
log records decisions or events, whether the security review is a reading of
your extension or of the template, whether the findings were addressed or
restated, whether the authorisation check still refuses a second customer's
token, whether the screen in the Angular application is usable, and whether the
data at the demonstration was live.

Every member of the team is expected to walk the extension unaided at the
showcase, including the parts they did not write, and to say where its boundary
with the rest of the service runs.

Bring to the review: the Trade REST API running with your module in it beside the
Auth service and whatever your extension consumes, one of your new routes
answering a real token and refusing both a missing one and one signed with a key
nobody holds, a Sprint 6 contract route answering as it did in week 6, the
decision log, the security review with its findings and their dispositions, and
the SonarQube gate on your screen.
