/**
 * AYRIA - Admin Tab: ALMA (Arquitetura Cognitiva Modular)
 *
 * Editor da ALMA da Ayria em 2 partes:
 *
 * 1. CONSTITUIÇÃO BASE (sempre carregada) — texto pequeno (1-2k tokens)
 *    define identidade, personalidade, limites, segurança, tom
 *
 * 2. MÓDULOS ESPECIALIZADOS (carregados sob demanda) — 13 módulos:
 *    numerologia, astrologia, psicologia, psicanálise, religião,
 *    visão de mundo, memória, crise emocional, luto, relacionamentos,
 *    carreira, onboarding, admin
 *
 * Cada um pode ser editado pelo admin. Banco > arquivo .md como fonte.
 */
import { useEffect, useState } from 'react'
import { adminApi } from '../lib/api'
import {
  Sparkles, Save, RotateCcw, AlertCircle, CheckCircle2, BookOpen,
  Layers, Plus, ChevronRight, Shield, Database, RefreshCw, MessageCircle, Trash2,
} from 'lucide-react'
import { PromptChatModal } from './PromptChatModal'
import { CreateModuleModal } from './CreateModuleModal'

type SubTab = 'constituicao' | 'modulos' | 'rag'

export function AlmaTab() {
  const [subTab, setSubTab] = useState<SubTab>('constituicao')
  const [modulosCount, setModulosCount] = useState<number | null>(null)
  const [modulosCustomCount, setModulosCustomCount] = useState<number>(0)

  return (
    <div className="space-y-4">
      {/* Header explicativo */}
      <div
        className="p-5 rounded-2xl"
        style={{
          background: 'linear-gradient(135deg, rgba(218,149,11,0.10), rgba(241,201,97,0.10))',
          border: '1px solid rgba(168, 85, 247, 0.3)',
        }}
      >
        <div className="flex items-start gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #da950b, #f1c961)' }}
          >
            <Sparkles size={18} className="text-white" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold gradient-text mb-1">ALMA da Ayria</h2>
            <p className="text-sm text-ayria-muted leading-relaxed">
              <strong className="text-ayria-text">Arquitetura cognitiva modular.</strong>{' '}
              O system prompt é montado dinamicamente pelo backend:
              a <strong className="text-ayria-text">constituição base</strong> sempre vai,
              e os <strong className="text-ayria-text">módulos especializados</strong> só
              entram quando relevantes pro contexto (tema, perfil, estado emocional).
            </p>
          </div>
        </div>
      </div>

      {/* Sub-abas */}
      <div className="flex gap-2 border-b border-ayria-border">
        <SubTabButton
          active={subTab === 'constituicao'}
          onClick={() => setSubTab('constituicao')}
          icon={<Shield size={14} />}
          label="Constituição Base"
          subtitle="sempre ativa"
        />
        <SubTabButton
          active={subTab === 'modulos'}
          onClick={() => setSubTab('modulos')}
          icon={<Layers size={14} />}
          label="Módulos"
          subtitle={
            modulosCount === null
              ? 'carregando...'
              : modulosCustomCount > 0
                ? `${modulosCount} (${modulosCustomCount} custom)`
                : `${modulosCount} disponíveis`
          }
        />
        <SubTabButton
          active={subTab === 'rag'}
          onClick={() => setSubTab('rag')}
          icon={<Database size={14} />}
          label="RAG (Qdrant)"
          subtitle="indexação"
        />
      </div>

      {subTab === 'constituicao' && <ConstituicaoEditor />}
      {subTab === 'modulos' && (
        <ModulosEditor
          onCountChange={(total, custom) => {
            setModulosCount(total)
            setModulosCustomCount(custom)
          }}
        />
      )}
      {subTab === 'rag' && <RagStatusPanel />}
    </div>
  )
}

