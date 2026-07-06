-- ============================================================
-- AYRIA - MIGRATION 009: Arquitetura Cognitiva Modular
-- Atualiza tabela ayria_prompt_config para suportar:
-- 1. Constituição base (key='constituicao_base')
-- 2. Módulos especializados (key='modulo_<nome>')
-- ============================================================

-- Sem mudança de schema — a tabela já é flexível (key única, content text, is_active bool)
-- Mas adicionamos um índice composto pra queries comuns (apenas ativos por key)
CREATE UNIQUE INDEX IF NOT EXISTS idx_ayria_prompt_active_key
    ON ayria_prompt_config(key) WHERE is_active = true;

-- Comentário: a partir dessa migration, as chaves usadas são:
-- - 'constituicao_base' → sempre carregada
-- - 'modulo_numerologia', 'modulo_astrologia', etc → sob demanda
-- Backwards compatible: configs antigas (com key='system_prompt') seguem funcionando.