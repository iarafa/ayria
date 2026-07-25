import { useState, useEffect, useRef, useMemo } from 'react'
import { Activity, AlertTriangle, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { adminApi, api } from '../../../lib/api'
import { SupervisorPromptModal } from '../../../components/SupervisorPromptModal'
import { SupervisorKeywordsViewer } from '../../../components/SupervisorKeywordsViewer'
import { BlockUserModal } from '../../../components/BlockUserModal'

/**
 * SupervisionTab - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function SupervisionTab() {
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<any>(null)
  const [supPromptOpen, setSupPromptOpen] = useState(false)
  const [blockUserTarget, setBlockUserTarget] = useState<{ id: string; email: string; full_name?: string } | null>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filterStatus] = useState<string>('open')
  // 🆕 Sub-abas internas (08/07/2026 — antes era tudo numa página só, ficou bagunçado)
  const [subTab, setSubTab] = useState<'dashboard' | 'categories' | 'alerts' | 'config'>('dashboard')
  // 🆕 Paginação e filtros
  const [viewTab, setViewTab] = useState<'open' | 'history'>('open')
  // ref pra scrollar ao filtro quando um card N1/N2/N3 for clicado
  const alertsListRef = useRef<HTMLDivElement>(null)
  const scrollToAlerts = () => alertsListRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const [filterLevel, setFilterLevel] = useState<string>('all')  // 'all' | 'N1' | 'N2' | 'N3'
  const [filterOffset, setFilterOffset] = useState(0)
  const [alertsTotal, setAlertsTotal] = useState(0)
  const [alertsHistoryTotal, setAlertsHistoryTotal] = useState(0)
  const [alertsHasNext, setAlertsHasNext] = useState(false)
  const PAGE_SIZE = 20
  const [selectedAlert, setSelectedAlert] = useState<any>(null)
  const [selectedUserTimeline, setSelectedUserTimeline] = useState<any>(null)

  useEffect(() => {
    loadAll()
  }, [filterStatus, viewTab, filterLevel, filterOffset])

  async function loadAll() {
    setLoading(true)
    try {
      const params: any = {
        status: viewTab === 'open' ? 'open' : 'resolved',
        limit: PAGE_SIZE,
        offset: filterOffset,
      }
      if (filterLevel !== 'all') {
        params.level = filterLevel
      }

      const [dashRes, alertsRes, openCountRes, histCountRes] = await Promise.all([
        adminApi.getSupervisionDashboard(),
        adminApi.listAlerts(params),
        // contagem total pros badges (busca 1x por loadAll)
        filterOffset === 0 && filterLevel === 'all'
          ? adminApi.listAlerts({ status: 'open', limit: 1, offset: 0 })
          : Promise.resolve(null),
        filterOffset === 0 && filterLevel === 'all'
          ? adminApi.listAlerts({ status: 'resolved', limit: 1, offset: 0 })
          : Promise.resolve(null),
      ])
      const openTotal = openCountRes?.data?.total ?? 0
      const histTotal = histCountRes?.data?.total ?? 0
      setAlertsTotal(prev => (filterOffset === 0 && filterLevel === 'all' && viewTab === 'open') ? openTotal : prev)
      setAlertsHistoryTotal(prev => (filterOffset === 0 && filterLevel === 'all' && viewTab === 'history') ? histTotal : prev)
      setDashboard(dashRes.data)
      const ad = alertsRes.data || {}
      // Compat: backend retorna {items} ou lista nua (legado)
      const items = ad.items || ad || []
      setAlerts(items)
      setAlertsTotal(ad.total ?? items.length)
      setAlertsHasNext(ad.has_next ?? false)
      if (openCountRes && openCountRes.data) {
        setAlertsHistoryTotal(prev => prev)  // não sobrescrever
        setAlertsTotal(openCountRes.data.total ?? alertsTotal)
      }
      if (histCountRes && histCountRes.data) {
        setAlertsHistoryTotal(histCountRes.data.total ?? alertsHistoryTotal)
      }
    } catch (e: any) {
      console.error('Erro ao carregar supervisão:', e)
    } finally {
      setLoading(false)
    }
  }

  async function handleAlertAction(alertId: string, action: 'acknowledge' | 'resolve' | 'dismiss', notes?: string) {
    try {
      const fn = action === 'acknowledge' ? adminApi.acknowledgeAlert : action === 'resolve' ? adminApi.resolveAlert : adminApi.dismissAlert
      await fn(alertId, notes)
      await loadAll()
      if (selectedAlert?.id === alertId) {
        setSelectedAlert(null)
      }
    } catch (e: any) {
      alert('Erro: ' + (e.response?.data?.detail || e.message))
    }
  }


  if (loading && !dashboard) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-2 border-ayria-admin border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const counters = dashboard?.counters
  const recentUrg = dashboard?.recent_urgencias || []  

  return (
    <div className="space-y-6">
      {/* HEADER: Contadores */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} className="text-ayria-admin" />
          <div className="text-lg font-semibold text-ayria-text">Painel de Supervisão</div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => setSupPromptOpen(true)}
              className="text-xs px-3 py-1.5 rounded-lg font-semibold text-white border border-purple-500/40 hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, rgba(218,149,11,0.25), rgba(241,201,97,0.25))' }}
              title="Editar prompt crítico do supervisor"
            >
              🛡️ Editar Prompt Crítico
            </button>
            <button
              onClick={loadAll}
              className="text-xs px-3 py-1.5 rounded-lg bg-ayria-admin/10 text-ayria-admin border border-ayria-admin/30 hover:bg-ayria-admin/20"
            >
              ↻ Atualizar
            </button>
          </div>
        </div>

        {/* 🆕 SUB-ABAS INTERNAS (08/07/2026) — separa Dashboard, Categorias, Alertas, Config */}
        <div
          className="flex items-center gap-1 p-1 rounded-xl mb-4"
          style={{ background: '#111111', border: '1px solid #1E1E2E' }}
        >
          {[
            { key: 'dashboard',  label: '📊 Dashboard',  hint: 'Visão geral' },
            { key: 'categories', label: '🏷️ Categorias', hint: 'Keywords por nível' },
            { key: 'alerts',     label: '🚨 Alertas',    hint: 'Abertos + histórico' },
            { key: 'config',     label: '⚙️ Config',     hint: 'Comportamento do supervisor' },
          ].map(s => (
            <button
              key={s.key}
              onClick={() => { setSubTab(s.key as any); setFilterOffset(0) }}
              className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold transition-all flex flex-col items-center justify-center gap-0.5 ${
                subTab === s.key ? '' : 'text-ayria-muted hover:text-ayria-text'
              }`}
              style={subTab === s.key ? {
                background: 'linear-gradient(135deg, rgba(241,201,97,0.20), rgba(218,149,11,0.20))',
                color: '#C4B5FD',
                border: '1px solid rgba(218,149,11,0.4)',
              } : {}}
              title={s.hint}
            >
              <span>{s.label}</span>
              <span className="text-[9px] font-normal opacity-70">{s.hint}</span>
            </button>
          ))}
        </div>

        {/* 🆕 SUB-ABA: Dashboard (default) — cards + avisos */}
        {subTab === 'dashboard' && (
          <>
            {/* Banner de avisos importantes (08/07/2026) */}
            <div className="mb-4 p-3 rounded-xl" style={{ background: 'rgba(241,201,97,0.08)', border: '1px solid rgba(241,201,97,0.3)' }}>
              <div className="flex items-start gap-2">
                <span className="text-base">💡</span>
                <div className="flex-1 text-xs text-ayria-text">
                  <div className="font-semibold mb-1">Como funciona</div>
                  <ul className="text-ayria-muted space-y-0.5">
                    <li>• Categorias N1, N2, N3 são checadas em cada mensagem do usuário</li>
                    <li>• Keywords regex batem primeiro (pré-check); IA confirma depois</li>
                    <li>• <span className="text-red-300 font-bold">N1</span> = risco à vida · <span className="text-orange-300 font-bold">N2</span> = crimes/violência · <span className="text-purple-300 font-bold">N3</span> = vícios/compulsões</li>
                    <li>• Por padrão nenhuma categoria BLOQUEIA o chat — admin decide pela aba Alertas</li>
                  </ul>
                </div>
              </div>
            </div>

        <div className="grid grid-cols-5 gap-2">
          {/* TOTAL USERS - minimalista em 1 linha */}
          <div className="p-3 rounded-lg" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
            <div className="text-[10px] text-ayria-muted leading-none">Usuários ativos</div>
            <div className="text-xl font-bold text-ayria-text mt-1 leading-none">{counters?.total_users ?? 0}</div>
          </div>

          {/* ANÁLISES 24h - minimalista (sem bolinhas, redundante com cards N1/N2/N3) */}
          <div className="p-3 rounded-lg" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
            <div className="text-[10px] text-ayria-muted leading-none">Análises 24h</div>
            <div className="text-xl font-bold text-ayria-text mt-1 leading-none">{counters?.total_analyses_24h ?? 0}</div>
          </div>

          {/* NÍVEL 1 - risco à vida (URGÊNCIA) - CLICÁVEL, filtra lista */}
          <button
            type="button"
            onClick={() => {
              setViewTab('open')
              setFilterLevel('N1')
              setFilterOffset(0)
              setTimeout(() => scrollToAlerts(), 80)
            }}
            className="p-3 rounded-lg text-left transition-all hover:scale-[1.03] active:scale-[0.98]"
            style={{
              background: filterLevel === 'N1' && viewTab === 'open'
                ? 'rgba(239,68,68,0.20)'
                : 'rgba(239,68,68,0.08)',
              border: filterLevel === 'N1' && viewTab === 'open'
                ? '2px solid rgba(239,68,68,0.7)'
                : '1px solid rgba(239,68,68,0.4)',
              cursor: 'pointer',
            }}
            title="Filtrar alertas N1 (vida)"
          >
            <div className="flex items-baseline justify-between">
              <div className="text-[10px] text-red-300 font-bold leading-none">🚨 N1 — Vida</div>
              <div className="text-xl font-bold text-red-300 leading-none">{counters?.open_nivel1 ?? 0}</div>
            </div>
            <div className="text-[9px] text-ayria-muted mt-1 leading-none">
              {counters?.users_in_urgencia ?? 0} user(s) · clicar p/ filtrar ↓
            </div>
          </button>

          {/* NÍVEL 2 - crimes/violência (ATENÇÃO) - CLICÁVEL */}
          <button
            type="button"
            onClick={() => {
              setViewTab('open')
              setFilterLevel('N2')
              setFilterOffset(0)
              setTimeout(() => scrollToAlerts(), 80)
            }}
            className="p-3 rounded-lg text-left transition-all hover:scale-[1.03] active:scale-[0.98]"
            style={{
              background: filterLevel === 'N2' && viewTab === 'open'
                ? 'rgba(245,158,11,0.20)'
                : 'rgba(245,158,11,0.05)',
              border: filterLevel === 'N2' && viewTab === 'open'
                ? '2px solid rgba(245,158,11,0.7)'
                : '1px solid rgba(245,158,11,0.3)',
              cursor: 'pointer',
            }}
            title="Filtrar alertas N2 (crimes/violência)"
          >
            <div className="flex items-baseline justify-between">
              <div className="text-[10px] text-orange-400 font-bold leading-none">⚠️ N2 — Crimes</div>
              <div className="text-xl font-bold text-orange-300 leading-none">{counters?.open_nivel2 ?? 0}</div>
            </div>
            <div className="text-[9px] text-ayria-muted mt-1 leading-none">
              {counters?.open_nivel2 ?? 0} alerta(s) · clicar p/ filtrar ↓
            </div>
          </button>

          {/* NÍVEL 3 - vícios/compulsões (ATENÇÃO) - CLICÁVEL */}
          <button
            type="button"
            onClick={() => {
              setViewTab('open')
              setFilterLevel('N3')
              setFilterOffset(0)
              setTimeout(() => scrollToAlerts(), 80)
            }}
            className="p-3 rounded-lg text-left transition-all hover:scale-[1.03] active:scale-[0.98]"
            style={{
              background: filterLevel === 'N3' && viewTab === 'open'
                ? 'rgba(218,149,11,0.20)'
                : 'rgba(218,149,11,0.05)',
              border: filterLevel === 'N3' && viewTab === 'open'
                ? '2px solid rgba(218,149,11,0.7)'
                : '1px solid rgba(218,149,11,0.3)',
              cursor: 'pointer',
            }}
            title="Filtrar alertas N3 (vícios/compulsões)"
          >
            <div className="flex items-baseline justify-between">
              <div className="text-[10px] text-purple-400 font-bold leading-none">🎲 N3 — Vícios</div>
              <div className="text-xl font-bold text-purple-300 leading-none">{counters?.open_nivel3 ?? 0}</div>
            </div>
            <div className="text-[9px] text-ayria-muted mt-1 leading-none">
              {counters?.open_nivel3 ?? 0} alerta(s) · clicar p/ filtrar ↓
            </div>
          </button>
        </div>

        {/* (banner removido: 'aviso + total + Editar prompt' eram redundantes com os próprios cards
            e com o botão grande '🛡️ Editar Prompt Crítico' no header) */}
          </>
        )}

        {/* 🆕 SUB-ABA: Categorias — keywords por nível (read-only) */}
        {subTab === 'categories' && (
          <div>
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold text-ayria-text">📚 Keywords de Crise</div>
              <button
                onClick={() => setSupPromptOpen(true)}
                className="text-xs px-3 py-1.5 rounded-lg font-semibold text-white border border-purple-500/40 hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, rgba(218,149,11,0.25), rgba(241,201,97,0.25))' }}
                title="Editar keywords via Prompt Crítico"
              >
                ✏️ Editar Keywords
              </button>
            </div>
            <SupervisorKeywordsViewer />
          </div>
        )}

        {/* 🆕 SUB-ABA: Config — comportamento do supervisor */}
        {subTab === 'config' && (
          <div className="space-y-3">
            <div className="p-4 rounded-xl" style={{ background: 'rgba(241,201,97,0.08)', border: '1px solid rgba(241,201,97,0.3)' }}>
              <div className="flex items-start gap-2">
                <span className="text-lg">⚙️</span>
                <div className="flex-1">
                  <div className="font-semibold text-sm text-ayria-text mb-1">Comportamento atual</div>
                  <div className="text-xs text-ayria-muted">
                    NENHUMA categoria bloqueia o chat automaticamente. Admin decide via tela de Supervisão
                    (aba Alertas).
                  </div>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
              <div className="font-semibold text-sm text-ayria-text mb-2">🛡️ Prompt Crítico do Supervisor</div>
              <p className="text-xs text-ayria-muted mb-3">
                O supervisor usa este prompt + as keywords acima para analisar cada mensagem em batches.
                Edite com cuidado — mudanças afetam todos os usuários.
              </p>
              <button
                onClick={() => setSupPromptOpen(true)}
                className="text-xs px-4 py-2 rounded-lg font-semibold text-white border border-purple-500/40 hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, rgba(218,149,11,0.30), rgba(241,201,97,0.30))' }}
              >
                🛡️ Abrir Editor de Prompt Crítico
              </button>
            </div>
            <div className="p-4 rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
              <div className="font-semibold text-sm text-ayria-text mb-2">📊 Estatísticas do Qdrant (conhecimento_geral)</div>
              <div className="text-xs text-ayria-muted space-y-1">
                <div>• Collection: <span className="font-mono">conhecimento_geral</span></div>
                <div>• Source padrão: <span className="font-mono">prompt_keywords_crise</span></div>
                <div>• Para reindexar: aba Conhecimento → "Reindex RAG" (categoria supervisor)</div>
              </div>
            </div>
          </div>
        )}

        {/* 🆕 SUB-ABA: Alertas — lista + sub-tabs Abertos/Histórico + filtro */}
        {subTab === 'alerts' && (
          <div>
      {/* ═══════════════════════════════════════════════════════
          🆕 LAYOUT NOVO: 2 TABS (Abertos / Histórico) + filtro nível + paginação

          - Default: Abertos
          - Filtro por nível: Todos | N1 | N2 | N3 (com badges de cor)
          - Paginação: 20 por página (← anterior | X de Y | próxima →)
          - Histórico: abertos e fechados são coisas DIFERENTES, não mistura
          ═══════════════════════════════════════════════════════ */}
      <div
        className="flex items-center gap-1 p-1 rounded-xl mb-3"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <button
          onClick={() => { setViewTab('open'); setFilterOffset(0) }}
          className={`flex-1 px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${viewTab === 'open' ? '' : 'text-ayria-muted hover:text-ayria-text'}`}
          style={viewTab === 'open' ? {
            background: 'linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.1))',
            color: '#FCA5A5',
            border: '1px solid rgba(239,68,68,0.3)',
          } : {}}
        >
          🟢 Abertos
          {alertsTotal > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: 'rgba(239,68,68,0.3)', color: '#FFF' }}>
              {alertsTotal}
            </span>
          )}
        </button>
        <button
          onClick={() => { setViewTab('history'); setFilterOffset(0) }}
          className={`flex-1 px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 ${viewTab === 'history' ? '' : 'text-ayria-muted hover:text-ayria-text'}`}
          style={viewTab === 'history' ? {
            background: 'rgba(74,222,128,0.1)',
            color: '#86EFAC',
            border: '1px solid rgba(74,222,128,0.3)',
          } : {}}
        >
          🗃️ Histórico
          {alertsHistoryTotal > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: 'rgba(74,222,128,0.2)', color: '#FFF' }}>
              {alertsHistoryTotal}
            </span>
          )}
        </button>
      </div>

      {/* FILTRO POR NÍVEL */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="text-[10px] text-ayria-muted">Nível:</div>
        {[
          { key: 'all', label: 'Todos', color: '#94A3B8' },
          { key: 'N1', label: '🚨 N1', color: '#EF4444' },
          { key: 'N2', label: '⚠️ N2', color: '#F59E0B' },
          { key: 'N3', label: '🎲 N3', color: '#da950b' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => { setFilterLevel(f.key); setFilterOffset(0) }}
            className="text-[10px] px-2.5 py-1 rounded-lg font-semibold transition-all"
            style={filterLevel === f.key ? {
              background: `${f.color}26`,  // 26 = 15% alpha
              color: f.color,
              border: `1px solid ${f.color}80`,
            } : {
              background: 'transparent',
              color: '#94A3B8',
              border: '1px solid #1E1E2E',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* LISTA DE ALERTAS */}
      <div>
        <div className="text-sm font-semibold text-ayria-text mb-2 flex items-center gap-2">
          {viewTab === 'open' ? '🟢 Abertos' : '🗃️ Histórico'}
          {filterLevel !== 'all' && (
            <span className="text-[10px] px-2 py-0.5 rounded font-bold" style={{
              background: 'rgba(218,149,11,0.15)', color: '#C084FC'
            }}>
              filtro: {filterLevel}
            </span>
          )}
          <span className="text-[10px] text-ayria-muted ml-auto">
            {alertsTotal} {viewTab === 'history' ? 'no histórico' : 'aberto(s)'}
            {' '}· página {Math.floor(filterOffset / PAGE_SIZE) + 1} de {Math.max(1, Math.ceil(alertsTotal / PAGE_SIZE))}
          </span>
        </div>
        <div className="space-y-2" ref={alertsListRef}>
          {alerts.length === 0 && (
            <div className="p-6 text-center text-ayria-muted rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
              Nenhum alerta {filterStatus === 'open' ? 'aberto' : 'neste status'}. 🎉
            </div>
          )}
          {alerts.map((a) => (
            <div
              key={a.id}
              className="p-4 rounded-xl"
              style={{
                background: a.level === 'URGENCIA' ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)',
                border: `1px solid ${a.level === 'URGENCIA' ? 'rgba(239,68,68,0.3)' : 'rgba(245,158,11,0.3)'}`
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  {a.user_avatar_url ? (
                    <img src={a.user_avatar_url} className="w-10 h-10 rounded-full flex-shrink-0" alt="" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-ayria-admin/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold">{a.user_full_name?.[0] || a.user_email?.[0] || '?'}</span>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-ayria-text truncate">{a.user_full_name || a.user_email}</span>
                      <span className="text-xs text-ayria-muted">·</span>
                      <span className="text-xs text-ayria-muted truncate">{a.user_email}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                        a.level === 'URGENCIA' ? 'bg-red-500/20 text-red-300' : 'bg-yellow-500/20 text-yellow-300'
                      }`}>
                        {a.level}
                      </span>
                      {/* ✅ Status IA: confirmada / aguardando / descartada */}
                      {a.ia_confirmed === true && (
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded font-bold"
                          style={{ background: 'rgba(34,197,94,0.2)', color: '#86EFAC' }}
                          title="IA MiniMax-M3 confirmou que é risco real"
                        >
                          ✅ IA confirmou
                        </span>
                      )}
                      {a.ia_confirmed === false && (
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded font-bold animate-pulse"
                          style={{ background: 'rgba(251,191,36,0.2)', color: '#FBBF24' }}
                          title="Pré-check regex bateu keyword. IA ainda não confirmou (aguarda próximo batch — 15min)."
                        >
                          ⏳ Aguardando IA
                        </span>
                      )}
                      {a.ia_confirmed === null && (
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded font-bold opacity-50"
                          style={{ background: 'rgba(156,163,175,0.2)', color: '#9CA3AF' }}
                          title="Alerta criado antes da feature de confirmação IA (legado)"
                        >
                          ⚙️ Legado
                        </span>
                      )}
                      {a.occurrences > 1 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-ayria-admin/20 text-ayria-admin">
                          ×{a.occurrences}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-ayria-text mt-1">{a.title}</div>
                    {a.message && <div className="text-xs text-ayria-muted mt-0.5">{a.message}</div>}
                    {a.message_excerpt && (
                      <div className="text-xs italic text-ayria-muted mt-2 p-2 rounded" style={{ background: 'rgba(0,0,0,0.2)' }}>
                        "{a.message_excerpt}"
                      </div>
                    )}
                    <div className="text-[10px] text-ayria-muted mt-2">
                      Última ocorrência: {new Date(a.last_occurrence_at).toLocaleString('pt-BR')}
                    </div>
                  </div>
                </div>
                {/* ═══════════════════════════════════════════════════════
                    🆕 3 BOTÕES PRINCIPAIS (Opção A): OK / Ver / Bloquear
                    Removidos: Assumir, Timeline, Descartar (workflow interno)
                    ═══════════════════════════════════════════════════════ */}
                <div className="flex gap-1.5 flex-shrink-0 items-start">
                  {/* ✅ OK = Resolve */}
                  {(a.status === 'open' || a.status === 'acknowledged') ? (
                    <button
                      onClick={() => handleAlertAction(a.id, 'resolve')}
                      className="text-xs px-3 py-1.5 rounded-lg font-bold text-white transition-all hover:opacity-90"
                      style={{
                        background: 'linear-gradient(135deg, #22C55E, #16A34A)',
                        boxShadow: '0 0 12px rgba(34,197,94,0.25)',
                      }}
                      title="Fechar alerta: caso tratado"
                    >
                      ✓ OK
                    </button>
                  ) : (
                    <span className="text-xs px-3 py-1.5 rounded-lg font-bold opacity-50"
                      style={{ background: 'rgba(74,222,128,0.1)', color: '#86EFAC' }}
                    >
                      ✓ Fechado
                    </span>
                  )}

                  {/* 👁 Ver mensagem */}
                  <button
                    onClick={() => {
                      const qs = a.message_id
                        ? `?msg=${a.message_id}${a.chat_id ? `&chat=${a.chat_id}` : ''}`
                        : ''
                      navigate(`/admin/observe/${a.user_id}${qs}`)
                    }}
                    className="text-xs px-3 py-1.5 rounded-lg font-semibold transition-all hover:opacity-90"
                    style={{
                      background: 'rgba(245,158,11,0.15)',
                      color: '#FBBF24',
                      border: '1px solid rgba(245,158,11,0.4)',
                    }}
                    title={a.message_id ? 'Abrir mensagem que gerou este alerta' : 'Abrir chat do usuário'}
                  >
                    👁 Ver
                  </button>

                  {/* 🚫 Bloquear */}
                  <button
                    onClick={() => setBlockUserTarget({ id: a.user_id, email: a.user_email, full_name: a.user_full_name })}
                    className="text-xs px-3 py-1.5 rounded-lg font-semibold transition-all hover:opacity-90"
                    style={{
                      background: 'rgba(239,68,68,0.15)',
                      color: '#FCA5A5',
                      border: '1px solid rgba(239,68,68,0.4)',
                    }}
                    title="Bloquear acesso do usuário (1h / 24h / permanente)"
                  >
                    🚫 Bloquear
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ══════════════ PAGINAÇÃO ══════════════ */}
      {(alertsTotal > PAGE_SIZE || filterOffset > 0) && (
        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-ayria-muted">
            {alertsTotal > 0
              ? `Mostrando ${Math.min(PAGE_SIZE, alerts.length)} de ${alertsTotal}`
              : 'Nenhum alerta'}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setFilterOffset(Math.max(0, filterOffset - PAGE_SIZE))}
              disabled={filterOffset === 0}
              className="text-xs px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1 disabled:opacity-30"
              style={{ background: '#1E1E2E', color: '#94A3B8', border: '1px solid #2A2A3A' }}
            >
              ◀ Anterior
            </button>
            <span className="text-xs px-3 py-1.5 rounded-lg font-bold" style={{ background: 'rgba(218,149,11,0.1)', color: '#C084FC', border: '1px solid rgba(218,149,11,0.3)' }}>
              {Math.floor(filterOffset / PAGE_SIZE) + 1} / {Math.max(1, Math.ceil(alertsTotal / PAGE_SIZE))}
            </span>
            <button
              onClick={() => setFilterOffset(filterOffset + PAGE_SIZE)}
              disabled={!alertsHasNext}
              className="text-xs px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1 disabled:opacity-30"
              style={{ background: '#1E1E2E', color: '#94A3B8', border: '1px solid #2A2A3A' }}
            >
              Próxima ▶
            </button>
          </div>
        </div>
      )}

      {/* ÚLTIMAS URGÊNCIAS */}
      {recentUrg.length > 0 && (
        <div>
          <div className="text-sm font-semibold text-ayria-text mb-2 flex items-center gap-2">
            <AlertTriangle size={14} className="text-red-400" />
            Últimas URGÊNCIAS detectadas
          </div>
          <div className="space-y-2">
            {recentUrg.map((u) => (
              <div key={u.analysis_id} className="p-3 rounded-lg" style={{ background: '#111111', border: '1px solid rgba(239,68,68,0.2)' }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ayria-text">{u.user_full_name || u.user_email}</span>
                    <span className="text-xs text-ayria-muted">score {u.score?.toFixed(2)}</span>
                  </div>
                  <span className="text-[10px] text-ayria-muted">{new Date(u.created_at).toLocaleString('pt-BR')}</span>
                </div>
                {u.reason && <div className="text-xs text-ayria-muted mt-1">{u.reason}</div>}
                {u.signals && u.signals.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {u.signals.slice(0, 5).map((s: string, i: number) => (
                      <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-300">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: Timeline do user */}
      {selectedUserTimeline && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
          onClick={() => setSelectedUserTimeline(null)}
        >
          <div
            className="w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-2xl p-6"
            style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold text-ayria-text">Timeline de Supervisão</h3>
                <div className="text-sm text-ayria-muted">
                  {selectedUserTimeline.user.full_name || selectedUserTimeline.user.email}
                </div>
              </div>
              <button onClick={() => setSelectedUserTimeline(null)} className="text-ayria-muted hover:text-white">
                <X size={20} />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-4">
              <div className="p-2 rounded bg-green-500/10 text-center">
                <div className="text-xs text-green-400">NORMAL</div>
                <div className="text-lg font-bold text-green-300">{selectedUserTimeline.totals_by_level.NORMAL || 0}</div>
              </div>
              <div className="p-2 rounded bg-yellow-500/10 text-center">
                <div className="text-xs text-yellow-400">ATENÇÃO</div>
                <div className="text-lg font-bold text-yellow-300">{selectedUserTimeline.totals_by_level.ATENCAO || 0}</div>
              </div>
              <div className="p-2 rounded bg-red-500/10 text-center">
                <div className="text-xs text-red-400">URGÊNCIA</div>
                <div className="text-lg font-bold text-red-300">{selectedUserTimeline.totals_by_level.URGENCIA || 0}</div>
              </div>
            </div>

            {selectedUserTimeline.last_analysis && (
              <div className="p-3 rounded mb-3" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
                <div className="text-xs text-ayria-muted">Última análise</div>
                <div className="text-sm text-ayria-text">
                  <span className="font-medium">{selectedUserTimeline.last_analysis.level}</span> (score {selectedUserTimeline.last_analysis.score.toFixed(2)})
                </div>
                {selectedUserTimeline.last_analysis.reason && (
                  <div className="text-xs text-ayria-muted mt-1">{selectedUserTimeline.last_analysis.reason}</div>
                )}
                <div className="text-[10px] text-ayria-muted mt-1">
                  {new Date(selectedUserTimeline.last_analysis.created_at).toLocaleString('pt-BR')}
                </div>
              </div>
            )}

            {selectedUserTimeline.open_alerts.length > 0 && (
              <div className="mb-3">
                <div className="text-sm font-semibold text-ayria-text mb-1">Alertas abertos</div>
                {selectedUserTimeline.open_alerts.map((a: any) => (
                  <div key={a.id} className="p-2 rounded text-xs" style={{ background: 'rgba(239,68,68,0.1)' }}>
                    {a.level} · ×{a.occurrences} · {new Date(a.created_at).toLocaleString('pt-BR')}
                  </div>
                ))}
              </div>
            )}

            {selectedUserTimeline.daily_history.length > 0 && (
              <div>
                <div className="text-sm font-semibold text-ayria-text mb-1">Histórico (últimos 7 dias)</div>
                {selectedUserTimeline.daily_history.map((d: any) => (
                  <div key={d.date} className="p-2 rounded text-xs mb-1" style={{ background: '#111111' }}>
                    <div className="flex justify-between">
                      <span className="text-ayria-muted">{new Date(d.date).toLocaleDateString('pt-BR')}</span>
                      <span className="text-ayria-text">{d.total} msgs · max {d.max_score.toFixed(2)}</span>
                    </div>
                    <div className="flex gap-2 mt-0.5 text-[10px]">
                      <span className="text-green-400">🟢 {d.normal}</span>
                      <span className="text-yellow-400">🟡 {d.atencao}</span>
                      <span className="text-red-400">🔴 {d.urgencia}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <button
                onClick={() => {
                  navigate(`/admin/observe/${selectedUserTimeline.user.id}`)
                  setSelectedUserTimeline(null)
                }}
                className="flex-1 px-3 py-2 rounded-lg text-sm bg-orange-500/20 text-orange-300 border border-orange-500/30"
              >
                👁 Abrir no Modo Observador
              </button>
            </div>
          </div>
        </div>
      )}
          </div>
        )}
      </div>

      {/* ============================================================ */}
      {/* MODAL DE EDIÇÃO DO PROMPT DO SUPERVISOR (aberto pelo botão) */}
      {/* ============================================================ */}
      <SupervisorPromptModal
        open={supPromptOpen}
        onClose={() => setSupPromptOpen(false)}
        onSaved={() => loadAll()}
      />

      {/* ═══════════════════════════════════════════════
          🆕 MODAL: Bloquear/Desbloquear usuário
          ═══════════════════════════════════════════════ */}
      <BlockUserModal
        open={!!blockUserTarget}
        onClose={() => setBlockUserTarget(null)}
        user={blockUserTarget}
        onSuccess={() => loadAll()}
      />
    </div>
  )
}



// ============================================================
// 🆕 22/07 20:38 — GESTÃO DE ADMINISTRADORES (só SUPER_ADMIN)
// Inclui / Exclui / Altera outros admins
// ============================================================