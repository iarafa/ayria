-- ============================================================
-- AYRIA - Schema Inicial do Banco de Dados PostgreSQL
-- ============================================================
-- Suporta: usuários, perfis dinâmicos, mensagens, onboarding,
--          atributos cadastráveis, controle admin
-- ============================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. USERS (Registro e Auth)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'SUPER_ADMIN')),
    numerology_data JSONB,
    onboarding_status VARCHAR(50) DEFAULT 'pending' CHECK (onboarding_status IN ('pending', 'in_progress', 'completed', 'skipped')),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================
-- 2. USER_PROFILES (Atributos dinâmicos via JSONB)
-- ============================================================
-- Cada usuário tem UM perfil. Atributos são flexíveis (JSONB).
-- Estrutura esperada (sugestão):
-- {
--   "nome_completo": "João Silva",
--   "data_nascimento": "1990-05-15",
--   "horario_nascimento": "14:30",
--   "local_nascimento": "São Paulo, SP",
--   "genero": "masculino",
--   "relacionamento": "solteiro",
--   "profissao": "Desenvolvedor",
--   "interesses": ["meditação", "astrologia"],
--   "preocupacoes": ["carreira", "família"],
--   "objetivos_psicologicos": ["auto-conhecimento", "ansiedade"],
--   "mapa_numerologico": {
--     "caminho_vida": 7,
--     "expressao": 5,
--     "alma": 3
--   },
--   "preferencias": {
--     "tom_resposta": "acolhedor",
--     "nivel_profundidade": "alto"
--   }
-- }
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    attributes JSONB DEFAULT '{}'::jsonb,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_attributes ON user_profiles USING GIN (attributes);
CREATE INDEX idx_user_profiles_onboarding ON user_profiles(onboarding_completed);

-- ============================================================
-- 3. USER_ATTRIBUTES (Catálogo de atributos - configurável pelo admin)
-- ============================================================
-- Admin define quais campos existem no perfil. Usado no onboarding.
CREATE TABLE IF NOT EXISTS attribute_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(100) UNIQUE NOT NULL,
    label VARCHAR(255) NOT NULL,
    description TEXT,
    attribute_type VARCHAR(50) NOT NULL CHECK (attribute_type IN (
        'text', 'textarea', 'number', 'date', 'time', 'datetime',
        'select', 'multiselect', 'boolean', 'json'
    )),
    options JSONB, -- para select/multiselect: [{"value":"x","label":"X"}]
    is_required BOOLEAN DEFAULT FALSE,
    is_onboarding BOOLEAN DEFAULT TRUE, -- aparece no onboarding?
    order_index INT DEFAULT 0,
    validation_rules JSONB, -- {"min":0,"max":120,"pattern":"..."}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_attributes_code ON attribute_definitions(code);
CREATE INDEX idx_user_attributes_active ON attribute_definitions(is_active, order_index);

-- ============================================================
-- 4. ONBOARDING_QUESTIONS (Fluxo dinâmico de perguntas)
-- ============================================================
CREATE TABLE IF NOT EXISTS onboarding_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    step INT NOT NULL,
    attribute_code VARCHAR(100), -- referência opcional a user_attributes
    question_text TEXT NOT NULL,
    helper_text TEXT,
    question_type VARCHAR(50) NOT NULL CHECK (question_type IN (
        'text', 'textarea', 'number', 'date', 'time', 'datetime',
        'select', 'multiselect', 'boolean', 'multi_step_intro'
    )),
    options JSONB,
    conditional_show JSONB, -- {"depends_on":"genero","equals":"feminino"}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_onboarding_questions_step ON onboarding_questions(step, is_active);

-- ============================================================
-- 5. CHATS (Conversas - agrupam mensagens)
-- ============================================================
CREATE TABLE IF NOT EXISTS chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    summary TEXT,
    context_snapshot JSONB, -- snapshot do perfil no momento da conversa
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_chats_user_archived ON chats(user_id, is_archived);
CREATE INDEX idx_chats_last_message ON chats(last_message_at DESC);

-- ============================================================
-- 6. MESSAGES (Mensagens do chat)
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_used INT,
    ai_model VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb, -- timing, kb refs, etc
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);

-- ============================================================
-- 7. KNOWLEDGE_DOCUMENTS (Documentos carregados pelo admin)
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    file_name VARCHAR(255),
    file_size_bytes BIGINT,
    storage_url TEXT, -- Azure Blob URL
    storage_provider VARCHAR(50) DEFAULT 'azure_blob', -- 'azure_blob' | 'local'
    file_hash VARCHAR(128), -- sha256 p/ dedup
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN (
        'pending', 'processing', 'indexed', 'failed'
    )),
    error_message TEXT,
    chunks_count INT DEFAULT 0,
    indexed_at TIMESTAMPTZ,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    collection VARCHAR(100) DEFAULT 'conhecimento_geral', -- qual collection do Qdrant
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_documents_status ON knowledge_documents(status);
CREATE INDEX idx_knowledge_documents_collection ON knowledge_documents(collection);
CREATE INDEX idx_knowledge_documents_hash ON knowledge_documents(file_hash);

