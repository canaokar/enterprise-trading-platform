/**
 * The market-data poller: the scheduled component that manufactures the price stream.
 *
 * <p>The curriculum promises a real-time price stream. Fauxnance does not have one: it serves
 * end-of-day candles and delayed quotes over HTTP, with no WebSocket and no server-sent events.
 * This package is what manufactures the stream. On a fixed interval it asks the batch quotes
 * endpoint for the symbols the platform holds and watches, and publishes one message per symbol to
 * {@code market-data}. Without it that topic is empty, and every Sprint 10 extension that reads
 * prices has nothing to consume.
 *
 * <p>It runs inside this service rather than beside it, and that is a deliberate placement. One
 * component calls Fauxnance, so one component holds the key, applies the retry policy and spends
 * the quota. The alternative is a second deployable running a second runtime with a second copy of
 * the same credential, which teaches deployment rather than trading.
 *
 * <p>Nothing here is on the order path. The poll loop runs on its own schedule and knows nothing
 * about an order, a fill or a consumer offset. A design that starts a poll when an order arrives,
 * or that makes the executor wait on a poll, has coupled two things the platform keeps apart.
 *
 * <p><b>Single responsibility.</b> Decide which symbols to ask about, ask in batches, publish what
 * comes back, and stay alive. The HTTP call itself belongs to the pricing package, which already
 * owns the Fauxnance client, the key and the quota. This package asks that client for a group of
 * symbols; it does not build a second one.
 *
 * <p><b>The symbol list is configuration.</b> It is the instruments the platform holds or watches,
 * read from the environment, not a constant in the source. A team that writes the list into the
 * code has to rebuild an image to watch a different instrument, and the Sprint 10 watchlist
 * extension has no way to influence what is polled.
 *
 * <p><b>Batching is the quota arithmetic.</b> The batch endpoint takes at most 25 symbols and costs
 * one request whatever the symbol count. Splitting the list into groups of 25 is what turns a
 * request per symbol into a request per 25 symbols, and it is the difference between a key that
 * lasts a day and a key that is gone before lunch. The quota is 2000 requests per day, it resets at
 * midnight UTC rather than at midnight where you are, and it is shared with the pricing of every
 * fill. Give this component a budget that is its share rather than the whole allowance, because the
 * first symptom of a poller that spent the lot is orders rejected for want of a price.
 *
 * <p><b>One message per symbol, keyed by the symbol. Never one message per batch.</b> Batching the
 * HTTP call is a quota optimisation and it is correct. Batching the Kafka message puts several
 * symbols behind one key, which destroys the per-symbol ordering the topic contract promises and
 * stops a consumer filtering to the instruments it cares about.
 *
 * <p>The envelope is the platform's five fields plus a payload, as on the other two topics, and
 * {@code source} is {@code market-poller}. It names the producing component rather than the
 * container, which is what keeps a quote distinguishable from an execution event now that both ship
 * in one process. {@code eventTime} and {@code quoteAsOf} are different timestamps and the
 * difference is the point: {@code eventTime} is when this component published, {@code quoteAsOf} is
 * when Fauxnance observed the price. Setting {@code quoteAsOf} to the current time because it was
 * easier is the most common error here, and it is invisible until Sprint 10.
 *
 * <p><b>The interval.</b> Enforce a floor in configuration rather than documenting one and hoping.
 * Below roughly fifteen seconds no configuration of this component survives even a half-day
 * session, and the quotes are delayed anyway, so polling faster than the data changes buys requests
 * and nothing else. Note also that a fixed delay after a cycle is not a fixed interval: a cycle that
 * takes four seconds followed by a thirty second wait is a thirty-four second cycle, and the drift
 * compounds over a taught day.
 *
 * <p><b>Staying alive.</b> A price feed that stops is worse than one that is wrong, because a dead
 * schedule is silent. One bad symbol does not stop the batch, one failed batch does not stop the
 * cycle, and anything unforeseen is caught at the top of the cycle, logged with its stack trace,
 * and followed by the next cycle. A scheduled method that throws is not necessarily rescheduled.
 *
 * <p>Everything this component decides is testable with the quote client and the producer faked:
 * that a list is split at 25, that one message goes out per symbol keyed by symbol, that the
 * envelope matches the contract, and that one unresolvable symbol does not stop the cycle. None of
 * it needs a broker, and none of it should spend a request.
 */
package com.tradingplatform.executor.marketdata;
