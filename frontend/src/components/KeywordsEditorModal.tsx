/**
 * AYRIA - Keywords Editor Modal
 *
 * Editor do arquivo `keywords_crise.md` (a fonte das keywords que o
 * supervisor usa pra detectar sinais de risco).
 *
 * Funcionalidades:
 * - Carrega o conteúdo cru (markdown original, com ## N1/N2/N3/ATENCAO)
 * - Textarea grande com syntax highlight via CSS (cores por nível)
 * - Botão "Salvar" → PUT, com backup automático no servidor
 * - Botão "Restaurar padrão" → restaura o template hardcoded
 * - Confirmação antes de salvar (pode dar ruim)
 * - Diff visual de quantas linhas mudaram
 *
 * Comportamento do supervisor (NÃO bloqueia chat):
 *   N1/N2 = ALERTA URGÊNCIA (admin decide se bloqueia)
 *   N3/ATENCAO = ALERTA ATENÇÃO
 *   Sem keyword = NORMAL (sem IA)
 *
 * Hot reload no servidor: ao salvar, mtime muda, próximo match já é novo.
 */
import { useEffect, useState } from 'react'
import { X, Save, RotateCcw, AlertTriangle, Loader2, CheckCircle2, FileText } from 'lucide-react'
import { adminApi } from '../lib/api'

interface KeywordsEditorModalProps {
  open: boolean
  onClose: () => void
  onSaved?: () => void
}

