package com.tradingplatform.tradeapi.extensions.watchlists;

import static com.tradingplatform.tradeapi.extensions.watchlists.WatchlistModels.*;

import com.tradingplatform.tradeapi.extensions.ExtensionException;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class WatchlistService {

    private final JdbcTemplate jdbc;

    public WatchlistService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public WatchlistDetail create(long accountId, String name) {
        UUID id = UUID.randomUUID();
        jdbc.update("INSERT INTO watchlists(id, account_id, name) VALUES (?, ?, ?)",
                id, accountId, name.trim());
        return get(accountId, id);
    }

    public List<WatchlistSummary> list(long accountId) {
        return jdbc.query(
                "SELECT w.id, w.name, w.created_on, COUNT(i.symbol) AS instrument_count "
                        + "FROM watchlists w LEFT JOIN watchlist_instruments i ON i.watchlist_id = w.id "
                        + "WHERE w.account_id = ? GROUP BY w.id ORDER BY w.created_on",
                (rs, row) -> new WatchlistSummary(
                        rs.getObject("id", UUID.class), rs.getString("name"),
                        rs.getInt("instrument_count"), rs.getTimestamp("created_on").toInstant()),
                accountId);
    }

    public WatchlistDetail get(long accountId, UUID id) {
        WatchlistHeader header = jdbc.query(
                "SELECT id, account_id, name, created_on FROM watchlists WHERE id = ? AND account_id = ?",
                (rs, row) -> new WatchlistHeader(
                        rs.getObject("id", UUID.class), rs.getLong("account_id"),
                        rs.getString("name"), rs.getTimestamp("created_on").toInstant()),
                id, accountId).stream().findFirst().orElseThrow(this::notFound);

        List<WatchlistEntry> entries = jdbc.query(
                "SELECT wi.symbol, mq.price, mq.currency, mq.quote_as_of, COALESCE(mq.stale, TRUE) AS stale "
                        + "FROM watchlist_instruments wi LEFT JOIN market_quotes mq ON mq.symbol = wi.symbol "
                        + "WHERE wi.watchlist_id = ? ORDER BY wi.symbol",
                (rs, row) -> new WatchlistEntry(
                        rs.getString("symbol"), rs.getBigDecimal("price"), rs.getString("currency"),
                        rs.getTimestamp("quote_as_of") == null ? null : rs.getTimestamp("quote_as_of").toInstant(),
                        rs.getBoolean("stale")),
                id);
        return new WatchlistDetail(header.id(), header.accountId(), header.name(), entries, header.createdOn());
    }

    public WatchlistDetail addInstrument(long accountId, UUID id, String symbol) {
        get(accountId, id);
        String normalized = symbol.trim().toUpperCase();
        Integer exists = jdbc.queryForObject(
                "SELECT COUNT(*) FROM instruments WHERE symbol = ? AND tradable = TRUE",
                Integer.class, normalized);
        if (exists == null || exists == 0) {
            throw new ExtensionException(HttpStatus.NOT_FOUND, "INS-404", "Instrument not found");
        }
        jdbc.update(
                "INSERT INTO watchlist_instruments(watchlist_id, symbol) VALUES (?, ?) ON CONFLICT DO NOTHING",
                id, normalized);
        return get(accountId, id);
    }

    public void removeInstrument(long accountId, UUID id, String symbol) {
        get(accountId, id);
        jdbc.update("DELETE FROM watchlist_instruments WHERE watchlist_id = ? AND symbol = ?",
                id, symbol.toUpperCase());
    }

    public AlertResponse createAlert(long accountId, CreateAlertRequest request) {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM price_alerts WHERE account_id = ? AND status = 'ACTIVE'",
                Integer.class, accountId);
        if (count != null && count >= 100) {
            throw new ExtensionException(HttpStatus.CONFLICT, "ALT-409", "Active alert limit reached");
        }
        String symbol = request.symbol().trim().toUpperCase();
        Integer exists = jdbc.queryForObject(
                "SELECT COUNT(*) FROM instruments WHERE symbol = ? AND tradable = TRUE",
                Integer.class, symbol);
        if (exists == null || exists == 0) {
            throw new ExtensionException(HttpStatus.NOT_FOUND, "INS-404", "Instrument not found");
        }
        UUID id = UUID.randomUUID();
        jdbc.update(
                "INSERT INTO price_alerts(id, account_id, symbol, direction, threshold, last_observed_price) "
                        + "VALUES (?, ?, ?, ?, ?, (SELECT price FROM market_quotes WHERE symbol = ?))",
                id, accountId, symbol, request.direction(), request.threshold(), symbol);
        return alert(accountId, id);
    }

    public List<AlertResponse> alerts(long accountId) {
        return jdbc.query(
                "SELECT * FROM price_alerts WHERE account_id = ? ORDER BY created_on DESC",
                (rs, row) -> mapAlert(rs), accountId);
    }

    public AlertResponse disableAlert(long accountId, UUID id) {
        int updated = jdbc.update(
                "UPDATE price_alerts SET status = 'DISABLED' WHERE id = ? AND account_id = ? AND status = 'ACTIVE'",
                id, accountId);
        if (updated == 0) {
            throw notFound();
        }
        return alert(accountId, id);
    }

    private AlertResponse alert(long accountId, UUID id) {
        return jdbc.query(
                "SELECT * FROM price_alerts WHERE id = ? AND account_id = ?",
                (rs, row) -> mapAlert(rs), id, accountId).stream().findFirst()
                .orElseThrow(this::notFound);
    }

    private static AlertResponse mapAlert(ResultSet rs) throws SQLException {
        return new AlertResponse(
                rs.getObject("id", UUID.class), rs.getLong("account_id"), rs.getString("symbol"),
                rs.getString("direction"), rs.getBigDecimal("threshold"), rs.getString("status"),
                rs.getTimestamp("created_on").toInstant(),
                rs.getTimestamp("triggered_on") == null ? null : rs.getTimestamp("triggered_on").toInstant(),
                rs.getBigDecimal("triggered_price"));
    }

    private ExtensionException notFound() {
        return new ExtensionException(HttpStatus.NOT_FOUND, "WCH-404", "Watchlist resource not found");
    }

    private record WatchlistHeader(UUID id, long accountId, String name, Instant createdOn) {}
}
