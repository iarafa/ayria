-- Migration 014: Backfill is_verified para users existentes (07/07/2026)
--
-- PROBLEMA: Antes da migration 013, o sistema não exigia verificação de email.
-- Todos os 29+ users existentes têm is_verified=FALSE (default do init.sql).
-- Se a gente deixasse assim, todos ficariam BLOQUEADOS no login com 403.
--
-- SOLUÇÃO: Marcar como verificados todos os users que foram criados ANTES
-- da verificação ser obrigatória (ou seja, todos os que já existem).
--
-- Apenas users novos (criados depois desta migration) passam pelo fluxo
-- normal de verificação de email.
--
-- SEGURANÇA: Aplicar essa migration é seguro porque:
--   1. Esses users já acessaram o sistema antes (tinham login livre)
--   2. Não estamos "dando acesso" a ninguém novo — só mantendo o que já tinham
--   3. O admin pode reverter manualmente se necessário

UPDATE users
SET
    is_verified = TRUE,
    verified_at = COALESCE(verified_at, created_at)
WHERE is_verified = FALSE
  AND verification_token IS NULL;

COMMENT ON COLUMN users.is_verified IS
    'Se TRUE, pode logar. Novos users (a partir de 2026-07-07) recebem FALSE e precisam verificar email.';