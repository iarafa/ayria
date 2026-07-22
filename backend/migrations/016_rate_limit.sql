-- ============================================================
-- 016_rate_limit.sql (19/07/2026)
-- Dashboard de Rate Limit + Blacklist para o Admin
--
-- Tabelas:
--   rate_limit_events: log append-only de TODA tentativa (success ou fail)
--   ip_blacklist: bloqueio permanente por IP (admin gerencia)
-- ============================================================

-- 1) Eventos de rate limit
CREATE TABLE IF NOT EXISTS rate_limit_events (
    id              BIGSERIAL PRIMARY KEY,
    ip              INET NOT NULL,
    endpoint        VARCHAR(64) NOT NULL,        -- '/auth/login', '/auth/register' etc
    success         BOOLEAN NOT NULL,            -- TRUE = sucesso (passou), FALSE = falhou
    email_attempted VARCHAR(255),               -- email digitado (NULL se não forneceu)
    user_agent      TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rle_ip_time
    ON rate_limit_events(ip, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_rle_occurred
    ON rate_limit_events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_rle_endpoint_fail
    ON rate_limit_events(endpoint, occurred_at DESC) WHERE success = FALSE;
CREATE INDEX IF NOT EXISTS idx_rle_email_fail
    ON rate_limit_events(email_attempted, occurred_at DESC) WHERE success = FALSE;


-- 2) Blacklist permanente (admin controla)
CREATE TABLE IF NOT EXISTS ip_blacklist (
    ip              INET PRIMARY KEY,
    reason          TEXT,
    added_by        VARCHAR(255) NOT NULL,        -- email do admin
    added_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ                   -- NULL = permanente
);

CREATE INDEX IF NOT EXISTS idx_blacklist_expires
    ON ip_blacklist(expires_at) WHERE expires_at IS NOT NULL;
