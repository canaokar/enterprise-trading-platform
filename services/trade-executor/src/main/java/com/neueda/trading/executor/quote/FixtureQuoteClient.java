package com.neueda.trading.executor.quote;

import java.math.BigDecimal;
import java.time.Clock;
import java.util.Map;
import java.util.Optional;

public class FixtureQuoteClient implements QuoteClient {

    private static final Map<String, BigDecimal> PRICES = Map.ofEntries(
            Map.entry("AAPL", new BigDecimal("232.71")),
            Map.entry("MSFT", new BigDecimal("409.50")),
            Map.entry("GOOGL", new BigDecimal("167.55")),
            Map.entry("AMZN", new BigDecimal("185.90")),
            Map.entry("TSLA", new BigDecimal("259.20")),
            Map.entry("NVDA", new BigDecimal("134.50")),
            Map.entry("JPM", new BigDecimal("237.40")),
            Map.entry("SPY", new BigDecimal("549.20")));

    private final Clock clock;

    public FixtureQuoteClient(Clock clock) {
        this.clock = clock;
    }

    @Override
    public Optional<Quote> quoteFor(String symbol) {
        BigDecimal price = PRICES.get(symbol.toUpperCase());
        return price == null
                ? Optional.empty()
                : Optional.of(new Quote(symbol.toUpperCase(), price, "USD", clock.instant(), "open", false));
    }
}