-- ============================================================
-- 8. AUDIT_LOG (Logs de admin - pra auditoria)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);

-- ============================================================
-- 9. TRIGGER: updated_at automático
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_attributes_updated_at BEFORE UPDATE ON attribute_definitions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chats_updated_at BEFORE UPDATE ON chats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_documents_updated_at BEFORE UPDATE ON knowledge_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 10. DADOS SEED: Primeiro admin + atributos padrão
-- ============================================================
-- Senha padrão: 'admin123' (hash bcrypt - MUDE EM PRODUÇÃO!)
-- O hash abaixo corresponde a 'admin123' com bcrypt cost 12.
INSERT INTO users (email, password_hash, full_name, role, is_active, is_verified)
VALUES (
    'admin@ayria.local',
    '$2b$12$KIXQzVxzF3GqBkC4FvDjmeqJWk8yHN8VK2.2U8YxVZmL8xKQxbPYu',
    'Administrador',
    'SUPER_ADMIN',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Atributos padrão do perfil (cadastráveis via admin depois)
INSERT INTO user_attributes (code, label, attribute_type, is_required, is_onboarding, order_index) VALUES
    ('nome_completo', 'Nome completo', 'text', TRUE, TRUE, 1),
    ('data_nascimento', 'Data de nascimento', 'date', TRUE, TRUE, 2),
    ('horario_nascimento', 'Horário de nascimento', 'time', FALSE, TRUE, 3),
    ('local_nascimento', 'Local de nascimento', 'text', FALSE, TRUE, 4),
    ('genero', 'Como se identifica', 'select', FALSE, TRUE, 5),
    ('relacionamento', 'Estado de relacionamento', 'select', FALSE, TRUE, 6),
    ('profissao', 'Profissão atual', 'text', FALSE, TRUE, 7),
    ('interesses', 'Interesses', 'multiselect', FALSE, TRUE, 8),
    ('objetivos_psicologicos', 'O que busca?', 'multiselect', FALSE, TRUE, 9)
ON CONFLICT (code) DO NOTHING;

-- Onboarding padrão
INSERT INTO onboarding_config (step, question_text, helper_text, question_type, attribute_code) VALUES
    (1, 'Bem-vindo(a) à AYRIA! 🌙', 'Vou te conhecer um pouco melhor para oferecer uma experiência personalizada. Pode levar 2 minutinhos.', 'multi_step_intro', NULL),
    (2, 'Como você se chama?', 'Seu nome completo, por favor.', 'text', 'nome_completo'),
    (3, 'Quando você nasceu?', 'Preciso da data para cálculos numerológicos.', 'date', 'data_nascimento'),
    (4, 'Em que horário você nasceu?', 'Se souber, aproximado já ajuda!', 'time', 'horario_nascimento'),
    (5, 'Onde você nasceu?', 'Cidade e estado. Para o mapa astral também.', 'text', 'local_nascimento'),
    (6, 'Como você se identifica?', NULL, 'select', 'genero'),
    (7, 'Qual seu estado de relacionamento atual?', NULL, 'select', 'relacionamento'),
    (8, 'O que você faz profissionalmente?', NULL, 'text', 'profissao'),
    (9, 'O que te interessa?', 'Pode escolher vários.', 'multiselect', 'interesses'),
    (10, 'O que você busca na AYRIA?', 'Auto-conhecimento, orientação, apoio... seja honesta(o).', 'multiselect', 'objetivos_psicologicos')
ON CONFLICT DO NOTHING;

-- ============================================================
-- FIM DO SCHEMA
-- ============================================================
-- Total: 8 tabelas principais + 1 audit
-- Próximas migrations via Alembic (backend/migrations/versions/)
-- ============================================================

-- ============================================================
-- 11. USER_ATTRIBUTES (Valores dos atributos por usuário)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_attributes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    attribute_definition_id UUID NOT NULL REFERENCES attribute_definitions(id) ON DELETE CASCADE,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, attribute_definition_id)
);

CREATE INDEX idx_user_attributes_user_id ON user_attributes(user_id);
CREATE INDEX idx_user_attributes_definition ON user_attributes(attribute_definition_id);

CREATE TRIGGER update_user_attributes_updated_at BEFORE UPDATE ON user_attributes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
