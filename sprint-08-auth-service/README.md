# Sprint 8: the auth service

Five services in this platform need to know who is calling and which account
that caller may act on. None of them should hold a password to find out. A
password that lives in the Trade REST API is a password that leaks when the
Trade REST API has an injection defect, and a hashing routine copied into the
Trade Executor is a hashing routine that gets upgraded in one of the two
places. This sprint builds the one component that ever sees a credential, and
gives every other component a signed statement of identity it can check on its
own.

That last part is why authentication is a service rather than a library. A
library means each service links its own copy of the verification code, and the
copies drift. A service means one process owns registration, login, hashing and
the token lifecycle, and every other process verifies a signature with no
network call and no shared database. When the hashing parameters change, one
service is redeployed. When a refresh token is stolen, one service revokes it.
When the auditor asks who can read a password hash, the answer is one name.

The stub in `services/auth-stub` has been standing in for that service since
Sprint 6. It has no database, no registration, no hashing and no refresh. This
sprint retires it.

## What you deliver

| Deliverable | Where it lives |
|---|---|
| Four endpoints implementing `contracts/auth-api.yaml` | `src/`, under the module tree you design |
| A credential store with hashed passwords | your migration or bootstrap, plus the repository that reads it |
| Access token issuance carrying the claims contract | `src/tokens/`, or wherever your design puts it |
| Refresh token issuance, storage and rotation | as above |
| A guard protecting `/auth/me` | `src/auth/`, or wherever your design puts it |
| Jest suites, including the guard paths named below | alongside the code, as `*.spec.ts` |
| A multi-stage `Dockerfile` | this folder, written by you |
| Your service in the root `docker-compose.yml`, with the stub removed | repository root |
| The OWASP review, filled in | `security-review/` |

The scaffold gives you the Node build, the TypeScript configuration, the
dependency set and the module directories. Every class, provider,
guard, DTO and test is yours to write. There are no stubs to fill in.

## The contract is the specification

`contracts/auth-api.yaml` was written before either implementation existed, and
it binds both of them. Four operations, and the paths, verbs, status codes and
bodies are fixed.

| Method | Path | Protected | Success | Documented failures |
|---|---|---|---|---|
| POST | `/auth/register` | no | 201 `UserResponse` | `AUTH-409`, `VAL-422` |
| POST | `/auth/login` | no | 200 `TokenResponse` | `AUTH-401`, `VAL-422` |
| POST | `/auth/refresh` | no | 200 `TokenResponse` | `AUTH-401`, `VAL-422` |
| GET | `/auth/me` | bearer token | 200 `UserResponse` | `AUTH-401` |

Two consequences of reading the contract properly.

Registration issues no tokens. An unauthenticated route that mints a session is
an authentication bypass as soon as it has its first defect, so the client logs
in afterwards. Registration also does not create a trading account: accounts
are owned by the Sprint 3 schema, and a registration naming an account that
does not exist fails validation.

The error envelope is the platform envelope, `{"errorCode": ..., "message":
...}` and nothing else, so that the Angular application in Sprint 9 keeps one
error handler for the whole platform. `AUTH-409` extends the catalogue and is
scoped to this service, because registration is not a trading operation and
`trade-api.yaml` has no code for it.

## The claim set, exactly

The token payload is not a place to put things that might be useful later. Every
claim in it is a field a consumer can start depending on, and every consumer
that depends on one is a service that breaks when you remove it.

| Claim | Type | Meaning |
|---|---|---|
| `sub` | string | The user identifier, a UUID. Stable for the life of the user, and not the username, because a username can change |
| `accountId` | integer | The numeric trading account key, `ACCOUNTS.id`. The Trade REST API compares it against the account in the request and answers `ACC-403` when they differ |
| `roles` | array of string | `CUSTOMER` or `ADMIN`. Always present, never empty |
| `iat` | integer | Issued at, seconds since the Unix epoch |
| `exp` | integer | Expiry, seconds since the Unix epoch. Fifteen minutes after `iat` |

