# Sprint 6: the Trade REST API

Everything the platform has built so far is unreachable. The schema answers
psql. The rules answer a JUnit test. Neither answers a customer, and no other
service in the platform can reach either of them. This sprint is the front
door: one HTTP service that accepts an order, proves the caller is who they
claim to be, applies the rules you wrote in Sprint 5, writes the result to the
schema you designed in Sprint 3, and answers in a shape the Angular
application can generate a client from.

What the service owns is transport and persistence: turning JSON into a domain
call, turning a domain exception into a documented error code, and holding one
database transaction open around the work that has to succeed or fail
together. It decides nothing about whether a trade is allowed, because that
decision belongs to the domain. It prices nothing, because there is no live
quote this sprint and pricing belongs to the Trade Executor.

It is also the host. The Sprint 5 domain package moves in here this week, as
source, and this service is the only place in the platform that holds it. In
Sprint 10 your extension arrives the same way: further packages inside this
service, with their own routes on the same port and their own Kafka consumers.
Two things follow. The layering you set up this week is the layering those
packages are added to five weeks from now, so a query written in a controller
is not a shortcut you pay for once. And the token verification you write once,
for every route under `/api/v1/`, is what will protect routes nobody has
designed yet.

Keeping the service thin is still not tidiness. The rules that decide whether
an order may be placed are read again by whoever writes the Trade Executor in
Sprint 7, which settles that same order in another process, minutes later,
against a price that did not exist when it was placed. A rule that leaked into
a controller has to be found there and written again, and the two copies
drift. The first drift is a customer whose order this service accepted and the
executor refused.

## What you deliver

| Deliverable | Where it lives |
|---|---|
| The Sprint 5 domain package, moved in as source | `src/main/java/`, under its own package |
| Six endpoints implementing `contracts/trade-api.yaml` | `src/main/java/`, under your base package |
| A layered controller, service and mapper structure | as above, one package per layer |
| MyBatis mappers with parameterised statements | `src/main/resources/mapper/`, or annotations on the mapper interfaces |
| One `@ControllerAdvice` producing the error envelope | as above |
| JWT verification on every `/api/v1/**` route | as above |
| Tests, unit and slice, that run without a container | `src/test/java/` |
| A multi-stage `Dockerfile` | this folder |
| Your service added to the root `docker-compose.yml` | repository root |

The scaffold gives you the Maven build, the package tree, the configuration
skeleton and a deliberately bad Dockerfile to improve on. The
package tree includes an empty package for the domain, at the name the Sprint 5
scaffold declares. Every class is yours to write. There are no stubs to fill
in: deciding what belongs in which layer is most of what this sprint assesses.

## The Sprint 5 package moves in

The domain you built last week is not a dependency of this service. It is part
of it. Copy the sources under `sprint-05-domain-engine/src/main/java` into
`src/main/java` here, keeping the package name, and copy the tests into
`src/test/java` so that they keep running.

Copy rather than move. Sprint 5 is assessed in its own folder against its own
criteria, and that folder is the record of last week's deliverable. From this
week onwards the copy inside this service is the one the platform runs and the
one you change.

There is no artefact and no `mvn install` step, and that is the point of doing
it this way. A separate Maven module means a build here that fails on any
machine where nobody has installed the domain into a local repository, which
is every fresh checkout, every new laptop and every image build. One project,
one `mvn verify`, and the Sprint 5 tests run in this service's suite beside
the ones you write this week.

What does not change is the constraint the module boundary used to enforce.
The domain package holds no Spring annotation beyond Bean Validation, no
servlet type, no MyBatis type and no SQL. It is now a rule about what may
appear inside a package rather than one a build enforces from outside, which
is the form the constraint takes in most real codebases, and it is easier to
break now that the domain and the service compile together: an import that
would have failed the Sprint 5 build resolves here without complaint. Nothing
outside the review catches it, so the package is read for those types.

## The contract is the specification

`contracts/trade-api.yaml` is not documentation of something you build. It is
the thing you build, and it was written before the service existed so that the
Angular application in Sprint 9 can generate a typed client from it without
anyone reading your Java.

Six operations, and the paths, verbs and status codes are fixed.

| Method | Path | Answers |
|---|---|---|
| POST | `/api/v1/orders` | The recorded order |
| DELETE | `/api/v1/orders/{id}` | The cancelled order |
| GET | `/api/v1/accounts/{id}` | Account details, both identifiers and the lock version |
| GET | `/api/v1/accounts/{id}/balance` | Available cash and its currency |
| GET | `/api/v1/accounts/{id}/positions` | Holdings with a net quantity above zero |
| GET | `/api/v1/accounts/{id}/orders` | The order history, newest first |

