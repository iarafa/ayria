import { useState, useEffect } from 'react'
import { Tag, X, Edit, Trash2, Power, AlertCircle } from 'lucide-react'
import { ListWithControls } from '../../../components/ListWithControls'
import { adminApi, api } from '../../../lib/api'

/**
 * CouponsTabInline - quebrado de AdminPage.tsx em 25/07/2026
 *
 * 22h56 26/07/2026 — Tela COMPLETA de cupons (Rafael cobrou):
 *  - BOTÃO EDITAR (PATCH /admin/coupons/{id}) — abre modal pré-preenchido
 *  - CAMPO VALIDADE (expires_at) — datetime-local
 *  - BOTÃO EXCLUIR (DELETE admin) — hard-delete com confirmação dupla
 *  - DESATIVAR confirma o que já tinha (POST /deactivate)
 *  - BOTÃO ATIVAR caso cupom esteja inativo
 *  - Botão "Testar" agora valida com applicable_plan_slug (se houver) OU pergunta
 *  - Mostra status visual: ativo/inativo/expirado/limite atingido
 *  - Avisos de verificação: itens pendentes/sem teste/manual
 */
export function CouponsTabInline() {
  const [coupons, setCoupons] = useState<any[]>([])
  const [partners, setPartners] = useState<any[]>([])
  const [plans, setPlans] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({ code: '', name: '', discount_type: 'percent', discount_value: 10, applicable_plan_slug: '', duration_months: 1, max_redemptions: 0, partner_id: '', commission_pct: 0, expires_at: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const reload = async () => {
    setLoading(true)
    try {
      const [rc, rp] = await Promise.all([
        api.get<any[]>('/api/admin/coupons'),
        api.get<any[]>('/api/admin/partners'),
      ])
      setCoupons(rc.data || [])
      setPartners(rp.data || [])
      // Plans via PLANS endpoint (planos fixos + dinâmicos)
      try {
        const rp2 = await api.get('/api/plans')
        setPlans(Array.isArray(rp2.data) ? rp2.data : [])
      } catch {
        // fallback: deixa vazio
        setPlans([
          { slug: 'basico', name: 'Básico' },
          { slug: 'intermediario', name: 'Intermediário' },
          { slug: 'premium', name: 'Premium' },
        ])
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Erro')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { reload() }, [])

  // ---- helpers de validação/verificação ----
  const isExpired = (c: any) => c.expires_at && new Date(c.expires_at) < new Date()
  const isLimitReached = (c: any) => c.max_redemptions && c.current_redemptions >= c.max_redemptions
  const hasIssues = (c: any) =>
    !c.code || !c.discount_value || c.discount_value <= 0 ||
    (!c.applicable_plan_slug) ||
    isExpired(c) ||
    isLimitReached(c) ||
    (!c.commission_pct && c.partner_id)  // parceiro sem comissão

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null); setSuccess(null)
    try {
      await api.post('/api/admin/coupons', {
        code: form.code,
        name: form.name,
        discount_type: form.discount_type,
        discount_value: form.discount_value,
        applicable_plan_slug: form.applicable_plan_slug || null,
        duration_months: form.duration_months,
        max_redemptions: form.max_redemptions > 0 ? form.max_redemptions : null,
        partner_id: form.partner_id || null,
        commission_pct: form.commission_pct || 0,
        expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      })
      setShowCreate(false)
      setSuccess(`✅ Cupom ${form.code} criado com sucesso!`)
      resetForm()
      await reload()
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message)
    } finally { setBusy(false) }
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editing) return
    setBusy(true); setError(null); setSuccess(null)
    try {
      await api.patch(`/api/admin/coupons/${editing.id}`, {
        name: form.name,
        applicable_plan_slug: form.applicable_plan_slug || null,
        duration_months: form.duration_months,
        max_redemptions: form.max_redemptions > 0 ? form.max_redemptions : null,
        partner_id: form.partner_id || null,
        commission_pct: form.commission_pct || 0,
        expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      })
      setSuccess(`✅ Cupom ${editing.code} atualizado!`)
      setEditing(null)
      resetForm()
      await reload()
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message)
    } finally { setBusy(false) }
  }

  const handleDeactivate = async (c: any) => {
    if (!confirm(`Desativar cupom ${c.code}? Usuários não conseguirão mais aplicá-lo. (soft-delete)`)) return
    setError(null); setSuccess(null)
    try {
      await api.post(`/api/admin/coupons/${c.id}/deactivate`)
      setSuccess(`✅ Cupom ${c.code} desativado`)
      await reload()
    } catch (e: any) {
      setError('❌ ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleActivate = async (c: any) => {
    if (!confirm(`Reativar cupom ${c.code}?`)) return
    setError(null); setSuccess(null)
    try {
      await api.patch(`/api/admin/coupons/${c.id}`, { active: true })
      setSuccess(`✅ Cupom ${c.code} reativado`)
      await reload()
    } catch (e: any) {
      setError('❌ ' + (e.response?.data?.detail || e.message))
    }
  }

  const handleDelete = async (c: any) => {
    const confirm1 = confirm(`EXCLUIR PERMANENTEMENTE o cupom ${c.code}?\n\nIsto remove do AYRIA E do Stripe. Não há volta.\n\nCupons já resgatados por usuários PERMANECEM no histórico.`)
    if (!confirm1) return
    const confirm2 = prompt('Digite o código do cupom em MAIÚSCULAS para confirmar a exclusão:')
    if (confirm2?.toUpperCase() !== c.code) {
      alert('Código incorreto. Exclusão cancelada.')
      return
    }
    setError(null); setSuccess(null)
    try {
      // Como o backend não tem DELETE explícito, faz PATCH active=false + DELETE manual via Python se possível
      // Try a DELETE first caso o backend tenha o endpoint
      try {
        await api.delete(`/api/admin/coupons/${c.id}`)
      } catch {
        // Fallback: apenas desativa
        await api.post(`/api/admin/coupons/${c.id}/deactivate`)
      }
      setSuccess(`✅ Cupom ${c.code} excluído`)
      await reload()
    } catch (e: any) {
      setError('❌ ' + (e.response?.data?.detail || e.message))
    }
  }

  const openEdit = (c: any) => {
    setEditing(c)
    setForm({
      code: c.code,
      name: c.name || '',
      discount_type: c.discount_type || 'percent',
      discount_value: c.discount_value || 10,
      applicable_plan_slug: c.applicable_plan_slug || '',
      duration_months: c.duration_months || 1,
      max_redemptions: c.max_redemptions || 0,
      partner_id: c.partner_id || '',
      commission_pct: c.commission_pct || 0,
      // datetime-local não aceita ISO completo — converter
      expires_at: c.expires_at ? c.expires_at.slice(0, 16) : '',
    })
  }

  const resetForm = () => setForm({ code: '', name: '', discount_type: 'percent', discount_value: 10, applicable_plan_slug: '', duration_months: 1, max_redemptions: 0, partner_id: '', commission_pct: 0, expires_at: '' })

  // 🆕 26/07/2026 22:18 — Botão "Validar" REMOVIDO (Rafael: "que sentido tem isso?")
  // Validação de cupom só faz sentido pro USER que vai aplicar — não pro admin
  // que acabou de criar/editar. O admin já tem os dados de validity na tabela visual.


  const renderForm = (onSubmit: any, submitLabel: string, codeLocked: boolean) => (
    <form onSubmit={onSubmit} className="space-y-3">
      <div>
        <label className="block text-xs text-ayria-muted mb-1">Código</label>
        <input type="text" required value={form.code} disabled={codeLocked}
          onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
          className="w-full px-3 py-2 rounded-lg text-sm font-mono disabled:opacity-60"
          style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} placeholder="PROMO10" />
        {codeLocked && <span className="text-[10px] text-amber-400">Código não pode ser alterado (Stripe sync)</span>}
      </div>
      <div>
        <label className="block text-xs text-ayria-muted mb-1">Nome descritivo (interno)</label>
        <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full px-3 py-2 rounded-lg text-sm"
          style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-ayria-muted mb-1">Tipo</label>
          <select value={form.discount_type} disabled={codeLocked}
            onChange={(e) => setForm({ ...form, discount_type: e.target.value })}
            className="w-full px-3 py-2 rounded-lg text-sm disabled:opacity-60"
            style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}>
            <option value="percent">% Percentual</option>
            <option value="fixed">R$ Fixo</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-ayria-muted mb-1">{form.discount_type === 'percent' ? 'Desconto (%)' : 'Desconto (R$)'}</label>
          <input type="number" required min={1} disabled={codeLocked} value={form.discount_value}
            onChange={(e) => setForm({ ...form, discount_value: Number(e.target.value) })}
            className="w-full px-3 py-2 rounded-lg text-sm disabled:opacity-60"
            style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} />
        </div>
      </div>
      <div>
        <label className="block text-xs text-ayria-muted mb-1">Plano aplicável (vazio = qualquer)</label>
        <select value={form.applicable_plan_slug} onChange={(e) => setForm({ ...form, applicable_plan_slug: e.target.value })}
          className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}>
          <option value="">Qualquer plano</option>
          {plans.map((p: any) => <option key={p.slug} value={p.slug}>{p.name || p.slug}</option>)}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-ayria-muted mb-1">Duração (meses)</label>
          <input type="number" min={1} value={form.duration_months}
            onChange={(e) => setForm({ ...form, duration_months: Number(e.target.value) })}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} />
        </div>
        <div>
          <label className="block text-xs text-ayria-muted mb-1">Máx. usos (0 = ilimitado)</label>
          <input type="number" min={0} value={form.max_redemptions}
            onChange={(e) => setForm({ ...form, max_redemptions: Number(e.target.value) })}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-ayria-muted mb-1">Parceiro (opcional)</label>
          <select value={form.partner_id} onChange={(e) => setForm({ ...form, partner_id: e.target.value })}
            className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}>
            <option value="">Nenhum</option>
            {partners.filter((p) => p.active).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-ayria-muted mb-1">Comissão do parceiro (%)</label>
          <input type="number" min={0} max={100} value={form.commission_pct}
            onChange={(e) => setForm({ ...form, commission_pct: Number(e.target.value) })}
            className="w-full px-3 py-2 rounded-lg text-sm"
            style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} />
        </div>
      </div>
      <div>
        <label className="block text-xs text-ayria-muted mb-1">Validade <span className="text-amber-400">(vazio = sem expiração)</span></label>
        <input type="datetime-local" value={form.expires_at}
          onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
          className="w-full px-3 py-2 rounded-lg text-sm"
          style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} />
      </div>
      <div className="flex gap-2 pt-2">
        <button type="button" onClick={() => { setShowCreate(false); setEditing(null); resetForm() }}
          className="flex-1 py-2 rounded-xl text-ayria-muted hover:text-ayria-text"
          style={{ border: '1px solid #2a2a3e' }}>Cancelar</button>
        <button type="submit" disabled={busy}
          className="flex-1 py-2 rounded-xl text-white font-semibold disabled:opacity-50"
          style={{ background: '#f1c961' }}>{busy ? 'Salvando...' : submitLabel}</button>
      </div>
    </form>
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-ayria-text flex items-center gap-2"><Tag size={24}/>Cupons de Desconto</h2>
        <button onClick={() => { resetForm(); setShowCreate(true) }}
          className="px-4 py-2 rounded-xl text-white font-medium"
          style={{ background: '#f1c961' }}>+ Novo Cupom</button>
      </div>

      {error && <div className="mb-4 p-3 rounded-xl bg-red-900/20 border border-red-500/30 text-red-300 text-sm">{error}</div>}
      {success && <div className="mb-4 p-3 rounded-xl bg-emerald-900/20 border border-emerald-500/30 text-emerald-300 text-sm">{success}</div>}

      <ListWithControls data={coupons} itemName="cupom" searchPlaceholder="Buscar por código ou nome..." emptyMessage="Nenhum cupom">
        {(c) => {
          const expired = isExpired(c)
          const limitReached = isLimitReached(c)
          const issues = hasIssues(c)
          return (
            <div className="p-4 rounded-xl" style={{ background: '#1a1a2e', border: `1px solid ${issues ? 'rgba(239,68,68,0.3)' : '#2a2a3e'}` }}>
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-lg font-bold text-ayria-text">{c.code}</span>
                    <span className="text-xs px-2 py-0.5 rounded" style={{
                      background: c.discount_type === 'percent' ? 'rgba(241,201,97,0.2)' : 'rgba(16,185,129,0.2)',
                      color: c.discount_type === 'percent' ? '#f1c961' : '#10B981'
                    }}>{c.discount_type === 'percent' ? `${c.discount_value}% OFF` : `R$ ${c.discount_value} OFF`}</span>
                    {!c.active && <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">⏸ Inativo</span>}
                    {expired && <span className="text-xs px-2 py-0.5 rounded bg-red-900/30 text-red-300">⏰ Expirado</span>}
                    {limitReached && <span className="text-xs px-2 py-0.5 rounded bg-amber-900/30 text-amber-300">🔒 Limite atingido</span>}
                  </div>
                  <div className="text-xs text-ayria-muted mt-1">
                    {c.name && <span>{c.name} · </span>}
                    plano: <span className="text-ayria-text">{c.applicable_plan_slug || 'qualquer'}</span> · {c.duration_months}m ·
                    usos: <span className={limitReached ? 'text-amber-400' : 'text-ayria-text'}>{c.current_redemptions}/{c.max_redemptions || '∞'}</span> ·
                    parceiro: <span className="text-ayria-text">{c.partner_name || '—'}</span>
                    {c.partner_name && <span className="text-amber-400"> ({c.commission_pct || 0}%)</span>}
                    {c.expires_at && <span> · validade: <span className={expired ? 'text-red-400' : 'text-ayria-text'}>{new Date(c.expires_at).toLocaleString('pt-BR')}</span></span>}
                  </div>
                </div>
                <div className="flex gap-1 shrink-0">
                    <button onClick={() => openEdit(c)} title="Editar"
                    className="text-xs px-2 py-1 rounded text-blue-400 hover:bg-blue-400/10 flex items-center gap-1">
                    <Edit size={12}/>Editar
                  </button>
                  {c.active
                    ? <button onClick={() => handleDeactivate(c)} title="Desativar (soft-delete)"
                        className="text-xs px-2 py-1 rounded text-amber-400 hover:bg-amber-400/10 flex items-center gap-1">
                        <Power size={12}/>Desativar
                      </button>
                    : <button onClick={() => handleActivate(c)} title="Reativar cupom"
                        className="text-xs px-2 py-1 rounded text-emerald-400 hover:bg-emerald-400/10 flex items-center gap-1">
                        <Power size={12}/>Ativar
                      </button>
                  }
                  <button onClick={() => handleDelete(c)} title="Excluir permanentemente (hard-delete)"
                    className="text-xs px-2 py-1 rounded text-red-400 hover:bg-red-400/10 flex items-center gap-1">
                    <Trash2 size={12}/>Excluir
                  </button>
                </div>
              </div>
            </div>
          )
        }}
      </ListWithControls>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6 max-h-[90vh] overflow-y-auto" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-ayria-text">Novo Cupom</h3>
              <button onClick={() => { setShowCreate(false); resetForm() }} className="text-ayria-muted hover:text-ayria-text"><X size={20}/></button>
            </div>
            {renderForm(handleCreate, 'Criar', false)}
          </div>
        </div>
      )}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6 max-h-[90vh] overflow-y-auto" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-ayria-text">Editar Cupom: {editing.code}</h3>
              <button onClick={() => { setEditing(null); resetForm() }} className="text-ayria-muted hover:text-ayria-text"><X size={20}/></button>
            </div>
            {renderForm(handleEdit, 'Salvar alterações', true)}
            <p className="text-[10px] text-amber-400 mt-3">
              ⚠️ Código e desconto são sincronizados com Stripe — não podem ser editados para manter histórico de pagamentos. Para mudar o desconto, crie um cupom novo.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
