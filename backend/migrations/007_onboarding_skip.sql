-- ============================================================
-- AYRIA - MIGRATION 007: Onboarding Skip / Pending Questions
-- Sistema 1: Pular / Responder depois (no onboarding inicial)
-- Sistema 2: Re-questionar em todo chat novo (pending_next_chat)
-- ============================================================

-- Adicionar colunas em user_attributes
ALTER TABLE user_attributes 
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'answered',
    ADD COLUMN IF NOT EXISTS skipped_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS snooze_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_asked_at TIMESTAMPTZ;

-- Status possíveis: 'answered' | 'skipped' | 'pending_next_chat' | 'pending_current_chat' | 'snoozed'
-- - answered: user respondeu, valor em `value`
-- - skipped: user pulou no onboarding, NÃO pergunta de novo
-- - pending_next_chat: user disse "responder depois", pergunta no PRÓXIMO chat
-- - pending_current_chat: pergunta ativa no chat atual (aguardando resposta)
-- - snoozed: user pediu pra adiar, lembra depois de snooze_until

-- Constraint
DO $$ BEGIN
    ALTER TABLE user_attributes 
        ADD CONSTRAINT user_attributes_status_check 
        CHECK (status IN ('answered', 'skipped', 'pending_next_chat', 'pending_current_chat', 'snoozed'));
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Índices pra busca rápida
CREATE INDEX IF NOT EXISTS idx_user_attributes_status ON user_attributes(status);
CREATE INDEX IF NOT EXISTS idx_user_attributes_snooze ON user_attributes(snooze_until) WHERE status = 'snoozed';
CREATE INDEX IF NOT EXISTS idx_user_attributes_pending ON user_attributes(user_id, status) 
    WHERE status IN ('pending_next_chat', 'pending_current_chat');

-- Retrocompatibilidade: status 'answered' para valores existentes
UPDATE user_attributes SET status = 'answered' WHERE status IS NULL OR status = '';