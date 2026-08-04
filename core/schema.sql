-- ============================================================================
-- Astro Palmistry — canonical PostgreSQL schema
-- Sized for 1 lakh+ registered users. Run once; safe to re-run.
--
-- Design notes are inline. The short version:
--   * money and access are separated: `orders` records what was PAID,
--     `entitlements` records what the user may SEE. One row per grant, so a
--     refund revokes access without deleting payment history.
--   * generated reports live in object storage; the DB stores keys only.
--   * `precomputes` caches the expensive ephemeris pass by birth-data hash —
--     the single biggest scalability win in the system.
--   * `jobs` and `payment_events` are partitioned by month and pruned.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;        -- case-insensitive email

-- ---------------------------------------------------------------- identity ---
CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_sub     TEXT UNIQUE,                -- NULL until they use Google
    email          CITEXT UNIQUE NOT NULL,
    name           TEXT,
    picture        TEXT,
    phone          TEXT,
    locale         TEXT NOT NULL DEFAULT 'en',
    status         TEXT NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active', 'blocked', 'deleted')),
    credits        INTEGER NOT NULL DEFAULT 0 CHECK (credits >= 0),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at   TIMESTAMPTZ,
    deleted_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_users_created ON users (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_users_last_seen ON users (last_seen_at DESC NULLS LAST);

-- Sessions are stored so we can revoke. The cookie/bearer carries a random
-- token; only its hash is kept here (a DB leak must not mint sessions).
CREATE TABLE IF NOT EXISTS sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   TEXT NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked_at   TIMESTAMPTZ,
    ip           INET,
    user_agent   TEXT
);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON sessions (user_id, expires_at DESC);

