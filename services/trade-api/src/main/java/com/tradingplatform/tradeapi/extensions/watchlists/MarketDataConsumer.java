package com.tradingplatform.tradeapi.extensions.watchlists;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.tradingplatform.tradeapi.extensions.notifications.NotificationService;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(prefix = "trading.kafka", name = "enabled", havingValue = "true", matchIfMissing = true)
public class MarketDataConsumer {

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final NotificationService notifications;

    public MarketDataConsumer(
            JdbcTemplate jdbc,
            ObjectMapper objectMapper,
            NotificationService notifications) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
        this.notifications = notifications;
    }

    @KafkaListener(topics = "${MARKET_DATA_TOPIC:market-data}", groupId = "watchlist-service")
    @Transactional
    public void consume(String raw) throws Exception {
        JsonNode event = objectMapper.readTree(raw);
        UUID eventId = UUID.fromString(event.path("eventId").asText());
        int claimed = jdbc.update(
                "INSERT INTO extension_processed_events(consumer_name, event_id) VALUES ('watchlist-service', ?) "
                        + "ON CONFLICT DO NOTHING",
                eventId);
        if (claimed == 0) {
            return;
        }

        JsonNode payload = event.path("payload");
        String symbol = payload.path("symbol").asText();
        BigDecimal price = payload.path("price").decimalValue();
        String currency = payload.path("currency").asText("USD");
        String asOfText = payload.path("quoteAsOf").asText(event.path("eventTime").asText());
        Instant quoteAsOf = Instant.parse(asOfText);
        boolean stale = payload.path("stale").asBoolean(false);
        String marketState = payload.path("marketState").asText("unknown");
        String feedMode = payload.path("feedMode").asText("fixture");

        jdbc.update(
                "INSERT INTO market_quotes(symbol, price, currency, quote_as_of, stale, market_state, feed_mode) "
                        + "VALUES (?, ?, ?, ?, ?, ?, ?) "
                        + "ON CONFLICT(symbol) DO UPDATE SET price = EXCLUDED.price, currency = EXCLUDED.currency, "
                        + "quote_as_of = EXCLUDED.quote_as_of, stale = EXCLUDED.stale, "
                        + "market_state = EXCLUDED.market_state, feed_mode = EXCLUDED.feed_mode, received_on = NOW()",
                symbol, price, currency, java.sql.Timestamp.from(quoteAsOf), stale, marketState, feedMode);

        java.util.List<AlertRow> alerts = jdbc.query(
                "SELECT id, account_id, direction, threshold, last_observed_price "
                        + "FROM price_alerts WHERE symbol = ? AND status = 'ACTIVE' FOR UPDATE",
                (rs, row) -> new AlertRow(
                        rs.getObject("id", UUID.class),
                        rs.getLong("account_id"),
                        rs.getString("direction"),
                        rs.getBigDecimal("threshold"),
                        rs.getBigDecimal("last_observed_price")),
                symbol);
        for (AlertRow alert : alerts) {
            handleAlert(eventId, symbol, price, alert);
        }
    }

    private void handleAlert(UUID eventId, String symbol, BigDecimal price, AlertRow alert) {
        UUID alertId = alert.id();
        long accountId = alert.accountId();
        String direction = alert.direction();
        BigDecimal threshold = alert.threshold();
        BigDecimal previous = alert.lastObservedPrice();

        boolean thresholdMet = "ABOVE".equals(direction)
                ? price.compareTo(threshold) >= 0
                : price.compareTo(threshold) <= 0;
        boolean crossed = thresholdMet && (previous == null || ("ABOVE".equals(direction)
                ? previous.compareTo(threshold) < 0
                : previous.compareTo(threshold) > 0));

        if (crossed) {
            jdbc.update(
                    "UPDATE price_alerts SET status = 'TRIGGERED', triggered_on = NOW(), "
                            + "triggered_price = ?, last_observed_price = ? WHERE id = ? AND status = 'ACTIVE'",
                    price, price, alertId);
            UUID notificationEvent = UUID.nameUUIDFromBytes(
                    (eventId + ":" + alertId).getBytes(StandardCharsets.UTF_8));
            notifications.create(
                    accountId,
                    notificationEvent,
                    "PRICE_ALERT_TRIGGERED",
                    symbol + " price alert triggered",
                    "%s crossed %s at %s".formatted(symbol, threshold, price));
        } else {
            jdbc.update("UPDATE price_alerts SET last_observed_price = ? WHERE id = ?", price, alertId);
        }
    }

    private record AlertRow(
            UUID id,
            long accountId,
            String direction,
            BigDecimal threshold,
            BigDecimal lastObservedPrice) {}
}