Those five are assessed. The contract defines one more, `iss`, carrying
`auth-service` here and `auth-stub` in the fixture, so that during the cutover
a team can decode a token and see which implementation signed it. Consumers must
not require a particular value for it.

Anything beyond those six is a finding, not a bonus. An email address in the
payload is an email address published to every holder of the token, because the
payload is base64 and not encryption: paste one into any decoder and read it.
A `passwordChangedAt` claim is a fact about a credential handed to whoever
intercepts the request. A `permissions` array duplicating `roles` is a second
source of truth that will disagree with the first. Any claim outside the set
above is a finding, because removing a claim after Sprint 9 has generated a
client from it is not a configuration change.

Signing is HS256 with the secret in `JWT_SECRET`, the same value the Trade REST
API verifies with. RS256 with a published public key is a documented upgrade
rather than a requirement, and it buys the property that the Trade REST API can
verify without holding the power to sign.

## Password storage

Store passwords with argon2id, or with bcrypt at cost 12 or above. Never MD5,
never SHA-256, never an unsalted digest of any kind. A general-purpose hash is
built to be fast, and fast is the one property a password hash must not have:
a modern GPU runs SHA-256 in the billions per second, so a stolen table of
SHA-256 digests is a stolen table of passwords by the weekend.

The cost factor is a decision you make and defend, not a default you inherit.
Argon2id is parameterised by memory, iterations and parallelism; bcrypt by a
cost exponent. Pick values that make one verification take on the order of a
tenth of a second on the hardware you deploy to, then write down what you chose
and why. Too low and an offline attacker gets the same speedup you did. Too
high and your login route becomes the cheapest denial-of-service target in the
platform, because every request ties up a worker for a second.

Never log a password. State that as a discipline rather than an intention,
because the ways a password reaches a log are all indirect: an error object
serialised whole, a request body dumped by a debug interceptor, a DTO printed
in a stack trace, a `console.log` left in during a bad afternoon. Two habits
make it structural rather than hopeful. Log through one logger that redacts by
key name at any depth, so a nested object cannot smuggle a field past you. Never
pass a whole request body to a log call, and pass the fields you actually want
instead. Searching your sources for a log call that names a credential field
catches the direct case and none of the indirect ones, and the indirect ones are
what the review asks about.

## Refresh rotation

An access token cannot be withdrawn. It is verified by signature alone, so no
service asks you whether it is still good, and fifteen minutes is the size of
that compromise. The refresh token is the opposite: opaque, stored, revocable,
and the reason a user is not asked for a password every fifteen minutes.

Rotate it on every refresh. The token presented is consumed and stops working
at that instant, and a new pair goes back in the response. What rotates is the
refresh token itself, not merely the access token that comes with it, and the
old value must be dead in your store before the response is written.

The scenario rotation defends against is replay. Suppose a refresh token is
stolen, from a log, from browser storage, or from a proxy that recorded a
request body. Without rotation the thief holds a seven-day credential and uses
it quietly, and the real user notices nothing because their own token still
works. With rotation, exactly one of the two can use it. The other presents a
token that has already been consumed, and that presentation is the alarm: it
means either a client repeated a request or somebody stole a token, and the
service cannot tell which. Treat it as theft. Revoke every live refresh token
for that user and return `AUTH-401`. The stolen session dies, the real user logs
in again, and you have a timestamped record of when the two diverged.

Two implementation points follow. Store a hash of the refresh token rather than
the token, so that read access to your database is not session takeover. Make
the consumption conditional in the statement that performs it, in the way
Sprint 6 made the account update conditional on the version, because reading a
row, deciding it is unused and then updating it races the second presentation
you are trying to catch.

## One answer for every failure

An unknown username and a wrong password get the same status, the same body and
comparable timing. This is the requirement most often failed by accident, and
it fails in three distinct ways.

