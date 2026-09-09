package com.tradingplatform.tradeapi.extensions.preferences;

import com.tradingplatform.tradeapi.extensions.ExtensionException;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class PreferenceService {

    private final JdbcTemplate jdbc;

    public PreferenceService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public PreferenceResponse get(long accountId) {
        return jdbc.query(
                "SELECT account_id, notification_channel, display_currency, theme, updated_on "
                        + "FROM customer_preferences WHERE account_id = ?",
                (rs, row) -> map(rs), accountId).stream().findFirst()
                .orElseThrow(() -> new ExtensionException(
                        HttpStatus.NOT_FOUND, "PREF-404", "Preferences not found"));
    }

    public PreferenceResponse updateChannel(long accountId, NotificationChannel channel) {
        requireAccount(accountId);
        jdbc.update(
                "INSERT INTO customer_preferences(account_id, notification_channel) VALUES (?, ?) "
                        + "ON CONFLICT(account_id) DO UPDATE SET notification_channel = EXCLUDED.notification_channel, updated_on = NOW()",
                accountId, channel.name());
        return get(accountId);
    }

    public PreferenceResponse updateDisplay(long accountId, DisplayPreferenceRequest request) {
        requireAccount(accountId);
        jdbc.update(
                "INSERT INTO customer_preferences(account_id, display_currency, theme) VALUES (?, ?, ?) "
                        + "ON CONFLICT(account_id) DO UPDATE SET display_currency = EXCLUDED.display_currency, theme = EXCLUDED.theme, updated_on = NOW()",
                accountId, request.currency(), request.theme());
        return get(accountId);
    }

    public String channelFor(long accountId) {
        return jdbc.query(
                "SELECT notification_channel FROM customer_preferences WHERE account_id = ?",
                (rs, row) -> rs.getString(1), accountId).stream().findFirst().orElse("IN_APP");
    }

    private void requireAccount(long accountId) {
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM accounts WHERE id = ?", Integer.class, accountId);
        if (count == null || count == 0) {
            throw new ExtensionException(HttpStatus.NOT_FOUND, "ACC-404", "Account not found");
        }
    }

    private static PreferenceResponse map(ResultSet rs) throws SQLException {
        return new PreferenceResponse(
                rs.getLong("account_id"),
                rs.getString("notification_channel"),
                rs.getString("display_currency"),
                rs.getString("theme"),
                rs.getTimestamp("updated_on").toInstant());
    }
}
