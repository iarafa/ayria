import { useState, useEffect } from 'react'
import { Plus, X } from 'lucide-react'
import { ListWithControls } from '../../../components/ListWithControls'

/**
 * CreditsTab - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function CreditsTab({ users, onAdjust }: {
  users: any[]
  onAdjust: (userId: string, amount: number, description: string, type: string) => Promise<void>
}) {
  const [filter, setFilter] = useState<'all' | 'zero' | 'pending_onboarding'>('all')
  const [planFilter, setPlanFilter] = useState<string>('')
  const [adjustModal, setAdjustModal] = useState<{ user: any; amount: number; description: string; type: string } | null>(null)

  const filtered = users.filter((u) => {
    if (filter === 'zero' && (u.credit_balance || 0) > 0) return false
    if (filter === 'pending_onboarding' && u.onboarding_status === 'completed') return false
    if (planFilter && u.selected_plan_slug !== planFilter) return false
    return true
  })

  const totalCredits = users.reduce((sum, u) => sum + (u.credit_balance || 0), 0)
  const usersWithCredits = users.filter((u) => (u.credit_balance || 0) > 0).length
  const usersZeroCredits = users.filter((u) => (u.credit_balance || 0) === 0).length

  return (
    <div>
      {/* Stats cards */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="p-4 rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
          <div className="text-xs text-ayria-muted mb-1">Total de créditos em circulação</div>
          <div className="text-2xl font-bold gradient-text">{totalCredits.toLocaleString('pt-BR')}</div>
        </div>
        <div className="p-4 rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
          <div className="text-xs text-ayria-muted mb-1">Usuários com saldo</div>
          <div className="text-2xl font-bold text-ayria-text">{usersWithCredits}</div>
        </div>
        <div className="p-4 rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
          <div className="text-xs text-ayria-muted mb-1">Usuários sem saldo</div>
          <div className="text-2xl font-bold" style={{ color: usersZeroCredits > 0 ? '#EF4444' : '#10B981' }}>{usersZeroCredits}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <select
          value={planFilter}
          onChange={(e) => setPlanFilter(e.target.value)}
          className="px-3 py-2 rounded-lg text-sm bg-[#111] border border-ayria-border text-ayria-text"
        >
          <option value="">Todos os planos</option>
          <option value="basico">Básico</option>
          <option value="intermediario">Intermediário</option>
          <option value="premium">Premium</option>
        </select>
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-2 rounded-lg text-sm ${filter === 'all' ? 'bg-ayria-primary text-white' : 'bg-[#111] text-ayria-muted'}`}
        >
          Todos
        </button>
        <button
          onClick={() => setFilter('zero')}
          className={`px-3 py-2 rounded-lg text-sm ${filter === 'zero' ? 'bg-red-500/20 text-red-400' : 'bg-[#111] text-ayria-muted'}`}
        >
          Sem saldo
        </button>
        <button
          onClick={() => setFilter('pending_onboarding')}
          className={`px-3 py-2 rounded-lg text-sm ${filter === 'pending_onboarding' ? 'bg-purple-500/20 text-purple-400' : 'bg-[#111] text-ayria-muted'}`}
        >
          Onboarding pendente
        </button>
      </div>

      {/* Lista com paginação + busca */}
      <ListWithControls
        data={filtered}
        itemName="usuário"
        searchPlaceholder="Buscar por email, plano..."
        emptyMessage="Nenhum usuário com esses filtros"
      >
        {(u) => (
          <div
            className="p-3 rounded-xl flex items-center justify-between"
            style={{ background: '#111111', border: '1px solid #1E1E2E' }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-semibold"
                style={{ background: u.role === 'SUPER_ADMIN' ? 'linear-gradient(135deg, #F59E0B, #EF4444)' : 'linear-gradient(135deg, #f1c961, #da950b)' }}
              >
                {u.email[0].toUpperCase()}
              </div>
              <div>
                <div className="text-ayria-text text-sm font-medium">{u.email}</div>
                <div className="text-xs text-ayria-muted">
                  {u.selected_plan_name || 'sem plano'} · onboarding: {u.onboarding_status}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div
                  className="text-lg font-bold"
                  style={{ color: (u.credit_balance || 0) === 0 ? '#EF4444' : '#10B981' }}
                >
                  {(u.credit_balance || 0).toLocaleString('pt-BR')}
                </div>
                <div className="text-xs text-ayria-muted">créditos</div>
              </div>
              <button
                onClick={() => setAdjustModal({ user: u, amount: 10, description: '', type: 'bonus_manual' })}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-white"
                style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
              >
                Ajustar
              </button>
            </div>
          </div>
        )}
      </ListWithControls>

      {/* Modal de ajuste */}
      {adjustModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
          onClick={() => setAdjustModal(null)}
        >
          <div
            className="w-full max-w-md rounded-2xl p-6"
            style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-ayria-text">Ajustar créditos</h3>
              <button onClick={() => setAdjustModal(null)} className="text-ayria-muted hover:text-white">
                <X size={20} />
              </button>
            </div>
            <div className="mb-3 text-sm text-ayria-muted">
              User: <strong className="text-ayria-text">{adjustModal.user.email}</strong>
              <br />
              Saldo atual: <strong style={{ color: '#da950b' }}>{adjustModal.user.credit_balance || 0}</strong>
            </div>
            <div className="space-y-3">
              <div className="flex gap-2">
                <button
                  onClick={() => setAdjustModal({ ...adjustModal, amount: 10 })}
                  className="flex-1 py-2 rounded-lg text-sm flex items-center justify-center gap-1"
                  style={{ background: 'rgba(16,185,129,0.15)', color: '#10B981' }}
                >
                  <Plus size={14} /> +10
                </button>
                <button
                  onClick={() => setAdjustModal({ ...adjustModal, amount: 50 })}
                  className="flex-1 py-2 rounded-lg text-sm flex items-center justify-center gap-1"
                  style={{ background: 'rgba(16,185,129,0.15)', color: '#10B981' }}
                >
                  <Plus size={14} /> +50
                </button>
                <button
                  onClick={() => setAdjustModal({ ...adjustModal, amount: 100 })}
                  className="flex-1 py-2 rounded-lg text-sm flex items-center justify-center gap-1"
                  style={{ background: 'rgba(16,185,129,0.15)', color: '#10B981' }}
                >
                  <Plus size={14} /> +100
                </button>
              </div>
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Quantidade (positivo adiciona, negativo remove)</label>
                <input
                  type="number"
                  value={adjustModal.amount}
                  onChange={(e) => setAdjustModal({ ...adjustModal, amount: parseInt(e.target.value) || 0 })}
                  className="w-full px-3 py-2 rounded-lg text-ayria-text outline-none"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                />
              </div>
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Motivo (obrigatório)</label>
                <textarea
                  value={adjustModal.description}
                  onChange={(e) => setAdjustModal({ ...adjustModal, description: e.target.value })}
                  placeholder="Ex: Bônus de boas-vindas, suporte técnico..."
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg text-ayria-text outline-none resize-none"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                />
              </div>
              <button
                disabled={!adjustModal.description.trim() || adjustModal.amount === 0}
                onClick={async () => {
                  await onAdjust(adjustModal.user.id, adjustModal.amount, adjustModal.description, adjustModal.type)
                  setAdjustModal(null)
                }}
                className="w-full py-3 rounded-xl font-semibold text-white disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
              >
                Confirmar ajuste ({adjustModal.amount > 0 ? '+' : ''}{adjustModal.amount})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


// ============================================================
// PlansTab - CRUD de planos (admin pode editar preço/creditos/ativo)
// ============================================================