Two parts of the contract are behaviour rather than decoration, and both are
assessed.

**The error envelope.** Every failure leaves the service as
`{"errorCode": "...", "message": "..."}` and nothing else. Not a Spring
whitelabel page, not a stack trace, not a bare status with an empty body. The
Angular application has one error handler because there is one envelope, and
a route that answers a validation failure in a different shape from a business
failure forces the client to branch on the status code instead.

**Every code in the catalogue.** Seven codes, and the mapping to HTTP status is
in the contract. Clients branch on `errorCode` and never on the status alone,
because 404 and 409 each carry more than one code.

| Code | HTTP | Raised when |
|---|---|---|
| `ACC-404` | 404 | No account exists with that key |
| `ACC-403` | 403 | The account is not `ACTIVE`, or the token does not reach it |
| `INS-404` | 404 | The instrument is unknown or no longer tradable |
| `ORD-400` | 400 | A buy costs more than the available cash |
| `ORD-409` | 409 | Insufficient holdings, a reused idempotency key, or an order that cannot be cancelled |
| `VAL-422` | 422 | The request failed field validation |
| `AUTH-401` | 401 | Missing, malformed, expired or wrongly signed token |

`message` is for a human reading a screen. It never carries a class name, a SQL
fragment, an account key or an internal identifier. Values an investigation
needs are logged on the server, where the customer cannot read them. Leaking
them in a response body is the OWASP finding you covered in Sprint 2.

The response bodies are the schemas in the contract, field for field. Note
that `AccountResponse` is the one place in the platform where `accountId`
means the string business reference rather than the numeric key, and that
`AccountResponse.id` is what every other endpoint calls `accountId`. The
contract explains why. Getting this wrong compiles and passes your own tests,
and breaks the generated client in Sprint 9.

## Layering, stated concretely

Three layers, and each one is allowed to speak exactly one language.

| Layer | Speaks | Must not |
|---|---|---|
| Controller | HTTP, DTOs, status codes, validation annotations | Contain SQL, open a transaction, or hold a business rule |
| Service | The domain package, mappers, one transaction | Take a servlet type, a request object or a status code as a parameter |
| Mapper | SQL, parameterised, and result mapping | Decide anything, or reach back into HTTP |

Two violations fail review on sight.

**SQL in a controller.** A query written in the class that handles the request
cannot be tested without a web layer, cannot be reused by the service that
needs the same rows next sprint, and puts the shape of your schema in the same
file as the shape of your JSON. When the schema moves, the controller changes,
and nothing about the transport changed.

**An HTTP type in the domain.** A domain exception that carries an HTTP
status, an entity annotated for a web framework, or a rule that takes a
request DTO has bound the rules to one caller. Whoever writes the Trade
Executor in Sprint 7 has no HTTP request and needs the same rules to mean the
same thing, and the Sprint 10 extension routes read the same domain from a
second set of controllers in this service.

The first shows up as a mapper, JDBC or MyBatis import in a controller source.
The second shows up as a servlet, Spring or MyBatis type inside the domain
package. Neither is the whole of it: a business rule written in a controller
that touches no mapper leaves no import behind, so the layering is read rather
than searched for.

## MyBatis, and why interpolation is a security finding

Persistence is MyBatis: mapper interfaces in Java, statements in XML under
`src/main/resources/mapper/` or in annotations on the interface. Either style
is acceptable and the scaffold assumes XML, because a long statement is easier
to read and to review outside a Java string.

Every value that comes from outside the service is bound with `#{}`. MyBatis
turns `#{}` into a JDBC bind parameter: the driver sends the statement and the
value separately, the database parses the statement once, and no value the
caller sends can change what the statement does.

`${}` is a string substitution performed before the statement reaches the
driver. A symbol of `AAPL' OR '1'='1` written into a statement with `${}`
becomes part of the statement, and the account whose positions come back is
whichever account the attacker asked for. That is OWASP A03, injection, and in
this service the values arriving from outside include an account key, a
symbol, a status filter and two timestamps.

Any `${}` in a mapper fails criterion 3. There is one legitimate use, a column
name or a sort direction that cannot be a bind parameter, and it is legitimate
only when the value is checked against a fixed list of permitted names before it
reaches the statement. If you need it, put a comment above the statement naming
what constrains the value, and bring the list of every such statement to the
review. Each one is a question you will be asked.

