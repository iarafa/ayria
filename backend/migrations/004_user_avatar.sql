-- ============================================================
-- Migration 004: Adicionar coluna avatar_url aos users
-- ============================================================

ALTER TABLE users
ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);

COMMENT ON COLUMN users.avatar_url IS 'URL pública da foto do usuário (Azure Blob Storage ou CDN)';