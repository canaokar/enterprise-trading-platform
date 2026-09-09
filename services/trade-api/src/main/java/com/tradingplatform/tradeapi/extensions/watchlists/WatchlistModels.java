package com.tradingplatform.tradeapi.extensions.watchlists;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class WatchlistModels {

    private WatchlistModels() {}

    public record CreateWatchlistRequest(@NotBlank @Size(max = 80) String name) {}

    public record AddInstrumentRequest(
            @NotBlank @Size(max = 20) String symbol) {}

    public record WatchlistSummary(UUID id, String name, int instrumentCount, Instant createdOn) {}

    public record WatchlistEntry(
            String symbol,
            BigDecimal price,
            String currency,
            Instant quoteAsOf,
            boolean stale) {}

    public record WatchlistDetail(
            UUID id,
            long accountId,
            String name,
            List<WatchlistEntry> instruments,
            Instant createdOn) {}

    public record CreateAlertRequest(
            @NotBlank @Size(max = 20) String symbol,
            @NotBlank @Pattern(regexp = "ABOVE|BELOW") String direction,
            @NotNull @DecimalMin(value = "0.00", inclusive = false) BigDecimal threshold) {}

    public record AlertResponse(
            UUID id,
            long accountId,
            String symbol,
            String direction,
            BigDecimal threshold,
            String status,
            Instant createdOn,
            Instant triggeredOn,
            BigDecimal triggeredPrice) {}
}
