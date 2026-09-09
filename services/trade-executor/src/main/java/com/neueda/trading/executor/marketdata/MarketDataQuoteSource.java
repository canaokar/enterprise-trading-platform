package com.neueda.trading.executor.marketdata;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.neueda.trading.executor.config.FauxnanceProperties;
import com.neueda.trading.executor.quote.FixtureQuoteClient;
import com.neueda.trading.executor.quote.Quote;
import java.time.Clock;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class MarketDataQuoteSource {

    private final FauxnanceProperties properties;
    private final FixtureQuoteClient fixtureClient;
    private final RestClient restClient;
    private final int dailyBudget;
    private LocalDate budgetDate;
    private int requestsToday;

    public MarketDataQuoteSource(
            RestClient.Builder builder,
            FauxnanceProperties properties,
            Clock clock,
            @Value("${fauxnance.daily-request-budget:2000}") int dailyBudget) {
        this.properties = properties;
        this.fixtureClient = new FixtureQuoteClient(clock);
        this.dailyBudget = dailyBudget;
        this.budgetDate = LocalDate.now(ZoneOffset.UTC);
        this.restClient = builder.baseUrl(properties.getBaseUrl())
                .defaultHeader("X-Api-Key", properties.getApiKey())
                .build();
    }

    public List<Quote> quotesFor(List<String> symbols) {
        if (symbols.size() > 25) {
            throw new IllegalArgumentException("Fauxnance accepts at most 25 symbols per batch");
        }
        if ("fixture".equalsIgnoreCase(properties.getMode())) {
            return symbols.stream().map(fixtureClient::quoteFor)
                    .flatMap(java.util.Optional::stream).toList();
        }

        RestClientException lastFailure = null;
        for (int attempt = 1; attempt <= Math.max(1, properties.getMaxAttempts()); attempt++) {
            reserveRequest();
            try {
                BatchResponse body = restClient.get()
                        .uri(uri -> uri.path("/quotes")
                                .queryParam("symbols", String.join(",", symbols)).build())
                        .retrieve()
                        .body(BatchResponse.class);
                return toQuotes(body);
            } catch (RestClientException failure) {
                lastFailure = failure;
            }
        }
        throw lastFailure == null ? new RestClientException("Quote request failed") : lastFailure;
    }

    private synchronized void reserveRequest() {
        LocalDate today = LocalDate.now(ZoneOffset.UTC);
        if (!today.equals(budgetDate)) {
            budgetDate = today;
            requestsToday = 0;
        }
        if (requestsToday >= dailyBudget) {
            throw new RestClientException("Daily Fauxnance request budget exhausted");
        }
        requestsToday++;
    }

    private static List<Quote> toQuotes(BatchResponse response) {
        if (response == null || response.data() == null || response.data().quotes() == null) {
            return List.of();
        }
        List<Quote> quotes = new ArrayList<>();
        for (BatchEntry entry : response.data().quotes()) {
            if (entry.quote() == null || entry.quote().price() == null) {
                continue;
            }
            QuoteData quote = entry.quote();
            quotes.add(new Quote(
                    entry.symbol(), quote.price(), quote.currency(), quote.asOf(),
                    quote.marketState() == null ? "unknown" : quote.marketState(),
                    Boolean.TRUE.equals(entry.stale())));
        }
        return quotes;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    record BatchResponse(BatchData data) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    record BatchData(List<BatchEntry> quotes) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    record BatchEntry(String symbol, QuoteData quote, Object error, Boolean stale) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    record QuoteData(
            java.math.BigDecimal price,
            String currency,
            java.time.Instant asOf,
            String marketState) {}
}
