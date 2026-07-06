-- ============================================================
-- Migration 010: risco em 3 níveis
-- Adiciona coluna risk_sublevel (1, 2, 3) em supervisor_analysis
-- pra refletir os 3 níveis do prompt oficial SEGURANÇA E CRISE
--
-- N1 (1) = Nível 1: suicídio / homicídio / autolesão  (URGENCIA)
-- N2 (2) = Nível 2: crimes, violência doméstica       (ATENCAO)
-- N3 (3) = Nível 3: vícios graves, compulsões        (ATENCAO)
-- ============================================================

ALTER TABLE supervisor_analysis
ADD COLUMN IF NOT EXISTS risk_sublevel SMALLINT;

-- Constraint: só 1, 2, 3 ou NULL
ALTER TABLE supervisor_analysis
ADD CONSTRAINT supervisor_risk_sublevel_check
CHECK (risk_sublevel IS NULL OR risk_sublevel IN (1, 2, 3));

-- Índice pra queries de contagem
CREATE INDEX IF NOT EXISTS idx_supervisor_sublevel
ON supervisor_analysis(risk_sublevel, created_at DESC);