## Optimistic locking on the account version column

Sprint 3 put a version column on the account row and Sprint 5 had the domain
report the version it was loaded at. This is the sprint where it does something.

Two requests arrive for account 3 at the same moment. Account 3 holds 25,000.
The first is a buy costing 20,000, the second a buy costing 20,000.

Without a lock, both requests read the row and both see 25,000. The first
computes 5,000 and writes it. The second, holding the balance it read a
millisecond earlier, computes 5,000 and writes it. Both orders are recorded,
both are filled, 40,000 of stock has been bought, and the account has 5,000
left instead of being 15,000 overdrawn. One of the two updates was lost. There
is no error, no log line and no symptom until somebody reconciles the cash
against the order history, which in a real firm happens the next morning.

Optimistic locking closes it by making the version part of the write rather
than a check before it. The update names the version the row held when it was
read, and increments it. The database serialises the two writes: the first
affects one row, the second affects none, because the version it named is no
longer there. Zero rows affected is not success. The service that gets it must
refuse the order rather than apply a balance computed from data that has since
moved, and the caller sees `ORD-409`.

Two things follow. Read the version with the row, do not fetch it separately.
Return the affected row count from the mapper, because a mapper that returns
`void` has thrown away the only evidence that anything happened.

The same reasoning applies to the order state transition behind
`DELETE /api/v1/orders/{id}`. Reading the status, deciding it is `NEW` and then
updating it races anything else that touches the order. Make the transition
conditional on the state you expect, in one statement, and treat zero rows as
the refusal it is.

## The auth stub

`services/auth-stub` is provided. It is a fixture, not a deliverable: nothing
in it is assessed, nothing in it is to be modified, and it exists because
Sprint 6 has to verify a real token and Node is not taught until Sprint 8.

Start it with the infrastructure:

```bash
docker compose --profile platform up -d --build
```

Obtain a token, then send it:

```bash
curl -s -X POST http://localhost:3001/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo1","password":"Trainee#2026"}'

curl -s http://localhost:8080/api/v1/accounts/1 \
  -H "Authorization: Bearer ${TOKEN}"
```

`services/auth-stub/README.md` lists the five demo users, the claims the token
carries and the shared signing secret. Read it before writing the verifier.

Verification means checking the signature, the expiry and the algorithm the
token asks for, in that order, before reading a single claim. A verifier that
decodes the payload first and checks the signature afterwards has already
trusted whatever the client sent. The signing secret is `JWT_SECRET` from the
environment, shared with whatever issued the token, and it is never a literal
in a properties file.

Four failures are one answer. A missing header, a wrong scheme, an expired
token and a forged signature all produce `AUTH-401` with the same body. A more
specific message tells an attacker which of the four they got wrong, which is
a free oracle and costs you nothing to avoid.

Authentication and authorisation are different questions and belong in
different places. Whether the caller holds a valid token is answered once, for
every route under `/api/v1/`, before any controller runs. Whether that caller
may reach the account in the request is answered where the account key is
known, and the answer is `ACC-403` with the same message a suspended account
gets, so that nobody can enumerate account keys by reading which of the two
came back.

Sprint 8 replaces the stub with the real service. The claims, the algorithm and
the secret are identical by design, so the swap is a configuration change and
no code in this service is expected to change. If yours needs a code change,
something in it is coupled to the stub rather than to the token, and that is
worth finding now rather than in week 9.

## The Dockerfile and the compose entry

The service has to run as a container built from a multi-stage Dockerfile in
this folder.

`Dockerfile.example` is the naive single-stage version. It works, and it is
wrong in the ways the criterion is about: the image it produces carries Maven,
a full JDK, the whole dependency cache and your source code, it runs as root,
and it rebuilds every dependency whenever one line of code changes. Read the
comments in it, then write `Dockerfile` properly. It is assessed, so the
improvement is yours rather than the scaffold's.

What a correct one does:

- Builds in one stage on an image that has Maven and a JDK 21, and runs from a
  separate final stage on a runtime image that has neither.
- Copies the built jar out of the build stage rather than building again.
- Runs as a user that is not root.
- Orders the copies so that a change to a source file does not invalidate the
  layer holding the resolved dependencies.
- Exposes the service port and answers a health check.

