-- Migration 013: Email Verification (07/07/2026)
-- Adiciona campos de token de verificação de email.
-- Após signup, user recebe email com link único. Só consegue logar após clicar.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS verification_token          VARCHAR(64),
  ADD COLUMN IF NOT EXISTS verification_token_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS verification_sent_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS verified_at                 TIMESTAMPTZ;

-- Índice único parcial: cada token é único APENAS enquanto existe
CREATE UNIQUE INDEX IF NOT EXISTS ux_users_verification_token
  ON users (verification_token)
  WHERE verification_token IS NOT NULL;

-- Índice pra queries de "tokens expirados pendentes" (cleanup futuro)
CREATE INDEX IF NOT EXISTS ix_users_verification_expires
  ON users (verification_token_expires_at)
  WHERE verification_token IS NOT NULL AND is_verified = false;

COMMENT ON COLUMN users.verification_token IS
  'Token único de verificação de email. Single-use, expira em 24h.';
COMMENT ON COLUMN users.verification_token_expires_at IS
  'Expiração do token (24h após geração).';
COMMENT ON COLUMN users.verification_sent_at IS
  'Última vez que email de verificação foi enviado (rate-limit).';
COMMENT ON COLUMN users.verified_at IS
  'Quando o user confirmou o email (NULL = ainda não verificado).';
