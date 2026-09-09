CREATE TABLE IF NOT EXISTS customer_preferences (
    account_id BIGINT PRIMARY KEY REFERENCES accounts(id),
    notification_channel VARCHAR(20) NOT NULL DEFAULT 'IN_APP'
        CHECK (notification_channel IN ('IN_APP', 'EMAIL', 'SMS', 'PUSH')),
    display_currency CHAR(3) NOT NULL DEFAULT 'USD'
        CHECK (display_currency ~ '^[A-Z]{3}$'),
    theme VARCHAR(10) NOT NULL DEFAULT 'SYSTEM'
        CHECK (theme IN ('LIGHT', 'DARK', 'SYSTEM')),
    updated_on TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    source_event_id UUID NOT NULL UNIQUE,
    type VARCHAR(40) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    subject VARCHAR(160) NOT NULL,
    message VARCHAR(1000) NOT NULL,
    delivery_state VARCHAR(20) NOT NULL DEFAULT 'SENT'
        CHECK (delivery_state IN ('QUEUED', 'SENT', 'FAILED')),
    read_on TIMESTAMPTZ,
    created_on TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_notifications_account_created
    ON notifications(account_id, created_on DESC);

CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    name VARCHAR(80) NOT NULL,
    created_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (account_id, name)
);

CREATE TABLE IF NOT EXISTS watchlist_instruments (
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL REFERENCES instruments(symbol),
    added_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (watchlist_id, symbol)
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id UUID PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    symbol VARCHAR(20) NOT NULL REFERENCES instruments(symbol),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('ABOVE', 'BELOW')),
    threshold NUMERIC(18,2) NOT NULL CHECK (threshold > 0),
    status VARCHAR(12) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'TRIGGERED', 'DISABLED')),
    created_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_on TIMESTAMPTZ,
    triggered_price NUMERIC(18,2)
);

ALTER TABLE price_alerts
    ADD COLUMN IF NOT EXISTS last_observed_price NUMERIC(18,2);

CREATE INDEX IF NOT EXISTS ix_price_alerts_active_symbol
    ON price_alerts(symbol) WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS market_quotes (
    symbol VARCHAR(20) PRIMARY KEY REFERENCES instruments(symbol),
    price NUMERIC(18,4) NOT NULL CHECK (price > 0),
    currency CHAR(3) NOT NULL,
    quote_as_of TIMESTAMPTZ NOT NULL,
    stale BOOLEAN NOT NULL DEFAULT FALSE,
    market_state VARCHAR(12) NOT NULL DEFAULT 'unknown',
    feed_mode VARCHAR(10) NOT NULL DEFAULT 'fixture',
    received_on TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE market_quotes ADD COLUMN IF NOT EXISTS market_state VARCHAR(12) NOT NULL DEFAULT 'unknown';
ALTER TABLE market_quotes ADD COLUMN IF NOT EXISTS feed_mode VARCHAR(10) NOT NULL DEFAULT 'fixture';

CREATE TABLE IF NOT EXISTS extension_processed_events (
    consumer_name VARCHAR(40) NOT NULL,
    event_id UUID NOT NULL,
    processed_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (consumer_name, event_id)
);

INSERT INTO customer_preferences (account_id)
SELECT id FROM accounts
ON CONFLICT (account_id) DO NOTHING;

INSERT INTO watchlists (id, account_id, name) VALUES
    ('10000000-0000-4000-8000-000000000001', 1, 'Tech watch'),
    ('10000000-0000-4000-8000-000000000002', 2, 'Core holdings')
ON CONFLICT (account_id, name) DO NOTHING;

INSERT INTO watchlist_instruments (watchlist_id, symbol) VALUES
    ('10000000-0000-4000-8000-000000000001', 'AAPL'),
    ('10000000-0000-4000-8000-000000000001', 'NVDA'),
    ('10000000-0000-4000-8000-000000000002', 'GOOGL')
ON CONFLICT DO NOTHING;
