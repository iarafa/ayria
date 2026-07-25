import { useState, useEffect, useMemo } from 'react'
import { Receipt } from 'lucide-react'
import { adminApi, api } from '../../../lib/api'

/**
 * CommissionsTabInline - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function CommissionsTabInline() {
  const [commissions, setCommissions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<'pending' | 'paid' | 'all'>('pending')
  const [searchPartner, setSearchPartner] = useState('')
  const [totals, setTotals] = useState<{ pending_cents: number; paid_cents: number }>({ pending_cents: 0, paid_cents: 0 })

  const reload = async () => {
    setLoading(true)
    try {
      const r = await api.get<any>('/api/admin/commissions')
      const data = r.data || {}
      setCommissions(data.items || [])
      setTotals({ pending_cents: data.total_pending_cents || 0, paid_cents: data.total_paid_cents || 0 })
    } catch (e: any) { console.error(e) }
    finally { setLoading(false) }
  }
  useEffect(() => { reload() }, [])

  const handlePay = async (redemptionId: string) => {
    const note = prompt('Motivo do pagamento (auditoria):') || ''
    if (note === null) return
    setPaying(redemptionId)
    try {
      await api.post(`/api/admin/commissions/${redemptionId}/pay`, { notes: note })
      await reload()
      alert('✅ Comissão marcada como paga!')
    } catch (e: any) { alert('❌ ' + (e.response?.data?.detail || e.message)) }
    finally { setPaying(null) }
  }

  // Agrupa por mês (YYYY-MM) — Rafael: "ela deveria mostrar oq tem pra pagar, no mes"
  const groupedByMonth = useMemo(() => {
    const filtered = commissions.filter((c) => {
      if (filterStatus === 'pending' && c.payout_status === 'paid') return false
      if (filterStatus === 'paid' && c.payout_status !== 'paid') return false
      if (searchPartner.trim()) {
        const q = searchPartner.toLowerCase()
        const hay = `${c.partner_name || ''} ${c.coupon_code || ''} ${c.user_email || ''}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })

    const byMonth: Record<string, { label: string; total_cents: number; pending_cents: number; items: any[] }> = {}
    for (const c of filtered) {
      if (!c.created_at) continue
      const d = new Date(c.created_at)
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      const label = d.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' }).toUpperCase()
      if (!byMonth[key]) byMonth[key] = { label, total_cents: 0, pending_cents: 0, items: [] }
      byMonth[key].items.push(c)
      byMonth[key].total_cents += c.commission_amount_cents || 0
      if (c.payout_status !== 'paid') byMonth[key].pending_cents += c.commission_amount_cents || 0
    }
    // Ordena por mês desc (mais recente primeiro)
    return Object.entries(byMonth).sort((a, b) => b[0].localeCompare(a[0]))
  }, [commissions, filterStatus, searchPartner])

  return (
    <div>
      {/* Header com título + cards de totais globais */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h2 className="text-2xl font-bold text-ayria-text flex items-center gap-2"><Receipt size={24}/>Comissões de Parceiros</h2>
        <div className="flex gap-3 text-xs">
          <div className="px-3 py-1.5 rounded-lg" style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.3)' }}>
            Total pendente: <span className="font-bold">R$ {(totals.pending_cents / 100).toFixed(2)}</span>
          </div>
          <div className="px-3 py-1.5 rounded-lg" style={{ background: 'rgba(16,185,129,0.1)', color: '#10B981', border: '1px solid rgba(16,185,129,0.3)' }}>
            Total pago: <span className="font-bold">R$ {(totals.paid_cents / 100).toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3 mb-5 p-3 rounded-xl" style={{ background: '#12121f', border: '1px solid #1f1f2e' }}>
        <div className="flex gap-1 rounded-lg p-0.5" style={{ background: '#0a0a14' }}>
          {([
            { key: 'pending', label: '⏳ Pendentes', color: '#F59E0B' },
            { key: 'paid', label: '✅ Pagas', color: '#10B981' },
            { key: 'all', label: '📋 Todas', color: '#818CF8' },
          ] as const).map((opt) => (
            <button key={opt.key} onClick={() => setFilterStatus(opt.key)}
              className="px-3 py-1.5 rounded-md text-xs font-medium transition-all"
              style={{
                background: filterStatus === opt.key ? opt.color : 'transparent',
                color: filterStatus === opt.key ? '#fff' : opt.color,
              }}>
              {opt.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px]">
          <input type="text" value={searchPartner} onChange={(e) => setSearchPartner(e.target.value)}
            placeholder="Buscar por parceiro, cupom ou email..."
            className="w-full pl-3 pr-3 py-1.5 rounded-lg text-xs"
            style={{ background: '#0a0a14', border: '1px solid #2a2a3e', color: '#fff' }} />
        </div>
        <button onClick={reload} className="px-3 py-1.5 rounded-lg text-xs text-ayria-muted hover:text-ayria-text" style={{ border: '1px solid #2a2a3e' }}>🔄 Atualizar</button>
      </div>

      {/* Lista agrupada por mês */}
      {loading && <div className="text-ayria-muted text-center py-12">Carregando...</div>}
      {!loading && groupedByMonth.length === 0 && (
        <div className="text-ayria-muted text-center py-12 p-6 rounded-xl" style={{ background: '#12121f', border: '1px dashed #2a2a3e' }}>
          {filterStatus === 'pending' ? '🎉 Nenhuma comissão pendente! Tudo pago.' : 'Nenhuma comissão encontrada com esses filtros.'}
        </div>
      )}
      {groupedByMonth.map(([monthKey, month]) => (
        <div key={monthKey} className="mb-6">
          {/* Cabeçalho do mês */}
          <div className="flex items-center justify-between mb-2 px-1">
            <h3 className="text-sm font-bold tracking-wider text-ayria-muted uppercase">{month.label}</h3>
            <div className="flex gap-2 text-xs">
              <span style={{ color: '#F59E0B' }}>Pendente: <span className="font-bold">R$ {(month.pending_cents / 100).toFixed(2)}</span></span>
              {month.pending_cents !== month.total_cents && (
                <span className="text-ayria-muted">· Total: <span className="font-bold">R$ {(month.total_cents / 100).toFixed(2)}</span></span>
              )}
            </div>
          </div>

          {/* Lista de comissões do mês */}
          <div className="space-y-2">
            {month.items.map((c) => (
              <div key={c.id} className="p-3 rounded-xl flex items-center justify-between gap-3" style={{ background: '#1a1a2e', border: `1px solid ${c.payout_status === 'paid' ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}` }}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-sm font-bold text-ayria-text">{c.coupon_code || '—'}</span>
                    <span style={{ color: '#818CF8' }}>·</span>
                    <span className="text-sm text-ayria-text">{c.partner_name || 'sem parceiro'}</span>
                    <span style={{ color: '#818CF8' }}>·</span>
                    <span className="text-xs text-ayria-muted">{c.user_email}</span>
                    <span className="text-xs px-2 py-0.5 rounded" style={{ background: c.payout_status === 'paid' ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)', color: c.payout_status === 'paid' ? '#10B981' : '#F59E0B' }}>
                      {c.payout_status === 'paid' ? '✅ PAGO' : '⏳ PENDENTE'}
                    </span>
                  </div>
                  <div className="text-xs text-ayria-muted mt-1">
                    Plano: <span className="text-ayria-text">{c.plan_slug || '—'}</span>
                    {' · '}Usuário pagou: R$ {((c.original_amount_cents || 0) / 100).toFixed(2)}
                    {c.discount_amount_cents > 0 && <span className="text-green-400"> (desc R$ {(c.discount_amount_cents / 100).toFixed(2)})</span>}
                    {' · '}{new Date(c.created_at).toLocaleDateString('pt-BR')}
                    {c.payout_at && <span className="text-green-400"> · pago em {new Date(c.payout_at).toLocaleDateString('pt-BR')}</span>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-base font-bold text-ayria-text">R$ {((c.commission_amount_cents || 0) / 100).toFixed(2)}</div>
                  {c.commission_pct > 0 && <div className="text-xs text-ayria-muted">{c.commission_pct}%</div>}
                </div>
                {c.payout_status !== 'paid' && (
                  <button onClick={() => handlePay(c.id)} disabled={paying === c.id}
                    className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium text-white disabled:opacity-50"
                    style={{ background: '#10B981' }}>
                    {paying === c.id ? '...' : '💸 Dar Baixa'}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
