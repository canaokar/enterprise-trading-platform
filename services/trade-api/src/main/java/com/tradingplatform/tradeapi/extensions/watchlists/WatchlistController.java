package com.tradingplatform.tradeapi.extensions.watchlists;

import static com.tradingplatform.tradeapi.extensions.watchlists.WatchlistModels.*;

import com.tradingplatform.tradeapi.security.AuthenticatedUser;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class WatchlistController {

    private final WatchlistService watchlists;

    public WatchlistController(WatchlistService watchlists) {
        this.watchlists = watchlists;
    }

    @PostMapping("/watchlists")
    public WatchlistDetail create(
            @Valid @RequestBody CreateWatchlistRequest request,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        return watchlists.create(user.accountId(), request.name());
    }

    @GetMapping("/watchlists")
    public List<WatchlistSummary> list(
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        return watchlists.list(user.accountId());
    }

    @GetMapping("/watchlists/{id}")
    public WatchlistDetail get(
            @PathVariable UUID id,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        return watchlists.get(user.accountId(), id);
    }

    @PostMapping("/watchlists/{id}/instruments")
    public WatchlistDetail addInstrument(
            @PathVariable UUID id,
            @Valid @RequestBody AddInstrumentRequest request,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        return watchlists.addInstrument(user.accountId(), id, request.symbol());
    }

    @DeleteMapping("/watchlists/{id}/instruments/{symbol}")
    public void removeInstrument(
            @PathVariable UUID id,
            @PathVariable String symbol,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        watchlists.removeInstrument(user.accountId(), id, symbol);
    }

    @PostMapping("/alerts")
    public AlertResponse createAlert(
            @Valid @RequestBody CreateAlertRequest request,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        return watchlists.createAlert(user.accountId(), request);
    }

    @GetMapping("/alerts")
    public List<AlertResponse> alerts(
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        return watchlists.alerts(user.accountId());
    }

    @DeleteMapping("/alerts/{id}")
    public AlertResponse disableAlert(
            @PathVariable UUID id,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        return watchlists.disableAlert(user.accountId(), id);
    }
}
