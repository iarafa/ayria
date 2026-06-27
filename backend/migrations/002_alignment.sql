-- ============================================================
-- AYRIA - Migration v2 - Alinhamento com Checklist Oficial
-- ============================================================
-- Adiciona campos faltantes no schema inicial conforme
-- AYRIA_CHECKLIST_AUDITORIA oficial (Bloco 3):
--   - users.numerology_data (JSONB)
--   - users.onboarding_status
--   - users.role aceita 'SUPER_ADMIN'
--   - Renomeia attribute_definitions (separar do user_attributes)
-- ============================================================

-- ============================================================
-- 1. Adicionar campos em users
-- ============================================================
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS numerology_data JSONB,
    ADD COLUMN IF NOT EXISTS onboarding_status VARCHAR(50) DEFAULT 'pending'
        CHECK (onboarding_status IN ('pending', 'in_progress', 'completed', 'skipped'));

-- Atualizar CHECK constraint de role pra incluir SUPER_ADMIN
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check
    CHECK (role IN ('user', 'admin', 'SUPER_ADMIN'));

-- ============================================================
-- 2. Renomear user_attributes -> attribute_definitions
--    (catálogo de definições, separado dos valores)
-- ============================================================
ALTER TABLE IF EXISTS user_attributes RENAME TO attribute_definitions;

-- Atualizar referências no seed (já feito direto no init.sql)
-- Atualizar FK se houver
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'attribute_definitions'
    ) THEN
        RAISE NOTICE 'Tabela attribute_definitions existe - OK';
    END IF;
END $$;

-- ============================================================
-- 3. Renomear onboarding_questions -> onboarding_config
-- ============================================================
ALTER TABLE IF EXISTS onboarding_questions RENAME TO onboarding_config;

-- ============================================================
-- 4. Adicionar tabela user_attributes (valores por usuário)
--    Diferente de attribute_definitions (que é o catálogo)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_attributes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    attribute_definition_id UUID NOT NULL REFERENCES attribute_definitions(id) ON DELETE CASCADE,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, attribute_definition_id)
);

CREATE INDEX IF NOT EXISTS idx_user_attributes_user_id ON user_attributes(user_id);
CREATE INDEX IF NOT EXISTS idx_user_attributes_definition ON user_attributes(attribute_definition_id);

-- ============================================================
-- 5. Trigger de updated_at
-- ============================================================
CREATE TRIGGER update_user_attributes_updated_at BEFORE UPDATE ON user_attributes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 6. Atualizar seed do admin pra usar role SUPER_ADMIN
-- ============================================================
UPDATE users SET role = 'SUPER_ADMIN' WHERE email = 'admin@ayria.local';

-- ============================================================
-- FIM DA MIGRATION v2
-- ============================================================
