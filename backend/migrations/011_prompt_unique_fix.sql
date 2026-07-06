-- Migration 011: fixa unique constraint errada no ayria_prompt_config
-- Permite múltiplas entradas por key (uma ativa + N históricas)
DROP INDEX IF EXISTS ix_ayria_prompt_config_key;
