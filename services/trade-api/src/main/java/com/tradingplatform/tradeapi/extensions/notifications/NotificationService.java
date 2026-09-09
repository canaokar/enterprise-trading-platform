package com.tradingplatform.tradeapi.extensions.notifications;

import com.tradingplatform.tradeapi.extensions.preferences.PreferenceService;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class NotificationService {

    private final JdbcTemplate jdbc;
    private final PreferenceService preferences;

    public NotificationService(JdbcTemplate jdbc, PreferenceService preferences) {
        this.jdbc = jdbc;
        this.preferences = preferences;
    }

    public void create(
            long accountId,
            UUID sourceEventId,
            String type,
            String subject,
            String message) {
        jdbc.update(
                "INSERT INTO notifications(id, account_id, source_event_id, type, channel, subject, message, delivery_state) "
                        + "VALUES (?, ?, ?, ?, ?, ?, ?, 'SENT') ON CONFLICT(source_event_id) DO NOTHING",
                UUID.randomUUID(), accountId, sourceEventId, type,
                preferences.channelFor(accountId), subject, message);
    }

    public List<NotificationResponse> list(long accountId) {
        return jdbc.query(
                "SELECT id, account_id, type, channel, subject, message, delivery_state, read_on, created_on "
                        + "FROM notifications WHERE account_id = ? ORDER BY created_on DESC",
                (rs, row) -> map(rs), accountId);
    }

    public int markAllRead(long accountId) {
        return jdbc.update(
                "UPDATE notifications SET read_on = NOW() WHERE account_id = ? AND read_on IS NULL",
                accountId);
    }

    private static NotificationResponse map(ResultSet rs) throws SQLException {
        return new NotificationResponse(
                rs.getObject("id", UUID.class),
                rs.getLong("account_id"),
                rs.getString("type"),
                rs.getString("channel"),
                rs.getString("subject"),
                rs.getString("message"),
                rs.getString("delivery_state"),
                rs.getTimestamp("read_on") == null ? null : rs.getTimestamp("read_on").toInstant(),
                rs.getTimestamp("created_on").toInstant());
    }
}
