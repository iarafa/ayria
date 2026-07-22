/**
 * AYRIA - Admin Page
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { adminApi, api } from '../lib/api'
import { LogoIcon } from '../components/Logo'
import { Users, FileText, Settings, LogOut, UserPlus, X, Shield, Wallet, Plus, Tag, Edit3, Eye, ChevronDown, ChevronRight, Calendar, MapPin, Star, Heart, Briefcase, Sparkles, ExternalLink, Cpu, CheckCircle2, AlertCircle, Database, Cloud, Activity, AlertTriangle, MessageCircle, MessageSquare, Receipt, User, Clock, Calculator, ClipboardList, Trash2 } from 'lucide-react'
import { AlmaTab } from '../components/AlmaTab'
import { LogsTab } from '../components/LogsTab'
import { ListWithControls } from '../components/ListWithControls'
import { SupervisorPromptModal } from '../components/SupervisorPromptModal'
import { SupervisorKeywordsViewer } from '../components/SupervisorKeywordsViewer'
import { BlockUserModal } from '../components/BlockUserModal'
import { AdminChangePasswordModal } from '../components/AdminChangePasswordModal'

type Tab = 'users' | 'plans' | 'credits' | 'knowledge' | 'onboarding' | 'attributes' | 'settings' | 'supervision' | 'alma' | 'logs' | 'admins'

export function AdminPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('users')
  const [users, setUsers] = useState<any[]>([])
  const [docs, setDocs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({ email: '', password: '', full_name: '', role: 'user', plan_slug: 'basico' })
  const [editingUser, setEditingUser] = useState<any>(null)
  const [passwordTarget, setPasswordTarget] = useState<{ id: string; email: string; full_name?: string | null } | null>(null)
  const [editForm, setEditForm] = useState({ full_name: '', is_active: true, selected_plan_slug: '' })
  const [availablePlans, setAvailablePlans] = useState<any[]>([])
  const [detailsUserId, setDetailsUserId] = useState<string | null>(null)
  const [detailsData, setDetailsData] = useState<any>(null)
  const [detailsLoading, setDetailsLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  useEffect(() => {
    if (user?.role !== 'admin' && user?.role !== 'SUPER_ADMIN') {
      navigate('/chat')
      return
    }
    // Carrega lista de planos (usada em criar/editar user e na aba Plans)
    if (availablePlans.length === 0) {
      adminApi.listPlans().then((r) => setAvailablePlans(r.data)).catch(() => {})
    }
    if (tab === 'users') {
      setLoading(true)
      adminApi.listUsers().then((r) => {
        setUsers(r.data)
        setLoading(false)
      })
    } else if (tab === 'knowledge') {
      setLoading(true)
      adminApi.listDocuments().then((r) => {
        setDocs(r.data)
        setLoading(false)
      })
    }
  }, [tab, user])

  const reloadUsers = async () => {
    const { data } = await adminApi.listUsers()
    setUsers(data)
  }

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setCreateError(null)
    try {
      await adminApi.createUser(createForm)
      setShowCreateModal(false)
      setCreateForm({ email: '', password: '', full_name: '', role: 'user', plan_slug: 'basico' })
      await reloadUsers()
      alert('✅ Usuário criado com sucesso!')
    } catch (e: any) {
      setCreateError(e.response?.data?.detail || 'Erro ao criar usuário')
    } finally {
      setCreating(false)
    }
  }

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingUser) return
    // Se selected_plan_slug vazio ('manter plano atual'), não envia o campo
    const payload = { ...editForm }
    if (!payload.selected_plan_slug) {
      delete (payload as any).selected_plan_slug
    }
    try {
      await adminApi.updateUser(editingUser.id, payload)
      setEditingUser(null)
      await reloadUsers()
    } catch (err: any) {
      alert('Erro ao editar: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleDeleteUser = async (u: any) => {
    if (!confirm(`Excluir o usuário ${u.email}?\n\nIsso deleta também todas as mensagens, chats e dados dele.\n\nEssa ação NÃO pode ser desfeita.`)) return
    try {
      await adminApi.deleteUser(u.id)
      await reloadUsers()
    } catch (err: any) {
      alert('Erro ao excluir: ' + (err.response?.data?.detail || err.message))
    }
  }

  const startEditUser = (u: any) => {
    setEditingUser(u)
    setEditForm({ full_name: u.full_name || '', is_active: u.is_active, selected_plan_slug: u.selected_plan_slug || '' })
  }

  const openUserDetails = async (userId: string) => {
    setDetailsUserId(userId)
    setDetailsData(null)
    setDetailsLoading(true)
    try {
      const { data } = await adminApi.getUserDetails(userId)
      setDetailsData(data)
    } catch (err: any) {
      alert('Erro ao carregar detalhes: ' + (err.response?.data?.detail || err.message))
      setDetailsUserId(null)
    } finally {
      setDetailsLoading(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('title', file.name)
    formData.append('file', file)
    await adminApi.uploadDocument(formData)
    alert('Upload feito! (Indexação em background - próxima fase)')
    const { data } = await adminApi.listDocuments()
    setDocs(data)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Deletar documento?')) return
    await adminApi.deleteDocument(id)
    setDocs(docs.filter((d) => d.id !== id))
  }

  return (
    <div className="min-h-screen" style={{ background: '#0A0A1A' }}>
      {/* Header */}
      <header className="glass px-6 py-4 flex items-center justify-between border-b border-ayria-border">
        <div className="flex items-center gap-3">
          <LogoIcon size={32} variant="circular" />
          <span
            className="px-2 py-1 rounded text-xs font-semibold"
            style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#F59E0B' }}
          >
            ADMIN
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/chat')} className="text-ayria-muted hover:text-ayria-text text-sm">
            Ir pro Chat
          </button>
          <button onClick={logout} className="text-ayria-muted hover:text-red-400">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Layout full-height: SIDEBAR lateral esquerda 100% altura + CONTEÚDO à direita (Rafael 22/07 20:34) */}
      <div className="flex" style={{ minHeight: 'calc(100vh - 73px)' }}>
        {/* Sidebar — LATERAL ESQUERDA COMPLETA, sem card, sem sticky, sem rounded, fundo próprio */}
        <aside
          className="w-64 shrink-0 flex flex-col border-r border-ayria-border"
          style={{ background: '#0F0F1F' }}
        >
          <nav className="flex-1 flex flex-col gap-1 p-3">
            {[
              { id: 'users', label: 'Usuários', icon: Users },
              { id: 'plans', label: 'Planos', icon: Tag },
              { id: 'credits', label: 'Créditos', icon: Wallet },
              { id: 'knowledge', label: 'Conhecimento', icon: FileText },
              { id: 'supervision', label: 'Supervisão', icon: Activity },
              { id: 'alma', label: 'ALMA', icon: Sparkles },
              { id: 'logs', label: 'Logs', icon: AlertTriangle },
              { id: 'settings', label: 'Configurações', icon: Cpu },
              // 🆕 22/07 20:38 — aba "Administradores" só pra SUPER_ADMIN
              ...(user?.role === 'SUPER_ADMIN'
                ? [{ id: 'admins', label: 'Administradores', icon: Shield }]
                : []),
            ].map((t) => {
              const isActive = tab === t.id
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id as Tab)}
                  className={`w-full px-4 py-3 text-sm flex items-center gap-3 transition-colors text-left ${
                    isActive
                      ? 'text-ayria-text font-medium'
                      : 'text-ayria-muted hover:bg-[#1a1a2e] hover:text-ayria-text'
                  }`}
                  style={
                    isActive
                      ? { borderLeft: '3px solid #6366F1', background: 'rgba(99, 102, 241, 0.15)' }
                      : { borderLeft: '3px solid transparent' }
                  }
                >
                  <t.icon size={16} />
                  <span>{t.label}</span>
                </button>
              )
            })}
          </nav>
        </aside>

        {/* Conteúdo principal */}
        <main className="flex-1 min-w-0 px-6 py-6 overflow-x-auto">

        {/* Content */}
        {loading && <div className="text-ayria-muted">Carregando...</div>}

        {/* USERS */}
        {tab === 'users' && !loading && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm text-ayria-muted">
                {users.length} usuário(s) cadastrado(s)
              </div>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 rounded-xl text-white font-medium flex items-center gap-2 hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
              >
                <UserPlus size={16} />
                Criar usuário
              </button>
            </div>

            <ListWithControls
              data={users}
              itemName="usuário"
              searchPlaceholder="Buscar por email, nome ou role..."
              emptyMessage="Nenhum usuário encontrado"
            >
              {(u) => (
                <div
                  key={u.id}
                  className="p-4 rounded-xl flex items-center justify-between"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold"
                      style={{ background: u.role === 'SUPER_ADMIN' ? 'linear-gradient(135deg, #F59E0B, #EF4444)' : 'linear-gradient(135deg, #6366F1, #A855F7)' }}
                    >
                      {u.email[0].toUpperCase()}
                    </div>
                    <div>
                      <div className="text-ayria-text font-medium">{u.email}</div>
                      <div className="text-xs text-ayria-muted">
                        {u.full_name || '-'} · {u.role} · {u.message_count} msgs
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className="text-xs px-2 py-1 rounded"
                      style={{
                        background: u.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                        color: u.is_active ? '#10B981' : '#EF4444',
                      }}
                    >
                      {u.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                    <span
                      className="text-xs px-2 py-1 rounded"
                      style={{
                        background: u.onboarding_status === 'completed' ? 'rgba(99,102,241,0.15)' : 'rgba(168,85,247,0.15)',
                        color: u.onboarding_status === 'completed' ? '#6366F1' : '#A855F7',
                      }}
                    >
                      {u.onboarding_status}
                    </span>
                    {u.id !== user?.id && (
                      <>
                        <button
                          onClick={() => openUserDetails(u.id)}
                          className="text-xs px-3 py-1 rounded flex items-center gap-1"
                          style={{ background: 'rgba(168,85,247,0.15)', color: '#A855F7' }}
                          title="Ver detalhes completos (perfil, numerologia, astrologia)"
                        >
                          <Eye size={12} />
                          Detalhes
                        </button>
                        <button
                          onClick={() => navigate(`/admin/observe/${u.id}`)}
                          className="text-xs px-3 py-1 rounded flex items-center gap-1 text-white"
                          style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}
                          title="Abrir modo observador (read-only, auditado)"
                        >
                          <Eye size={12} />
                          Observador
                        </button>
                        <button
                          onClick={() => startEditUser(u)}
                          className="text-xs px-3 py-1 rounded flex items-center gap-1"
                          style={{ background: 'rgba(99,102,241,0.15)', color: '#6366F1' }}
                          title="Editar usuário"
                        >
                          Editar
                        </button>
                        <button
                          onClick={() => setPasswordTarget({ id: u.id, email: u.email, full_name: u.full_name })}
                          className="text-xs px-3 py-1 rounded flex items-center gap-1"
                          style={{ background: 'rgba(245,158,11,0.15)', color: '#F59E0B' }}
                          title="Resetar senha do usuário"
                        >
                          🔑 Senha
                        </button>
                        <button
                          onClick={() => handleDeleteUser(u)}
                          className="text-xs px-3 py-1 rounded text-red-400 hover:text-red-300 flex items-center gap-1"
                          style={{ background: 'rgba(239,68,68,0.1)' }}
                          title="Excluir usuário"
                        >
                          Excluir
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </ListWithControls>
          </div>
        )}

        {/* PLANOS - CRUD de planos (admin) */}
        {tab === 'plans' && !loading && (
          <PlansTab
            availablePlans={availablePlans}
            reloadPlans={async () => {
              const r = await adminApi.listPlans()
              setAvailablePlans(r.data)
            }}
          />
        )}

        {/* CRÉDITOS - visão comercial + ajuste manual */}
        {tab === 'credits' && !loading && (
          <CreditsTab users={users} onAdjust={async (userId, amount, description, type) => {
            try {
              await adminApi.adjustCredits({ user_id: userId, amount, description, type })
              await reloadUsers() // recarrega lista
              alert(`✅ Ajuste de ${amount > 0 ? '+' : ''}${amount} créditos realizado.`)
            } catch (e: any) {
              alert(`❌ Erro: ${e?.response?.data?.detail || 'Falhou'}`)
            }
          }} />
        )}

        {/* ═══════════════════════════════════════════════
            🆕 MODAL: Admin resetar senha do usuário
            ═══════════════════════════════════════════════ */}
        <AdminChangePasswordModal
          open={!!passwordTarget}
          onClose={() => setPasswordTarget(null)}
          user={passwordTarget}
          onSuccess={() => reloadUsers()}
        />
{/* KNOWLEDGE */}
        {tab === 'knowledge' && !loading && (
          <div>
            <div className="mb-4">
              <label className="inline-block px-4 py-2 rounded-xl cursor-pointer text-white font-medium"
                style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}>
                + Upload de documento
                <input type="file" accept=".pdf,.txt,.md" onChange={handleUpload} className="hidden" />
              </label>
            </div>
            <div className="space-y-2">
              {docs.map((d) => (
                <div
                  key={d.id}
                  className="p-4 rounded-xl flex items-center justify-between"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="text-ayria-text font-medium">{d.title}</div>
                      <span
                        className="text-[10px] px-2 py-0.5 rounded uppercase tracking-wider font-semibold"
                        style={{
                          background: d.storage_provider === 'azure' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(168, 85, 247, 0.15)',
                          color: d.storage_provider === 'azure' ? '#38BDF8' : '#A855F7',
                          border: `1px solid ${d.storage_provider === 'azure' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(168, 85, 247, 0.3)'}`,
                        }}
                      >
                        {d.storage_provider || 'local'}
                      </span>
                    </div>
                    <div className="text-xs text-ayria-muted mt-1">
                      {d.file_name} · {(d.file_size_bytes / 1024).toFixed(1)}KB · {d.status}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(d.id)}
                    className="text-red-400 hover:text-red-300 text-sm"
                  >
                    Deletar
                  </button>
                </div>
              ))}
              {docs.length === 0 && (
                <div className="text-center text-ayria-muted py-8">
                  Nenhum documento ainda.
                </div>
              )}
            </div>
          </div>
        )}

        {/* SETTINGS / CONFIGURAÇÕES DO SISTEMA */}
        {tab === 'settings' && <SystemSettingsTab />}
        {tab === 'logs' && <LogsTab />}

        {/* SUPERVISÃO - monitoramento de risco */}
        {tab === 'supervision' && <SupervisionTab />}

        {/* ALMA - editor do system prompt da Ayria */}
        {tab === 'alma' && <AlmaTab />}

        {/* 🆕 22/07 20:38 — ADMINISTRADORES (só SUPER_ADMIN pode mexer) */}
        {tab === 'admins' && user?.role === 'SUPER_ADMIN' && <AdminsManagementTab />}
        </main>
      </div>

      {/* MODAL: Criar usuário */}
      {showCreateModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
          onClick={() => setShowCreateModal(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl p-6 relative"
            style={{ background: '#111111', border: '1px solid #1E1E2E' }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowCreateModal(false)}
              className="absolute top-4 right-4 text-ayria-muted hover:text-ayria-text"
            >
              <X size={20} />
            </button>

            <h2 className="text-2xl font-bold mb-2 gradient-text">Criar novo usuário</h2>
            <p className="text-sm text-ayria-muted mb-6">
              Cria uma conta que pode logar imediatamente e fazer o onboarding.
            </p>

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm text-ayria-muted mb-2">Nome completo</label>
                <input
                  type="text"
                  value={createForm.full_name}
                  onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                  placeholder="Maria Silva"
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}
                />
              </div>

              <div>
                <label className="block text-sm text-ayria-muted mb-2">Email *</label>
                <input
                  type="email"
                  required
                  value={createForm.email}
                  onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                  placeholder="maria@exemplo.com"
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}
                />
              </div>

              <div>
                <label className="block text-sm text-ayria-muted mb-2">Senha * (mín 6 chars)</label>
                <input
                  type="text"
                  required
                  minLength={6}
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  placeholder="senha123"
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}
                />
                <p className="text-xs text-ayria-muted mt-1">
                  (pode ver a senha digitada - útil pra você passar pro usuário)
                </p>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="isAdminCheckbox"
                  checked={createForm.role === 'SUPER_ADMIN'}
                  onChange={(e) => setCreateForm({ ...createForm, role: e.target.checked ? 'SUPER_ADMIN' : 'user' })}
                  className="w-4 h-4 rounded accent-indigo-500"
                />
                <label htmlFor="isAdminCheckbox" className="text-sm text-ayria-text cursor-pointer">
                  Criar como <strong>administrador</strong> (acesso ao dashboard admin)
                </label>
              </div>

              <div>
                <label className="block text-sm text-ayria-muted mb-2">Plano inicial</label>
                <select
                  value={createForm.plan_slug}
                  onChange={(e) => setCreateForm({ ...createForm, plan_slug: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#050505', border: '1px solid #1E1E2E' }}
                >
                  {availablePlans.filter((p: any) => p.active).map((p: any) => (
                    <option key={p.id} value={p.slug}>
                      {p.name} - {p.credits} créditos · R$ {p.price_brl.toFixed(2)}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-ayria-muted mt-1">
                  O saldo inicial será concedido automaticamente.
                </p>
              </div>

              {createError && (
                <div
                  className="px-4 py-2 rounded-lg text-sm"
                  style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444' }}
                >
                  {createError}
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 py-3 rounded-xl text-ayria-muted hover:text-ayria-text"
                  style={{ border: '1px solid #1E1E2E' }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 py-3 rounded-xl text-white font-semibold disabled:opacity-50"
                  style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
                >
                  {creating ? 'Criando...' : 'Criar usuário'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL EDITAR */}
      {editingUser && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={() => setEditingUser(null)}
        >
          <div
            className="w-full max-w-md p-6 rounded-2xl"
            style={{ background: '#0a0a0a', border: '1px solid #1E1E2E' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold gradient-text">Editar usuário</h2>
              <button onClick={() => setEditingUser(null)} className="text-ayria-muted hover:text-ayria-text">
                <X size={20} />
              </button>
            </div>

            <div className="text-xs text-ayria-muted mb-4 space-y-1">
              <div>📧 <strong className="text-ayria-text">{editingUser.email}</strong></div>
              <div>👤 Role: <strong className="text-ayria-text">{editingUser.role}</strong> (não pode ser alterado)</div>
            </div>

            <form onSubmit={handleUpdateUser} className="space-y-4">
              <div>
                <label className="block text-sm text-ayria-muted mb-2">Nome completo</label>
                <input
                  type="text"
                  value={editForm.full_name}
                  onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                  placeholder="Nome do usuário"
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#050505', border: '1px solid #1E1E2E' }}
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="isActiveCheckbox"
                  checked={editForm.is_active}
                  onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                  className="w-4 h-4 rounded accent-indigo-500"
                />
                <label htmlFor="isActiveCheckbox" className="text-sm text-ayria-text cursor-pointer">
                  Usuário <strong>ativo</strong> (pode logar)
                </label>
              </div>

              <div>
                <label className="block text-sm text-ayria-muted mb-2">Plano</label>
                <select
                  value={editForm.selected_plan_slug}
                  onChange={(e) => setEditForm({ ...editForm, selected_plan_slug: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#050505', border: '1px solid #1E1E2E' }}
                >
                  <option value="">- manter plano atual -</option>
                  {availablePlans.filter((p: any) => p.active).map((p: any) => (
                    <option key={p.id} value={p.slug}>
                      {p.name} - {p.credits} créditos
                    </option>
                  ))}
                </select>
                <p className="text-xs text-ayria-muted mt-1">
                  Trocar o plano ajusta o saldo pela diferença (pode adicionar ou remover créditos) e registra uma transação.
                </p>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="flex-1 py-3 rounded-xl text-ayria-text"
                  style={{ border: '1px solid #1E1E2E' }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 rounded-xl text-white font-semibold"
                  style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
                >
                  Salvar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL DETALHES DO USUÁRIO */}
      <UserDetailsModal
        userId={detailsUserId}
        data={detailsData}
        loading={detailsLoading}
        onClose={() => setDetailsUserId(null)}
      />
    </div>
  )
}

// ============================================================
// CreditsTab - visão comercial + ajuste manual
// ============================================================
function CreditsTab({ users, onAdjust }: {
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

      {/* Lista */}
      <div className="space-y-2">
        {filtered.map((u) => (
          <div
            key={u.id}
            className="p-3 rounded-xl flex items-center justify-between"
            style={{ background: '#111111', border: '1px solid #1E1E2E' }}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-semibold"
                style={{ background: u.role === 'SUPER_ADMIN' ? 'linear-gradient(135deg, #F59E0B, #EF4444)' : 'linear-gradient(135deg, #6366F1, #A855F7)' }}
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
                style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
              >
                Ajustar
              </button>
            </div>
          </div>
        ))}
      </div>

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
              Saldo atual: <strong style={{ color: '#A855F7' }}>{adjustModal.user.credit_balance || 0}</strong>
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
                style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
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
function PlansTab({ availablePlans, reloadPlans }: {
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
              style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
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
                  style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
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
function UserDetailsModal({ userId, data, loading, onClose }: {
  userId: string | null
  data: any
  loading: boolean
  onClose: () => void
}) {
  const navigate = useNavigate()
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    basics: true, onboarding: true, numerology: true, astrology: true,
    dynamic: false, stats: true,
  })

  const toggle = (k: string) => setExpandedSections((s) => ({ ...s, [k]: !s[k] }))

  if (!userId) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center px-4 py-8 overflow-y-auto"
      style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(6px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl rounded-2xl p-6 my-auto"
        style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-ayria-border">
          <div>
            <h2 className="text-2xl font-bold gradient-text">
              {data?.full_name || data?.email || 'Detalhes do usuário'}
            </h2>
            <div className="text-xs text-ayria-muted mt-1">
              {data?.email} · {data?.role}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {userId && (
              <button
                onClick={() => navigate(`/admin/observe/${userId}`)}
                className="px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 text-white"
                style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}
                title="Abrir modo observador (read-only, auditado) - mesma aba"
              >
                <Eye size={14} />
                Modo Observador
                <ExternalLink size={11} />
              </button>
            )}
            <button onClick={onClose} className="text-ayria-muted hover:text-white">
              <X size={24} />
            </button>
          </div>
        </div>

        {loading || !data ? (
          <div className="py-12 text-center text-ayria-muted">Carregando detalhes...</div>
        ) : (
          <div className="space-y-5">
            {/* ============================================================ */}
            {/* HEADER DO PERFIL - avatar grande + identidade + ações */}
            {/* ============================================================ */}
            <UserHeader data={data} onClose={onClose} navigate={navigate} />

            {/* ============================================================ */}
            {/* STATS - 4 cards de uso rápido */}
            {/* ============================================================ */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard
                icon={<MessageCircle size={18} />}
                label="Chats"
                value={data.chats_count || 0}
                color="#A855F7"
              />
              <StatCard
                icon={<MessageSquare size={18} />}
                label="Mensagens"
                value={data.message_count || 0}
                color="#6366F1"
              />
              <StatCard
                icon={<Wallet size={18} />}
                label="Saldo"
                value={`${(data.credit_balance || 0).toLocaleString('pt-BR')}`}
                subtitle="créditos"
                color={data.credit_balance > 0 ? '#10B981' : '#EF4444'}
              />
              <StatCard
                icon={<Receipt size={18} />}
                label="Transações"
                value={data.credit_transactions_count || 0}
                color="#F59E0B"
              />
            </div>

            {/* ============================================================ */}
            {/* VISÃO GERAL - dados de conta */}
            {/* ============================================================ */}
            <Section title="Visão geral" icon={<Shield size={16} />} expanded={expandedSections.basics} onToggle={() => toggle('basics')}>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-4">
                <Field label="Plano" value={data.selected_plan_name || '- sem plano -'} highlight={!!data.selected_plan_slug} />
                <Field label="Status onboarding" value={data.onboarding_status} highlight={data.onboarding_status === 'completed' ? 'success' : 'danger'} />
                <Field label="Status perfil" value={data.profile_status || '-'} />
                <Field label="Role" value={data.role} highlight={data.role === 'SUPER_ADMIN' || data.role === 'admin'} />
                <Field label="Conta ativa" value={data.is_active ? 'Sim' : 'Não'} highlight={data.is_active ? 'success' : 'danger'} />
                <Field label="Cadastro" value={data.created_at ? new Date(data.created_at).toLocaleDateString('pt-BR') : '-'} />
                <Field label="Último login" value={data.last_login_at ? new Date(data.last_login_at).toLocaleString('pt-BR') : 'Nunca'} />
                <Field label="Último chat" value={data.last_chat_at ? new Date(data.last_chat_at).toLocaleString('pt-BR') : 'Nunca'} />
                <Field label="Avatar" value={data.avatar_url ? 'Configurado' : 'Sem foto'} />
              </div>
            </Section>

            {/* ============================================================ */}
            {/* DADOS DE ONBOARDING */}
            {/* ============================================================ */}
            {data.profile_attributes && Object.keys(data.profile_attributes).length > 0 && (
              <Section title="Dados de onboarding" icon={<ClipboardList size={16} />} expanded={expandedSections.onboarding} onToggle={() => toggle('onboarding')}>
                <div className="space-y-2">
                  {Object.entries(data.profile_attributes).map(([key, value]) => (
                    <DataRow
                      key={key}
                      icon={<Tag size={12} />}
                      label={humanizeKey(key)}
                      value={formatValue(value)}
                    />
                  ))}
                </div>
              </Section>
            )}

            {/* ============================================================ */}
            {/* NUMEROLOGIA - cards grandes */}
            {/* ============================================================ */}
            {data.numerology_data && Object.keys(data.numerology_data).length > 0 && (
              <Section title="Numerologia" icon={<Sparkles size={16} />} expanded={expandedSections.numerology} onToggle={() => toggle('numerology')}>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {data.numerology_data.caminho_vida && (
                    <NumberCard label="Caminho de Vida" numero={data.numerology_data.caminho_vida.numero} ehMestre={data.numerology_data.caminho_vida.eh_mestre} />
                  )}
                  {data.numerology_data.alma && (
                    <NumberCard label="Alma" numero={data.numerology_data.alma.numero} />
                  )}
                  {data.numerology_data.expressao && (
                    <NumberCard label="Expressão" numero={data.numerology_data.expressao.numero} ehMestre={data.numerology_data.expressao.eh_mestre} />
                  )}
                  {data.numerology_data.personalidade && (
                    <NumberCard label="Personalidade" numero={data.numerology_data.personalidade.numero} />
                  )}
                  {data.numerology_data.ano_pessoal && (
                    <NumberCard label={`Ano Pessoal ${data.numerology_data.ano_pessoal.ano || new Date().getFullYear()}`} numero={data.numerology_data.ano_pessoal.numero} />
                  )}
                </div>
                {data.numerology_data.dados_usados && (
                  <div className="mt-4 pt-3 border-t border-ayria-border">
                    <div className="text-xs font-semibold text-ayria-text mb-2">Dados usados no cálculo</div>
                    <div className="space-y-1">
                      {data.numerology_data.dados_usados.nome_completo && (
                        <DataRow icon={<User size={12} />} label="Nome completo" value={data.numerology_data.dados_usados.nome_completo} />
                      )}
                      {data.numerology_data.dados_usados.data_nascimento && (
                        <DataRow icon={<Calendar size={12} />} label="Data de nascimento" value={data.numerology_data.dados_usados.data_nascimento} />
                      )}
                      {data.numerology_data.dados_usados.hora_nascimento && (
                        <DataRow icon={<Clock size={12} />} label="Hora" value={data.numerology_data.dados_usados.hora_nascimento} />
                      )}
                      {data.numerology_data.dados_usados.local_nascimento && (
                        <DataRow icon={<MapPin size={12} />} label="Local" value={data.numerology_data.dados_usados.local_nascimento} />
                      )}
                      {data.numerology_data.calculado_em && (
                        <DataRow icon={<Calculator size={12} />} label="Calculado em" value={new Date(data.numerology_data.calculado_em).toLocaleString('pt-BR')} />
                      )}
                    </div>
                  </div>
                )}
              </Section>
            )}

            {/* ============================================================ */}
            {/* ASTROLOGIA - mapa astral */}
            {/* ============================================================ */}
            {data.astrology_data && Object.keys(data.astrology_data).length > 0 && (
              <Section title="Mapa Astral" icon={<Star size={16} />} expanded={expandedSections.astrology} onToggle={() => toggle('astrology')}>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                  {data.astrology_data.sol && (
                    <PlanetCard nome="☀️ Sol" signo={data.astrology_data.sol.signo_pt} elemento={data.astrology_data.sol.elemento} casa={data.astrology_data.sol.casa} destaque />
                  )}
                  {data.astrology_data.lua && (
                    <PlanetCard nome="🌙 Lua" signo={data.astrology_data.lua.signo_pt} elemento={data.astrology_data.lua.elemento} casa={data.astrology_data.lua.casa} destaque />
                  )}
                  {data.astrology_data.ascendente && (
                    <PlanetCard nome="⬆️ Ascendente" signo={data.astrology_data.ascendente.signo_pt} destaque />
                  )}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
                  {['mercurio', 'venus', 'marte', 'jupiter', 'saturno'].map((p) => {
                    const info = data.astrology_data[p]
                    if (!info) return null
                    const emoji = p === 'mercurio' ? '☿' : p === 'venus' ? '♀' : p === 'marte' ? '♂' : p === 'jupiter' ? '♃' : '♄'
                    return <PlanetCard key={p} nome={`${emoji} ${capitalize(p)}`} signo={info.signo_pt} elemento={info.elemento} casa={info.casa} />
                  })}
                </div>
                {data.astrology_data.coordenadas && (
                  <div className="pt-3 border-t border-ayria-border">
                    <div className="text-xs font-semibold text-ayria-text mb-2">Dados do cálculo</div>
                    <div className="space-y-1">
                      {data.astrology_data.cidade_usada && (
                        <DataRow icon={<MapPin size={12} />} label="Cidade" value={data.astrology_data.cidade_usada} />
                      )}
                      {data.astrology_data.coordenadas && (
                        <DataRow icon={<MapPin size={12} />} label="Lat / Lon" value={`${data.astrology_data.coordenadas.lat} / ${data.astrology_data.coordenadas.lon}`} />
                      )}
                      {data.astrology_data.data_calculo && (
                        <DataRow icon={<Calculator size={12} />} label="Calculado em" value={new Date(data.astrology_data.data_calculo).toLocaleString('pt-BR')} />
                      )}
                    </div>
                  </div>
                )}
              </Section>
            )}

            {/* ============================================================ */}
            {/* ATRIBUTOS DINÂMICOS */}
            {/* ============================================================ */}
            {data.dynamic_attributes && data.dynamic_attributes.length > 0 && (
              <Section title="Atributos dinâmicos" icon={<Briefcase size={16} />} expanded={expandedSections.dynamic} onToggle={() => toggle('dynamic')}>
                <div className="space-y-2">
                  {data.dynamic_attributes.map((a: any, i: number) => (
                    <DataRow
                      key={i}
                      icon={<Tag size={12} />}
                      label={`${a.attribute_name}`}
                      sublabel={a.attribute_code}
                      value={formatValue(a.value)}
                    />
                  ))}
                </div>
              </Section>
            )}

            {!data.profile_attributes && !data.numerology_data && !data.astrology_data && !data.dynamic_attributes?.length && (
              <EmptyState />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// === Sub-componentes auxiliares ===
function Section({ title, icon, expanded, onToggle, children }: { title: string; icon: React.ReactNode; expanded: boolean; onToggle: () => void; children: React.ReactNode }) {
  return (
    <div className="rounded-xl overflow-hidden" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between hover:bg-[#1a1a1a] transition-colors">
        <div className="flex items-center gap-2 text-ayria-text font-semibold">
          {icon}
          {title}
        </div>
        {expanded ? <ChevronDown size={16} className="text-ayria-muted" /> : <ChevronRight size={16} className="text-ayria-muted" />}
      </button>
      {expanded && <div className="px-4 pb-4 pt-1">{children}</div>}
    </div>
  )
}

function Field({ label, value, highlight }: { label: string; value: any; highlight?: 'success' | 'danger' | boolean }) {
  let color = ''
  if (highlight === 'success') color = '#10B981'
  else if (highlight === 'danger') color = '#EF4444'
  else if (highlight === true) color = '#A855F7'

  return (
    <div>
      <div className="text-xs text-ayria-muted mb-0.5">{label}</div>
      <div className="text-sm font-medium" style={{ color: color || undefined }}>{value || '-'}</div>
    </div>
  )
}

// === Header grande do user (avatar + identidade + status badges) ===
function UserHeader({ data, onClose, navigate }: { data: any; onClose: () => void; navigate: any }) {
  const initials = (data.full_name || data.email || '?')
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s.charAt(0).toUpperCase())
    .join('')

  const planColor =
    data.selected_plan_slug === 'premium' ? '#F59E0B' :
    data.selected_plan_slug === 'intermediario' ? '#A855F7' :
    '#6366F1'

  const onboardingColors: Record<string, string> = {
    completed: '#10B981',
    in_progress: '#F59E0B',
    pending: '#94A3B8',
    skipped: '#64748B',
  }
  const obColor = onboardingColors[data.onboarding_status] || '#94A3B8'

  return (
    <div
      className="rounded-2xl p-5 sm:p-6"
      style={{
        background: 'linear-gradient(135deg, rgba(99,102,241,0.10), rgba(168,85,247,0.10))',
        border: '1px solid rgba(99, 102, 241, 0.3)',
      }}
    >
      <div className="flex items-start gap-4">
        {/* Avatar ou iniciais */}
        {data.avatar_url ? (
          <img src={data.avatar_url} alt="avatar" className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover flex-shrink-0" onError={(e) => (e.currentTarget.style.display = 'none')} />
        ) : (
          <div
            className="w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center font-bold text-2xl flex-shrink-0"
            style={{
              background: `linear-gradient(135deg, ${planColor}, #A855F7)`,
              color: '#FFFFFF',
            }}
          >
            {initials}
          </div>
        )}

        {/* Identidade */}
        <div className="flex-1 min-w-0">
          <h3 className="text-xl sm:text-2xl font-bold text-ayria-text truncate">
            {data.full_name || data.email}
          </h3>
          <div className="text-sm text-ayria-muted truncate mt-0.5">{data.email}</div>

          {/* Badges */}
          <div className="flex flex-wrap gap-2 mt-3">
            {data.role && (
              <Badge color="#A855F7" icon={<Shield size={11} />}>
                {data.role}
              </Badge>
            )}
            {data.selected_plan_name ? (
              <Badge color={planColor} icon={<Star size={11} />}>
                {data.selected_plan_name}
              </Badge>
            ) : (
              <Badge color="#64748B">Sem plano</Badge>
            )}
            <Badge color={obColor} icon={<CheckCircle2 size={11} />}>
              Onboarding: {data.onboarding_status || '-'}
            </Badge>
            {data.is_active ? (
              <Badge color="#10B981" icon={<CheckCircle2 size={11} />}>Ativo</Badge>
            ) : (
              <Badge color="#EF4444" icon={<AlertCircle size={11} />}>Inativo</Badge>
            )}
          </div>
        </div>

        {/* Ação: abrir no Modo Observador */}
        {data?.id && (
          <button
            onClick={() => navigate(`/admin/observe/${data.id}`)}
            className="flex-shrink-0 px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 text-white shadow-lg hover:scale-105 transition-transform"
            style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}
            title="Abrir modo observador (read-only, auditado)"
          >
            <Eye size={14} />
            <span className="hidden sm:inline">Observar</span>
            <ExternalLink size={11} />
          </button>
        )}
      </div>

      {/* Datas em uma linha */}
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-ayria-muted mt-4 pt-4 border-t" style={{ borderColor: 'rgba(99, 102, 241, 0.2)' }}>
        <span>📅 Cadastrado em {data.created_at ? new Date(data.created_at).toLocaleDateString('pt-BR') : '-'}</span>
        <span>🕐 Último login {data.last_login_at ? new Date(data.last_login_at).toLocaleString('pt-BR') : 'nunca'}</span>
      </div>
    </div>
  )
}

// === Badge compacto ===
function Badge({ color, icon, children }: { color: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold"
      style={{
        background: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
      }}
    >
      {icon}
      {children}
    </span>
  )
}

// === Stat card (4 stats em grade) ===
function StatCard({ icon, label, value, subtitle, color }: { icon: React.ReactNode; label: string; value: any; subtitle?: string; color: string }) {
  return (
    <div
      className="p-4 rounded-xl"
      style={{
        background: `${color}10`,
        border: `1px solid ${color}30`,
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-ayria-muted">{label}</span>
        <span style={{ color: color }}>{icon}</span>
      </div>
      <div className="text-2xl font-bold" style={{ color: color }}>{value}</div>
      {subtitle && <div className="text-xs text-ayria-muted mt-0.5">{subtitle}</div>}
    </div>
  )
}

// === Data row (label à esquerda, valor à direita) ===
function DataRow({ icon, label, sublabel, value }: { icon?: React.ReactNode; label: string; sublabel?: string; value: any }) {
  return (
    <div
      className="flex items-start gap-3 px-3 py-2.5 rounded-lg"
      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)' }}
    >
      {icon && <span className="text-ayria-muted mt-0.5 flex-shrink-0">{icon}</span>}
      <div className="flex-1 min-w-0">
        <div className="text-xs text-ayria-muted">{label}</div>
        {sublabel && <div className="text-[10px] text-ayria-muted opacity-60">{sublabel}</div>}
      </div>
      <div className="text-sm font-medium text-ayria-text text-right break-words max-w-[60%]">
        {value || '-'}
      </div>
    </div>
  )
}

// === Empty state ===
function EmptyState() {
  return (
    <div className="text-center text-ayria-muted py-12">
      <Heart size={48} className="mx-auto mb-3 opacity-30" />
      <div className="text-sm">Este usuário ainda não completou o onboarding.</div>
      <div className="text-xs mt-1 opacity-70">Numerologia, astrologia e atributos dinâmicos aparecerão aqui depois.</div>
    </div>
  )
}

function NumberCard({ label, numero, ehMestre }: { label: string; numero: number; ehMestre?: boolean }) {
  return (
    <div
      className="p-4 rounded-xl text-center"
      style={{
        background: ehMestre
          ? 'linear-gradient(135deg, rgba(245,158,11,0.2), rgba(239,68,68,0.2))'
          : 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.15))',
        border: ehMestre ? '1px solid rgba(245,158,11,0.4)' : '1px solid rgba(168,85,247,0.3)',
      }}
    >
      <div className="text-3xl font-bold gradient-text">{numero}</div>
      <div className="text-xs text-ayria-muted mt-1">{label}</div>
      {ehMestre && <div className="text-xs mt-1" style={{ color: '#F59E0B' }}>✨ Número Mestre</div>}
    </div>
  )
}

function PlanetCard({ nome, signo, elemento, casa, destaque }: { nome: string; signo: string; elemento?: string; casa?: number | string; destaque?: boolean }) {
  return (
    <div
      className="p-3 rounded-xl"
      style={{
        background: destaque ? 'rgba(168,85,247,0.1)' : '#0a0a0a',
        border: destaque ? '1px solid rgba(168,85,247,0.3)' : '1px solid #1E1E2E',
      }}
    >
      <div className="text-xs text-ayria-muted">{nome}</div>
      <div className="text-lg font-bold text-ayria-text">{signo || '-'}</div>
      {elemento && <div className="text-xs text-ayria-muted">{elemento}{casa ? ` · Casa ${casa}` : ''}</div>}
    </div>
  )
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatValue(value: any): string {
  if (value === null || value === undefined) return '-'
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}


// ============================================================
// SETTINGS TAB - Mostra QUAL IA está em uso + status sistema
// ============================================================
function SystemSettingsTab() {
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  async function loadConfig() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/api/admin/config/ai')
      setConfig(res.data)
    } catch (e: any) {
      setError(e.message || 'Erro ao carregar config')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-2 border-ayria-admin border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-red-900/20 border border-red-500/30 text-red-300">
        ❌ {error}
      </div>
    )
  }

  const ai = config?.ai
  const azure = config?.azure_storage
  const env = config?.environment
  const rules = config?.rules || []

  return (
    <div className="space-y-6">
      {/* HEADER: qual IA tá rodando */}
      <div
        className="p-6 rounded-2xl"
        style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)', border: '1px solid #2a2a3e' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}
            >
              <Cpu size={24} className="text-white" />
            </div>
            <div>
              <div className="text-xs text-ayria-muted uppercase tracking-wider">Modelo de IA em uso</div>
              <div className="text-2xl font-bold text-ayria-text mt-1">
                {ai?.model || '(não configurado)'}
              </div>
              <div className="text-sm text-ayria-muted mt-1">
                Provider: <span className="text-ayria-text font-medium">{ai?.provider || '-'}</span>
              </div>
            </div>
          </div>
          {ai?.configured ? (
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/30">
              <CheckCircle2 size={14} />
              ATIVO
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/30">
              <AlertCircle size={14} />
              NÃO CONFIGURADO
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Base URL</div>
            <div className="text-sm text-ayria-text font-mono break-all">{ai?.base_url || '-'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">API Key</div>
            <div className="text-sm text-ayria-text font-mono">{ai?.api_key_preview || '(vazio)'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Status</div>
            <div className="text-sm text-ayria-text">
              {ai?.api_key_set ? '✅ Chave configurada' : '❌ Sem chave'}
            </div>
          </div>
        </div>
      </div>

      {/* REGRAS DO SISTEMA */}
      <div
        className="p-5 rounded-2xl"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Shield size={16} className="text-ayria-admin" />
          <div className="text-sm font-semibold text-ayria-text">Regras do Sistema</div>
        </div>
        <ul className="space-y-2">
          {rules.map((r: string, i: number) => (
            <li key={i} className="flex items-start gap-2 text-sm text-ayria-muted">
              <CheckCircle2 size={14} className="text-green-400 mt-0.5 flex-shrink-0" />
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* AZURE STORAGE */}
      <div
        className="p-5 rounded-2xl"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Cloud size={16} className="text-blue-400" />
          <div className="text-sm font-semibold text-ayria-text">Azure Blob Storage</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Status</div>
            <div className="text-sm text-ayria-text">
              {azure?.configured ? '✅ Configurado' : '❌ Não configurado'}
            </div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Container</div>
            <div className="text-sm text-ayria-text font-mono">{azure?.container || '-'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">SAS expira em</div>
            <div className="text-sm text-ayria-text">{azure?.sas_expires || '-'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Fallback local</div>
            <div className="text-sm text-ayria-text">
              {azure?.use_local_fallback ? '⚠️ Ativo (debug)' : '✅ Desativado (produção)'}
            </div>
          </div>
        </div>
      </div>

      {/* AMBIENTE */}
      <div
        className="p-5 rounded-2xl"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Database size={16} className="text-purple-400" />
          <div className="text-sm font-semibold text-ayria-text">Ambiente</div>
        </div>
        <div className="text-sm text-ayria-muted">
          Modo: <span className="text-ayria-text font-mono">{env || '-'}</span>
        </div>
      </div>

      {/* BOTÃO REFRESH */}
      <div className="flex justify-end">
        <button
          onClick={loadConfig}
          className="px-4 py-2 rounded-lg text-sm bg-ayria-admin/10 text-ayria-admin border border-ayria-admin/30 hover:bg-ayria-admin/20 transition-colors flex items-center gap-2"
        >
          <Settings size={14} />
          Atualizar
        </button>
      </div>
    </div>
  )
}


// ============================================================
// SUPERVISION TAB - Monitoramento de risco psicossocial
// ============================================================
function SupervisionTab() {
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
              style={{ background: 'linear-gradient(135deg, rgba(168,85,247,0.25), rgba(99,102,241,0.25))' }}
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
                background: 'linear-gradient(135deg, rgba(99,102,241,0.20), rgba(168,85,247,0.20))',
                color: '#C4B5FD',
                border: '1px solid rgba(168,85,247,0.4)',
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
            <div className="mb-4 p-3 rounded-xl" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.3)' }}>
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
                ? 'rgba(168,85,247,0.20)'
                : 'rgba(168,85,247,0.05)',
              border: filterLevel === 'N3' && viewTab === 'open'
                ? '2px solid rgba(168,85,247,0.7)'
                : '1px solid rgba(168,85,247,0.3)',
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
                style={{ background: 'linear-gradient(135deg, rgba(168,85,247,0.25), rgba(99,102,241,0.25))' }}
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
            <div className="p-4 rounded-xl" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.3)' }}>
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
                style={{ background: 'linear-gradient(135deg, rgba(168,85,247,0.30), rgba(99,102,241,0.30))' }}
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
          { key: 'N3', label: '🎲 N3', color: '#A855F7' },
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
              background: 'rgba(168,85,247,0.15)', color: '#C084FC'
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
            <span className="text-xs px-3 py-1.5 rounded-lg font-bold" style={{ background: 'rgba(168,85,247,0.1)', color: '#C084FC', border: '1px solid rgba(168,85,247,0.3)' }}>
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
function AdminsManagementTab() {
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
          style={{ background: '#6366F1' }}
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
                  style={{ background: a.role === 'SUPER_ADMIN' ? '#F59E0B' : '#6366F1' }}
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
                <button type="submit" disabled={busy} className="flex-1 py-2 rounded-xl text-white font-semibold disabled:opacity-50" style={{ background: '#6366F1' }}>
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
                <button type="submit" disabled={busy} className="flex-1 py-2 rounded-xl text-white font-semibold disabled:opacity-50" style={{ background: '#6366F1' }}>
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
