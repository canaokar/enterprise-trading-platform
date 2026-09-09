package com.tradingplatform.tradeapi.extensions.market;

import java.math.BigDecimal;
import java.time.Instant;

public final class MarketQuoteModels {

    private MarketQuoteModels() {}

    public record MarketQuoteResponse(
            String symbol,
            BigDecimal price,
            String currency,
            Instant quoteAsOf,
            boolean stale,
            String marketState,
            String feedMode,
            Instant receivedOn) {}
}
