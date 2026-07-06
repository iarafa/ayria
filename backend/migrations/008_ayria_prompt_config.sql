-- ============================================================
-- AYRIA - MIGRATION 008: System Prompt Config (admin ALMA)
-- Tabela editável pelo admin no dashboard.
-- Quando não há config ativo, chat.py usa o SYSTEM_PROMPT_TEMPLATE hardcoded.
-- ============================================================

CREATE TABLE IF NOT EXISTS ayria_prompt_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,             -- ex: 'system_prompt'
    content TEXT NOT NULL,                         -- template com {user_profile}, {rag_context}, {memories}
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,                              -- nota do admin: "versão com guardrails"
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ayria_prompt_active 
    ON ayria_prompt_config(is_active, updated_at DESC);