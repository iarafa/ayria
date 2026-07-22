-- 020_action_types_and_usage.sql (21/07/2026 11:18)
-- Modelo de cobrança variável por tipo de ação + rastreamento de uso de IA
-- Decisão Rafael: 1 crédito (chat simples), 2 (contexto grande), 5 (especiais como tarot/cartomancia/buzios)
-- Detecção por payload explícito (action_type), não por keyword.

-- ============================================================
-- 1. ACTION_TYPES (catálogo de tipos de ação com custo variável)
-- ============================================================
CREATE TABLE IF NOT EXISTS action_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,            -- 'chat_simples' | 'chat_profundo' | 'cartomancia' | 'tarot' | 'buzios'
    name VARCHAR(100) NOT NULL,                  -- exibido pro user no UI
    description TEXT,                            -- tooltip do user
    credits_cost INTEGER NOT NULL CHECK (credits_cost > 0),  -- quanto custa em créditos
    is_special BOOLEAN NOT NULL DEFAULT FALSE,   -- TRUE = serviço místico/premium
    category VARCHAR(50) DEFAULT 'chat',         -- 'chat' | 'mystic' | 'astrology' | 'divination'
    icon VARCHAR(50),                            -- emoji ou nome de ícone pra UI
    sort_order INTEGER DEFAULT 0,                -- ordem no seletor do chat
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_types_slug ON action_types(slug);
CREATE INDEX IF NOT EXISTS idx_action_types_active ON action_types(active);
CREATE INDEX IF NOT EXISTS idx_action_types_category ON action_types(category);

COMMENT ON TABLE action_types IS 'Catálogo de tipos de ação do chat com custo variável em créditos';
COMMENT ON COLUMN action_types.slug IS 'Identificador único usado no payload (action_type)';
COMMENT ON COLUMN action_types.credits_cost IS 'Quanto desconta do user por uso';
COMMENT ON COLUMN action_types.is_special IS 'TRUE = ação premium (cartomancia, tarot, buzios, etc)';

-- Trigger de updated_at
CREATE TRIGGER update_action_types_updated_at BEFORE UPDATE ON action_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Seed inicial — 5 tipos base (Rafael aprovou 21/07/2026)
INSERT INTO action_types (slug, name, description, credits_cost, is_special, category, icon, sort_order) VALUES
    ('chat_simples',     'Chat',                 'Pergunta rápida, bate-papo curto',                1, FALSE, 'chat',       '💬', 1),
    ('chat_profundo',    'Conversa Profunda',    'Diálogo com contexto emocional, reflexão longa', 2, FALSE, 'chat',       '🧠', 2),
    ('cartomancia',      'Cartomancia',          'Leitura de cartas com tiragem completa',          5, TRUE,  'divination', '🃏', 10),
    ('tarot',            'Tarô',                 'Jogada de tarô com interpretação detalhada',     5, TRUE,  'divination', '🔮', 11),
    ('buzios',           'Búzios',               'Jogada de búzios com mensagem dos orixás',       5, TRUE,  'divination', '🪙', 12)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- 2. AI_USAGE_LOG (rastreamento de tokens/custo por chamada de IA)
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action_type_id UUID REFERENCES action_types(id) ON DELETE SET NULL,
    chat_id UUID REFERENCES chats(id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    
    model VARCHAR(100) NOT NULL,                 -- 'MiniMax-M3', etc
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Custo calculado em USD (valores de MiniMax pay-as-you-go, M3 Standard 50% off)
    cost_input_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
    cost_output_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
    cost_total_usd NUMERIC(12,6) NOT NULL DEFAULT 0,
    
    -- Performance
    response_ms INTEGER,                         -- latency
    status VARCHAR(20) NOT NULL DEFAULT 'success',  -- success | error | rate_limited
    error_message TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_user_id ON ai_usage_log(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_usage_created_at ON ai_usage_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_action_type ON ai_usage_log(action_type_id);
CREATE INDEX IF NOT EXISTS idx_ai_usage_user_created ON ai_usage_log(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_usage_status ON ai_usage_log(status);
CREATE INDEX IF NOT EXISTS idx_ai_usage_model ON ai_usage_log(model);

COMMENT ON TABLE ai_usage_log IS 'Log de cada chamada de IA com tokens consumidos e custo';
COMMENT ON COLUMN ai_usage_log.cost_total_usd IS 'Calculado em runtime baseado nos rates do model';

-- ============================================================
-- 3. ALTER MESSAGES — referenciar action_type_id
-- ============================================================
ALTER TABLE messages 
    ADD COLUMN IF NOT EXISTS action_type_id UUID REFERENCES action_types(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_messages_action_type ON messages(action_type_id);

COMMENT ON COLUMN messages.action_type_id IS 'Qual tipo de ação gerou esta mensagem (rastreia custo variável)';