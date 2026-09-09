package com.tradingplatform.tradeapi.extensions.portfolio;

import static com.tradingplatform.tradeapi.extensions.ExtensionAccess.requireAccount;
import static com.tradingplatform.tradeapi.extensions.portfolio.PortfolioModels.*;

import com.tradingplatform.tradeapi.extensions.ExtensionException;
import com.tradingplatform.tradeapi.security.AuthenticatedUser;
import java.time.LocalDate;
import java.util.List;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/portfolio/{accountId}")
public class PortfolioController {

    private final PortfolioService portfolio;

    public PortfolioController(PortfolioService portfolio) {
        this.portfolio = portfolio;
    }

    @GetMapping
    public PortfolioSummary summary(
            @PathVariable long accountId,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return portfolio.summary(accountId);
    }

    @GetMapping("/positions")
    public List<PricedPosition> positions(
            @PathVariable long accountId,
            @RequestParam(required = false) String symbol,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        return portfolio.positions(accountId, symbol);
    }

    @GetMapping("/pnl")
    public PnlResponse pnl(
            @PathVariable long accountId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(defaultValue = "false") boolean bySymbol,
            @RequestAttribute(AuthenticatedUser.ATTRIBUTE) AuthenticatedUser user) {
        requireAccount(user, accountId);
        if (from != null && to != null && from.isAfter(to)) {
            throw new ExtensionException(HttpStatus.UNPROCESSABLE_ENTITY, "VAL-422", "Invalid date range");
        }
        return portfolio.pnl(accountId, from, to, bySymbol);
    }
}
