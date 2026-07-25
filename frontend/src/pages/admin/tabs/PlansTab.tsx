import { useState, useEffect } from 'react'
import { Edit3, X } from 'lucide-react'
import { adminApi, api } from '../../../lib/api'
import { UserDetailsModal } from '../modals/UserDetailsModal'

/**
 * PlansTab - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function PlansTab({ availablePlans, reloadPlans }: {
  availablePlans: any[]
  reloadPlans: () => Promise<void>
}) {
  const [editingPlan, setEditingPlan] = useState<any | null>(null)
  const [form, setForm] = useState({ name: '', credits: 100, price_brl: 29.9, active: true })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const startEdit = (plan: any) => {
    setEditingPlan(plan)
    setForm({ name: plan.name, credits: plan.credits, price_brl: plan.price_brl, active: plan.active })
    setError(null)
  }

  const handleSave = async () => {
    if (!editingPlan) return
    setSaving(true)
    setError(null)
    try {
      await adminApi.updatePlan(editingPlan.id, form)
      await reloadPlans()
      setEditingPlan(null)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar plano')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="mb-4 text-sm text-ayria-muted">
        {availablePlans.length} plano(s) cadastrado(s). <strong className="text-ayria-text">Atenção:</strong> alterar <em>créditos</em> afeta apenas <strong>novos cadastros</strong>. Usuários existentes mantêm o saldo atual - pra migrar, use a aba "Usuários".
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {availablePlans.map((p) => (
          <div
            key={p.id}
            className="p-5 rounded-2xl"
            style={{
              background: p.active ? '#111111' : 'rgba(239, 68, 68, 0.05)',
              border: p.active ? '1px solid #1E1E2E' : '1px solid rgba(239, 68, 68, 0.3)',
              opacity: p.active ? 1 : 0.7,
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <span
                className="text-xs px-2 py-1 rounded uppercase tracking-wider font-semibold"
                style={{
                  background: p.active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: p.active ? '#10B981' : '#EF4444',
                }}
              >
                {p.active ? 'Ativo' : 'Inativo'}
              </span>
              <span className="text-xs text-ayria-muted">{p.slug}</span>
            </div>
            <h3 className="text-xl font-bold text-ayria-text mb-2">{p.name}</h3>
            <div className="flex items-baseline gap-1 mb-1">
              <span className="text-3xl font-bold gradient-text">{p.credits.toLocaleString('pt-BR')}</span>
              <span className="text-xs text-ayria-muted">créditos</span>
            </div>
            <div className="text-sm text-ayria-text mb-4">
              <span className="text-ayria-muted">R$ </span>
              <span className="font-semibold">{p.price_brl.toFixed(2).replace('.', ',')}</span>
              <span className="text-ayria-muted text-xs"> /mês ref.</span>
            </div>
            <button
              onClick={() => startEdit(p)}
              className="w-full py-2 rounded-lg text-sm font-medium text-white flex items-center justify-center gap-1.5"
              style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
            >
              <Edit3 size={14} />
              Editar plano
            </button>
          </div>
        ))}
      </div>

      {/* Modal de edição */}
      {editingPlan && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
          onClick={() => setEditingPlan(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl p-6"
            style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-ayria-text">Editar plano</h3>
              <button onClick={() => setEditingPlan(null)} className="text-ayria-muted hover:text-white">
                <X size={20} />
              </button>
            </div>
            <div className="text-xs text-ayria-muted mb-4">
              Slug (identidade): <strong className="text-ayria-text">{editingPlan.slug}</strong> - não pode ser alterado
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Nome</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-ayria-text outline-none"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-ayria-muted mb-1">Créditos</label>
                  <input
                    type="number"
                    min="1"
                    max="1000000"
                    value={form.credits}
                    onChange={(e) => setForm({ ...form, credits: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg text-ayria-text outline-none"
                    style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                  />
                </div>
                <div>
                  <label className="block text-xs text-ayria-muted mb-1">Preço (R$)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price_brl}
                    onChange={(e) => setForm({ ...form, price_brl: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 rounded-lg text-ayria-text outline-none"
                    style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="planActive"
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                  className="w-4 h-4 rounded accent-indigo-500"
                />
                <label htmlFor="planActive" className="text-sm text-ayria-text cursor-pointer">
                  Plano <strong>ativo</strong> (visível no cadastro de novos usuários)
                </label>
              </div>
              {error && (
                <div className="px-3 py-2 rounded-lg text-sm" style={{ background: 'rgba(239,68,68,0.1)', color: '#EF4444' }}>
                  {error}
                </div>
              )}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => setEditingPlan(null)}
                  className="flex-1 py-2.5 rounded-lg text-ayria-text"
                  style={{ border: '1px solid #1E1E2E' }}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex-1 py-2.5 rounded-lg font-semibold text-white disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
                >
                  {saving ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


// ============================================================
// UserDetailsModal - exibe TUDO sobre um user (perfil, astro, número)
// ============================================================