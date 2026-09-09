package com.tradingplatform.tradeapi.extensions;

import org.springframework.http.HttpStatus;

public class ExtensionException extends RuntimeException {

    private final HttpStatus status;
    private final String errorCode;

    public ExtensionException(HttpStatus status, String errorCode, String message) {
        super(message);
        this.status = status;
        this.errorCode = errorCode;
    }

    public HttpStatus status() {
        return status;
    }

    public String errorCode() {
        return errorCode;
    }
}