// ============================================================
// SUB-ABA: CONSTITUIÇÃO BASE
// ============================================================
function ConstituicaoEditor() {
  const [activeContent, setActiveContent] = useState<string>('')
  const [defaultTemplate, setDefaultTemplate] = useState<string>('')
  const [editContent, setEditContent] = useState<string>('')
  const [description, setDescription] = useState<string>('')
  const [isCustom, setIsCustom] = useState<boolean>(false)
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await adminApi.getPromptSystem()
      setActiveContent(data.active.content)
      setDefaultTemplate(data.default_template)
      setEditContent(data.active.content)
      setDescription(data.active.description || '')
      setIsCustom(data.active.is_custom)
      setUpdatedAt(data.active.updated_at)
      setDirty(false)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao carregar constituição')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await adminApi.updatePromptSystem({
        key: 'constituicao_base',
        content: editContent,
        description: description || undefined,
      })
      setSuccess(`✅ Constituição salva. Válida a partir da próxima mensagem. (id: ${data.id.slice(0, 8)}…)`)
      setIsCustom(true)
      setActiveContent(editContent)
      setUpdatedAt(data.updated_at)
      setDirty(false)
      setTimeout(() => setSuccess(null), 5000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async () => {
    if (!confirm('Restaurar a constituição padrão?\n\nA versão customizada será DESATIVADA. A Ayria volta a usar o arquivo prompt_base.md.')) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await adminApi.restoreDefaultPrompt('constituicao_base')
      setSuccess('✅ Constituição restaurada para o padrão.')
      setIsCustom(false)
      setEditContent(defaultTemplate)
      setDescription('Constituição padrão (arquivo prompt_base.md)')
      setDirty(false)
      setActiveContent(defaultTemplate)
      setTimeout(() => setSuccess(null), 5000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao restaurar')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setEditContent(activeContent)
    setDescription(description)
    setDirty(false)
    setError(null)
  }

  if (loading) {
    return <div className="text-ayria-muted py-12 text-center">Carregando constituição...</div>
  }

  const charCount = editContent.length
  const tokenEstimated = Math.ceil(charCount / 4)

  return (
    <div className="space-y-4">
      {/* Status bar */}
      <div
        className="p-3 rounded-xl flex items-center justify-between text-sm flex-wrap gap-2"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-3 flex-wrap">
          <span
            className="text-xs px-2 py-1 rounded uppercase tracking-wider font-semibold"
            style={{
              background: isCustom ? 'rgba(168, 85, 247, 0.15)' : 'rgba(148, 163, 184, 0.15)',
              color: isCustom ? '#da950b' : '#94A3B8',
            }}
          >
            {isCustom ? '✨ Customizada' : '📦 Padrão'}
          </span>
          {updatedAt && (
            <span className="text-xs text-ayria-muted">
              {new Date(updatedAt).toLocaleString('pt-BR')}
            </span>
          )}
          <span className="text-xs text-ayria-muted">
            {charCount.toLocaleString('pt-BR')} chars · ~{tokenEstimated.toLocaleString('pt-BR')} tokens
          </span>
        </div>
        {tokenEstimated > 2500 && (
          <span
            className="text-xs px-2 py-1 rounded flex items-center gap-1"
            style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#F59E0B' }}
          >
            <AlertCircle size={12} />
            Constituição grande (ideal: 1000-2000 tokens)
          </span>
        )}
        <button
          onClick={() => setChatOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors hover:opacity-80"
          style={{
            background: 'linear-gradient(135deg, rgba(241,201,97,0.2), rgba(218,149,11,0.2))',
            color: '#C084FC',
            border: '1px solid rgba(218,149,11,0.3)',
          }}
          title="Conversar com IA sobre esta constituição"
        >
          <MessageCircle size={14} />
          Chat com IA
        </button>
      </div>

      {/* Editor */}
      <div
        className="rounded-2xl overflow-hidden"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid #1E1E2E' }}>
          <div className="flex items-center gap-2">
            <BookOpen size={16} className="text-ayria-muted" />
            <span className="text-sm font-semibold text-ayria-text">Constituição</span>
            {dirty && (
              <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#F59E0B' }}>
                ● não salvo
              </span>
            )}
          </div>
        </div>

        <textarea
          value={editContent}
          onChange={(e) => {
            setEditContent(e.target.value)
            setDirty(true)
          }}
          spellCheck={false}
          className="w-full px-4 py-4 outline-none resize-none font-mono text-sm text-ayria-text"
          style={{
            background: '#0a0a0a',
            border: 'none',
            minHeight: '500px',
            lineHeight: '1.6',
          }}
        />

        <div className="px-4 py-3" style={{ borderTop: '1px solid #1E1E2E' }}>
          <label className="block text-xs text-ayria-muted mb-1">Descrição da versão (opcional)</label>
          <input
            type="text"
            value={description}
            onChange={(e) => {
              setDescription(e.target.value)
              setDirty(true)
            }}
            placeholder="Ex: v3 — incluiu regra de ouro sobre perguntas reflexivas"
            className="w-full px-3 py-2 rounded-lg text-sm text-ayria-text outline-none"
            style={{ background: '#050505', border: '1px solid #1E1E2E' }}
          />
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="p-3 rounded-xl flex items-start gap-2 text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}
      {success && (
        <div className="p-3 rounded-xl flex items-start gap-2 text-sm" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10B981', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
          <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5" />
          <div>{success}</div>
        </div>
      )}

      {/* Botões */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleSave}
          disabled={saving || !dirty}
          className="flex-1 min-w-[180px] px-4 py-3 rounded-xl font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #da950b, #f1c961)' }}
        >
          <Save size={16} />
          {saving ? 'Salvando...' : 'Salvar e ativar'}
        </button>
        <button
          onClick={handleReset}
          disabled={!dirty || saving}
          className="px-4 py-3 rounded-xl text-ayria-muted hover:text-ayria-text disabled:opacity-50"
          style={{ border: '1px solid #1E1E2E' }}
        >
          Descartar mudanças
        </button>
        <button
          onClick={handleRestore}
          disabled={saving || !isCustom}
          className="px-4 py-3 rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#F59E0B', border: '1px solid rgba(245, 158, 11, 0.3)' }}
        >
          <RotateCcw size={16} />
          Restaurar padrão
        </button>
      </div>

      {/* Dica */}
      <div className="p-4 rounded-xl text-xs text-ayria-muted" style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}>
        <div className="font-semibold text-ayria-text mb-1">💡 Sobre a constituição</div>
        <div>Esta camada é SEMPRE carregada em TODA conversa. Idealmente entre 1.000 e 2.000 tokens.</div>
        <div className="mt-1">Regras específicas (numerologia, crise, luto, etc.) ficam nos <strong className="text-ayria-text">módulos</strong> — use esta aba só pra personalidade, tom, segurança e princípios gerais.</div>
      </div>

      <PromptChatModal
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        promptKey="constituicao_base"
        promptLabel="Constituição Base da Ayria"
        onSaved={() => load()}
      />
    </div>
  )
}

// ============================================================
// SUB-ABA: MÓDULOS ESPECIALIZADOS
// ============================================================
function ModulosEditor({ onCountChange }: { onCountChange?: (total: number, custom: number) => void } = {}) {
  const [availableModules, setAvailableModules] = useState<string[]>([])
  const [defaultPreviews, setDefaultPreviews] = useState<Record<string, string>>({})
  const [customMods, setCustomMods] = useState<Record<string, { content: string; description: string; updated_at: string }>>({})
  const [selectedModule, setSelectedModule] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [chatKey, setChatKey] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [availRes, systemRes] = await Promise.all([
        adminApi.listAvailableModules(),
        adminApi.getPromptSystem(),
      ])
      setAvailableModules(availRes.data.available_modules)
      const previews: Record<string, string> = {}
      availRes.data.modules.forEach((m: any) => {
        previews[m.key] = m.default_preview
      })
      setDefaultPreviews(previews)

      const customs: Record<string, any> = {}
      systemRes.data.modulos_customizados.forEach((m: any) => {
        customs[m.short_key] = {
          content: m.content,
          description: m.description || '',
          updated_at: m.updated_at,
        }
      })
      setCustomMods(customs)
      // Atualiza contagem no header
      if (onCountChange) {
        onCountChange(availRes.data.available_modules.length, Object.keys(customs).length)
      }
    } catch (e: any) {
      console.error('Erro ao carregar módulos:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleDelete = async (key: string) => {
    setDeleting(true)
    setDeleteError(null)
    try {
      const res = await adminApi.deletePromptModule(key)
      setDeleteTarget(null)
      setSelectedModule(null)
      await load()
      console.log('✅ Módulo excluído:', key, res.data)
    } catch (e: any) {
      setDeleteError(e?.response?.data?.detail || 'Erro ao excluir')
    } finally {
      setDeleting(false)
    }
  }

  if (loading) {
    return <div className="text-ayria-muted py-12 text-center">Carregando módulos...</div>
  }

  if (selectedModule) {
    return (
      <ModuleEditor
        moduleKey={selectedModule}
        defaultContent={
          customMods[selectedModule]
            ? ''
            : defaultPreviews[selectedModule] || ''
        }
        customData={customMods[selectedModule]}
        onBack={() => {
          setSelectedModule(null)
          load()
        }}
      />
    )
  }

  return (
    <div className="space-y-4">
      <DeleteModuleModal
        target={deleteTarget || ''}
        onClose={() => { setDeleteTarget(null); setDeleteError(null) }}
        onConfirm={() => deleteTarget && handleDelete(deleteTarget)}
        deleting={deleting}
        error={deleteError}
      />

      {/* Info */}
      <div className="p-4 rounded-xl text-xs text-ayria-muted" style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}>
        <div className="font-semibold text-ayria-text mb-1">📚 Sobre os módulos</div>
        <div>O classificador carrega módulos sob demanda baseado em:</div>
        <ul className="mt-1 ml-4 list-disc space-y-0.5">
          <li><strong className="text-ayria-text">Mensagem</strong> — keywords (ex: "demissão" → carreira)</li>
          <li><strong className="text-ayria-text">Perfil</strong> — numerologia, astrologia, preferência espiritual</li>
          <li><strong className="text-ayria-text">Contexto</strong> — role (admin), onboarding pendente, memórias</li>
        </ul>
        <div className="mt-2">Clique num módulo pra ver/editar. Customizações no banco sobrescrevem o arquivo <code className="px-1 py-0.5 rounded" style={{ background: '#1E1E2E' }}>prompt_*.md</code>.</div>
      </div>

      {/* Lista de módulos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {availableModules.map((key) => {
          const isCustom = !!customMods[key]
          return (
            <div
              key={key}
              className="relative text-left p-4 rounded-xl transition-colors hover:scale-[1.01] cursor-pointer group"
              style={{
                background: isCustom ? 'rgba(168, 85, 247, 0.08)' : '#111111',
                border: isCustom ? '1px solid rgba(168, 85, 247, 0.4)' : '1px solid #1E1E2E',
              }}
              onClick={() => setSelectedModule(key)}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-base font-bold text-ayria-text">{key}</span>
                  {isCustom && (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded font-bold"
                      style={{ background: '#da950b', color: '#FFFFFF' }}
                    >
                      ✨ CUSTOM
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={(e) => { e.stopPropagation(); setChatKey(`modulo_${key}`) }}
                    className="p-1.5 rounded-lg text-ayria-muted hover:text-purple-300 hover:bg-purple-500/10 transition-colors"
                    title="Conversar com IA sobre este prompt"
                  >
                    <MessageCircle size={14} />
                  </button>
                  {isCustom && (
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget(key) }}
                      className="p-1.5 rounded-lg text-ayria-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Excluir módulo"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                  <ChevronRight size={16} className="text-ayria-muted" />
                </div>
              </div>
              <div className="text-xs text-ayria-muted line-clamp-3">
                {isCustom ? customMods[key].description : (defaultPreviews[key] || '(sem preview)').substring(0, 180)}
              </div>
              {isCustom && (
                <div className="text-[10px] text-ayria-muted mt-2">
                  Editado em {new Date(customMods[key].updated_at).toLocaleDateString('pt-BR')}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* ═══════════════════════════════════════════════
          🆕 BOTÃO: Criar novo módulo — abre MODAL (não inline)
          ═══════════════════════════════════════════════ */}
      <button
        onClick={() => setCreateOpen(true)}
        className="w-full p-4 rounded-xl border-2 border-dashed flex items-center justify-center gap-2 hover:scale-[1.01] transition-transform"
        style={{ borderColor: 'rgba(218,149,11,0.3)', color: '#C084FC' }}
      >
        <Plus size={16} />
        <span className="text-sm font-semibold">Criar novo módulo</span>
        <span className="text-[10px] px-1.5 py-0.5 rounded ml-2" style={{ background: 'rgba(218,149,11,0.15)' }}>
          ✨ com ajuda da IA
        </span>
      </button>

      {/* Modal de criação de módulo */}
      <CreateModuleModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(key) => {
          load()
          setSelectedModule(key)
        }}
      />

      {/* Modal de Chat sobre MD */}
      {chatKey && (
        <PromptChatModal
          open={!!chatKey}
          onClose={() => setChatKey(null)}
          promptKey={chatKey}
          promptLabel={chatKey.replace('modulo_', 'Módulo: ').replace(/_/g, ' ')}
          onSaved={() => load()}
        />
      )}
    </div>
  )
}