The body. `AUTH-401` with the message `Unauthorised`, for an unknown user, a
wrong password, an expired token, a wrongly signed token, a consumed refresh
token and a malformed header. A helpful message tells an attacker which half of
the credential pair was wrong, which turns a login form into a free directory
of your customers.

The status. 401 for all of them. A 404 for an unknown user and a 401 for a bad
password is the same disclosure written in the status line.

The timing. This is the one that survives a correct body. If the unknown-user
path returns as soon as the lookup misses, it answers in a millisecond, while
the wrong-password path spends a tenth of a second verifying a hash. An attacker
with a username list and a stopwatch reads your customer base off the response
times without ever guessing a password.

The fix is to make the two paths do the same work. Where the username is not
found, verify the supplied password against a fixed dummy hash of the same
algorithm and the same parameters, discard the result and return the same
failure. This is where argon2 or bcrypt help you rather than cost you: because
the verification is deliberately expensive, it dominates everything else in the
request, so two paths that both perform one verification land within noise of
each other. The same trick with SHA-256 leaves both paths so fast that the
database lookup is the measurable difference.

Be ready to demonstrate it. Run both paths repeatedly in front of your
instructor and compare the elapsed times. Judge the shape rather than the size:
a generous absolute threshold is fair, because a laptop under load, a container
that has just been scheduled and a cold connection pool all move a response by
tens of milliseconds, but one path taking twice as long as the other is an early
return even when both numbers are small. Comparable timing is not proof of
constant time. A consistent gap is proof of an early return.

Throttling the login route collides with that demonstration, because a burst of
failed logins from one address is what a throttle refuses before either path
does any work. Build the throttle anyway, and know its cooldown window so that
the timing comparison can be run outside it. Throttling is not a substitute for
the uniform failure: it limits how fast an attacker can use an oracle you left
open, rather than closing it.

## Replacing the stub

The acceptance statement is that the Trade REST API needs no code change. Not
that it needs a small one, and not that only a configuration class changes: no
Java changes. The same holds for the Angular application in Sprint 9. That is
achievable because both implementations sign HS256 with the same `JWT_SECRET`
and issue the same claims, so a token from either verifies with the code that
was written in Sprint 6 against the fixture.

What actually changes:

| Change | Where |
|---|---|
| The compose service that answers on the auth port becomes yours, and the `auth-stub` service is removed | root `docker-compose.yml` |
| Your service reads the same `JWT_SECRET` the Trade REST API verifies with | root `.env`, passed through compose |
| The Trade REST API's issuer setting, if it pins one, names your issuer instead of the stub's | that service's configuration, from the environment |
| The database connection for the credential store | your service's environment |

Nothing in that table is a Java file. If your Trade REST API needs a code change
to accept a token from this service, something in it is coupled to the fixture
rather than to the token, and the coupling is worth finding now. The usual
culprits are a hard-coded issuer string, a claim read with a name the stub
happened to use, and a verifier that decodes the payload before checking the
signature and therefore never noticed which key signed it.

Write the parity check the stub's README asks for. It signs with both
implementations and cross-verifies: a stub token verifies here, a token from
here verifies in the stub, and the claim names, types, algorithm and lifetime
match. A test of that shape fails on the day the two drift, which is cheaper
than finding out during the cutover.

One thing to decide deliberately. The stub's development secret is published in
its own README, which means anyone who has read this repository can mint a token
that your service's consumers will accept, for as long as that secret is the one
in use. Keeping it is a legitimate choice for a training stack and it is the
configuration the contract describes. Rotating it once the stub is gone is the
better habit. Whichever you choose, record it in your security review as a
decision with its reason, rather than leaving it as something nobody discussed.

## Tests

Jest, with the Nest testing utilities, running without a database and without an
HTTP server. The suite is a deliverable and not an afterthought: this is the
service where a defect is a breach rather than a bug.

