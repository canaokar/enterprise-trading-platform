package com.tradingplatform.tradeapi.extensions.preferences;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record DisplayPreferenceRequest(
        @NotBlank @Pattern(regexp = "^[A-Z]{3}$") String currency,
        @NotBlank @Pattern(regexp = "LIGHT|DARK|SYSTEM") String theme) {}
