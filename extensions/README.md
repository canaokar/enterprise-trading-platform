# Extensions

Sprint 10 of the Enterprise Trading Platform. By this point a team has the trading
domain, the Trade REST API, Kafka, the Trade Executor with its market-data poller, and
the Auth service in place. Extensions are what a team builds on top of that platform to
demonstrate depth: a capability that consumes the events the core platform already
produces, or reads the data it already holds, and turns that into a feature a customer
would recognise.

An extension is a module inside the Trade REST API, not a separate deployable service.
It owns its own tables and its own service boundary inside the shared application, and
it reuses the API's authentication, error handling and database configuration rather
than carrying duplicate copies. Its security boundary is the route: every new route
enforces its own authorisation against the verified token, and a route that answers a
valid token with another customer's data is a finding rather than a feature.

This changed in the restructure recorded in `docs/TARGET_ARCHITECTURE.md`. Extensions
were previously specified as separate services with their own ports. They are not, and
the reason is that a Sprint 10 team has one week: a new deployable costs them a
Dockerfile, a port, a JWT verification path and a compose entry before it delivers any
feature, and none of that is what the sprint assesses.

## The six extensions

| Extension | Consumes | Owns |
|---|---|---|
| Portfolio and P&L | `trade-events`, `market-data`, Fauxnance API quotes, the shared Postgres schema, read-only | Realised profit-and-loss ledger |
| Watchlists and Price Alerts | `market-data` | Watchlists, alert thresholds |
| Customer Notifications | `trade-events` | Notification history and delivery state |
| Customer Preferences | nothing from Kafka | Channel and contact preferences |
| Trade Advice and Signals | `trade-events`, `market-data`, Fauxnance API candles | Generated signals |
| Automated Strategy Execution | `trade-events`, `market-data` | Strategy configuration and its own order placement |

Design briefs for the five not built out in full are under `extensions/briefs/`, one
file per extension. Portfolio and P&L is the one worked implementation in this
repository, built against `docs/contracts/portfolio-api.yaml`. It currently sits at
`extensions/portfolio-pnl/` and moves into a package of the Trade REST API in the
reference rebuild described by `docs/REFERENCE_IMPLEMENTATION_SPEC.md`.

## Policy by cohort

**US and Ireland (12 weeks).** One extension is mandatory. The team chooses which.
Assessment is on depth, integration quality and the security review for that one
extension, so a narrow, well-built extension outscores a wide, thin one.

**India (9 weeks).** All six are recommended. Four are mandatory:

- Portfolio and P&L
- Watchlists and Price Alerts
- Customer Preferences
- Customer Notifications

These four form one coherent customer-facing feature set: a customer sets a
preference, receives a notification through the channel they chose, and watches a
price move trigger an alert delivered the same way. Portfolio and P&L stands apart
from that set and has no dependency on the other three.

## Dependency warning

Two of the four India-mandatory extensions depend on a third:

- **Customer Notifications depends on Customer Preferences.** A notification cannot
  be routed without a channel to route it to. Build Customer Preferences first.
- **Watchlists alerting depends on Customer Notifications.** A triggered price
  threshold is not an alert until it has been delivered somewhere. Build Customer
  Notifications before wiring up watchlist alerts, or build both in step and stub the
  half not yet ready.

The build order that respects both dependencies is: Customer Preferences, then
Customer Notifications, then Watchlists and Price Alerts, with Portfolio and P&L
built in parallel at any point, since nothing else depends on it and it depends on
nothing else in the extension set.

A watchlist that writes a triggered alert only to a log has not met the acceptance
criterion for that extension. The alert must reach Customer Notifications, and that
module must respect the customer's stored channel preference rather than defaulting to
one channel regardless of what was configured.

## Shared expectations

Every extension, mandatory or chosen, is held to the same bar as the core platform:

- Enforce authorisation on every new route, against the verified token. Compare the
  account in the path to the claim in the token rather than assuming a request that
  reached the module has already been checked.
- Use the standard error envelope, `{errorCode, message}`, extending the platform
  catalogue with an extension-specific code only where the platform catalogue has no
  code that fits, as `portfolio-api.yaml` does with `MKT-503`.
- State explicitly, in the module's README, which Kafka consumer group it uses, and
  confirm that group identifier is not shared with any other module. Distinct group
  ids are what keep the modules independent consumers now that they ship in one
  process.
- Never call the Fauxnance API from the browser. A key reaching client-side JavaScript
  is a credential leak regardless of which extension did it.
- Ship a README covering configuration, local run instructions and what the test suite
  does and does not cover. The Trade REST API's own multi-stage Dockerfile already
  covers packaging; an extension does not add one.
