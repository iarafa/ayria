-- 018_coupons.sql (20/07/2026 22:54)
-- Cupons de desconto AYRIA
-- Espelho do Stripe + link com partner

CREATE TABLE IF NOT EXISTS coupons (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code                  VARCHAR(50) UNIQUE NOT NULL,
    stripe_coupon_id      VARCHAR(100) UNIQUE NOT NULL,
    partner_id            UUID REFERENCES partners(id) ON DELETE SET NULL,
    
    name                  VARCHAR(200),
    discount_type         VARCHAR(10) NOT NULL,                  -- 'percent' | 'fixed'
    discount_value        NUMERIC(10,2) NOT NULL,
    
    applicable_plan_slug  VARCHAR(50) NOT NULL,                  -- 🆕 20/07 22:21: vinculado a 1 plano
    duration_months       INTEGER DEFAULT 1,                     -- 🆕 20/07 22:21: 1, 3, 6, 12 meses
    commission_pct        NUMERIC(5,2) NOT NULL,                 -- 🆕 20/07 22:21: comissão POR CUPOM
    
    max_redemptions       INTEGER,                              -- NULL = ilimitado
    current_redemptions   INTEGER DEFAULT 0,
    expires_at            TIMESTAMPTZ,                          -- NULL = sem expiração
    
    active                BOOLEAN DEFAULT TRUE,
    created_by            UUID REFERENCES users(id),
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(code);
CREATE INDEX IF NOT EXISTS idx_coupons_active ON coupons(active);
CREATE INDEX IF NOT EXISTS idx_coupons_partner ON coupons(partner_id);
CREATE INDEX IF NOT EXISTS idx_coupons_stripe_id ON coupons(stripe_coupon_id);
CREATE INDEX IF NOT EXISTS idx_coupons_plan ON coupons(applicable_plan_slug);

COMMENT ON TABLE coupons IS 'Cupom de desconto (espelho Stripe + dados AYRIA)';
