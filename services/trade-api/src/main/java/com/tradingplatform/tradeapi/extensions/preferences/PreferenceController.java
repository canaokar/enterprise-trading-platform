package com.tradingplatform.tradeapi.extensions.preferences;

import static com.tradingplatform.tradeapi.extensions.ExtensionAccess.requireAccount;

import com.tradingplatform.tradeapi.security.AuthenticatedUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/preferences/{accountId}")
public class PreferenceController {

    private final PreferenceService preferences;

    public PreferenceController(PreferenceService preferences) {
        this.preferences = preferences;
    }

    @GetMapping
    public PreferenceResponse get(
            @PathVariable long accountId,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return preferences.get(accountId);
    }

    @GetMapping("/notifications")
    public NotificationPreference getNotificationPreference(
            @PathVariable long accountId,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return new NotificationPreference(accountId, preferences.channelFor(accountId));
    }

    @PutMapping("/notifications")
    public PreferenceResponse updateNotifications(
            @PathVariable long accountId,
            @Valid @RequestBody NotificationPreferenceRequest request,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return preferences.updateChannel(accountId, request.channel());
    }

    @PutMapping("/display")
    public PreferenceResponse updateDisplay(
            @PathVariable long accountId,
            @Valid @RequestBody DisplayPreferenceRequest request,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return preferences.updateDisplay(accountId, request);
    }

    public record NotificationPreference(long accountId, String channel) {}
}
