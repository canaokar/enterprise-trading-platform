/**
 * Pricing: obtaining a quote from the Fauxnance API.
 *
 * <p>Single responsibility: given a symbol, or a group of symbols, answer with the prices Fauxnance
 * served and say plainly which ones it did not. It applies no fill rule and knows nothing about
 * orders.
 *
 * <p>This package has two callers inside the service. The execution path asks for one symbol,
 * through {@code GET /quotes/{symbol}}, to price a fill. The poller in {@code marketdata} asks for a
 * group, through {@code GET /quotes?symbols=A,B,C}, which takes at most 25 symbols and costs one
 * request whatever the symbol count. Both cross the same client, carry the same key and spend the
 * same budget, which is the reason the poller lives in this service at all.
 *
 * <p>One symbol coming back as an error entry, or with no price, is not the same as the call
 * failing. The other symbols in that response are good. Log the symbol, count it, and return the
 * rest, because publishing a null price breaks the arithmetic of every consumer downstream.
 *
 * <p>Two properties of this package are design decisions rather than plumbing, and both are asked
 * about at the review.
 *
 * <p>Which failures cost a retry. A timeout will probably succeed on the next attempt. A 404 for a
 * symbol Fauxnance does not serve will not, and retrying it spends requests to learn the same thing
 * three times. A 429 will not either, because the quota does not refill inside a retry window.
 *
 * <p>What happens to the quota. 2000 requests a day, resetting at midnight UTC, shared between
 * pricing and polling and, from Sprint 10, with anything else that prices. Ten orders on one symbol
 * inside a second do not need ten requests. A poller that spends the whole allowance leaves the fill
 * path with nothing, and the first symptom is orders rejected for want of a price, so the budget is
 * divided deliberately rather than by whichever caller gets there first.
 *
 * <p>Structure this package so that the HTTP layer is passed in rather than constructed here. A test
 * that has to reach Fauxnance to run is a test that fails on a train, gets skipped by the third
 * person who sees it fail, and spends quota every time it does run.
 *
 * <p>The key is read from {@code FAUXNANCE_API_KEY} and from nowhere else. It is never a literal, a
 * default, or a value in a properties file. One service calls Fauxnance, so one service holds the
 * key.
 */
package com.tradingplatform.executor.pricing;
