import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, DollarSign, Tag, Users, Clock, RefreshCw, ExternalLink, TrendingUp, LogOut } from 'lucide-react'
import { api } from '../lib/api'

const PARTNER_TOKEN_KEY = 'ayria_partner_token'
const PARTNER_INFO_KEY = 'ayria_partner_info'

/**
 * 🆕 26/07/2026 22:35 — Portal do Parceiro
 *
 * Mostra:
 *  - Cabeçalho com nome do parceiro + saldo (pendente / pago)
 *  - Lista de cupons (ativos + soft-deletados, badge diferenciando)
 *  - Histórico completo de resgates (comissão, plano, user, data)
 *  - Resumo: total de resgates, receita total gerada pros usuários
 *
 * Acesso:
 *  - Admin passa o link /partner/:id pela lista de parceiros
 *  - (futuro) Parceiro autenticado via sessão própria
 *
 * Endpoints usados:
 *  - GET /api/partner/me/coupons?partner_id=X
 *  - GET /api/partner/me/redemptions?partner_id=X
 */
export function PartnerPortalPage() {
  const { partnerId } = useParams<{ partnerId: string }>()
  const navigate = useNavigate()
  const [coupons, setCoupons] = useState<any[]>([])
  const [redemptions, setRedemptions] = useState<any[]>([])
  const [partner, setPartner] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  // 🆕 26/07/2026 22:43 — Usa JWT de parceiro quando logado
  const partnerToken = localStorage.getItem(PARTNER_TOKEN_KEY)
  const partnerInfo = JSON.parse(localStorage.getItem(PARTNER_INFO_KEY) || 'null')

  // Se logou como parceiro, ignora partnerId da URL e usa o dele
  const effectivePartnerId = partnerToken ? partnerInfo?.id : partnerId

  const reload = async () => {
    setLoading(true)
    setError(null)
    try {
      const headers = partnerToken ? { Authorization: `Bearer ${partnerToken}` } : {}
      const url = partnerToken
        ? '/api/partner/me/coupons'  // token já identifica o parceiro
        : `/api/partner/me/coupons?partner_id=${effectivePartnerId}`
      const [rc, rr] = await Promise.all([
        api.get(url, { headers }),
        api.get(partnerToken ? '/api/partner/me/redemptions' : `/api/partner/me/redemptions?partner_id=${effectivePartnerId}`, { headers }),
      ])
      setCoupons(rc.data?.coupons || [])
      setPartner(rc.data?.partner || null)
      setRedemptions(rr.data?.items || [])
      setLastUpdated(new Date())
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Erro ao carregar')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (effectivePartnerId) reload()
  }, [effectivePartnerId])

  const handleLogout = () => {
    localStorage.removeItem(PARTNER_TOKEN_KEY)
    localStorage.removeItem(PARTNER_INFO_KEY)
    navigate('/partner/login')
  }

  if (loading && !partner) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#0A0A1A' }}>
        <div className="text-ayria-muted">Carregando portal do parceiro...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen p-8" style={{ background: '#0A0A1A' }}>
        <Link to="/admin" className="text-ayria-muted hover:text-ayria-text flex items-center gap-2 mb-4">
          <ArrowLeft size={16}/>Voltar pro admin
        </Link>
        <div className="p-6 rounded-2xl" style={{ background: '#1a1a2e', border: '1px solid #da3737' }}>
          <div className="text-red-300 mb-2">❌ Erro</div>
          <div className="text-sm text-ayria-muted">{error}</div>
          <button onClick={reload} className="mt-4 px-4 py-2 rounded-xl text-white" style={{ background: '#f1c961' }}>
            Tentar de novo
          </button>
        </div>
      </div>
    )
  }

  // Stats agregados
  const totalPending = coupons.reduce((sum, c) => 0, 0) // vem no partner payload, computado abaixo
  const pendingCents = (coupons && (window as any).__pending) || 0  // fallback
  const activeCoupons = coupons.filter(c => !c.is_deleted)
  const deletedCoupons = coupons.filter(c => c.is_deleted)

  // Total de comissão: percorre redemptions
  const totalCommissionCents = redemptions.reduce((sum, r) => sum + (r.commission_amount_cents || 0), 0)
  const pendingCommission = redemptions.filter(r => r.payout_status === 'pending').reduce((sum, r) => sum + (r.commission_amount_cents || 0), 0)
  const paidCommission = redemptions.filter(r => r.payout_status === 'paid').reduce((sum, r) => sum + (r.commission_amount_cents || 0), 0)

  // Total de descontos gerados pros usuários
  const totalDiscountCents = redemptions.reduce((sum, r) => sum + (r.discount_amount_cents || 0), 0)
  const totalRevenueCents = redemptions.reduce((sum, r) => sum + (r.final_amount_cents || 0), 0)
  const totalOriginalCents = redemptions.reduce((sum, r) => sum + (r.original_amount_cents || 0), 0)

  // Resumo por cupom
  const redemptionsByCode = redemptions.reduce((acc: any, r) => {
    const key = r.coupon_code || '—'
    if (!acc[key]) acc[key] = { count: 0, commission: 0, discount: 0 }
    acc[key].count += 1
    acc[key].commission += r.commission_amount_cents || 0
    acc[key].discount += r.discount_amount_cents || 0
    return acc
  }, {})

  return (
    <div className="min-h-screen p-4 sm:p-6" style={{ background: '#0A0A1A' }}>
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <Link to="/admin" className="text-ayria-muted hover:text-ayria-text flex items-center gap-2 text-sm mb-2">
              <ArrowLeft size={14}/>Voltar pro admin
            </Link>
            <h1 className="text-2xl sm:text-3xl font-bold text-ayria-text flex items-center gap-2">
              <Users size={24}/>Portal do Parceiro
            </h1>
            {partner && (
              <div className="text-sm text-ayria-muted mt-1">
                {partner.name} · <span className="font-mono">{partner.email}</span>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            {partnerToken && (
              <button onClick={handleLogout} className="px-3 py-2 rounded-xl text-sm text-red-300 hover:text-red-200 flex items-center gap-1"
                style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }} title="Sair">
                <LogOut size={14}/>Sair
              </button>
            )}
            <button onClick={reload} className="px-3 py-2 rounded-xl text-sm text-ayria-muted hover:text-ayria-text flex items-center gap-1"
              style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }} title="Recarregar">
              <RefreshCw size={14}/>Atualizar
            </button>
          </div>
        </div>

        {/* Cards de estatísticas */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <StatCard icon={<DollarSign size={20} className="text-amber-400"/>}
            label="Comissão pendente"
            value={`R$ ${(pendingCommission / 100).toFixed(2)}`}
            accent="amber" />
          <StatCard icon={<DollarSign size={20} className="text-emerald-400"/>}
            label="Comissão paga"
            value={`R$ ${(paidCommission / 100).toFixed(2)}`}
            accent="emerald" />
          <StatCard icon={<Tag size={20} className="text-blue-400"/>}
            label="Cupons ativos"
            value={activeCoupons.length.toString()}
            accent="blue" />
          <StatCard icon={<TrendingUp size={20} className="text-purple-400"/>}
            label="Resgates totais"
            value={redemptions.length.toString()}
            accent="purple" />
        </div>

        {/* Resumo por cupom */}
        {Object.keys(redemptionsByCode).length > 0 && (
          <div className="mb-6 p-4 rounded-2xl" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <h2 className="text-lg font-bold text-ayria-text mb-3">📊 Resumo por cupom</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-ayria-muted text-xs uppercase">
                    <th className="text-left py-2">Cupom</th>
                    <th className="text-right py-2">Resgates</th>
                    <th className="text-right py-2">Desconto dado</th>
                    <th className="text-right py-2">Comissão</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(redemptionsByCode).sort((a: any, b: any) => b[1].commission - a[1].commission).map(([code, data]: any) => (
                    <tr key={code} className="border-t" style={{ borderColor: '#2a2a3e' }}>
                      <td className="py-2 font-mono font-bold text-ayria-text">{code}</td>
                      <td className="py-2 text-right text-ayria-muted">{data.count}</td>
                      <td className="py-2 text-right text-ayria-muted">R$ {(data.discount / 100).toFixed(2)}</td>
                      <td className="py-2 text-right font-bold" style={{ color: '#10B981' }}>R$ {(data.commission / 100).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t" style={{ borderColor: '#2a2a3e' }}>
                    <td className="py-2 font-bold text-ayria-text">Total</td>
                    <td className="py-2 text-right text-ayria-text font-bold">{redemptions.length}</td>
                    <td className="py-2 text-right text-ayria-text font-bold">R$ {(totalDiscountCents / 100).toFixed(2)}</td>
                    <td className="py-2 text-right font-bold" style={{ color: '#10B981' }}>R$ {(totalCommissionCents / 100).toFixed(2)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}

        {/* Cupons */}
        <div className="mb-6 p-4 rounded-2xl" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
          <h2 className="text-lg font-bold text-ayria-text mb-3">
            🎟️ Cupons ({coupons.length})
            {deletedCoupons.length > 0 && (
              <span className="ml-2 text-xs font-normal text-ayria-muted">({deletedCoupons.length} no histórico)</span>
            )}
          </h2>
          {coupons.length === 0 ? (
            <div className="text-center py-8 text-ayria-muted text-sm">Nenhum cupom cadastrado pra este parceiro.</div>
          ) : (
            <div className="space-y-2">
              {coupons.map((c: any) => (
                <div key={c.id} className="p-3 rounded-xl flex items-start justify-between gap-3"
                  style={{ background: '#0A0A1A', border: `1px solid ${c.is_deleted ? 'rgba(239,68,68,0.3)' : '#2a2a3e'}` }}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-base font-bold text-ayria-text">{c.code}</span>
                      <span className="text-xs px-2 py-0.5 rounded"
                        style={{
                          background: c.discount_type === 'percent' ? 'rgba(241,201,97,0.2)' : 'rgba(16,185,129,0.2)',
                          color: c.discount_type === 'percent' ? '#f1c961' : '#10B981'
                        }}>
                        {c.discount_type === 'percent' ? `${c.discount_value}% OFF` : `R$ ${c.discount_value} OFF`}
                      </span>
                      {c.is_deleted && <span className="text-xs px-2 py-0.5 rounded bg-red-900/30 text-red-300">🗂️ Histórico</span>}
                      {!c.active && !c.is_deleted && <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">⏸ Inativo</span>}
                    </div>
                    <div className="text-xs text-ayria-muted mt-1">
                      {c.name && <span>{c.name} · </span>}
                      plano: <span className="text-ayria-text">{c.applicable_plan_slug || 'qualquer'}</span> ·
                      comissão: <span className="text-amber-400">{c.commission_pct}%</span> ·
                      resgates: <span className="text-ayria-text">{c.current_redemptions}/{c.max_redemptions || '∞'}</span>
                      {c.expires_at && <span> · validade: {new Date(c.expires_at).toLocaleDateString('pt-BR')}</span>}
                    </div>
                    {c.deleted_at && (
                      <div className="text-[10px] text-red-300 mt-1">
                        Removido em {new Date(c.deleted_at).toLocaleString('pt-BR')}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Histórico de resgates */}
        <div className="mb-6 p-4 rounded-2xl" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
          <h2 className="text-lg font-bold text-ayria-text mb-3 flex items-center gap-2">
            <Clock size={18}/>Histórico de resgates
            {redemptions.length > 500 && (
              <span className="text-xs font-normal text-amber-400">(mostrando 500 — total {redemptions.length})</span>
            )}
          </h2>
          {redemptions.length === 0 ? (
            <div className="text-center py-8 text-ayria-muted text-sm">Nenhum resgate ainda. Seus cupons estão prontos pra uso!</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-ayria-muted text-xs uppercase">
                    <th className="text-left py-2">Data</th>
                    <th className="text-left py-2">Cupom</th>
                    <th className="text-left py-2">Usuário</th>
                    <th className="text-left py-2">Plano</th>
                    <th className="text-right py-2">$ Original</th>
                    <th className="text-right py-2">Desconto</th>
                    <th className="text-right py-2">Final</th>
                    <th className="text-right py-2">Comissão</th>
                    <th className="text-left py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {redemptions.map((r: any) => (
                    <tr key={r.id} className="border-t" style={{ borderColor: '#2a2a3e' }}>
                      <td className="py-2 text-ayria-muted text-xs whitespace-nowrap">
                        {new Date(r.created_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-2 font-mono font-bold text-ayria-text whitespace-nowrap">
                        {r.coupon_code}
                        {r.coupon_deleted && <span className="ml-1 text-[10px] text-red-400" title="Cupom removido">🗑️</span>}
                      </td>
                      <td className="py-2 text-xs text-ayria-muted truncate max-w-[140px]" title={r.user_email || ''}>
                        {r.user_email || '—'}
                      </td>
                      <td className="py-2 text-xs text-ayria-muted">{r.plan_slug}</td>
                      <td className="py-2 text-right text-ayria-muted">R$ {((r.original_amount_cents || 0) / 100).toFixed(2)}</td>
                      <td className="py-2 text-right text-amber-400">-R$ {((r.discount_amount_cents || 0) / 100).toFixed(2)}</td>
                      <td className="py-2 text-right text-ayria-text">R$ {((r.final_amount_cents || 0) / 100).toFixed(2)}</td>
                      <td className="py-2 text-right font-bold" style={{ color: '#10B981' }}>R$ {((r.commission_amount_cents || 0) / 100).toFixed(2)}</td>
                      <td className="py-2 text-xs">
                        <span className="px-2 py-0.5 rounded" style={{
                          background: r.payout_status === 'paid' ? 'rgba(16,185,129,0.2)' : r.payout_status === 'pending' ? 'rgba(241,201,97,0.2)' : 'rgba(239,68,68,0.2)',
                          color: r.payout_status === 'paid' ? '#10B981' : r.payout_status === 'pending' ? '#f1c961' : '#ef4444'
                        }}>
                          {r.payout_status === 'paid' ? '✓ Pago' : r.payout_status === 'pending' ? '⏳ Pendente' : r.payout_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Resumo financeiro */}
        {redemptions.length > 0 && (
          <div className="mb-6 p-4 rounded-2xl" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <h2 className="text-lg font-bold text-ayria-text mb-3">💰 Resumo financeiro</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div className="p-3 rounded-xl" style={{ background: '#0A0A1A' }}>
                <div className="text-xs text-ayria-muted">Volume original</div>
                <div className="text-lg font-bold text-ayria-text">R$ {(totalOriginalCents / 100).toFixed(2)}</div>
                <div className="text-[10px] text-ayria-muted mt-1">Soma do que usuário pagaria sem cupom</div>
              </div>
              <div className="p-3 rounded-xl" style={{ background: '#0A0A1A' }}>
                <div className="text-xs text-ayria-muted">Receita gerada AYRIA</div>
                <div className="text-lg font-bold text-ayria-text">R$ {(totalRevenueCents / 100).toFixed(2)}</div>
                <div className="text-[10px] text-ayria-muted mt-1">Soma do que entrou no Stripe</div>
              </div>
              <div className="p-3 rounded-xl" style={{ background: '#0A0A1A' }}>
                <div className="text-xs text-ayria-muted">Total desconto dado</div>
                <div className="text-lg font-bold text-amber-400">R$ {(totalDiscountCents / 100).toFixed(2)}</div>
                <div className="text-[10px] text-ayria-muted mt-1">Quanto usuários economizaram</div>
              </div>
              <div className="p-3 rounded-xl" style={{ background: '#0A0A1A' }}>
                <div className="text-xs text-ayria-muted">Total comissão</div>
                <div className="text-lg font-bold text-emerald-400">R$ {(totalCommissionCents / 100).toFixed(2)}</div>
                <div className="text-[10px] text-ayria-muted mt-1">Sua comissão acumulada</div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-8 text-center text-xs text-ayria-muted">
          Atualizado em {lastUpdated.toLocaleTimeString('pt-BR')} · Portal do Parceiro AYRIA
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, accent }: { icon: any; label: string; value: string; accent: string }) {
  const colors: any = {
    amber: 'rgba(241,201,97,0.1)',
    emerald: 'rgba(16,185,129,0.1)',
    blue: 'rgba(96,165,250,0.1)',
    purple: 'rgba(192,132,252,0.1)',
  }
  const borders: any = {
    amber: 'rgba(241,201,97,0.3)',
    emerald: 'rgba(16,185,129,0.3)',
    blue: 'rgba(96,165,250,0.3)',
    purple: 'rgba(192,132,252,0.3)',
  }
  return (
    <div className="p-3 rounded-xl" style={{ background: colors[accent] || '#0A0A1A', border: `1px solid ${borders[accent] || '#2a2a3e'}` }}>
      <div className="flex items-center gap-2 mb-1">{icon}<span className="text-xs text-ayria-muted">{label}</span></div>
      <div className="text-xl font-bold text-ayria-text">{value}</div>
    </div>
  )
}
