# Angular screen design

The reference UI is desktop-first, responsive down to a narrow browser, and styled as a compact
broker portal. A persistent market header connects overview, trade, orders, portfolio and markets.
It uses standalone Angular components, reactive forms and the shared controls in
`ui/src/styles.css`; there is no component library, state-management layer or animation system.

## Screen inventory and routes

| Capability | Route | Component | Main decision |
|---|---|---|---|
| Sign in | `/login` | `login` | One credential form and one readable failure message. |
| Account dashboard | `/dashboard` | `dashboard` | Portfolio metrics, priced positions and market watch. |
| Order ticket | `/orders/new` | `order-ticket` | Kafka-fed market board, selected quote context and visible `NEW` state. |
| Order history | `/orders` | `blotter` | A compact table with side, status, price and timestamps. |
| Portfolio summary and priced positions | `/portfolio` | `portfolio` | Summary cards and priced positions share one page. |
| Profit and loss detail | `/portfolio` | `portfolio` | Realised and unrealised values are separate columns. |
| Customer preferences | `/preferences` | `preferences` | Notification and display settings share one form. |
| Notification inbox and delivery state | `/notifications` | `notifications` | Every row shows its resolved channel, state and read status. |
| Watchlist detail and current prices | `/watchlists` | `watchlists` | Selection, symbols and freshness stay together. |
| Price-alert creation and history | `/watchlists` | `watchlists` | Creation and history share the watchlist context. |

All routes except sign-in use `authGuard`. The lightweight application shell keeps primary trading
routes visible and removes repeated back buttons from individual screens.

## State matrix

| Screen | Loading / empty | Populated | Failure / validation | Special state |
|---|---|---|---|---|
| Sign in | Submit button shows progress | Redirects to dashboard | Uniform login error | Unauthenticated is expected |
| Dashboard | Loading labels | Cash and positions | Retry action | Account status and timestamp |
| Order ticket | Quote and submit progress | Market board and submitted order | Field, feed and platform errors | Live/demo label; `NEW` remains visible while polling |
| Order history | Loading/empty row | Order table | Readable platform error | Side and terminal-status badges |
| Portfolio | Loading/empty rows | Totals, positions, P&L | Readable platform error | Partial banner; missing/stale price labels |
| Preferences | Disabled while loading/saving | Current settings | Three-letter currency validation | Saved confirmation and update time |
| Notifications | Loading/empty message | Inbox rows | Readable platform error | Resolved channel, delivery and read state |
| Watchlists | Loading/empty rows | Current prices | Required symbol/name/threshold validation | Missing/stale/current freshness labels |
| Price alerts | Empty history | Active and triggered rows | Positive threshold validation | Triggered timestamp and disable action |

## Review decisions

- Portfolio and P&L share a page because the totals and symbol breakdown explain each other.
- Watchlists and alerts share a page because an alert without the current quote lacks context.
- Delivery is recorded, not sent externally; the inbox makes the selected channel observable.
- Currency, quote time and freshness are shown next to the numbers they qualify.
- The order ticket reads prices from the Trade API's Kafka-fed cache and never calls Fauxnance
  from the browser. Clicking a market tile selects the symbol and limit price.
- The UI uses typed transport interfaces kept beside its API service. Client generation is
  deliberately omitted from the local example to avoid adding a generator toolchain for four
  small contracts.
