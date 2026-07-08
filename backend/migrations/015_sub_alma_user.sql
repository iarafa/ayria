-- ============================================================
-- AYRIA - MIGRATION 015: SUB-ALMA POR USUÁRIO (08/07/2026)
-- 2 tabelas novas:
--   1) user_alma             → alma INDIVIDUAL por user (modula constituição)
--   2) user_supervisor_notes → notas/análises manuais do admin sobre um user
-- Plano: 01_Memories/AYRIA_SUB_ALMA_PLANO_08072026.md
-- ============================================================

-- 1) SUB-ALMA DO USUÁRIO (camada 2 da alma)
CREATE TABLE IF NOT EXISTS user_alma (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version         INT NOT NULL,                         -- incrementado a cada regeneração
    status          TEXT NOT NULL DEFAULT 'draft',        -- 'draft' | 'active' | 'superseded' | 'archived'
    content         TEXT NOT NULL,                        -- markdown estruturado
    signals_used    JSONB NOT NULL DEFAULT '{}'::jsonb,   -- auditoria do que entrou
    trigger         TEXT NOT NULL,                        -- origem: onboarding_complete|admin_manual|periodic|...
    model_used      TEXT NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at     TIMESTAMPTZ,
    approved_by     UUID REFERENCES users(id),
    created_by      UUID REFERENCES users(id),            -- null se for auto
    expires_at      TIMESTAMPTZ,                          -- draft que expira
    manual_lock     JSONB NOT NULL DEFAULT '{}'::jsonb,   -- campos travados contra regeneração

    CONSTRAINT user_alma_status_check CHECK (status IN ('draft','active','superseded','archived'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_alma_user_version
    ON user_alma(user_id, version);

CREATE INDEX IF NOT EXISTS idx_user_alma_user_active
    ON user_alma(user_id) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_user_alma_user_draft
    ON user_alma(user_id) WHERE status = 'draft';


-- 2) NOTAS MANUAIS DO ADMIN SOBRE UM USER
CREATE TABLE IF NOT EXISTS user_supervisor_notes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admin_id        UUID NOT NULL REFERENCES users(id),
    kind            TEXT NOT NULL DEFAULT 'analysis',     -- 'analysis' | 'observation' | 'action'
    title           TEXT,                                  -- título curto opcional
    content         TEXT NOT NULL,                         -- markdown da análise
    conversation    JSONB NOT NULL DEFAULT '[]'::jsonb,    -- histórico do chat (user/assistant)
    model_used      TEXT NOT NULL,
    signals_used    JSONB NOT NULL DEFAULT '{}'::jsonb,    -- o que a IA leu pra gerar
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT user_supervisor_notes_kind_check CHECK (kind IN ('analysis','observation','action'))
);

CREATE INDEX IF NOT EXISTS idx_user_notes_user
    ON user_supervisor_notes(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_notes_admin
    ON user_supervisor_notes(admin_id, created_at DESC);