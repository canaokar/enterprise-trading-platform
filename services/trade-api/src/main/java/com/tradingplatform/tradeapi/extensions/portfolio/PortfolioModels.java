package com.tradingplatform.tradeapi.extensions.portfolio;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

public final class PortfolioModels {

    private PortfolioModels() {}

    public record PricedPosition(
            long accountId,
            String symbol,
            int quantity,
            BigDecimal averageCost,
            BigDecimal costBasis,
            BigDecimal lastPrice,
            BigDecimal marketValue,
            BigDecimal unrealisedPnl,
            BigDecimal unrealisedPnlPercent,
            String currency,
            Instant priceAsOf,
            boolean stale) {}

    public record PortfolioSummary(
            long accountId,
            String baseCurrency,
            BigDecimal cashBalance,
            BigDecimal marketValue,
            BigDecimal costBasis,
            BigDecimal unrealisedPnl,
            BigDecimal unrealisedPnlPercent,
            BigDecimal realisedPnl,
            BigDecimal totalValue,
            int positionCount,
            boolean partial,
            Instant asOf) {}

    public record SymbolPnl(
            String symbol,
            BigDecimal realisedPnl,
            BigDecimal unrealisedPnl,
            BigDecimal totalPnl) {}

    public record PnlResponse(
            long accountId,
            String baseCurrency,
            LocalDate from,
            LocalDate to,
            BigDecimal realisedPnl,
            BigDecimal unrealisedPnl,
            BigDecimal totalPnl,
            List<SymbolPnl> bySymbol,
            Instant asOf) {}
}