One constraint has gone this year, and it is worth knowing that it was there.
When the domain was a separate artefact, the image build could not reach the
local Maven repository on your laptop, so the build context had to be the
repository root and the build stage had to compile two projects before it
could package one. The domain is source in this project now. The context is
this folder, and the build stage runs one `mvn package`.

Adding the service to `docker-compose.yml` is your change, in your own copy of
the repository. A correct entry:

| Needs | Because |
|---|---|
| A `build` block with the context and the Dockerfile path | The image is built from source, not pulled |
| `profiles: [platform]` | It starts with `--profile platform`, alongside the auth stub, and not with the bare infrastructure |
| `networks: [trading-net]` | It resolves `postgres` and `auth-stub` by service name |
| A published port for the service port | `curl` from the host reaches it |
| Database host, port, name, user and password from the environment | The compose service name is `postgres`, not `localhost`, and `localhost` inside a container is the container |
| `JWT_SECRET` passed through from `.env` | It has to be the same secret the stub signed with |
| `depends_on` Postgres, on its health condition | Starting before the database is ready is a crash loop, not a failure |
| A health check | `docker compose ps` should tell you the service is up, not merely running |

Nothing in this sprint needs Kafka. The broker starts with the infrastructure
and this service ignores it until Sprint 7.

## The toolchain

Java 21 and Maven 3.9 or later, Spring Boot, MyBatis, the Postgres JDBC driver
and Docker.

```bash
cd sprint-06-trade-api
mvn clean verify                             # build and test
mvn spring-boot:run                          # run against the compose stack
```

One project and one build. Nothing has to be installed anywhere first, and
nothing outside this folder has to be built before it, which is what the
domain being source here buys you.

The package tree ships as empty packages, each with a `package-info.java`
stating what belongs in it, including the one the domain lands in. Rename or
reorganise them if your design says something else.

`src/main/resources/application.yml` is a skeleton of the sections the service
needs, with comments and without values. Every value that differs between a
laptop and a container is read from an environment variable with a default
that works under Docker Compose. The connection details are in
`infra/README.md`. No secret is committed, including the development ones: a
signing secret that appears in a properties file is a signing secret in the
history of the repository forever.

## Acceptance criteria

These are the criteria your instructor assesses against.

1. All six endpoints are implemented and match the contract, including the
   error envelope and every code in the catalogue.
2. Layering is enforced: no SQL in a controller, no HTTP type in the domain.
3. MyBatis mappers use parameterised statements throughout.
4. `@ControllerAdvice` maps every domain exception to its documented code and
   status.
5. Order placement is `@Transactional`.
6. Optimistic locking is applied on the account version column.
7. A protected route rejects a missing or invalid token with `AUTH-401`.
8. The service builds and runs from a multi-stage Dockerfile.

## Evaluation

This sprint contributes 18 marks to the 100-mark Capstone assessment. The
package tree, the `application.yml` skeleton and `Dockerfile.example` carry no
marks unchanged, and a service that builds but does nothing earns none either.
Your instructor reads the code and exercises the running service against the
criteria above.

| Criterion | Marks |
|---|---:|
| Six endpoints, response bodies, error envelope and catalogue compliance | 4 |
| Controller, service and mapper separation with central exception mapping | 3 |
| Parameterised MyBatis persistence, transactions and concurrency control | 4 |
| JWT verification, account authorisation and safe failure responses | 3 |
| Unit, slice and live contract evidence | 3 |
| Multi-stage container build and Compose integration | 1 |
| **Total** | **18** |

## The review

Your instructor assesses this sprint by reading the code against the criteria
above and by exercising the running service. Structure is the easy half. A
mapper can bind every parameter and still run the wrong statement, and an
annotation can be present with the transaction boundary in the wrong place.

Read rather than searched for:

- whether the transaction boundary encloses the work that has to be atomic,
  and nothing more
- whether every domain exception reaches the advice and leaves as its
  documented code, rather than most of them
- whether the layering holds in the places a search cannot see, including a
  business rule written in a service that should have called the domain
- whether the optimistic lock is applied to every write to the account row
- whether the response bodies match the contract field for field, including
  the two meanings of `accountId`
- whether the image would survive being deployed, including what it runs as

Bring to the review: the running stack with the auth stub beside it, one order
traced from the request to the committed row, each of the seven error codes in
the catalogue produced on demand in the envelope, a missing token and an invalid
token on a protected route, several concurrent orders against one account with
the cash reconciled against the order history afterwards, your Dockerfile, and
your answer to what happens when two customers spend the same money at the same
moment.
