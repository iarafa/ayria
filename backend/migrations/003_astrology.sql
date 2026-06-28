-- AYRIA Migration 003: Astrologia no perfil
-- Adiciona coluna astrology_data (JSONB) na tabela users

ALTER TABLE users
ADD COLUMN IF NOT EXISTS astrology_data JSONB;

-- Adiciona coluna profile_status pra controlar fluxo "criando seu perfil..."
ALTER TABLE users
ADD COLUMN IF NOT EXISTS profile_status VARCHAR(50) DEFAULT 'pending';

-- Valores possíveis:
-- 'pending' = user fez signup mas perfil ainda não calculado
-- 'calculating' = cálculo em andamento (background)
-- 'ready' = perfil completo (numerologia + astrologia salvos)
-- 'failed' = erro no cálculo

CREATE INDEX IF NOT EXISTS idx_users_profile_status ON users(profile_status);

-- Documentação
COMMENT ON COLUMN users.astrology_data IS 'Mapa astral completo: sol, lua, ascendente, planetas, casas, diretrizes';
COMMENT ON COLUMN users.profile_status IS 'pending | calculating | ready | failed';
COMMENT ON COLUMN users.numerology_data IS 'Mapa numerológico completo: caminho de vida, expressão, alma, personalidade';