The guard is assessed specifically, and two paths through it are named.

| Path | What the test proves |
|---|---|
| An expired token | A token that was valid, signed by you, with an `exp` in the past, is refused. A guard that checks the signature and forgets the clock accepts every token it ever issued, forever |
| A wrong signature | A well-formed token whose signature does not match the key is refused before any claim is read. This is the test that catches a verifier that decoded first and verified afterwards |

Write them, and make them fail for the right reason. A test that builds an
"expired" token by corrupting the payload passes against a guard that has no
expiry check at all, because the signature check catches it first. Build the
expired case by signing a genuine token with a past `exp`, and the wrong
signature case by signing a genuine, unexpired token with a different key.

Name both tests for what they assert, so that a reader finds them without
opening the guard. Which spec file they live in is your design's business: a
guard that hands the token to a token service, and tests the two cases where the
verifying actually happens, is a defensible shape. Beyond the guard, expect to be
asked at the review for tests covering the
identical failure for an unknown user and a wrong password, rotation and replay,
and the fact that a plaintext password never reaches your repository.

## OpenAPI, served by the running service

The running service publishes its own OpenAPI document. A YAML file maintained
by hand beside the code drifts from the code within a fortnight, and the
document that matters is the one describing what is deployed, so generate it
from the decorators on your controller and DTOs and serve it from the process.

Two paths: the human page, `/docs`, and the JSON document, `/docs/json`. Serve
them elsewhere if your design says so, and say where at the review. What is
assessed is that the JSON is a valid OpenAPI document served by the running
process and that it describes all four routes. The generated document is not a
replacement for `contracts/auth-api.yaml`, which remains the source of truth
binding both implementations. It is the evidence that your code still matches
it.

## The security review

The deliverable is a committed file, not a conversation at the review. Copy
`security-review/TEMPLATE.md` to a file of your own in the same folder, and fill
it in as you build rather than the night before.

The categories in the template are the OWASP Top Ten items that bear on an
authentication service. A01 broken access control, because `/auth/me` must read
identity from the verified token and never from a parameter the client controls.
A02 cryptographic failures, because the hashing algorithm, the cost factors, the
signing algorithm and the secret length all sit here. A03 injection, because
every statement this service runs touches a credential table. A04 insecure
design, because rotation, throttling and the uniform failure are design choices
rather than defects. A05 security misconfiguration, because a secret with a
default value and a permissive CORS list are both configuration. A06 vulnerable
and outdated components, because the dependency set is yours to keep current.
A07 identification and authentication failures, which is the whole service. A09
security logging and monitoring failures, because a login route that logs
nothing usable leaves you unable to answer when the incident arrives.

Documented means each category carries a finding and a disposition, both
written. A finding of "none" is allowed and requires a sentence of justification
naming what you checked, because "none" with nothing beside it is
indistinguishable from a category nobody looked at. A disposition of "accepted"
is also allowed, and requires the same: say what the residual risk is and why
the team is carrying it. Every category carries both cells, and a finding of
none carries its sentence. Whether the sentence is true is read by your
instructor.

## The toolchain

Node 20 or later, TypeScript, NestJS, Jest, and Postgres from the compose stack.

```bash
cd sprint-08-auth-service
npm install                  # first run, and whenever you add a dependency
npm run build                # tsc through the Nest CLI
npm test                     # the Jest suite
npm run start:dev            # run against the compose stack
```

Commit `package-lock.json`. A build that resolves a different dependency tree on
a teammate's laptop is not the build you tested, and `npm ci` exists to install
exactly what the lock file names.

### The scaffold

```
package.json          the dependency set and the Jest configuration
tsconfig.json         strict TypeScript, decorators enabled
tsconfig.build.json   the build view, with tests excluded
nest-cli.json         the Nest CLI build configuration
.env.example          the variables this service reads, with no secret in it
src/                  one directory per module, each with a README saying what belongs in it
test/                 for suites that do not sit beside a source file
security-review/      the OWASP review template
```

