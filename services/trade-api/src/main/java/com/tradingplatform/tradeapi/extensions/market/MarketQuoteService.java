package com.tradingplatform.tradeapi.extensions.market;

import static com.tradingplatform.tradeapi.extensions.market.MarketQuoteModels.MarketQuoteResponse;

import com.tradingplatform.tradeapi.extensions.ExtensionException;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class MarketQuoteService {

    private static final String SELECT = "SELECT symbol, price, currency, quote_as_of, stale, "
            + "market_state, feed_mode, received_on FROM market_quotes ";

    private final JdbcTemplate jdbc;

    public MarketQuoteService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<MarketQuoteResponse> list() {
        return jdbc.query(SELECT + "ORDER BY symbol", (rs, row) -> new MarketQuoteResponse(
                rs.getString("symbol"), rs.getBigDecimal("price"), rs.getString("currency"),
                rs.getTimestamp("quote_as_of").toInstant(), rs.getBoolean("stale"),
                rs.getString("market_state"), rs.getString("feed_mode"),
                rs.getTimestamp("received_on").toInstant()));
    }

    public MarketQuoteResponse get(String symbol) {
        return jdbc.query(SELECT + "WHERE symbol = ?", (rs, row) -> new MarketQuoteResponse(
                rs.getString("symbol"), rs.getBigDecimal("price"), rs.getString("currency"),
                rs.getTimestamp("quote_as_of").toInstant(), rs.getBoolean("stale"),
                rs.getString("market_state"), rs.getString("feed_mode"),
                rs.getTimestamp("received_on").toInstant()), symbol.trim().toUpperCase())
                .stream().findFirst()
                .orElseThrow(() -> new ExtensionException(
                        HttpStatus.NOT_FOUND, "MKT-404", "No current quote for this symbol"));
    }
}
