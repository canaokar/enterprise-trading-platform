package com.tradingplatform.tradeapi.extensions.notifications;

import static com.tradingplatform.tradeapi.extensions.ExtensionAccess.requireAccount;

import com.tradingplatform.tradeapi.security.AuthenticatedUser;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/notifications/{accountId}")
public class NotificationController {

    private final NotificationService notifications;

    public NotificationController(NotificationService notifications) {
        this.notifications = notifications;
    }

    @GetMapping
    public List<NotificationResponse> list(
            @PathVariable long accountId,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return notifications.list(accountId);
    }

    @PostMapping("/read")
    public MarkReadResponse markRead(
            @PathVariable long accountId,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return new MarkReadResponse(notifications.markAllRead(accountId));
    }

    public record MarkReadResponse(int updated) {}
}
