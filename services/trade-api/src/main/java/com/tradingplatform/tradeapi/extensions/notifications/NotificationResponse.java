package com.tradingplatform.tradeapi.extensions.notifications;

import java.time.Instant;
import java.util.UUID;

public record NotificationResponse(
        UUID id,
        long accountId,
        String type,
        String channel,
        String subject,
        String message,
        String deliveryState,
        Instant readOn,
        Instant createdOn) {}
