/**
 * The Trade Executor: the platform's execution venue.
 *
 * <p>Single responsibility of this service: take an order that the Trade REST API has already
 * accepted and recorded, decide whether it fills and at what price, move the cash and the position
 * to match that decision, and tell the rest of the platform what happened. It is the only component
 * that decides whether an order fills.
 *
 * <p>It accepts nothing from a customer. Everything it acts on arrived on the {@code orders} topic,
 * was validated at acceptance, and has a row in Postgres already. The executor's job starts at the
 * point where the answer stopped being computable inside one HTTP request.
 *
 * <p>The service carries a second responsibility that is not on that path. It runs the market-data
 * poller on a schedule, in {@code marketdata}, calling the Fauxnance batch quotes endpoint for the
 * symbols the platform holds and watches and publishing each quote to {@code market-data}. The
 * poller lives here because this is the service that already calls Fauxnance, and one component
 * calling Fauxnance means one key, one retry policy and one budget. The two responsibilities share
 * a quote client and share nothing else: the poller never waits on an order, and an order never
 * waits on a poll.
 *
 * <p>The annotated application class belongs here, at the root, so that component scanning reaches
 * every package below it without being configured to. Scheduling is enabled on it, because without
 * that the poller's scheduled method is an ordinary method nobody calls.
 *
 * <p>Rename or reorganise these packages if your design says something else, and be ready to say
 * why in the review.
 */
package com.tradingplatform.executor;