// MODAL DE CONFIRMAÇÃO DE EXCLUSÃO (listado no ModulosEditor)
function DeleteModuleModal({
  target,
  onClose,
  onConfirm,
  deleting,
  error,
}: {
  target: string
  onClose: () => void
  onConfirm: () => void
  deleting: boolean
  error: string | null
}) {
  // 🛡️ FIX: só renderiza se há um target selecionado
  if (!target) return null

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="rounded-2xl p-6 max-w-md w-full"
        style={{ background: '#16161F', border: '1px solid #EF4444' }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold text-ayria-text mb-2 flex items-center gap-2">
          <Trash2 size={18} className="text-red-400" />
          Excluir módulo
        </h3>
        <p className="text-sm text-ayria-muted mb-4">
          Tem certeza que quer excluir o módulo <strong style={{ color: '#da950b' }}>{target}</strong>?
        </p>
        <div className="text-xs p-3 rounded mb-4" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#FCA5A5' }}>
          ⚠️ <strong>Esta ação:</strong>
          <ul className="list-disc ml-4 mt-1 space-y-0.5">
            <li>Remove o arquivo <code>.md</code> do disco</li>
            <li>Desativa a config no banco (histórico preservado)</li>
            <li>Remove chunks do RAG</li>
            <li>Cria backup <code>.deleted</code> por segurança</li>
          </ul>
          O backup permite recuperação manual se você mudar de ideia.
        </div>
        {error && (
          <div className="text-xs p-2 rounded mb-4" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444' }}>
            ❌ {error}
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={onClose}
            disabled={deleting}
            className="flex-1 px-4 py-2.5 rounded-lg font-medium text-ayria-text disabled:opacity-50"
            style={{ background: '#1E1E2E', border: '1px solid #2A2A3A' }}
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="flex-1 px-4 py-2.5 rounded-lg font-semibold text-white disabled:opacity-50 flex items-center justify-center gap-2"
            style={{ background: 'linear-gradient(135deg, #EF4444, #DC2626)' }}
          >
            <Trash2 size={16} />
            {deleting ? 'Excluindo...' : 'Excluir'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// EDITOR DE MÓDULO INDIVIDUAL
// ============================================================
function ModuleEditor({
  moduleKey,
  defaultContent,
  customData,
  onBack,
}: {
  moduleKey: string
  defaultContent: string
  customData?: { content: string; description: string; updated_at: string }
  onBack: () => void
}) {
  const [editContent, setEditContent] = useState(customData?.content || defaultContent)
  const [description, setDescription] = useState(customData?.description || '')
  const [isCustom, setIsCustom] = useState(!!customData)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleDeleteModule = async () => {
    setDeleting(true)
    setDeleteError(null)
    try {
      await adminApi.deletePromptModule(moduleKey)
      setDeleteOpen(false)
      onBack()
    } catch (e: any) {
      setDeleteError(e?.response?.data?.detail || 'Erro ao excluir')
    } finally {
      setDeleting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await adminApi.updatePromptSystem({
        key: `modulo_${moduleKey}`,
        content: editContent,
        description: description || undefined,
      })
      setSuccess('✅ Módulo salvo.')
      setIsCustom(true)
      setDirty(false)
      setTimeout(() => setSuccess(null), 5000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async () => {
    if (!confirm(`Restaurar módulo '${moduleKey}' pro padrão (arquivo .md)?\n\nA versão customizada será DESATIVADA.`)) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await adminApi.restoreDefaultPrompt(`modulo_${moduleKey}`)
      setSuccess('✅ Restaurado pro padrão.')
      setIsCustom(false)
      setEditContent(defaultContent)
      setDirty(false)
      setTimeout(() => setSuccess(null), 5000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao restaurar')
    } finally {
      setSaving(false)
    }
  }

  const charCount = editContent.length
  const tokenEstimated = Math.ceil(charCount / 4)

  return (
    <div className="space-y-4">
      {/* Header com voltar */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="text-ayria-muted hover:text-ayria-text p-2 rounded-lg hover:bg-[#1a1a1a]"
        >
          ← Voltar
        </button>
        <div className="flex-1">
          <h3 className="text-lg font-bold text-ayria-text">
            Módulo: <span style={{ color: '#da950b' }}>{moduleKey}</span>
          </h3>
          <div className="text-xs text-ayria-muted">
            Carregado sob demanda quando o classificador detecta o tema
          </div>
        </div>
        <button
          onClick={() => setChatOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors hover:opacity-80"
          style={{
            background: 'linear-gradient(135deg, rgba(241,201,97,0.2), rgba(218,149,11,0.2))',
            color: '#C084FC',
            border: '1px solid rgba(218,149,11,0.3)',
          }}
          title="Conversar com IA sobre este módulo"
        >
          <MessageCircle size={14} />
          Chat com IA
        </button>
        <span
          className="text-xs px-2 py-1 rounded uppercase tracking-wider font-semibold"
          style={{
            background: isCustom ? 'rgba(168, 85, 247, 0.15)' : 'rgba(148, 163, 184, 0.15)',
            color: isCustom ? '#da950b' : '#94A3B8',
          }}
        >
          {isCustom ? '✨ Custom' : '📦 Padrão'}
        </span>
      </div>

      {/* Stats */}
      <div className="text-xs text-ayria-muted">
        {charCount.toLocaleString('pt-BR')} chars · ~{tokenEstimated.toLocaleString('pt-BR')} tokens
      </div>

      {/* Editor */}
      <textarea
        value={editContent}
        onChange={(e) => {
          setEditContent(e.target.value)
          setDirty(true)
        }}
        spellCheck={false}
        className="w-full px-4 py-4 outline-none resize-none font-mono text-sm text-ayria-text rounded-2xl"
        style={{
          background: '#111111',
          border: '1px solid #1E1E2E',
          minHeight: '400px',
          lineHeight: '1.6',
        }}
      />

      {/* Descrição */}
      <div>
        <label className="block text-xs text-ayria-muted mb-1">Descrição (opcional)</label>
        <input
          type="text"
          value={description}
          onChange={(e) => {
            setDescription(e.target.value)
            setDirty(true)
          }}
          placeholder="Ex: v2 — adicionei regra sobre trauma"
          className="w-full px-3 py-2 rounded-lg text-sm text-ayria-text outline-none"
          style={{ background: '#050505', border: '1px solid #1E1E2E' }}
        />
      </div>

      {error && (
        <div className="p-3 rounded-xl flex items-start gap-2 text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
          <div>{error}</div>
        </div>
      )}
      {success && (
        <div className="p-3 rounded-xl flex items-start gap-2 text-sm" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10B981', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
          <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5" />
          <div>{success}</div>
        </div>
      )}

      {/* Botões */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleSave}
          disabled={saving || !dirty}
          className="flex-1 min-w-[180px] px-4 py-3 rounded-xl font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #da950b, #f1c961)' }}
        >
          <Save size={16} />
          {saving ? 'Salvando...' : 'Salvar'}
        </button>
        <button
          onClick={handleRestore}
          disabled={saving || !isCustom}
          className="px-4 py-3 rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#F59E0B', border: '1px solid rgba(245, 158, 11, 0.3)' }}
        >
          <RotateCcw size={16} />
          Restaurar padrão
        </button>
        <button
          onClick={() => { setDeleteOpen(true); setDeleteError(null) }}
          disabled={saving}
          className="px-4 py-3 rounded-xl font-medium flex items-center justify-center gap-2 disabled:opacity-50"
          style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444', border: '1px solid rgba(239, 68, 68, 0.3)' }}
          title="Excluir módulo (remove arquivo, banco e RAG)"
        >
          <Trash2 size={16} />
          Excluir módulo
        </button>
      </div>

      {/* Modal de confirmação de exclusão */}
      {deleteOpen && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => !deleting && setDeleteOpen(false)}
        >
          <div
            className="rounded-2xl p-6 max-w-md w-full"
            style={{ background: '#16161F', border: '1px solid #EF4444' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-ayria-text mb-2 flex items-center gap-2">
              <Trash2 size={18} className="text-red-400" />
              Excluir módulo
            </h3>
            <p className="text-sm text-ayria-muted mb-4">
              Tem certeza que quer excluir o módulo <strong style={{ color: '#da950b' }}>{moduleKey}</strong>?
            </p>
            <div className="text-xs p-3 rounded mb-4" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#FCA5A5' }}>
              ⚠️ <strong>Esta ação:</strong>
              <ul className="list-disc ml-4 mt-1 space-y-0.5">
                <li>Remove o arquivo <code>.md</code> do disco</li>
                <li>Desativa a config no banco (histórico preservado)</li>
                <li>Remove chunks do RAG</li>
                <li>Cria backup <code>.deleted</code> por segurança</li>
              </ul>
              O backup permite recuperação manual se você mudar de ideia.
            </div>
            {deleteError && (
              <div className="text-xs p-2 rounded mb-4" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444' }}>
                ❌ {deleteError}
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => setDeleteOpen(false)}
                disabled={deleting}
                className="flex-1 px-4 py-2.5 rounded-lg font-medium text-ayria-text disabled:opacity-50"
                style={{ background: '#1E1E2E', border: '1px solid #2A2A3A' }}
              >
                Cancelar
              </button>
              <button
                onClick={handleDeleteModule}
                disabled={deleting}
                className="flex-1 px-4 py-2.5 rounded-lg font-semibold text-white disabled:opacity-50 flex items-center justify-center gap-2"
                style={{ background: 'linear-gradient(135deg, #EF4444, #DC2626)' }}
              >
                <Trash2 size={16} />
                {deleting ? 'Excluindo...' : 'Excluir'}
              </button>
            </div>
          </div>
        </div>
      )}

      <PromptChatModal
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        promptKey={`modulo_${moduleKey}`}
        promptLabel={`Módulo: ${moduleKey}`}
        onSaved={(newContent) => {
          setEditContent(newContent)
          setIsCustom(true)
          setDirty(true)
          setSuccess('✅ Conteúdo atualizado pelo chat. Clique Salvar pra confirmar.')
          setTimeout(() => setSuccess(null), 5000)
        }}
      />
    </div>
  )
}

// === Sub-componente ===
function SubTabButton({
  active, onClick, icon, label, subtitle,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
  subtitle: string
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-3 text-sm flex items-center gap-2 border-b-2 transition-colors ${
        active ? 'border-ayria-admin text-ayria-text' : 'border-transparent text-ayria-muted hover:text-ayria-text'
      }`}
    >
      {icon}
      <div className="text-left">
        <div>{label}</div>
        <div className="text-[10px] text-ayria-muted">{subtitle}</div>
      </div>
    </button>
  )
}

// ============================================================
// SUB-ABA: RAG STATUS (Indexação no Qdrant)
// ============================================================
function RagStatusPanel() {
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState<string | null>(null)
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const load = async () => {
    setLoading(true)
    try {
      const { data } = await adminApi.getPromptRagStatus()
      setStatus(data)
    } catch (e: any) {
      setMsg({ type: 'err', text: e?.response?.data?.detail || 'Erro ao carregar status' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const formatError = (e: any, action: string): string => {
    // Mostra TUDO do erro pra facilitar debug - status, data, message, name
    const status = e?.response?.status
    const data = e?.response?.data
    const detail = data?.detail || data?.message || e?.message
    const code = data?.error_code || data?.code
    const lines: string[] = []
    lines.push(`❌ ERRO ao ${action}`)
    if (status) lines.push(`Status HTTP: ${status}`)
    if (code) lines.push(`Código: ${code}`)
    if (detail) lines.push(`Detalhe: ${detail}`)
    if (data && typeof data === 'object') {
      const dataStr = JSON.stringify(data, null, 2)
      if (dataStr !== `{"detail":"${detail}"}`) {
        lines.push(`Response data: ${dataStr}`)
      }
    }
    if (e?.message && e.message !== detail) lines.push(`Mensagem: ${e.message}`)
    if (e?.code) lines.push(`Erro code: ${e.code}`)
    return lines.join('\n')
  }

  const reindexAll = async () => {
    if (!confirm('Reindexar TODOS os .md? Os chunks antigos serão substituídos.')) return
    setWorking('all')
    setMsg(null)
    try {
      const { data } = await adminApi.indexPromptsRag({ recreate: true })
      setMsg({ type: 'ok', text: `✅ ${data.chunks} chunks indexados em ${data.sources.length} fontes.` })
      load()
    } catch (e: any) {
      setMsg({ type: 'err', text: formatError(e, 'reindexar TODOS') })
    } finally {
      setWorking(null)
    }
  }

  const reindexOne = async (source: string) => {
    setWorking(source)
    setMsg(null)
    try {
      await adminApi.indexPromptsRag({ source, recreate: true })
      setMsg({ type: 'ok', text: `✅ ${source} reindexado.` })
      load()
    } catch (e: any) {
      setMsg({ type: 'err', text: formatError(e, `reindexar ${source}`) })
    } finally {
      setWorking(null)
    }
  }

  const deleteOne = async (source: string) => {
    if (!confirm(`Remover "${source}" do Qdrant? O .md em disco continua, só os chunks vetorizados serão apagados.`)) return
    setWorking(source)
    setMsg(null)
    try {
      await adminApi.deletePromptRag({ source })
      setMsg({ type: 'ok', text: `🗑️ ${source} removido do Qdrant.` })
      load()
    } catch (e: any) {
      setMsg({ type: 'err', text: formatError(e, `deletar ${source}`) })
    } finally {
      setWorking(null)
    }
  }

  if (loading) return <div className="text-ayria-muted py-12 text-center">Carregando status RAG...</div>
  if (!status) return null

  return (
    <div className="space-y-4">
      {/* Info card */}
      <div className="p-4 rounded-xl text-xs text-ayria-muted" style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}>
        <div className="font-semibold text-ayria-text mb-1">🗄️ RAG — Indexação no Qdrant</div>
        <div>Os arquivos .md são quebrados em chunks e indexados na coleção <code className="px-1 py-0.5 rounded" style={{ background: '#1E1E2E' }}>conhecimento_geral</code> com embedding 1536.</div>
        <div className="mt-1">Em cada mensagem da Ayria, o backend busca os chunks mais relevantes e injeta no system prompt.</div>
        <div className="mt-2 text-amber-400">⚠️ MiniMax não tem endpoint /embeddings confirmado — usando fallback hash determinístico (busca limitada mas funcional).</div>
      </div>

      {/* Summary bar */}
      <div
        className="p-4 rounded-xl flex items-center justify-between flex-wrap gap-3"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-6 flex-wrap">
          <Stat icon="📁" label="Arquivos .md" value={status.files_count} />
          <Stat icon="✅" label="Indexados" value={status.indexed_count} color="#10B981" />
          <Stat
            icon="❌"
            label="Faltando"
            value={status.missing_index.length}
            color={status.missing_index.length ? '#EF4444' : '#10B981'}
          />
        </div>
        <button
          onClick={reindexAll}
          disabled={working === 'all'}
          className="px-4 py-2 rounded-lg font-semibold text-white flex items-center gap-2 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #da950b, #f1c961)' }}
        >
          <RefreshCw size={14} className={working === 'all' ? 'animate-spin' : ''} />
          {working === 'all' ? 'Reindexando...' : 'Reindexar tudo'}
        </button>
      </div>

      {msg && (
        <div
          className="p-3 rounded-xl text-sm"
          style={{
            background: msg.type === 'ok' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            color: msg.type === 'ok' ? '#10B981' : '#EF4444',
            border: msg.type === 'ok' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: msg.type === 'err' ? 'ui-monospace, monospace' : 'inherit',
            fontSize: msg.type === 'err' ? '12px' : 'inherit',
          }}
        >
          {msg.text}
        </div>
      )}

      {/* Lista de fontes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {status.indexed_docs.map((doc: any) => (
          <div
            key={doc.source}
            className="p-4 rounded-xl"
            style={{ background: '#111111', border: '1px solid #1E1E2E' }}
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="font-mono text-sm font-bold text-ayria-text">{doc.source}</div>
                <div className="text-xs text-ayria-muted">
                  {doc.type_label === 'constituicao' ? '🛡️ Constituição' : '📦 Módulo'} · {doc.chunks} chunks
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => reindexOne(doc.source)}
                  disabled={working === doc.source}
                  className="text-xs px-2 py-1 rounded text-ayria-muted hover:text-ayria-text disabled:opacity-50"
                  style={{ background: 'rgba(99, 102, 241, 0.1)' }}
                  title="Reindexar"
                >
                  {working === doc.source ? <RefreshCw size={12} className="animate-spin" /> : <RefreshCw size={12} />}
                </button>
                <button
                  onClick={() => deleteOne(doc.source)}
                  disabled={working === doc.source}
                  className="text-xs px-2 py-1 rounded text-red-400 hover:text-red-300 disabled:opacity-50"
                  style={{ background: 'rgba(239, 68, 68, 0.1)' }}
                  title="Remover do Qdrant"
                >
                  ✕
                </button>
              </div>
            </div>
            <div className="text-[10px] text-ayria-muted line-clamp-2">
              {doc.first_chunk}
            </div>
          </div>
        ))}
      </div>

      {/* Arquivos não indexados */}
      {status.missing_index.length > 0 && (
        <div className="p-4 rounded-xl" style={{ background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
          <div className="text-sm font-bold text-amber-400 mb-2">⚠️ {status.missing_index.length} arquivo(s) sem indexar:</div>
          <ul className="text-xs text-ayria-muted space-y-1">
            {status.missing_index.map((f: string) => (
              <li key={f} className="font-mono">• {f}</li>
            ))}
          </ul>
          <button
            onClick={reindexAll}
            className="mt-3 text-xs px-3 py-1.5 rounded text-amber-400 hover:text-amber-300"
            style={{ background: 'rgba(245, 158, 11, 0.1)' }}
          >
            Indexar tudo agora
          </button>
        </div>
      )}

      </div>
  )
}

function Stat({ icon, label, value, color }: { icon: string; label: string; value: number; color?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-lg">{icon}</span>
      <div>
        <div className="text-[10px] text-ayria-muted uppercase tracking-wider">{label}</div>
        <div className="text-lg font-bold" style={{ color: color || '#da950b' }}>{value}</div>
      </div>
    </div>
  )
}
