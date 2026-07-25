import { useState, useEffect } from 'react'
import { Tag, X } from 'lucide-react'
import { ListWithControls } from '../../../components/ListWithControls'
import { adminApi, api } from '../../../lib/api'

/**
 * CouponsTabInline - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function CouponsTabInline() {
  const [coupons, setCoupons] = useState<any[]>([])
  const [partners, setPartners] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ code: '', name: '', discount_type: 'percent', discount_value: 10, applicable_plan_slug: '', duration_months: 1, max_redemptions: 0, partner_id: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [validating, setValidating] = useState<{ code: string; result: any } | null>(null)

  const reload = async () => {
    setLoading(true)
    try {
      const [rc, rp] = await Promise.all([api.get<any[]>('/api/admin/coupons'), api.get<any[]>('/api/admin/partners')])
      setCoupons(rc.data || [])
      setPartners(rp.data || [])
    } catch (e: any) { setError(e.response?.data?.detail || 'Erro') }
    finally { setLoading(false) }
  }
  useEffect(() => { reload() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      await api.post('/api/admin/coupons', {
        ...form,
        max_redemptions: form.max_redemptions > 0 ? form.max_redemptions : null,
        partner_id: form.partner_id || null,
        applicable_plan_slug: form.applicable_plan_slug || null,
      })
      setShowCreate(false)
      await reload()
      alert('✅ Cupom criado! Anota: ' + form.code)
    } catch (e: any) { setError(e.response?.data?.detail || e.message) }
    finally { setBusy(false) }
  }

  const handleValidate = async (code: string) => {
    setValidating({ code, result: null } as any)
    try {
      const r = await api.post('/api/coupons/validate', { code, plan_slug: '' })
      setValidating({ code, result: r.data })
    } catch (e: any) { setValidating({ code, result: { error: e.response?.data?.detail || e.message } }) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-ayria-text flex items-center gap-2"><Tag size={24}/>Cupons de Desconto</h2>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 rounded-xl text-white font-medium" style={{ background: '#f1c961' }}>+ Novo Cupom</button>
      </div>
      {error && <div className="mb-4 p-3 rounded-xl bg-red-900/20 border border-red-500/30 text-red-300 text-sm">{error}</div>}
      {validating && (
        <div className="mb-4 p-3 rounded-xl text-sm" style={{ background: '#1a1a2e' }}>
          <div className="font-medium text-ayria-text mb-1">Validação: {validating.code}</div>
          <pre className="text-xs text-ayria-muted whitespace-pre-wrap">{JSON.stringify(validating.result, null, 2)}</pre>
          <button onClick={() => setValidating(null)} className="mt-2 text-xs text-ayria-muted hover:text-ayria-text">Fechar</button>
        </div>
      )}
      <ListWithControls data={coupons} itemName="cupom" searchPlaceholder="Buscar por código ou nome..." emptyMessage="Nenhum cupom">
        {(c) => (
          <div className="p-4 rounded-xl flex items-center justify-between" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-lg font-bold text-ayria-text">{c.code}</span>
                <span className="text-xs px-2 py-0.5 rounded" style={{ background: c.discount_type === 'percent' ? 'rgba(241,201,97,0.2)' : 'rgba(16,185,129,0.2)', color: c.discount_type === 'percent' ? '#818CF8' : '#10B981' }}>
                  {c.discount_type === 'percent' ? `${c.discount_value}% OFF` : `R$ ${c.discount_value} OFF`}
                </span>
              </div>
              <div className="text-xs text-ayria-muted mt-1">{c.name} · plano: {c.applicable_plan_slug || 'qualquer'} · {c.duration_months}m · {c.current_redemptions}/{c.max_redemptions || '∞'} usos · parceiro: {c.partner_name || '-'}</div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => handleValidate(c.code)} className="text-xs px-2 py-1 rounded text-indigo-400 hover:bg-indigo-400/10">Testar</button>
              <button onClick={async () => {
                if (!confirm('Desativar cupom ' + c.code + '?')) return
                try { await api.post(`/api/admin/coupons/${c.id}/deactivate`); await reload() }
                catch (e: any) { alert('❌ ' + (e.response?.data?.detail || e.message)) }
              }} className="text-xs px-2 py-1 rounded text-red-400 hover:bg-red-400/10">Desativar</button>
            </div>
          </div>
        )}
      </ListWithControls>
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-ayria-text">Novo Cupom</h3>
              <button onClick={() => setShowCreate(false)} className="text-ayria-muted hover:text-ayria-text"><X size={20}/></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              <div><label className="block text-xs text-ayria-muted mb-1">Código</label><input type="text" required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} className="w-full px-3 py-2 rounded-lg text-sm font-mono" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} placeholder="PROMO10" /></div>
              <div><label className="block text-xs text-ayria-muted mb-1">Nome</label><input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} /></div>
              <div className="grid grid-cols-2 gap-2">
                <div><label className="block text-xs text-ayria-muted mb-1">Tipo</label><select value={form.discount_type} onChange={(e) => setForm({ ...form, discount_type: e.target.value })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}><option value="percent">% Percentual</option><option value="fixed">R$ Fixo</option></select></div>
                <div><label className="block text-xs text-ayria-muted mb-1">{form.discount_type === 'percent' ? '%' : 'R$'}</label><input type="number" required min={1} value={form.discount_value} onChange={(e) => setForm({ ...form, discount_value: Number(e.target.value) })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} /></div>
              </div>
              <div><label className="block text-xs text-ayria-muted mb-1">Plano aplicável (vazio = qualquer)</label><input type="text" value={form.applicable_plan_slug} onChange={(e) => setForm({ ...form, applicable_plan_slug: e.target.value })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} placeholder="basico / intermediario / premium" /></div>
              <div className="grid grid-cols-2 gap-2">
                <div><label className="block text-xs text-ayria-muted mb-1">Duração (meses)</label><input type="number" min={1} value={form.duration_months} onChange={(e) => setForm({ ...form, duration_months: Number(e.target.value) })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} /></div>
                <div><label className="block text-xs text-ayria-muted mb-1">Máx. usos (0 = ilimitado)</label><input type="number" min={0} value={form.max_redemptions} onChange={(e) => setForm({ ...form, max_redemptions: Number(e.target.value) })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} /></div>
              </div>
              <div><label className="block text-xs text-ayria-muted mb-1">Parceiro (opcional)</label><select value={form.partner_id} onChange={(e) => setForm({ ...form, partner_id: e.target.value })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}><option value="">Nenhum</option>{partners.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 py-2 rounded-xl text-ayria-muted hover:text-ayria-text" style={{ border: '1px solid #2a2a3e' }}>Cancelar</button>
                <button type="submit" disabled={busy} className="flex-1 py-2 rounded-xl text-white font-semibold disabled:opacity-50" style={{ background: '#f1c961' }}>{busy ? 'Criando...' : 'Criar'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// 🆕 22/07 21:21 — Comissões AGRUPADAS POR MÊS (Rafael pediu visão mensal)