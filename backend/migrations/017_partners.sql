-- 017_partners.sql (20/07/2026 22:54)
-- Sistema de cupom/parceiro AYRIA
-- Cadastro de parceiros que indicam clientes com cupom

CREATE TABLE IF NOT EXISTS partners (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(20),
    document_type   VARCHAR(10),                     -- CPF | CNPJ
    document_number VARCHAR(20),
    pix_key         VARCHAR(255),                    -- chave PIX pra repasse
    commission_pct  NUMERIC(5,2),                    -- 🆕 20/07 22:21: OPCIONAL (comissão fica no cupom)
    notes           TEXT,
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partners_active ON partners(active);
CREATE INDEX IF NOT EXISTS idx_partners_email ON partners(email);

COMMENT ON TABLE partners IS 'Cadastro de parceiros que indicam clientes via cupom';
