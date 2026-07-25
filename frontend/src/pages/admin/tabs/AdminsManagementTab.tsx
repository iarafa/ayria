import { useState, useEffect } from 'react'
import { Edit3, Shield, Trash2, UserPlus, X } from 'lucide-react'
import { ListWithControls } from '../../../components/ListWithControls'
import { useAuth } from '../../../store/auth'
import { adminApi, api } from '../../../lib/api'

/**
 * AdminsManagementTab - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function AdminsManagementTab() {
  const { user: currentUser } = useAuth()
  const [admins, setAdmins] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<any>(null)
  const [editForm, setEditForm] = useState({ full_name: '', is_active: true, role: 'admin', new_password: '' })
  const [createForm, setCreateForm] = useState({ email: '', password: '', full_name: '', role: 'admin' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = async () => {
    setLoading(true)
    setError(null)
    try {
      // lista admins (role=admin OU role=SUPER_ADMIN) — faz 2 chamadas pra garantir
      const [r1, r2] = await Promise.all([
        adminApi.listUsers({ role: 'admin' }),
        adminApi.listUsers({ role: 'SUPER_ADMIN' }),
      ])
      setAdmins([...(r1.data || []), ...(r2.data || [])])
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Erro ao carregar administradores')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      // 1) Cria user comum
      await adminApi.createUser({
        email: createForm.email,
        password: createForm.password,
        full_name: createForm.full_name,
        role: 'user',
        plan_slug: 'basico',
      })
      // 2) Promove pra admin (precisa pegar id do recém-criado)
      const res = await adminApi.listUsers()
      const created = (res.data || []).find((u: any) => u.email === createForm.email)
      if (!created) throw new Error('Usuário criado mas não encontrado na lista')
      await api.put(`/admin/users/${created.id}/role`, { new_role: createForm.role, reason: 'criado via aba Administradores' })
      setShowCreate(false)
      setCreateForm({ email: '', password: '', full_name: '', role: 'admin' })
      await reload()
      alert('✅ Administrador criado com sucesso!')
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Erro ao criar administrador')
    } finally {
      setBusy(false)
    }
  }

  const handleRoleChange = async (adminId: string, newRole: string) => {
    if (adminId === currentUser?.id && newRole !== 'SUPER_ADMIN') {
      alert('⚠️ Você não pode rebaixar a si mesmo')
      return
    }
    if (!confirm(`Tem certeza que quer mudar o role deste administrador para "${newRole}"?`)) return
    setBusy(true)
    try {
      await api.put(`/admin/users/${adminId}/role`, { new_role: newRole, reason: 'mudança via aba Administradores' })
      await reload()
    } catch (e: any) {
      alert('❌ Erro: ' + (e.response?.data?.detail || e.message))
    } finally {
      setBusy(false)
    }
  }

  const openEdit = (admin: any) => {
    setEditTarget(admin)
    setEditForm({
      full_name: admin.full_name || '',
      is_active: admin.is_active,
      role: admin.role,
      new_password: '',
    })
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editTarget) return
    setBusy(true)
    setError(null)
    try {
      // 1) Atualiza full_name + is_active (endpoint PUT /admin/users/{id})
      await adminApi.updateUser(editTarget.id, {
        full_name: editForm.full_name,
        is_active: editForm.is_active,
      } as any)
      // 2) Se role mudou, chama endpoint dedicado
      if (editForm.role !== editTarget.role) {
        await api.put(`/admin/users/${editTarget.id}/role`, {
          new_role: editForm.role,
          reason: 'alteração via modal Editar',
        })
      }
      // 3) Se preencheu senha, troca (endpoint POST /admin/users/{id}/password)
      if (editForm.new_password && editForm.new_password.length >= 8) {
        await api.post(`/admin/users/${editTarget.id}/password`, {
          new_password: editForm.new_password,
          reason: 'reset via modal Editar',
        })
      } else if (editForm.new_password && editForm.new_password.length < 8 && editForm.new_password.length > 0) {
        alert('⚠️ Senha precisa ter no mínimo 8 caracteres — não foi trocada')
      }
      setEditTarget(null)
      await reload()
      alert('✅ Administrador atualizado!')
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Erro ao atualizar')
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (adminId: string, adminEmail: string) => {
    if (adminId === currentUser?.id) {
      alert('⚠️ Você não pode excluir a si mesmo')
      return
    }
    if (!confirm(`Excluir PERMANENTEMENTE o administrador ${adminEmail}?\n\nIsso vai apagar:\n- Conta\n- Perfil\n- Atributos\n- Conversas\n- Mensagens\n- Memórias (Qdrant)\n\nNÃO tem volta.`)) return
    setBusy(true)
    try {
      await api.delete(`/admin/users/${adminId}`)
      await reload()
      alert('✅ Administrador excluído')
    } catch (e: any) {
      alert('❌ Erro: ' + (e.response?.data?.detail || e.message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-ayria-text flex items-center gap-2">
            <Shield size={24} />
            Administradores
          </h2>
          <p className="text-sm text-ayria-muted mt-1">
            Apenas SUPER_ADMIN pode incluir, alterar ou excluir outros administradores.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          disabled={busy}
          className="px-4 py-2 rounded-xl text-white font-medium flex items-center gap-2 hover:opacity-90 disabled:opacity-50"
          style={{ background: '#f1c961' }}
        >
          <UserPlus size={16} />
          Novo Administrador
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-xl bg-red-900/20 border border-red-500/30 text-red-300 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-ayria-muted">Carregando...</div>
      ) : admins.length === 0 ? (
        <div className="text-center py-12 text-ayria-muted">
          <Shield size={48} className="mx-auto mb-3 opacity-30" />
          <p>Nenhum administrador cadastrado</p>
        </div>
      ) : (
        <ListWithControls
          data={admins}
          itemName="administrador"
          searchPlaceholder="Buscar por email, nome ou role..."
          emptyMessage="Nenhum administrador encontrado"
        >
          {(a) => (
            <div className="p-4 rounded-xl flex items-center justify-between" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold shrink-0"
                  style={{ background: a.role === 'SUPER_ADMIN' ? '#F59E0B' : '#f1c961' }}
                >
                  {a.email[0].toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-ayria-text font-medium truncate">{a.email}</div>
                  <div className="text-xs text-ayria-muted truncate">
                    {a.full_name || '(sem nome)'} • {a.message_count} mensagens
                    {a.id === currentUser?.id && <span className="ml-2 text-indigo-400">← VOCÊ</span>}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <select
                  value={a.role}
                  disabled={busy || a.id === currentUser?.id}
                  onChange={(e) => handleRoleChange(a.id, e.target.value)}
                  className="px-3 py-1.5 rounded-lg text-xs"
                  style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>
                <button
                  onClick={() => openEdit(a)}
                  disabled={busy}
                  className="text-indigo-400 hover:text-indigo-300 p-1"
                  title="Editar administrador"
                >
                  <Edit3 size={16} />
                </button>
                <button
                  onClick={() => handleDelete(a.id, a.email)}
                  disabled={busy || a.id === currentUser?.id}
                  className="text-red-400 hover:text-red-300 p-1 disabled:opacity-30"
                  title="Excluir administrador"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          )}
        </ListWithControls>
      )}

      {/* MODAL: Criar administrador */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6 relative" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <button onClick={() => setShowCreate(false)} className="absolute top-4 right-4 text-ayria-muted hover:text-ayria-text">
              <X size={20} />
            </button>
            <h3 className="text-xl font-bold text-ayria-text mb-4 flex items-center gap-2">
              <UserPlus size={20} />
              Novo Administrador
            </h3>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Email</label>
                <input
                  type="email" required
                  value={createForm.email}
                  onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                />
              </div>
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Nome completo</label>
                <input
                  type="text"
                  value={createForm.full_name}
                  onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                />
              </div>
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Senha (mínimo 8 caracteres)</label>
                <input
                  type="password" required minLength={8}
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                />
              </div>
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Role inicial</label>
                <select
                  value={createForm.role}
                  onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                >
                  <option value="admin">Admin</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>
              </div>
              {error && <div className="text-xs text-red-300">{error}</div>}
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 py-2 rounded-xl text-ayria-muted hover:text-ayria-text" style={{ border: '1px solid #2a2a3e' }}>
                  Cancelar
                </button>
                <button type="submit" disabled={busy} className="flex-1 py-2 rounded-xl text-white font-semibold disabled:opacity-50" style={{ background: '#f1c961' }}>
                  {busy ? 'Criando...' : 'Criar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Editar administrador */}
      {editTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6 relative" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <button onClick={() => setEditTarget(null)} className="absolute top-4 right-4 text-ayria-muted hover:text-ayria-text">
              <X size={20} />
            </button>
            <h3 className="text-xl font-bold text-ayria-text mb-1 flex items-center gap-2">
              <Edit3 size={20} />
              Editar Administrador
            </h3>
            <p className="text-xs text-ayria-muted mb-4">{editTarget.email}</p>
            <form onSubmit={handleEdit} className="space-y-3">
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Nome completo</label>
                <input
                  type="text"
                  value={editForm.full_name}
                  onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                  placeholder="Ex: João da Silva"
                />
              </div>
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Role</label>
                <select
                  value={editForm.role}
                  disabled={editTarget.id === currentUser?.id}
                  onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm disabled:opacity-50" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>
                {editTarget.id === currentUser?.id && (
                  <p className="text-xs text-ayria-muted mt-1">Você não pode rebaixar a si mesmo</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active_edit"
                  checked={editForm.is_active}
                  onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                  disabled={editTarget.id === currentUser?.id}
                  className="w-4 h-4"
                />
                <label htmlFor="is_active_edit" className="text-sm text-ayria-text cursor-pointer">
                  Administrador ativo
                </label>
                {editTarget.id === currentUser?.id && (
                  <span className="text-xs text-ayria-muted ml-2">(não pode desativar a si mesmo)</span>
                )}
              </div>
              <div>
                <label className="block text-xs text-ayria-muted mb-1">Nova senha (deixe vazio pra não trocar)</label>
                <input
                  type="password"
                  value={editForm.new_password}
                  onChange={(e) => setEditForm({ ...editForm, new_password: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
                  placeholder="Mínimo 8 caracteres"
                  minLength={0}
                />
              </div>
              {error && <div className="text-xs text-red-300">{error}</div>}
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setEditTarget(null)} className="flex-1 py-2 rounded-xl text-ayria-muted hover:text-ayria-text" style={{ border: '1px solid #2a2a3e' }}>
                  Cancelar
                </button>
                <button type="submit" disabled={busy} className="flex-1 py-2 rounded-xl text-white font-semibold disabled:opacity-50" style={{ background: '#f1c961' }}>
                  {busy ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}


// ============================================================
// 🆕 22/07 21:08 — SISTEMA DE CUPOM DE DESCONTO + PAGAMENTO
// 3 abas inline: Parceiros, Cupons, Comissões
// Usa stripeApi + couponsApi (já restaurados em lib/api.ts)
// ============================================================