-- ------------------------------------------------------------------ charts ---
-- chart_hash = sha256(dob|tob|lat|lon|tz). Deliberately NOT user-scoped: two
-- people born at the same moment and place share one precompute.
CREATE TABLE IF NOT EXISTS charts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label        TEXT,                          -- "me", "my daughter", …
    person_name  TEXT,
    dob          DATE NOT NULL,
    tob          TIME NOT NULL,
    tz_offset    NUMERIC(4,2) NOT NULL,
    lat          NUMERIC(9,6) NOT NULL,
    lon          NUMERIC(9,6) NOT NULL,
    place        TEXT,
    gender       SMALLINT NOT NULL DEFAULT 0,
    chart_hash   TEXT NOT NULL,
    is_primary   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_charts_user ON charts (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_charts_hash ON charts (chart_hash);
CREATE UNIQUE INDEX IF NOT EXISTS ux_charts_user_hash ON charts (user_id, chart_hash);

-- The cache. A full precompute is ~0.5-3 s of ephemeris work and every other
-- feature (daily, muhurat, timing, report) needs it. Store once, reuse forever
-- unless the engine version changes.
CREATE TABLE IF NOT EXISTS precomputes (
    chart_hash     TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    payload        JSONB,                       -- small charts inline …
    payload_key    TEXT,                        -- … large ones in object storage
    bytes          INTEGER,
    hits           BIGINT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (chart_hash, engine_version)
);
CREATE INDEX IF NOT EXISTS ix_precomputes_lru ON precomputes (last_used_at);

-- ------------------------------------------------------------------- money ---
CREATE TABLE IF NOT EXISTS orders (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_id          TEXT NOT NULL UNIQUE,     -- OD-XXXXXXXX, shown to users
    user_id            UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    item               TEXT NOT NULL,            -- full_report | horary | subscription | …
    ref_id             UUID,                     -- the report/chart it unlocks
    amount_paise       INTEGER NOT NULL CHECK (amount_paise >= 0),
    currency           TEXT NOT NULL DEFAULT 'INR',
    status             TEXT NOT NULL DEFAULT 'created'
                       CHECK (status IN ('created','pending','paid','failed','refunded')),
    gateway            TEXT,                     -- razorpay | cashfree | …
    gateway_order_id   TEXT,
    gateway_payment_id TEXT,
    idempotency_key    TEXT UNIQUE,              -- retry-safe order creation
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at            TIMESTAMPTZ,
    refunded_at        TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_orders_user ON orders (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders (status) WHERE status IN ('created','pending');
CREATE INDEX IF NOT EXISTS ix_orders_gateway ON orders (gateway_order_id);

-- Every webhook, verified or not. This is the evidence trail for a dispute or
-- a chargeback, so nothing is ever deleted from here.
CREATE TABLE IF NOT EXISTS payment_events (
    id            BIGSERIAL,
    order_id      UUID REFERENCES orders(id) ON DELETE SET NULL,
    gateway       TEXT,
    event_type    TEXT,
    signature_ok  BOOLEAN NOT NULL DEFAULT FALSE,
    payload       JSONB NOT NULL,
    received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, received_at)
) PARTITION BY RANGE (received_at);

-- What the user may SEE. Separate from orders so a subscription, a promo and a
-- purchase all grant access the same way, and a refund revokes it.
CREATE TABLE IF NOT EXISTS entitlements (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item        TEXT NOT NULL,
    ref_id      UUID,                            -- NULL = account-wide (subscription)
    source      TEXT NOT NULL CHECK (source IN ('order','subscription','promo','support')),
    order_id    UUID REFERENCES orders(id) ON DELETE SET NULL,
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ,                     -- NULL = perpetual
    revoked_at  TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_entitlement_live
    ON entitlements (user_id, item, COALESCE(ref_id, '00000000-0000-0000-0000-000000000000'::uuid))
    WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_entitlements_lookup ON entitlements (user_id, item, ref_id);

CREATE TABLE IF NOT EXISTS subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan                TEXT NOT NULL DEFAULT 'daily_monthly',
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','past_due','cancelled','expired')),
    current_period_end  TIMESTAMPTZ NOT NULL,
    cancel_at           TIMESTAMPTZ,
    gateway_sub_id      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_subs_user ON subscriptions (user_id, status);
CREATE INDEX IF NOT EXISTS ix_subs_renewal ON subscriptions (current_period_end)
    WHERE status = 'active';

-- Wallet as an append-only ledger. The balance on `users` is a cache of this;
-- the ledger is the truth, so support can always explain a balance.
CREATE TABLE IF NOT EXISTS credit_ledger (
    id             BIGSERIAL PRIMARY KEY,
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delta          INTEGER NOT NULL,
    reason         TEXT NOT NULL,
    ref_id         UUID,
    balance_after  INTEGER NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_credits_user ON credit_ledger (user_id, created_at DESC);

-- Free-tier metering (3 free daily readings, 3 horary a month on a plan…).
CREATE TABLE IF NOT EXISTS usage_counters (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,
    period     TEXT NOT NULL,                    -- 'all' | '2026-08' | '2026-08-04'
    used       INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, kind, period)
);

-- ----------------------------------------------------------------- reports ---
CREATE TABLE IF NOT EXISTS reports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chart_id     UUID REFERENCES charts(id) ON DELETE SET NULL,
    kind         TEXT NOT NULL,
    paid         BOOLEAN NOT NULL DEFAULT FALSE,
    free_key     TEXT,                            -- object-storage keys
    paid_key     TEXT,
    meta         JSONB NOT NULL DEFAULT '{}',
    engine_version TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ                      -- for retention sweeps
);
CREATE INDEX IF NOT EXISTS ix_reports_user ON reports (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_reports_kind ON reports (kind, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_reports_expiry ON reports (expires_at) WHERE expires_at IS NOT NULL;

-- -------------------------------------------------------------------- jobs ---
-- Redis runs the live queue; this table is the durable record (history,
-- support, retries after a crash). Partitioned monthly, pruned at 90 days.
CREATE TABLE IF NOT EXISTS jobs (
    id           UUID NOT NULL DEFAULT gen_random_uuid(),
    public_id    TEXT NOT NULL,
    user_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    kind         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued','processing','done','failed','cancelled')),
    priority     SMALLINT NOT NULL DEFAULT 5,     -- lower runs first
    attempts     SMALLINT NOT NULL DEFAULT 0,
    chart_id     UUID,
    report_id    UUID,
    payload      JSONB,
    error        TEXT,
    worker_id    TEXT,
    duration_ms  INTEGER,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);
CREATE INDEX IF NOT EXISTS ix_jobs_public ON jobs (public_id);
CREATE INDEX IF NOT EXISTS ix_jobs_user ON jobs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_jobs_live ON jobs (status, kind) WHERE status IN ('queued','processing');

-- ------------------------------------------------------------------- misc ----
CREATE TABLE IF NOT EXISTS enquiries (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    name       TEXT, phone TEXT, email CITEXT, message TEXT,
    status     TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_enquiries_status ON enquiries (status, created_at DESC);

CREATE TABLE IF NOT EXISTS waitlist (
    email      CITEXT PRIMARY KEY,
    topic      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Promo codes. `redeemed_count` is a cache of promo_redemptions; the CHECK is
-- the cap's last line of defence, so even a hand-written UPDATE cannot
-- over-issue. The redemption path guards in its WHERE clause instead of
-- relying on this, because a CHECK violation is an error, not a refusal.
CREATE TABLE IF NOT EXISTS promo_codes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            TEXT UNIQUE NOT NULL,
    item            TEXT NOT NULL DEFAULT 'bundle_all',
    max_redemptions INTEGER NOT NULL CHECK (max_redemptions > 0),
    redeemed_count  INTEGER NOT NULL DEFAULT 0 CHECK (redeemed_count >= 0),
    active          SMALLINT NOT NULL DEFAULT 1,
    expires_at      TIMESTAMPTZ,
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_promo_cap CHECK (redeemed_count <= max_redemptions)
);

CREATE TABLE IF NOT EXISTS promo_redemptions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code_id     UUID NOT NULL REFERENCES promo_codes(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item        TEXT NOT NULL,
    redeemed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- One per person, decided by the database rather than by a SELECT that can be
-- overtaken under load.
CREATE UNIQUE INDEX IF NOT EXISTS ux_promo_once
    ON promo_redemptions (code_id, user_id);
CREATE INDEX IF NOT EXISTS ix_promo_red_user ON promo_redemptions (user_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id         BIGSERIAL PRIMARY KEY,
    actor      TEXT,
    action     TEXT NOT NULL,
    subject    TEXT,
    detail     JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_created ON audit_log (created_at DESC);

-- --------------------------------------------------------------- partitions --
-- Create the current and next month up front; extend_partitions() (called by
-- the API on startup and by cron) keeps rolling them forward.
CREATE OR REPLACE FUNCTION ensure_month_partition(parent TEXT, month DATE)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    part TEXT := parent || '_' || to_char(month, 'YYYYMM');
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = part) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
            part, parent, month, (month + INTERVAL '1 month')::date);
    END IF;
END $$;

CREATE OR REPLACE FUNCTION extend_partitions() RETURNS void LANGUAGE plpgsql AS $$
DECLARE m DATE := date_trunc('month', now())::date;
BEGIN
    PERFORM ensure_month_partition('jobs', m);
    PERFORM ensure_month_partition('jobs', (m + INTERVAL '1 month')::date);
    PERFORM ensure_month_partition('payment_events', m);
    PERFORM ensure_month_partition('payment_events', (m + INTERVAL '1 month')::date);
END $$;

SELECT extend_partitions();

-- ------------------------------------------------------------------ views ----
CREATE OR REPLACE VIEW v_active_entitlements AS
SELECT user_id, item, ref_id, source, expires_at
FROM entitlements
WHERE revoked_at IS NULL
  AND (expires_at IS NULL OR expires_at > now());

CREATE OR REPLACE VIEW v_daily_revenue AS
SELECT date_trunc('day', paid_at) AS day,
       item,
       count(*)                   AS orders,
       sum(amount_paise) / 100.0  AS rupees
FROM orders
WHERE status = 'paid'
GROUP BY 1, 2
ORDER BY 1 DESC;
