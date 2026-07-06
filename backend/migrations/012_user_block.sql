-- Migration 012: User Block (admin controla acesso)
-- Bloqueio temporário ou permanente: blocked_until + block_reason + blocked_by + blocked_at
-- Quando blocked_until == NULL E blocked_at != NULL → bloqueio permanente

ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_until TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at     TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_by     UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS block_reason   TEXT;

-- Indice pra queries de "está bloqueado agora?" (basta partial index)
CREATE INDEX IF NOT EXISTS ix_users_blocked_until
  ON users (blocked_until)
  WHERE blocked_at IS NOT NULL;
