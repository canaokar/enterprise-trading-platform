package com.neueda.trading.executor.marketdata;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.neueda.trading.executor.quote.Quote;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component("marketDataPoller")
public class MarketDataPoller implements HealthIndicator {

    private static final Logger log = LoggerFactory.getLogger(MarketDataPoller.class);
    private static final int MAX_BATCH_SIZE = 25;

    private final JdbcTemplate jdbc;
    private final KafkaTemplate<String, String> kafka;
    private final ObjectMapper objectMapper;
    private final MarketDataQuoteSource quoteSource;
    private final Clock clock;
    private final String topic;
    private final String feedMode;
    private volatile Instant lastPoll;
    private volatile Instant lastSuccess;
    private volatile String lastFailure;

    public MarketDataPoller(
            JdbcTemplate jdbc,
            KafkaTemplate<String, String> kafka,
            ObjectMapper objectMapper,
            MarketDataQuoteSource quoteSource,
            Clock clock,
            @Value("${executor.topics.market-data:market-data}") String topic,
            @Value("${fauxnance.mode:live}") String feedMode) {
        this.jdbc = jdbc;
        this.kafka = kafka;
        this.objectMapper = objectMapper;
        this.quoteSource = quoteSource;
        this.clock = clock;
        this.topic = topic;
        this.feedMode = feedMode.toLowerCase();
    }

    @Scheduled(
            fixedDelayString = "#{${POLL_INTERVAL_SECONDS:30} * 1000}",
            initialDelayString = "${MARKET_DATA_INITIAL_DELAY_MS:3000}")
    public void poll() {
        lastPoll = clock.instant();
        List<String> symbols = discoverSymbols();
        int published = 0;
        List<String> failures = new ArrayList<>();

        for (int start = 0; start < symbols.size(); start += MAX_BATCH_SIZE) {
            List<String> batch = symbols.subList(start, Math.min(start + MAX_BATCH_SIZE, symbols.size()));
            try {
                for (Quote quote : quoteSource.quotesFor(batch)) {
                    publish(quote);
                    published++;
                }
            } catch (Exception failure) {
                failures.addAll(batch);
                log.warn("Market-data batch failed symbols={} reason={}", batch, failure.getMessage());
            }
        }

        if (published > 0) {
            lastSuccess = clock.instant();
        }
        lastFailure = failures.isEmpty() ? null : String.join(",", failures);
        log.info("Market-data poll complete symbols={} published={} failed={}",
                symbols.size(), published, failures.size());
    }

    private List<String> discoverSymbols() {
        return jdbc.queryForList(
                "SELECT symbol FROM positions WHERE quantity > 0 "
                        + "UNION SELECT symbol FROM watchlist_instruments ORDER BY symbol",
                String.class);
    }

    private void publish(Quote quote) throws Exception {
        Instant eventTime = clock.instant();
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("symbol", quote.symbol());
        payload.put("price", quote.price());
        payload.put("currency", quote.currency());
        payload.put("change", null);
        payload.put("changePercent", null);
        payload.put("previousClose", null);
        payload.put("marketState", quote.marketState());
        payload.put("stale", quote.stale());
        payload.put("quoteAsOf", quote.asOf());
        payload.put("feedMode", feedMode);

        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("eventId", UUID.randomUUID());
        envelope.put("eventType", "QUOTE");
        envelope.put("eventTime", eventTime);
        envelope.put("source", "market-poller");
        envelope.put("schemaVersion", 1);
        envelope.put("payload", payload);

        kafka.send(topic, quote.symbol(), json(envelope)).get(10, TimeUnit.SECONDS);
    }

    private String json(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException failure) {
            throw new IllegalStateException("Could not serialize market-data event", failure);
        }
    }

    @Override
    public Health health() {
        Health.Builder result = lastFailure == null ? Health.up() : Health.status("DEGRADED");
        return result.withDetail("lastPoll", lastPoll == null ? "" : lastPoll)
                .withDetail("lastSuccess", lastSuccess == null ? "" : lastSuccess)
                .withDetail("failedSymbols", lastFailure == null ? "" : lastFailure)
                .build();
    }
}
