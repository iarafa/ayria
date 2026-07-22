-- 019_coupon_redemptions.sql (20/07/2026 22:54)
-- Log de uso de cupom + comissão gerada

CREATE TABLE IF NOT EXISTS coupon_redemptions (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id                UUID REFERENCES coupons(id) ON DELETE SET NULL,
    partner_id               UUID REFERENCES partners(id) ON DELETE SET NULL,
    user_id                  UUID REFERENCES users(id) ON DELETE SET NULL,
    stripe_invoice_id        VARCHAR(100),
    stripe_subscription_id   VARCHAR(100),
    
    plan_slug                VARCHAR(50) NOT NULL,
    original_amount_cents    INTEGER NOT NULL,
    discount_amount_cents    INTEGER NOT NULL,
    final_amount_cents       INTEGER NOT NULL,
    
    commission_pct           NUMERIC(5,2),
    commission_amount_cents  INTEGER,
    
    payout_status            VARCHAR(20) DEFAULT 'pending',     -- pending|paid|cancelled
    payout_at                TIMESTAMPTZ,
    payout_notes             TEXT,
    
    created_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_redemptions_coupon ON coupon_redemptions(coupon_id);
CREATE INDEX IF NOT EXISTS idx_redemptions_partner ON coupon_redemptions(partner_id);
CREATE INDEX IF NOT EXISTS idx_redemptions_user ON coupon_redemptions(user_id);
CREATE INDEX IF NOT EXISTS idx_redemptions_payout ON coupon_redemptions(payout_status);
CREATE INDEX IF NOT EXISTS idx_redemptions_created ON coupon_redemptions(created_at);
CREATE INDEX IF NOT EXISTS idx_redemptions_invoice ON coupon_redemptions(stripe_invoice_id);

COMMENT ON TABLE coupon_redemptions IS 'Log de uso de cupom + comissão gerada';