export function KeywordsEditorModal({ open, onClose, onSaved }: KeywordsEditorModalProps) {
  const [content, setContent] = useState('')
  const [original, setOriginal] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [meta, setMeta] = useState<{ source: string; size_bytes: number } | null>(null)
  const [confirmSave, setConfirmSave] = useState(false)
  const [confirmRestore, setConfirmRestore] = useState(false)

  useEffect(() => {
    if (!open) return
    const load = async () => {
      setLoading(true)
      setError(null)
      setSuccess(null)
      setConfirmSave(false)
      setConfirmRestore(false)
      try {
        const { data } = await adminApi.getSupervisorKeywordsSource()
        setContent(data.content)
        setOriginal(data.content)
        setMeta({ source: data.source, size_bytes: data.size_bytes })
      } catch (e: any) {
        setError(e?.response?.data?.detail || 'Erro ao carregar keywords')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [open])

  // ESC fecha
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open && !saving && !restoring) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose, saving, restoring])

  if (!open) return null

  const dirty = content !== original
  const linesChanged =
    content.split('\n').filter((l, i) => l !== (original.split('\n')[i] ?? '')).length

  const handleSave = async () => {
    if (!dirty) {
      setError('Nada mudou. Edita o conteúdo antes de salvar.')
      return
    }
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await adminApi.saveSupervisorKeywordsSource(content)
      setSuccess(`✅ Salvo! Backup: ${data.backup.split('/').pop()} (${data.keywords_count} keywords)`)
      setOriginal(content)
      setConfirmSave(false)
      onSaved?.()
      // Auto-fechar após 2s
      setTimeout(() => {
        if (open) onClose()
      }, 2000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async () => {
    setRestoring(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await adminApi.restoreSupervisorKeywordsDefault()
      setSuccess(`✅ Padrão restaurado! Backup: ${data.backup.split('/').pop()}`)
      // Recarrega
      const src = await adminApi.getSupervisorKeywordsSource()
      setContent(src.data.content)
      setOriginal(src.data.content)
      setMeta({ source: src.data.source, size_bytes: src.data.size_bytes })
      setConfirmRestore(false)
      onSaved?.()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao restaurar')
    } finally {
      setRestoring(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(6px)' }}
      onClick={(saving || restoring || loading) ? undefined : onClose}
    >
      <div
        className="w-full max-w-4xl rounded-2xl flex flex-col"
        style={{
          background: '#0A0A0A',
          border: '1px solid #1E1E2E',
          maxHeight: '90vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: '#1E1E2E' }}>
          <div className="flex items-center gap-2">
            <FileText size={20} className="text-emerald-400" />
            <h3 className="text-lg font-bold text-ayria-text">Editor de Keywords de Crise</h3>
          </div>
          <button
            onClick={onClose}
            disabled={saving || restoring}
            className="text-ayria-muted hover:text-white disabled:opacity-30"
          >
            <X size={20} />
          </button>
        </div>

        {/* Meta info */}
        <div className="px-4 py-2 text-xs text-ayria-muted flex items-center gap-4 border-b" style={{ borderColor: '#1E1E2E' }}>
          <span>
            <strong className="text-ayria-text">Arquivo:</strong>{' '}
            <code className="font-mono">{meta?.source.split('/').pop() || '...'}</code>
          </span>
          <span>
            <strong className="text-ayria-text">Tamanho:</strong> {meta?.size_bytes || content.length} bytes
          </span>
          {dirty && (
            <span className="text-amber-400 font-bold">
              ✏️ {linesChanged} linha(s) alterada(s)
            </span>
          )}
          {!dirty && !loading && (
            <span className="text-green-400">✓ Sem mudanças</span>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 p-12 text-ayria-muted">
            <Loader2 size={18} className="animate-spin" />
            Carregando keywords...
          </div>
        ) : (
          <>
            {/* Editor */}
            <div className="flex-1 overflow-hidden p-4">
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                disabled={saving || restoring}
                className="w-full h-full p-3 rounded-lg text-sm font-mono resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                style={{
                  background: '#0f0f1e',
                  border: '1px solid #1E1E2E',
                  color: '#E5E7EB',
                  minHeight: '400px',
                  maxHeight: 'calc(90vh - 280px)',
                  lineHeight: '1.5',
                }}
                spellCheck={false}
              />
              <div
                className="text-[11px] text-ayria-muted mt-2 flex items-start gap-1.5"
              >
                <AlertTriangle size={12} className="mt-0.5" />
                <div>
                  <strong>Formato:</strong> cada categoria começa com <code className="text-emerald-300">## N1</code>, <code className="text-orange-300">## N2</code>, <code className="text-purple-300">## N3</code> ou <code className="text-yellow-300">## ATENCAO</code>.
                  Keywords são linhas começando com <code>- </code> e o texto entre aspas. <br />
                  <strong>Após salvar,</strong> a mudança vale INSTANTANEAMENTE (hot-reload por mtime, sem restart).
                </div>
              </div>
            </div>

            {/* Mensagens */}
            {error && (
              <div
                className="mx-4 mb-3 p-3 rounded-lg text-sm text-red-300 flex items-start gap-2"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}
              >
                <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
            {success && (
              <div
                className="mx-4 mb-3 p-3 rounded-lg text-sm text-green-300 flex items-start gap-2"
                style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)' }}
              >
                <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5" />
                <span>{success}</span>
              </div>
            )}

            {/* Confirmação de save */}
            {confirmSave && (
              <div
                className="mx-4 mb-3 p-3 rounded-lg"
                style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.4)' }}
              >
                <div className="text-sm text-amber-200 mb-2">
                  <strong>⚠️ Confirmar substituição?</strong> Backup do atual será criado.
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setConfirmSave(false)}
                    className="text-xs px-3 py-1 rounded"
                    style={{ background: '#1E1E2E' }}
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleSave}
                    className="text-xs px-3 py-1 rounded text-white font-bold"
                    style={{ background: 'linear-gradient(135deg, #22C55E, #16A34A)' }}
                  >
                    Sim, salvar
                  </button>
                </div>
              </div>
            )}

            {/* Confirmação de restore */}
            {confirmRestore && (
              <div
                className="mx-4 mb-3 p-3 rounded-lg"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.4)' }}
              >
                <div className="text-sm text-red-200 mb-2">
                  <strong>🚨 Restaurar padrão?</strong> Seu arquivo atual será substituído pelo template original (103 keywords). Backup será criado.
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setConfirmRestore(false)}
                    className="text-xs px-3 py-1 rounded"
                    style={{ background: '#1E1E2E' }}
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={handleRestore}
                    className="text-xs px-3 py-1 rounded text-white font-bold"
                    style={{ background: 'linear-gradient(135deg, #EF4444, #DC2626)' }}
                  >
                    Sim, restaurar
                  </button>
                </div>
              </div>
            )}

            {/* Botões */}
            <div className="p-4 border-t flex items-center gap-2" style={{ borderColor: '#1E1E2E' }}>
              <button
                onClick={onClose}
                disabled={saving || restoring}
                className="px-4 py-2 rounded-lg text-sm font-medium text-ayria-muted hover:text-white disabled:opacity-30"
                style={{ background: '#141420', border: '1px solid #1E1E2E' }}
              >
                Fechar
              </button>
              <button
                onClick={() => setConfirmRestore(true)}
                disabled={saving || restoring || confirmSave}
                className="px-4 py-2 rounded-lg text-sm font-medium text-red-300 hover:text-red-200 transition disabled:opacity-30 flex items-center gap-1.5"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}
                title="Restaurar palavras-chave padrão"
              >
                {restoring ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
                Restaurar padrão
              </button>
              <div className="flex-1" />
              {dirty && (
                <span className="text-xs text-amber-400">
                  ⚠️ {linesChanged} alteração(ões) não salvas
                </span>
              )}
              <button
                onClick={() => (confirmSave ? handleSave() : setConfirmSave(true))}
                disabled={saving || restoring || !dirty}
                className="px-4 py-2 rounded-lg text-sm font-bold text-white flex items-center gap-1.5 disabled:opacity-30 transition"
                style={{
                  background: dirty
                    ? 'linear-gradient(135deg, #22C55E, #16A34A)'
                    : '#1E1E2E',
                }}
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                {confirmSave ? 'Confirmar e salvar' : 'Salvar'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
