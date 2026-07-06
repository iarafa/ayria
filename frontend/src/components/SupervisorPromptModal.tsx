import { useEffect, useState } from 'react'
import { adminApi } from '../lib/api'
import {
  Shield, Sparkles, Save, RotateCcw, AlertCircle, CheckCircle2,
  Loader2, X, FileText,
} from 'lucide-react'
import { PromptChatModal } from './PromptChatModal'

interface SupervisorPromptModalProps {
  open: boolean
  onClose: () => void
  /** Callback opcional após salvar (pra recarregar dados do pai) */
  onSaved?: () => void
}

/**
 * Modal de edição do prompt do Supervisor (camada paralela que classifica
 * risco em N1/N2/N3). Popup centralizado (não inline).
 *
 * Diferente dos módulos da Ayria (que ela lê), este prompt é LIDO PELA IA
 * SUPERVISORA — define os 3 níveis oficiais de risco.
 */
export function SupervisorPromptModal({ open, onClose, onSaved }: SupervisorPromptModalProps) {
  const [data, setData] = useState<any>(null)
  const [editContent, setEditContent] = useState('')
  const [description, setDescription] = useState('')
  const [isCustom, setIsCustom] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const { data: d } = await adminApi.getSupervisorPrompt()
        setData(d)
        setEditContent(d.active.content)
        setDescription(d.active.description || '')
        setIsCustom(d.active.is_custom)
        setDirty(false)
      } catch (e: any) {
        setError(e?.response?.data?.detail || 'Erro ao carregar prompt do supervisor')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [open])

  if (!open) return null

  const handleSave = async (contentToSave?: string) => {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await adminApi.updateSupervisorPrompt({
        content: contentToSave ?? editContent,
        description: description || undefined,
      })
      setSuccess('✅ Prompt do supervisor atualizado.')
      setIsCustom(true)
      setDirty(false)
      onSaved?.()
      setTimeout(() => {
        setSuccess(null)
        onClose()
      }, 800)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async () => {
    if (!confirm('Restaurar prompt do supervisor pro padrão (arquivo .md)?\n\nA versão customizada será DESATIVADA.')) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await adminApi.restoreSupervisorPrompt()
      setSuccess('✅ Restaurado pro padrão.')
      setIsCustom(false)
      setEditContent(data?.default_content || '')
      setDirty(false)
      onSaved?.()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao restaurar')
    } finally {
      setSaving(false)
    }
  }

  const handleChatSave = (newContent: string) => {
    setEditContent(newContent)
    setSuccess('✅ Conteúdo atualizado pelo chat.')
    setChatOpen(false)
    setDirty(true)
    setTimeout(() => setSuccess(null), 3000)
  }

  const handleChatAutoSave = (newContent: string) => {
    setEditContent(newContent)
    setChatOpen(false)
    setDirty(true)
    setTimeout(() => handleSave(newContent), 100)
  }

  const charCount = editContent.length

  return (
    <>
      {/* OVERLAY */}
      <div
        className="fixed inset-0 z-40 flex items-center justify-center p-4"
        style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
        onClick={() => {
          if (!saving) onClose()
        }}
      >
        {/* CARD */}
        <div
          className="w-full max-w-3xl max-h-[90vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          style={{
            background: '#0a0a0a',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            boxShadow: '0 0 40px rgba(239, 68, 68, 0.2)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* HEADER */}
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: '#1E1E2E' }}
          >
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{
                  background: 'linear-gradient(135deg, #EF4444, #DC2626)',
                  boxShadow: '0 0 8px rgba(239, 68, 68, 0.3)',
                }}
              >
                <Shield size={14} className="text-white" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-bold text-ayria-text">Prompt do Supervisor</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded font-bold" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#EF4444' }}>
                    CRÍTICO
                  </span>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded font-bold"
                    style={{
                      background: isCustom ? 'rgba(168, 85, 247, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                      color: isCustom ? '#A855F7' : '#94A3B8',
                    }}
                  >
                    {isCustom ? '✨ Custom' : '📦 Padrão'}
                  </span>
                </div>
                <div className="text-[10px] text-ayria-muted font-mono truncate">
                  prompts/supervisor/seguranca_crise.md
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => setChatOpen(true)}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={{
                  background: 'linear-gradient(135deg, rgba(168,85,247,0.25), rgba(99,102,241,0.25))',
                  color: '#C084FC',
                  border: '1px solid rgba(168,85,247,0.4)',
                  boxShadow: '0 0 8px rgba(168,85,247,0.15)',
                }}
                title="Conversar com IA sobre o prompt do supervisor"
              >
                <Sparkles size={12} />
                Chat com IA
              </button>
              <button
                onClick={() => {
                  if (!saving) onClose()
                }}
                className="p-1.5 rounded-lg hover:bg-white/5 text-ayria-muted hover:text-ayria-text"
                title="Fechar"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* BODY (scroll) */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-12 gap-2 text-ayria-muted">
                <Loader2 size={16} className="animate-spin" />
                Carregando prompt do supervisor...
              </div>
            ) : (
              <>
                {/* BLOCO INFO: o que é + 3 níveis esperados */}
                <div
                  className="p-3 rounded-lg space-y-3"
                  style={{ background: '#0a0a0a', border: '1px solid rgba(239, 68, 68, 0.25)' }}
                >
                  <div>
                    <div className="text-xs font-bold text-ayria-text mb-1 flex items-center gap-1">
                      <Shield size={12} style={{ color: '#EF4444' }} />
                      🛡️ Sobre este prompt
                    </div>
                    <div className="text-[11px] text-ayria-muted space-y-1">
                      <div>Lido pela <strong className="text-ayria-text">IA SUPERVISORA</strong> — classifica cada msg do user em NORMAL/ATENÇÃO/URGÊNCIA.</div>
                      <div>Define os <strong className="text-ayria-text">3 níveis oficiais de risco</strong> e o que cada um dispara.</div>
                      <div className="text-amber-400">⚠️ Quando detecta risco, NÃO bloqueia a resposta da Ayria — só te avisa no dashboard.</div>
                    </div>
                  </div>

                  {/* ESTRUTURA DOS 3 NÍVEIS */}
                  <div>
                    <div className="text-xs font-bold text-ayria-text mb-2">📋 Estrutura esperada (3 níveis)</div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                      <div className="p-2 rounded" style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                        <div className="text-[10px] font-bold flex items-center gap-1 mb-1" style={{ color: '#FCA5A5' }}>
                          🚨 Nível 1 — URGÊNCIA
                        </div>
                        <div className="text-[10px] text-ayria-muted">
                          Suicídio, autolesão, homicídio
                        </div>
                      </div>
                      <div className="p-2 rounded" style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                        <div className="text-[10px] font-bold flex items-center gap-1 mb-1" style={{ color: '#FBBF24' }}>
                          ⚠️ Nível 2 — ATENÇÃO
                        </div>
                        <div className="text-[10px] text-ayria-muted">
                          Violência doméstica, crimes, abuso
                        </div>
                      </div>
                      <div className="p-2 rounded" style={{ background: 'rgba(168, 85, 247, 0.08)', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                        <div className="text-[10px] font-bold flex items-center gap-1 mb-1" style={{ color: '#C084FC' }}>
                          🎲 Nível 3 — ATENÇÃO
                        </div>
                        <div className="text-[10px] text-ayria-muted">
                          Vícios, compulsões, transtornos alimentares
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* CHAR COUNT + DIRTY */}
                <div className="flex items-center justify-between text-xs">
                  <span className="text-ayria-muted">
                    <strong style={{ color: editContent.length >= 200 ? '#4ADE80' : '#94A3B8' }}>
                      {charCount.toLocaleString('pt-BR')}
                    </strong>
                    {' '}chars · ~{Math.ceil(charCount / 4)} tokens
                  </span>
                  {dirty && <span style={{ color: '#F59E0B' }}>● não salvo</span>}
                </div>

                {/* TEXTAREA */}
                <div>
                  <label className="block text-xs font-semibold text-ayria-text mb-2 flex items-center gap-1">
                    <FileText size={12} />
                    Conteúdo do prompt (markdown)
                  </label>
                  <textarea
                    value={editContent}
                    onChange={(e) => {
                      setEditContent(e.target.value)
                      setDirty(true)
                    }}
                    spellCheck={false}
                    rows={16}
                    className="w-full px-4 py-3 outline-none resize-none font-mono text-xs text-ayria-text rounded-xl"
                    style={{
                      background: '#050505',
                      border: '1px solid #1E1E2E',
                      lineHeight: '1.6',
                    }}
                  />
                </div>

                {/* DESCRIPTION */}
                <div>
                  <label className="block text-xs font-semibold text-ayria-text mb-2">
                    Descrição da versão
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => {
                      setDescription(e.target.value)
                      setDirty(true)
                    }}
                    placeholder="ex: v2 — inclui Nível 2 e 3"
                    className="w-full px-3 py-2 rounded-lg text-sm text-ayria-text outline-none"
                    style={{ background: '#050505', border: '1px solid #1E1E2E' }}
                  />
                </div>

                {error && (
                  <div
                    className="p-3 rounded-lg flex items-start gap-2 text-xs"
                    style={{ background: 'rgba(239,68,68,0.1)', color: '#FCA5A5', border: '1px solid rgba(239,68,68,0.3)' }}
                  >
                    <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                    {error}
                  </div>
                )}

                {success && (
                  <div
                    className="p-3 rounded-lg flex items-start gap-2 text-xs"
                    style={{ background: 'rgba(74,222,128,0.1)', color: '#86EFAC', border: '1px solid rgba(74,222,128,0.3)' }}
                  >
                    <CheckCircle2 size={14} className="flex-shrink-0 mt-0.5" />
                    {success}
                  </div>
                )}
              </>
            )}
          </div>

          {/* FOOTER */}
          <div
            className="flex items-center justify-between gap-2 px-5 py-3 border-t"
            style={{ borderColor: '#1E1E2E', background: 'rgba(0,0,0,0.3)' }}
          >
            <div className="flex items-center gap-2">
              <button
                onClick={handleRestore}
                disabled={saving || !isCustom || loading}
                className="px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1 disabled:opacity-50"
                style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#F59E0B', border: '1px solid rgba(245, 158, 11, 0.3)' }}
                title="Restaurar prompt pro padrão (arquivo .md)"
              >
                <RotateCcw size={12} />
                Restaurar padrão
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onClose()}
                disabled={saving}
                className="px-4 py-2 rounded-lg text-xs font-medium text-ayria-muted hover:text-ayria-text"
              >
                Fechar
              </button>
              <button
                onClick={() => handleSave(editContent)}
                disabled={saving || loading || !dirty}
                className="px-5 py-2 rounded-lg text-sm font-semibold text-white flex items-center gap-2 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #EF4444, #DC2626)' }}
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                {saving ? 'Salvando...' : 'Salvar prompt crítico'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* MODAL DE CHAT (interno) */}
      {chatOpen && (
        <PromptChatModal
          open={chatOpen}
          onClose={() => setChatOpen(false)}
          promptKey="supervisor_seguranca_crise"
          promptLabel="Supervisor — Segurança e Crise (3 níveis)"
          onSaved={handleChatSave}
          onSaveAndCreate={handleChatAutoSave}
        />
      )}
    </>
  )
}