`src/` ships as empty directories. Each carries a README stating the single
responsibility of that module and the dependency direction it has to respect.
Reorganise them if your design says something else.

`.env.example` lists every variable the service reads. `JWT_SECRET` ships empty
on purpose: it is read from the environment, it is shared with the Trade REST
API, and a signing secret written into a committed file is a signing secret in
the history of the repository forever. Copy the file to `.env`, which is
git-ignored, and take the value from the repository root `.env`.

### There is no Dockerfile here

Deliberately. You wrote a multi-stage Dockerfile for a Spring Boot service in
Sprint 6, and writing the equivalent for a Node service is the exercise. The
shape is the same: build in a stage that has the toolchain, run in a stage that
does not, copy the artefact across, run as a user that is not root, expose the
port and answer a health check.

Two differences from Sprint 6 are worth planning for. Your production stage
needs `node_modules` as well as the compiled JavaScript, so install production
dependencies deliberately rather than copying a development tree across. And if
you chose argon2, it is a native module: the build stage needs a compiler, the
runtime stage must not have one, and the compiled binding has to be built
against the same Node version and platform the runtime stage uses.

## Acceptance criteria

These are the criteria your instructor assesses against.

1. All four endpoints are implemented and match the contract, including the
   error envelope and every code in it.
2. The access token carries exactly the claims contract: `sub`, `accountId`,
   `roles`, `iat`, `exp`, and the `iss` the contract also defines.
3. Swapping the stub for this service is a configuration change only, with no
   code change in the Trade REST API.
4. Passwords are hashed with argon2 or bcrypt, and never logged.
5. Refresh tokens rotate, and the token that was presented stops working.
6. A failed login returns the same response, and comparable timing, for an
   unknown user as for a wrong password.
7. Jest tests cover the guard, including the expired-token and wrong-signature
   paths.
8. The running service serves its OpenAPI document.
9. The security review against the auth-related OWASP items is committed, with
   a finding and a disposition for every category.

## Evaluation

This sprint contributes 13 marks to the 100-mark Capstone assessment. The Node
build files, the empty module directories and `security-review/TEMPLATE.md`
carry no marks unchanged. Your instructor reads the security properties, the
integration and the behaviour you implement and demonstrate against the
criteria above.

| Criterion | Marks |
|---|---:|
| Four contract-compliant endpoints and the served OpenAPI document | 2 |
| Password hashing, credential handling and uniform login failure | 3 |
| Access-token claims, refresh rotation and replay response | 3 |
| Guard behaviour and replacement of the auth stub without Java changes | 2 |
| Jest evidence, OWASP review, container build and Compose integration | 3 |
| **Total** | **13** |

## The review

Your instructor assesses this sprint by reading the code against the criteria
above and by exercising the running service. A green suite and a complete
template are the floor, and neither can see intent.

Read or demonstrated, never counted:

- whether a password can reach a log by an indirect route: an error object
  serialised whole, a request body passed to a log call, a stack trace
- whether the cost factors were chosen, and what they were chosen against
- whether the replay of a consumed refresh token revokes the whole chain, or
  merely refuses the one token
- whether the uniform failure holds because both paths do the same work, or
  because the machine happened to be quiet
- whether the security review is a reading of your service or a reading of the
  template
- whether the guard runs before every route that needs it, including the one
  added last

Bring to the review: the running stack with the stub removed, all four
endpoints exercised against the contract, one token decoded in front of the
panel claim by claim, a wrong password and an unknown user compared on status,
body and elapsed time, your refresh rotation traced through your store with the
consumed token refused afterwards, the stored password hash, the OpenAPI
document fetched from the running process, a protected Trade REST API route
answering a token from this service and refusing one signed with a key it should
not trust, the `git diff` showing no Java changed, and your answer to what you
would do at 09:00 on the morning somebody reports a stolen refresh token.
