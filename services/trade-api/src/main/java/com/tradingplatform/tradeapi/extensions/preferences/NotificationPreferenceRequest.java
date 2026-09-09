package com.tradingplatform.tradeapi.extensions.preferences;

import jakarta.validation.constraints.NotNull;

public record NotificationPreferenceRequest(@NotNull NotificationChannel channel) {}
