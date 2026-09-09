package com.tradingplatform.tradeapi.extensions.market;

import static com.tradingplatform.tradeapi.extensions.market.MarketQuoteModels.MarketQuoteResponse;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/market/quotes")
public class MarketQuoteController {

    private final MarketQuoteService quotes;

    public MarketQuoteController(MarketQuoteService quotes) {
        this.quotes = quotes;
    }

    @GetMapping
    public List<MarketQuoteResponse> list() {
        return quotes.list();
    }

    @GetMapping("/{symbol}")
    public MarketQuoteResponse get(@PathVariable String symbol) {
        return quotes.get(symbol);
    }
}
