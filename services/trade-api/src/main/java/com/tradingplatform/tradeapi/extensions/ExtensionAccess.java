package com.tradingplatform.tradeapi.extensions;

import com.tradingplatform.tradeapi.security.AccountAccessDeniedException;
import com.tradingplatform.tradeapi.security.AuthenticatedUser;

public final class ExtensionAccess {

    private ExtensionAccess() {}

    public static void requireAccount(AuthenticatedUser user, Long accountId) {
        if (!user.canAccess(accountId)) {
            throw new AccountAccessDeniedException(user.subject(), accountId);
        }
    }
}
