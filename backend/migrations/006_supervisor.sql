-- ============================================================
-- AYRIA - MIGRATION 006: Sistema Supervisor
-- Análise de risco em mensagens: NORMAL | ATENÇÃO | URGÊNCIA
-- ============================================================

-- Análise por mensagem (gerada async após user mandar msg)
CREATE TABLE IF NOT EXISTS supervisor_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,

    -- Classificação
    level VARCHAR(20) NOT NULL CHECK (level IN ('NORMAL', 'ATENCAO', 'URGENCIA')),
    score NUMERIC(4, 3) NOT NULL DEFAULT 0.0,  -- 0.000 a 1.000
    reason TEXT,                                  -- por que foi classificado assim
    recommended_action TEXT,                      -- ação sugerida (CVV, ligar familiar, etc)
    signals JSONB DEFAULT '[]'::jsonb,           -- array de strings com sinais detectados
    context_used JSONB DEFAULT '{}'::jsonb,      -- contexto adicional (numerologia, astro, etc)

    -- Auditoria
    model_used VARCHAR(50) DEFAULT 'MiniMax-M3',
    analysis_duration_ms INT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_supervisor_user_id ON supervisor_analysis(user_id);
CREATE INDEX IF NOT EXISTS idx_supervisor_chat_id ON supervisor_analysis(chat_id);
CREATE INDEX IF NOT EXISTS idx_supervisor_level ON supervisor_analysis(level);
CREATE INDEX IF NOT EXISTS idx_supervisor_created_at ON supervisor_analysis(created_at DESC);

-- Alertas críticos (URGÊNCIA sempre; ATENÇÃO só se persistir)
CREATE TABLE IF NOT EXISTS supervisor_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES supervisor_analysis(id) ON DELETE SET NULL,

    level VARCHAR(20) NOT NULL CHECK (level IN ('ATENCAO', 'URGENCIA')),
    status VARCHAR(20) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'acknowledged', 'resolved', 'dismissed')),
    title TEXT NOT NULL,
    message TEXT,
    message_excerpt TEXT,            -- trecho da msg que disparou

    -- Quem tratou
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,

    -- Contadores
    occurrences INT DEFAULT 1,       -- quantas análises iguais seguidas
    last_occurrence_at TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON supervisor_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON supervisor_alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_level ON supervisor_alerts(level);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON supervisor_alerts(created_at DESC);

-- Resumo diário por user (pra reduzir queries)
CREATE TABLE IF NOT EXISTS supervisor_daily_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    summary_date DATE NOT NULL,
    total_messages INT DEFAULT 0,
    normal_count INT DEFAULT 0,
    atencao_count INT DEFAULT 0,
    urgencia_count INT DEFAULT 0,
    current_level VARCHAR(20) DEFAULT 'NORMAL',  -- pior nível do dia
    max_score NUMERIC(4, 3) DEFAULT 0.0,
    UNIQUE(user_id, summary_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_user ON supervisor_daily_summary(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_date ON supervisor_daily_summary(summary_date DESC);

-- Trigger: atualiza updated_at em alerts
CREATE OR REPLACE FUNCTION update_supervisor_alerts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_supervisor_alerts_updated_at ON supervisor_alerts;
CREATE TRIGGER trg_supervisor_alerts_updated_at
    BEFORE UPDATE ON supervisor_alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_supervisor_alerts_updated_at();
