package com.tradingplatform.tradeapi.extensions.notifications;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(prefix = "trading.kafka", name = "enabled", havingValue = "true", matchIfMissing = true)
public class TradeNotificationConsumer {

    private static final Logger log = LoggerFactory.getLogger(TradeNotificationConsumer.class);
    private static final Set<String> TYPES = Set.of(
            "ORDER_FILLED", "ORDER_REJECTED", "ORDER_CANCELLED");

    private final ObjectMapper objectMapper;
    private final NotificationService notifications;

    public TradeNotificationConsumer(ObjectMapper objectMapper, NotificationService notifications) {
        this.objectMapper = objectMapper;
        this.notifications = notifications;
    }

    @KafkaListener(
            topics = "${trading.kafka.trade-events-topic:trade-events}",
            groupId = "notification-service")
    public void consume(String raw) {
        try {
            JsonNode event = objectMapper.readTree(raw);
            String type = event.path("eventType").asText();
            if (!TYPES.contains(type)) {
                return;
            }
            UUID eventId = UUID.fromString(event.path("eventId").asText());
            JsonNode payload = event.path("payload");
            long accountId = payload.path("accountId").asLong();
            String symbol = payload.path("symbol").asText();
            String status = payload.path("status").asText();
            String subject = "Order " + status.toLowerCase();
            String message = "%s order for %s %s is %s".formatted(
                    payload.path("side").asText(), payload.path("quantity").asText(), symbol, status);
            notifications.create(accountId, eventId, type, subject, message);
        } catch (Exception failure) {
            log.error("Could not process trade notification event", failure);
            throw new IllegalArgumentException("Invalid trade event", failure);
        }
    }
}
