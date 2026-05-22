-- Postgres schema for my-flight-tracker (Neon)

CREATE TABLE IF NOT EXISTS ingest_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR NOT NULL,
    error TEXT,
    records_count INTEGER,
    provider VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id BIGINT PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    provider VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    notes VARCHAR
);

CREATE TABLE IF NOT EXISTS offers (
    offer_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES scrape_runs(run_id),
    direction VARCHAR NOT NULL,
    departure_date DATE NOT NULL,
    departure_at TIMESTAMPTZ NOT NULL,
    arrival_at TIMESTAMPTZ NOT NULL,
    carrier_code VARCHAR NOT NULL,
    flight_number VARCHAR NOT NULL,
    duration_minutes INTEGER NOT NULL,
    stops INTEGER NOT NULL,
    price_total_usd DOUBLE PRECISION NOT NULL,
    adults INTEGER NOT NULL,
    cabin VARCHAR NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    external_id VARCHAR NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_offers_run_direction ON offers(run_id, direction);
CREATE INDEX IF NOT EXISTS idx_offers_departure ON offers(direction, departure_date);

CREATE TABLE IF NOT EXISTS leg_observations (
    id BIGSERIAL PRIMARY KEY,
    ingest_run_id BIGINT NOT NULL REFERENCES ingest_runs(id),
    route VARCHAR NOT NULL,
    outbound_date DATE NOT NULL,
    return_date DATE,
    provider VARCHAR NOT NULL,
    observed_at_bucket TIMESTAMPTZ NOT NULL,
    direction VARCHAR NOT NULL,
    departure_at TIMESTAMPTZ NOT NULL,
    arrival_at TIMESTAMPTZ NOT NULL,
    carrier_code VARCHAR NOT NULL,
    flight_number VARCHAR NOT NULL,
    duration_minutes INTEGER NOT NULL,
    stops INTEGER NOT NULL,
    price_total_usd DOUBLE PRECISION NOT NULL,
    adults INTEGER NOT NULL,
    cabin VARCHAR NOT NULL,
    external_id VARCHAR NOT NULL,
    UNIQUE (route, outbound_date, return_date, provider, observed_at_bucket)
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    flight_date DATE,
    return_date DATE,
    price DOUBLE PRECISION,
    reason VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'new',
    ingest_run_id BIGINT,
    route VARCHAR,
    carrier_code VARCHAR,
    flight_number VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_reason ON alerts(reason);

CREATE TABLE IF NOT EXISTS notification_state (
    key VARCHAR PRIMARY KEY,
    last_sent_at TIMESTAMPTZ NOT NULL
);
