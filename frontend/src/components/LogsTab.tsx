/**
 * AYRIA - Admin Tab: LOGS
 *
 * Mostra TODOS os logs do sistema num lugar só:
 * - Backend (arquivo /app/logs/ayria.log)
 * - Frontend (erros enviados via /api/admin/log/event)
 *
 * Recursos:
 * - Auto-refresh a cada 5s
 * - Filtro por substring
 * - Filtro por nível (INFO/WARNING/ERROR/EXCEPTION)
 * - Botão "Atualizar agora"
 * - Highlight de erros em vermelho
 */
import { useEffect, useState, useCallback } from 'react'
import { adminApi } from '../lib/api'
import { AlertCircle, CheckCircle2, AlertTriangle, Info, RefreshCw, Filter, X } from 'lucide-react'

const LEVELS = ['all', 'ERROR', 'EXCEPTION', 'WARNING', 'INFO'] as const
type Level = typeof LEVELS[number]

export function LogsTab() {
  const [logText, setLogText] = useState<string>('')
  const [lines, setLines] = useState<number>(300)
  const [filter, setFilter] = useState('')
  const [level, setLevel] = useState<Level>('all')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<{ files: number; total_errors: number } | null>(null)

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Carrega info do log
      const infoRes = await adminApi.debugLogInfo()
      setInfo({
        files: infoRes.data?.files?.length || 0,
        total_errors: infoRes.data?.errors_count_last_1000 || 0,
      })

      // Carrega conteúdo
      const params: any = { lines }
      if (filter) params.filter = filter
      if (level !== 'all') params.level = level
      const res = await adminApi.debugLog(params)
      setLogText(typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2))
      setLastUpdate(new Date())
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Erro ao carregar logs')
    } finally {
      setLoading(false)
    }
  }, [lines, filter, level])

  // Auto-refresh
  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(fetchLogs, 5000)
    return () => clearInterval(id)
  }, [autoRefresh, fetchLogs])

  const parseLine = (line: string): { level: string; color: string; icon: any } => {
    if (/\bERROR\b|\bEXCEPTION\b|\bTraceback\b|\bUNCAUGHT\b/.test(line)) {
      return { level: 'ERROR', color: '#EF4444', icon: AlertCircle }
    }
    if (/❌/.test(line)) {
      return { level: 'ERROR', color: '#EF4444', icon: AlertCircle }
    }
    if (/\bWARNING\b|⚠️/.test(line)) {
      return { level: 'WARN', color: '#F59E0B', icon: AlertTriangle }
    }
    if (/\bINFO\b/.test(line)) {
      return { level: 'INFO', color: '#10B981', icon: Info }
    }
    return { level: 'LOG', color: '#94A3B8', icon: CheckCircle2 }
  }

  const logLines = logText.split('\n').filter(Boolean)
  const errorCount = logLines.filter(l => /\bERROR\b|\bEXCEPTION\b|\bTraceback\b|❌/.test(l)).length
  const warnCount = logLines.filter(l => /\bWARNING\b|⚠️/.test(l)).length

  return (
    <div className="space-y-4">
      {/* Header */}
      <div
        className="p-5 rounded-2xl"
        style={{
          background: 'linear-gradient(135deg, rgba(239,68,68,0.10), rgba(245,158,11,0.10))',
          border: '1px solid rgba(239, 68, 68, 0.3)',
        }}
      >
        <div className="flex items-start gap-3">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #EF4444, #F59E0B)' }}
          >
            <AlertCircle size={18} className="text-white" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold gradient-text mb-1">Logs do Sistema</h2>
            <p className="text-sm text-ayria-muted leading-relaxed">
              <strong className="text-ayria-text">Tudo que acontece no AYRIA, num lugar só.</strong>{' '}
              Backend, frontend, requisições, erros, exceções — auto-refresh a cada 5s.
            </p>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label="Erros"
          value={errorCount}
          color={errorCount > 0 ? '#EF4444' : '#10B981'}
          icon={<AlertCircle size={14} />}
        />
        <StatCard
          label="Avisos"
          value={warnCount}
          color={warnCount > 0 ? '#F59E0B' : '#10B981'}
          icon={<AlertTriangle size={14} />}
        />
        <StatCard
          label="Linhas"
          value={logLines.length}
          color="#da950b"
          icon={<Info size={14} />}
        />
        <StatCard
          label="Arquivos"
          value={info?.files ?? '—'}
          color="#f1c961"
          icon={<Filter size={14} />}
        />
      </div>

      {/* Filtros */}
      <div
        className="p-4 rounded-xl flex flex-wrap items-center gap-3"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <Filter size={14} className="text-ayria-muted" />
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filtrar (ex: FRONTEND, qdrant, login...)"
            className="flex-1 px-3 py-1.5 rounded text-sm text-ayria-text outline-none"
            style={{ background: '#050505', border: '1px solid #1E1E2E' }}
          />
          {filter && (
            <button onClick={() => setFilter('')} className="text-ayria-muted hover:text-ayria-text">
              <X size={14} />
            </button>
          )}
        </div>

        <div className="flex gap-1">
          {LEVELS.map((lvl) => (
            <button
              key={lvl}
              onClick={() => setLevel(lvl)}
              className="px-3 py-1.5 rounded text-xs font-semibold transition-colors"
              style={{
                background: level === lvl ? 'rgba(218,149,11,0.2)' : 'transparent',
                color: level === lvl ? '#C084FC' : '#94A3B8',
                border: '1px solid',
                borderColor: level === lvl ? 'rgba(218,149,11,0.4)' : '#1E1E2E',
              }}
            >
              {lvl === 'all' ? 'TODOS' : lvl}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={lines}
            onChange={(e) => setLines(Number(e.target.value))}
            className="px-2 py-1.5 rounded text-xs text-ayria-text outline-none"
            style={{ background: '#050505', border: '1px solid #1E1E2E' }}
          >
            <option value={100}>100 linhas</option>
            <option value={300}>300 linhas</option>
            <option value={1000}>1000 linhas</option>
            <option value={3000}>3000 linhas</option>
          </select>
        </div>

        <label className="flex items-center gap-2 text-xs text-ayria-muted cursor-pointer">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="accent-purple-500"
          />
          Auto-refresh 5s
        </label>

        <button
          onClick={fetchLogs}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg font-semibold text-white flex items-center gap-1.5 disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, #da950b, #f1c961)' }}
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl text-sm" style={{ background: 'rgba(239,68,68,0.1)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.3)' }}>
          ❌ {error}
        </div>
      )}

      {/* Log content */}
      <div
        className="rounded-2xl overflow-hidden"
        style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}
      >
        <div className="px-4 py-2 flex items-center justify-between text-xs" style={{ borderBottom: '1px solid #1E1E2E', background: '#050505' }}>
          <span className="text-ayria-muted">
            {lastUpdate ? `Última atualização: ${lastUpdate.toLocaleTimeString('pt-BR')}` : 'Carregando...'}
          </span>
          <span className="text-ayria-muted">
            {logLines.length} linha{logLines.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div
          className="p-4 overflow-auto font-mono text-xs"
          style={{ maxHeight: '70vh', minHeight: '400px' }}
        >
          {logLines.length === 0 ? (
            <div className="text-ayria-muted text-center py-12">
              {loading ? 'Carregando logs...' : '(sem logs no momento)'}
            </div>
          ) : (
            logLines.map((line, i) => {
              const { color } = parseLine(line)
              return (
                <div
                  key={i}
                  className="hover:bg-[#111111] px-2 py-0.5 rounded whitespace-pre-wrap break-all"
                  style={{
                    color,
                    borderLeft: `2px solid ${color}`,
                    paddingLeft: '8px',
                    marginBottom: '2px',
                  }}
                >
                  {line}
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Info footer */}
      <div className="p-3 rounded-xl text-xs text-ayria-muted" style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}>
        <div className="font-semibold text-ayria-text mb-1">💡 Sobre os logs</div>
        <div>O backend grava tudo em <code className="px-1 py-0.5 rounded" style={{ background: '#1E1E2E' }}>/app/logs/ayria.log</code> (rotacionado quando fica grande).</div>
        <div className="mt-1">Erros do frontend chegam aqui via <code className="px-1 py-0.5 rounded" style={{ background: '#1E1E2E' }}>POST /api/admin/log/event</code> e aparecem como <code style={{ color: '#EF4444' }}>[FRONTEND]</code>.</div>
        <div className="mt-1">Auto-refresh atualiza a cada 5s — você vê erros em tempo real.</div>
      </div>
    </div>
  )
}

function StatCard({ label, value, color, icon }: { label: string; value: number | string; color: string; icon: React.ReactNode }) {
  return (
    <div
      className="p-3 rounded-xl flex items-center gap-3"
      style={{ background: '#111111', border: '1px solid #1E1E2E' }}
    >
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: `${color}22`, color }}
      >
        {icon}
      </div>
      <div>
        <div className="text-[10px] text-ayria-muted uppercase tracking-wider">{label}</div>
        <div className="text-lg font-bold" style={{ color }}>{value}</div>
      </div>
    </div>
  )
}