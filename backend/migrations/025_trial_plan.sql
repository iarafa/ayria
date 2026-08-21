-- ============================================================
-- MIGRATION 025 — Plano Trial (20/08/2026)
--
-- Adiciona:
--   plans.trial_days (INT NULL) — quantos dias o plano dura
--     NULL = plano normal (sem expiracao por tempo), 7 = trial
--   users.trial_expires_at (TIMESTAMPTZ NULL) — quando o trial expira
--   Plan trial (slug unico, 30 creditos, 7 dias)
--   CreditTransaction.type aceita trial_expired
-- ============================================================

BEGIN;

-- 1. Coluna trial_days em plans
ALTER TABLE plans
    ADD COLUMN IF NOT EXISTS trial_days INT NULL;

COMMENT ON COLUMN plans.trial_days IS
    'Dias ate o plano expirar (NULL = sem expiracao por tempo, 7 = trial)';

-- 2. Coluna trial_expires_at em users
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN users.trial_expires_at IS
    'Quando o trial do user expira (NULL = não está em trial)';

-- 3. Cria plano trial (idempotente)
INSERT INTO plans (slug, name, credits, price_brl, active, trial_days)
VALUES ('trial', 'Trial Gratuito', 30, 0.00, true, 7)
ON CONFLICT (slug) DO NOTHING;

-- Garante trial_days = 7 se já existia sem esse campo
UPDATE plans
SET trial_days = 7
WHERE slug = 'trial' AND trial_days IS NULL;

-- 4. Comentário novo no enum de credit_transactions.type
COMMENT ON COLUMN credit_transactions.type IS
    'grant_initial_plan, usage_chat_message, bonus_manual, adjustment_manual, recharge_future, refund_future, grant_subscription_plan, trial_expired';

COMMIT;
