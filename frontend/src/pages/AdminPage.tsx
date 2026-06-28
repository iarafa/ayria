/**
 * AYRIA - Admin Page
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { adminApi } from '../lib/api'
import { Logo } from '../components/Logo'
import { Users, FileText, Settings, ListChecks, LogOut, UserPlus, X, Shield } from 'lucide-react'

type Tab = 'users' | 'knowledge' | 'onboarding' | 'attributes'

export function AdminPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('users')
  const [users, setUsers] = useState<any[]>([])
  const [docs, setDocs] = useState<any[]>([])
  const [attributes, setAttributes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({ email: '', password: '', full_name: '' })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  useEffect(() => {
    if (user?.role !== 'admin' && user?.role !== 'SUPER_ADMIN') {
      navigate('/chat')
      return
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
    } else if (tab === 'attributes') {
      setLoading(true)
      adminApi.listAttributes().then((r) => {
        setAttributes(r.data)
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
      setCreateForm({ email: '', password: '', full_name: '' })
      await reloadUsers()
      alert('✅ Usuário criado com sucesso!')
    } catch (e: any) {
      setCreateError(e.response?.data?.detail || 'Erro ao criar usuário')
    } finally {
      setCreating(false)
    }
  }

  const handleToggleRole = async (u: any) => {
    const newRole = u.role === 'SUPER_ADMIN' ? 'user' : 'SUPER_ADMIN'
    if (!confirm(`Mudar role de ${u.email} para ${newRole}?`)) return
    try {
      await adminApi.updateUserRole(u.id, newRole)
      await reloadUsers()
    } catch (e: any) {
      alert('Erro: ' + (e.response?.data?.detail || 'desconhecido'))
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
          <Logo size={32} />
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

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-ayria-border">
          {[
            { id: 'users', label: 'Usuários', icon: Users },
            { id: 'knowledge', label: 'Conhecimento', icon: FileText },
            { id: 'onboarding', label: 'Onboarding', icon: ListChecks },
            { id: 'attributes', label: 'Atributos', icon: Settings },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as Tab)}
              className={`px-4 py-3 text-sm flex items-center gap-2 border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-ayria-admin text-ayria-text'
                  : 'border-transparent text-ayria-muted hover:text-ayria-text'
              }`}
            >
              <t.icon size={14} />
              {t.label}
            </button>
          ))}
        </div>

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

            <div className="space-y-2">
              {users.map((u) => (
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
                        {u.full_name || '—'} · {u.role} · {u.message_count} msgs
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
                      <button
                        onClick={() => handleToggleRole(u)}
                        className="text-xs px-2 py-1 rounded text-amber-400 hover:text-amber-300 flex items-center gap-1"
                        title="Promover/Rebaixar para SUPER_ADMIN"
                      >
                        <Shield size={12} />
                        {u.role}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {users.length === 0 && (
                <div className="text-center text-ayria-muted py-8">
                  Nenhum usuário cadastrado ainda.
                </div>
              )}
            </div>
          </div>
        )}

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

        {/* ONBOARDING */}
        {tab === 'onboarding' && (
          <div className="text-center text-ayria-muted py-12">
            <p>Editor de onboarding dinâmico - configurar via backend</p>
            <p className="text-sm mt-2">Endpoint: <code>PUT /api/admin/onboarding/config</code></p>
          </div>
        )}

        {/* ATTRIBUTES */}
        {tab === 'attributes' && !loading && (
          <div className="space-y-2">
            {attributes.map((a) => (
              <div
                key={a.id}
                className="p-4 rounded-xl"
                style={{ background: '#111111', border: '1px solid #1E1E2E' }}
              >
                <div className="text-ayria-text font-medium">{a.label}</div>
                <div className="text-xs text-ayria-muted">
                  {a.code} · {a.attribute_type} {a.is_required ? '· obrigatório' : ''}
                </div>
              </div>
            ))}
            {attributes.length === 0 && (
              <div className="text-center text-ayria-muted py-8">
                Nenhum atributo no catálogo.
              </div>
            )}
          </div>
        )}
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
                  (pode ver a senha digitada — útil pra você passar pro usuário)
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
    </div>
  )
}