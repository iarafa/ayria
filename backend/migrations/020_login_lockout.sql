-- AYRIA - Migration 020: Progressive Login Lockout (security anti-brute-force)
-- Data: 22/07/2026 — Rafael pediu bloqueio progressivo
-- Regras:
--   3 erros  → bloqueia 15 min
--   4 erros  → 30 min
--   5 erros  → 60 min
--   6+ erros → 24 horas
--   Depois disso → bloqueio total (precisa de suporte pra resetar)

CREATE TABLE IF NOT EXISTS login_lockouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier VARCHAR(255) NOT NULL,
    identifier_type VARCHAR(20) NOT NULL,
    failed_attempts INT NOT NULL DEFAULT 0,
    first_failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_until TIMESTAMPTZ,
    lockout_level INT NOT NULL DEFAULT 0,
    unlocked_by VARCHAR(255),
    unlocked_at TIMESTAMPTZ,
    unlock_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(identifier, identifier_type)
);

CREATE INDEX IF NOT EXISTS idx_login_lockouts_identifier ON login_lockouts(identifier, identifier_type);
CREATE INDEX IF NOT EXISTS idx_login_lockouts_locked_until ON login_lockouts(locked_until);

COMMENT ON TABLE login_lockouts IS 'Bloqueio progressivo anti brute-force: 3 tentativas = 15min, 4 = 30min, 5 = 60min, 6+ = 24h, 7+ = bloqueio total (só admin libera)';
COMMENT ON COLUMN login_lockouts.identifier IS 'Email do user OU IP de origem';
COMMENT ON COLUMN login_lockouts.identifier_type IS 'email (mais comum) ou ip (fallback se email não existe)';
COMMENT ON COLUMN login_lockouts.lockout_level IS '0=livre, 1=15min, 2=30min, 3=60min, 4=24h, 5=total (admin only)';
