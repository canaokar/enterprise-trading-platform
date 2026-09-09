package com.tradingplatform.tradeapi.extensions.portfolio;

import static com.tradingplatform.tradeapi.extensions.portfolio.PortfolioModels.*;

import com.tradingplatform.tradeapi.extensions.ExtensionException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class PortfolioService {

    private static final BigDecimal HUNDRED = new BigDecimal("100");

    private final JdbcTemplate jdbc;

    public PortfolioService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<PricedPosition> positions(long accountId, String symbol) {
        requireAccount(accountId);
        String sql = "SELECT p.account_id, p.symbol, p.quantity, p.average_cost, "
                + "mq.price, mq.currency, mq.quote_as_of, COALESCE(mq.stale, TRUE) AS stale "
                + "FROM positions p LEFT JOIN market_quotes mq ON mq.symbol = p.symbol "
                + "WHERE p.account_id = ? AND p.quantity > 0";
        List<Object> args = new ArrayList<>();
        args.add(accountId);
        if (symbol != null && !symbol.isBlank()) {
            sql += " AND p.symbol = ?";
            args.add(symbol.trim().toUpperCase());
        }
        sql += " ORDER BY p.symbol";

        List<PricedPosition> positions = jdbc.query(sql, (rs, row) -> {
            int quantity = rs.getInt("quantity");
            BigDecimal averageCost = rs.getBigDecimal("average_cost");
            BigDecimal costBasis = money(averageCost.multiply(BigDecimal.valueOf(quantity)));
            BigDecimal lastPrice = rs.getBigDecimal("price");
            BigDecimal marketValue = lastPrice == null
                    ? null : money(lastPrice.multiply(BigDecimal.valueOf(quantity)));
            BigDecimal unrealised = marketValue == null ? null : money(marketValue.subtract(costBasis));
            BigDecimal percent = unrealised == null || costBasis.signum() == 0
                    ? null : percent(unrealised, costBasis);
            Timestamp quoteTime = rs.getTimestamp("quote_as_of");
            return new PricedPosition(
                    rs.getLong("account_id"), rs.getString("symbol"), quantity, averageCost,
                    costBasis, lastPrice, marketValue, unrealised, percent,
                    rs.getString("currency"), quoteTime == null ? null : quoteTime.toInstant(),
                    rs.getBoolean("stale"));
        }, args.toArray());

        if (!positions.isEmpty() && positions.stream().allMatch(position -> position.lastPrice() == null)) {
            throw new ExtensionException(HttpStatus.SERVICE_UNAVAILABLE, "MKT-503", "Pricing unavailable");
        }
        return positions;
    }

    public PortfolioSummary summary(long accountId) {
        Account account = requireAccount(accountId);
        List<PricedPosition> positions = positions(accountId, null);
        BigDecimal marketValue = sum(positions.stream().map(PricedPosition::marketValue).toList());
        BigDecimal costBasis = sum(positions.stream().map(PricedPosition::costBasis).toList());
        BigDecimal unrealised = sum(positions.stream().map(PricedPosition::unrealisedPnl).toList());
        boolean partial = positions.stream().anyMatch(position -> position.lastPrice() == null || position.stale());
        return new PortfolioSummary(
                accountId, "USD", account.cashBalance(), marketValue, costBasis, unrealised,
                costBasis.signum() == 0 ? BigDecimal.ZERO.setScale(2) : percent(unrealised, costBasis),
                realisedBySymbol(accountId, null, null).values().stream()
                        .reduce(BigDecimal.ZERO, BigDecimal::add).setScale(2, RoundingMode.HALF_UP),
                money(account.cashBalance().add(marketValue)), positions.size(), partial, Instant.now());
    }

    public PnlResponse pnl(long accountId, LocalDate from, LocalDate to, boolean bySymbol) {
        requireAccount(accountId);
        List<PricedPosition> positions = positions(accountId, null);
        Map<String, BigDecimal> realised = realisedBySymbol(accountId, from, to);
        Map<String, BigDecimal> unrealised = new LinkedHashMap<>();
        for (PricedPosition position : positions) {
            unrealised.put(position.symbol(), zero(position.unrealisedPnl()));
        }

        BigDecimal realisedTotal = money(realised.values().stream()
                .reduce(BigDecimal.ZERO, BigDecimal::add));
        BigDecimal unrealisedTotal = money(unrealised.values().stream()
                .reduce(BigDecimal.ZERO, BigDecimal::add));
        List<SymbolPnl> breakdown = List.of();
        if (bySymbol) {
            java.util.Set<String> symbols = new java.util.TreeSet<>();
            symbols.addAll(realised.keySet());
            symbols.addAll(unrealised.keySet());
            breakdown = symbols.stream().map(symbolName -> {
                BigDecimal realisedValue = money(realised.getOrDefault(symbolName, BigDecimal.ZERO));
                BigDecimal unrealisedValue = money(unrealised.getOrDefault(symbolName, BigDecimal.ZERO));
                return new SymbolPnl(
                        symbolName, realisedValue, unrealisedValue, money(realisedValue.add(unrealisedValue)));
            }).toList();
        }
        return new PnlResponse(
                accountId, "USD", from, to, realisedTotal, unrealisedTotal,
                money(realisedTotal.add(unrealisedTotal)), breakdown, Instant.now());
    }

    private Map<String, BigDecimal> realisedBySymbol(long accountId, LocalDate from, LocalDate to) {
        List<Trade> trades = jdbc.query(
                "SELECT symbol, side, quantity, executed_price, executed_on FROM orders "
                        + "WHERE account_id = ? AND status = 'FILLED' ORDER BY executed_on",
                (rs, row) -> new Trade(
                        rs.getString("symbol"), rs.getString("side"), rs.getInt("quantity"),
                        rs.getBigDecimal("executed_price"), rs.getTimestamp("executed_on").toInstant()),
                accountId);
        Map<String, Holding> holdings = new HashMap<>();
        Map<String, BigDecimal> realised = new HashMap<>();
        for (Trade trade : trades) {
            Holding holding = holdings.computeIfAbsent(trade.symbol(), ignored -> new Holding());
            if ("BUY".equals(trade.side())) {
                BigDecimal oldCost = holding.averageCost.multiply(BigDecimal.valueOf(holding.quantity));
                holding.quantity += trade.quantity();
                holding.averageCost = oldCost.add(trade.price().multiply(BigDecimal.valueOf(trade.quantity())))
                        .divide(BigDecimal.valueOf(holding.quantity), 8, RoundingMode.HALF_UP);
            } else {
                LocalDate tradeDate = trade.executedOn().atZone(ZoneOffset.UTC).toLocalDate();
                if ((from == null || !tradeDate.isBefore(from)) && (to == null || !tradeDate.isAfter(to))) {
                    BigDecimal value = trade.price().subtract(holding.averageCost)
                            .multiply(BigDecimal.valueOf(trade.quantity()));
                    realised.merge(trade.symbol(), value, BigDecimal::add);
                }
                holding.quantity -= trade.quantity();
            }
        }
        return realised;
    }

    private Account requireAccount(long accountId) {
        return jdbc.query(
                "SELECT id, cash_balance FROM accounts WHERE id = ?",
                (rs, row) -> new Account(rs.getLong("id"), rs.getBigDecimal("cash_balance")),
                accountId).stream().findFirst().orElseThrow(() -> new ExtensionException(
                        HttpStatus.NOT_FOUND, "ACC-404", "Account not found"));
    }

    private static BigDecimal sum(List<BigDecimal> values) {
        return money(values.stream().filter(java.util.Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add));
    }

    private static BigDecimal zero(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value;
    }

    private static BigDecimal money(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }

    private static BigDecimal percent(BigDecimal value, BigDecimal basis) {
        return value.multiply(HUNDRED).divide(basis, 2, RoundingMode.HALF_UP);
    }

    private record Account(long id, BigDecimal cashBalance) {}
    private record Trade(String symbol, String side, int quantity, BigDecimal price, Instant executedOn) {}

    private static final class Holding {
        private int quantity;
        private BigDecimal averageCost = BigDecimal.ZERO;
    }
}
