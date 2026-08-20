# Customer preferences and personalisation

Every customer-facing feature on this platform needs to know something about the
customer beyond their trades. Which channel to reach them on. Which currency to
show a total in. Which instruments to put on the front of their dashboard.
Nothing owns any of that today, so each feature that needs it invents its own
copy, and within a fortnight the copies disagree and nobody can say which one the
customer actually set. This extension is the single place that owns it.

## Who uses it

The customer, through a settings screen in the Angular application. And other
parts of the platform, which resolve a preference before they act: a
notification path asks which channel to send on, a portfolio or watchlist screen
asks which currency to render totals in.

## What it integrates with

| Surface | How this module uses it |
|---|---|
| Kafka | Nothing by default. This module consumes no topic and produces none unless you decide it should. |
| Angular application | The settings screen: reading the preference set and writing changes. |
| Customer notifications | Resolves a channel through this module before sending, across a package boundary rather than over HTTP. |
| Trade REST API | Read-only, to resolve an account when a screen needs the holder's details. Do not copy anything `accounts` already owns. |

## The API is yours

There is no contract for this extension. Design the API, write it as OpenAPI
before you write the controller, and bring it to your instructor on day one for
review. The platform conventions still bind: the `{errorCode, message}` envelope,
the platform error catalogue extended only where nothing in it fits, and the
bearer token the Trade REST API verifies before any of your routes run. What the
verifier cannot decide for you is whether this caller may reach this resource,
so every route you add compares the `accountId` claim against what it is about
to return.

Note the integration requirement for the sprint when you scope this one: the
extension has to integrate with the platform through Kafka or the trading data.
A preferences module that touches neither meets its own brief and not the
sprint's, so agree the integration surface with your instructor on day one.
Publishing a preference-changed event, or resolving account details through the
account path this service already has, are two answers.

## What makes it worth building

Availability, not feature surface. Something else calls this on a path that
decides whether a customer gets told about their own trade. That inverts the
usual priority: a small interface that is always there is worth more than a
large one that is occasionally not. What that call looks like, what the caller
does when there is no preference to read, and whether it fails open or fails
closed are the interesting parts, and every one of them is a decision log entry.

The call is in-process this year, which removes the timeout and adds a subtler
risk: a caller that reaches into your tables directly because it can. Publish
one interface for resolution, keep everything behind it, and say in the review
who calls it.

The second question is what this module should hold at all. An email address and
a telephone number are personal data, and they may already exist somewhere else
on the platform. Storing a second copy doubles the number of places a leak can
happen and creates a reconciliation problem the day one of them changes. Deciding
to store a reference rather than a copy is a defensible answer, and so is the
opposite, but the decision has to be taken rather than fallen into.

## Scope for one week

A preference record per account covering at least a notification channel with its
contact detail and a display setting such as base currency. Reads and writes from
the Angular settings screen. A resolution route the notification path can call.
Persistence that survives a restart. The integration surface agreed on day one.

Out of scope unless the rest is finished: preference history and revert, multiple
contact points per channel, and publishing a change event so that callers do not
have to ask.

## What to get right

- **Access control.** A customer reads and writes their own preferences only. The
  account comes from the verified token and is compared against the account in
  the path on every route.
- **Personal data.** Decide what is stored here, encrypt or reference what is
  sensitive, and keep contact details out of logs and out of Kafka payloads.
- **The internal path is not the customer route.** What another part of the
  service calls to resolve a channel is a Java interface, not an HTTP route
  reachable by anyone holding a customer token. Keep resolution off the wire, or
  say why it has to be on it.
- **A default is a decision.** What the platform does when no preference has been
  set, and what a caller does when nothing has been stored, are both behaviours
  somebody has to choose deliberately.
