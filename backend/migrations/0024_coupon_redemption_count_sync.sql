-- 26/07/2026 22:25 — Trigger de sincronia: mantém coupons.current_redemptions
-- em sync com a contagem real de coupon_redemptions, independente da origem.

CREATE OR REPLACE FUNCTION maintain_coupon_redemption_count() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE coupons SET current_redemptions = COALESCE(current_redemptions, 0) + 1
    WHERE id = NEW.coupon_id;
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    UPDATE coupons SET current_redemptions = GREATEST(COALESCE(current_redemptions, 0) - 1, 0)
    WHERE id = OLD.coupon_id;
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_maintain_coupon_redemption_count ON coupon_redemptions;
CREATE TRIGGER trg_maintain_coupon_redemption_count
AFTER INSERT OR DELETE ON coupon_redemptions
FOR EACH ROW EXECUTE FUNCTION maintain_coupon_redemption_count();
