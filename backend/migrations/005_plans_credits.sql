-- AYRIA Migration 005: Planos Comerciais + Sistema de Créditos
-- Data: 2026-06-28

-- ============================================================
-- 1. Tabela: plans
-- ============================================================
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    credits INTEGER NOT NULL CHECK (credits >= 0),
    price_brl NUMERIC(10, 2) NOT NULL CHECK (price_brl >= 0),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plans_slug ON plans(slug);
CREATE INDEX IF NOT EXISTS idx_plans_active ON plans(active);

COMMENT ON TABLE plans IS 'Planos comerciais disponíveis (Básico, Intermediário, Premium)';
COMMENT ON COLUMN plans.slug IS 'Identificador único (basico, intermediario, premium)';
COMMENT ON COLUMN plans.credits IS 'Quantidade de créditos concedida ao escolher o plano';
COMMENT ON COLUMN plans.price_brl IS 'Preço em reais (referência — billing NÃO ativo nesta fase)';

-- Seed: 3 planos oficiais
INSERT INTO plans (name, slug, credits, price_brl, active)
VALUES
    ('Básico', 'basico', 100, 29.90, TRUE),
    ('Intermediário', 'intermediario', 500, 59.90, TRUE),
    ('Premium', 'premium', 1000, 99.90, TRUE)
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    credits = EXCLUDED.credits,
    price_brl = EXCLUDED.price_brl,
    active = EXCLUDED.active,
    updated_at = NOW();

-- ============================================================
-- 2. Tabela: credit_transactions (auditoria)
-- ============================================================
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,                   -- positivo=grant, negativo=uso
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT NOT NULL,
    reference_type VARCHAR(50),                -- ex: chat_message, admin_adjust
    reference_id VARCHAR(100),                 -- ex: message_id
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_tx_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_tx_type ON credit_transactions(type);
CREATE INDEX IF NOT EXISTS idx_credit_tx_created_at ON credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_tx_user_created ON credit_transactions(user_id, created_at DESC);

COMMENT ON TABLE credit_transactions IS 'Auditoria de toda movimentação de créditos';
COMMENT ON COLUMN credit_transactions.type IS 'grant_initial_plan | usage_chat_message | bonus_manual | adjustment_manual | recharge_future | refund_future';
COMMENT ON COLUMN credit_transactions.amount IS 'Positivo (concessão) ou negativo (consumo)';
COMMENT ON COLUMN credit_transactions.reference_type IS 'Tipo do recurso relacionado (chat_message, admin_adjust, etc)';

-- ============================================================
-- 3. ALTER users — campos de billing/plano
-- ============================================================
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS selected_plan_id UUID REFERENCES plans(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS credit_balance INTEGER NOT NULL DEFAULT 0 CHECK (credit_balance >= 0),
    ADD COLUMN IF NOT EXISTS credit_status VARCHAR(50) NOT NULL DEFAULT 'inactive',  -- inactive|active|exhausted|suspended
    ADD COLUMN IF NOT EXISTS plan_selected_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS billing_status VARCHAR(50) NOT NULL DEFAULT 'billing_not_enabled', -- billing_not_enabled|active|past_due|canceled|trialing
    ADD COLUMN IF NOT EXISTS billing_provider VARCHAR(50),                              -- stripe|asaas|mercadopago|null
    ADD COLUMN IF NOT EXISTS external_customer_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS external_subscription_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS next_renewal_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS credits_last_granted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_users_selected_plan_id ON users(selected_plan_id);
CREATE INDEX IF NOT EXISTS idx_users_credit_balance ON users(credit_balance);
CREATE INDEX IF NOT EXISTS idx_users_credit_status ON users(credit_status);

COMMENT ON COLUMN users.selected_plan_id IS 'FK pro plano escolhido no cadastro';
COMMENT ON COLUMN users.credit_balance IS 'Saldo atual de créditos (nunca pode ser negativo)';
COMMENT ON COLUMN users.credit_status IS 'inactive (sem plano) | active (com saldo) | exhausted (sem saldo) | suspended (admin bloqueou)';
COMMENT ON COLUMN users.billing_status IS 'billing_not_enabled (fase atual) | active | past_due | canceled | trialing';
COMMENT ON COLUMN users.billing_provider IS 'Provedor de pagamento futuro (Stripe, Asaas, MercadoPago)';

-- ============================================================
-- 4. Migração retroativa: usuários existentes → plano Básico
-- ============================================================
DO $$
DECLARE
    basico_id UUID;
    affected_count INTEGER;
BEGIN
    -- Pega ID do plano básico
    SELECT id INTO basico_id FROM plans WHERE slug = 'basico' LIMIT 1;

    IF basico_id IS NULL THEN
        RAISE EXCEPTION 'Plano básico não encontrado — seed falhou';
    END IF;

    -- Atribui plano básico a usuários sem plano (idempotente)
    UPDATE users
    SET
        selected_plan_id = basico_id,
        credit_balance = 100,
        credit_status = 'active',
        billing_status = 'billing_not_enabled',
        plan_selected_at = COALESCE(plan_selected_at, NOW()),
        credits_last_granted_at = COALESCE(credits_last_granted_at, NOW())
    WHERE selected_plan_id IS NULL;

    GET DIAGNOSTICS affected_count = ROW_COUNT;
    RAISE NOTICE 'Migração retroativa: % usuários atribuídos ao plano Básico', affected_count;

    -- Cria credit_transactions retroativos pra quem não tinha
    INSERT INTO credit_transactions (
        user_id, type, amount, balance_before, balance_after,
        description, reference_type
    )
    SELECT
        u.id,
        'grant_initial_plan',
        100,
        0,
        100,
        'Créditos iniciais concedidos retroativamente na migração do plano básico',
        'migration_005'
    FROM users u
    WHERE u.selected_plan_id = basico_id
      AND NOT EXISTS (
          SELECT 1 FROM credit_transactions ct
          WHERE ct.user_id = u.id
            AND ct.type = 'grant_initial_plan'
            AND ct.reference_type = 'migration_005'
      );

    GET DIAGNOSTICS affected_count = ROW_COUNT;
    RAISE NOTICE 'Transações retroativas criadas: %', affected_count;
END $$;
