/**
 * AYRIA - Supervisor Keywords Viewer
 *
 * Painel LEITURA das keywords de crise que o supervisor usa pra detectar
 * sinais de risco. Não tem editor (por enquanto) — só lista organizado por
 * categoria com cores.
 *
 * Importante: nenhuma categoria BLOQUEIA o chat automaticamente. O admin é
 * quem decide se bloqueia ou não na tela de Supervisão.
 */
import { useEffect, useState } from 'react'
import { Eye, EyeOff, Loader2, FileText, AlertCircle, Shield, Edit3 } from 'lucide-react'
import { adminApi } from '../lib/api'
import { KeywordsEditorModal } from './KeywordsEditorModal'

interface KeywordCategory {
  key: string
  label: string
  color: string
  count: number
  patterns: string[]
}

export function SupervisorKeywordsViewer() {
  const [data, setData] = useState<{
    source: string
    comportamento_atual: string
    categorias: KeywordCategory[]
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [editorOpen, setEditorOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [openCats, setOpenCats] = useState<Record<string, boolean>>({
    N1: true,
    N2: false,
    N3: false,
    ATENCAO: false,
  })

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const { data: d } = await adminApi.getSupervisorKeywords()
        if (alive) setData(d)
      } catch (e) {
        // silencioso — admin pode não ter permissão
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    return () => {
      alive = false
    }
  }, [reloadKey])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-ayria-muted p-3">
        <Loader2 size={14} className="animate-spin" />
        Carregando keywords...
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex items-center gap-2 text-xs text-amber-400 p-3 rounded-lg"
           style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
        <AlertCircle size={14} />
        Endpoint <code className="font-mono">/api/admin/supervisor/keywords</code> indisponível.
      </div>
    )
  }

  return (
    <div
      className="rounded-2xl p-4 mt-4"
      style={{ background: '#0f0f1e', border: '1px solid #1E1E2E' }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Shield size={16} className="text-ayria-admin" />
        <div className="text-sm font-semibold text-ayria-text">
          Keywords de Crise
        </div>
        <div className="ml-auto flex items-center gap-3">
          <div className="text-[10px] text-ayria-muted hidden sm:block">
            Fonte: <code className="font-mono">{data.source?.split('/').pop()}</code>
          </div>
          <button
            onClick={() => setEditorOpen(true)}
            className="text-xs px-2.5 py-1 rounded-lg flex items-center gap-1 font-semibold transition-all hover:opacity-90"
            style={{
              background: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(20,184,166,0.15))',
              color: '#6EE7B7',
              border: '1px solid rgba(16,185,129,0.3)',
            }}
            title="Editar arquivo keywords_crise.md (hot-reload)"
          >
            <Edit3 size={12} />
            Editar
          </button>
        </div>
      </div>

      {/* Aviso novo comportamento */}
      <div
        className="flex items-start gap-2 text-xs p-2 rounded mb-3"
        style={{
          background: 'rgba(34,197,94,0.08)',
          border: '1px solid rgba(34,197,94,0.25)',
        }}
      >
        <AlertCircle size={14} className="text-green-400 flex-shrink-0 mt-0.5" />
        <span className="text-green-200/90">
          <strong>⚙️ Comportamento atual:</strong> {data.comportamento_atual}
        </span>
      </div>

      {/* Categorias */}
      <div className="space-y-2">
        {data.categorias.map((cat) => {
          const open = openCats[cat.key] ?? false
          return (
            <div
              key={cat.key}
              className="rounded-lg overflow-hidden"
              style={{
                background: `${cat.color}0a`, // 4% alpha
                border: `1px solid ${cat.color}40`,
              }}
            >
              <button
                onClick={() => setOpenCats((p) => ({ ...p, [cat.key]: !open }))}
                className="w-full px-3 py-2 flex items-center gap-2 text-left hover:opacity-80 transition"
              >
                {open ? <Eye size={14} /> : <EyeOff size={14} />}
                <span
                  className="text-xs font-bold uppercase"
                  style={{ color: cat.color }}
                >
                  {cat.key}
                </span>
                <span className="text-xs text-ayria-muted">— {cat.label}</span>
                <span className="ml-auto text-xs text-ayria-muted">
                  {cat.count} {cat.count === 1 ? 'padrão' : 'padrões'}
                </span>
              </button>

              {open && (
                <div
                  className="px-3 py-2 border-t"
                  style={{ borderColor: `${cat.color}30` }}
                >
                  {cat.patterns.length === 0 ? (
                    <div className="text-xs text-ayria-muted italic">
                      (sem keywords nesta categoria)
                    </div>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {cat.patterns.map((p, i) => (
                        <span
                          key={i}
                          className="text-[11px] px-2 py-0.5 rounded font-mono"
                          style={{
                            background: `${cat.color}15`,
                            color: cat.color,
                            border: `1px solid ${cat.color}40`,
                          }}
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Hint */}
      <div className="mt-3 text-[11px] text-ayria-muted flex items-start gap-1.5">
        <FileText size={12} className="mt-0.5" />
        <span>
          Hot-reload por mtime — editar o arquivo MD atualiza sem reiniciar.
          Total: <strong>{data.categorias.reduce((s, c) => s + c.count, 0)}</strong> keywords.
        </span>
      </div>

      {/* Modal de edição */}
      <KeywordsEditorModal
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        onSaved={() => setReloadKey((k) => k + 1)}
      />
    </div>
  )
}
