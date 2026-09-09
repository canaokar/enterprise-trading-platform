package com.tradingplatform.tradeapi.extensions.preferences;

import java.time.Instant;

public record PreferenceResponse(
        long accountId,
        String notificationChannel,
        String displayCurrency,
        String theme,
        Instant updatedOn) {}
