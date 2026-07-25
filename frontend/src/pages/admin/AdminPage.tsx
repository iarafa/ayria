/**
 * AYRIA - Admin Page
 */
import { useEffect, useRef, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../store/auth'
import { adminApi, api } from '../../lib/api'
import { LogoIcon } from '../../components/Logo'
import { Users, FileText, Settings, LogOut, UserPlus, X, Shield, Wallet, Plus, Tag, Edit3, Eye, ChevronDown, ChevronRight, Calendar, MapPin, Star, Heart, Briefcase, Sparkles, ExternalLink, Cpu, CheckCircle2, AlertCircle, Database, Cloud, Activity, AlertTriangle, MessageCircle, MessageSquare, Receipt, User, Clock, Calculator, ClipboardList, Trash2, KeyRound } from 'lucide-react'
import { AlmaTab } from '../../components/AlmaTab'
import { LogsTab } from '../../components/LogsTab'
import { ListWithControls } from '../../components/ListWithControls'
import { SupervisorPromptModal } from '../../components/SupervisorPromptModal'
import { SupervisorKeywordsViewer } from '../../components/SupervisorKeywordsViewer'
import { BlockUserModal } from '../../components/BlockUserModal'
import { ChangePasswordModal } from '../../components/ChangePasswordModal'
import { AdminChangePasswordModal } from '../../components/AdminChangePasswordModal'

// Componentes quebrados em arquivos separados (25/07/2026)
import { Section, Field, Badge, StatCard, DataRow, EmptyState, NumberCard, PlanetCard, humanizeKey, formatValue, capitalize } from './tabs/helpers'
import { UserHeader } from './tabs/UserHeader'
import { UserDetailsModal } from './modals/UserDetailsModal'

// Tabs quebradas em arquivos separados (25/07/2026)
import { CreditsTab } from './tabs/CreditsTab'
import { PlansTab } from './tabs/PlansTab'
import { SystemSettingsTab } from './tabs/SystemSettingsTab'
import { SupervisionTab } from './tabs/SupervisionTab'
import { AdminsManagementTab } from './tabs/AdminsManagementTab'
import { PartnersTabInline } from './tabs/PartnersTabInline'
import { CouponsTabInline } from './tabs/CouponsTabInline'
import { CommissionsTabInline } from './tabs/CommissionsTabInline'

type Tab = 'users' | 'plans' | 'credits' | 'knowledge' | 'onboarding' | 'attributes' | 'settings' | 'supervision' | 'alma' | 'logs' | 'admins' | 'partners' | 'coupons' | 'commissions'

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
  const [selfPasswordOpen, setSelfPasswordOpen] = useState(false)
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
          <button
            onClick={() => setSelfPasswordOpen(true)}
            className="text-ayria-muted hover:text-ayria-text text-sm flex items-center gap-1.5"
            title="Trocar minha senha"
          >
            <KeyRound size={16} />
            Trocar senha
          </button>
          <button onClick={logout} className="text-ayria-muted hover:text-red-400" title="Sair">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Layout full-height: SIDEBAR lateral esquerda 100% altura + CONTEÚDO à direita (Rafael 22/07 20:34) */}
      <div className="flex" style={{ minHeight: 'calc(100vh - 73px)' }}>
        {/* Sidebar — LATERAL ESQUERDA COMPLETA, sem card, sem sticky, sem rounded, fundo próprio */}
        <aside
          className="w-64 shrink-0 flex flex-col border-r border-ayria-border overflow-y-auto"
          style={{ background: '#0F0F1F' }}
        >
          <nav className="flex-1 flex flex-col gap-3 p-3">
            {(() => {
              // 🆕 22/07 20:55 — categorias pra organizar o menu (Rafael pediu)
              type Item = { id: string; label: string; icon: any }
              type Section = { title: string; items: Item[] }
              const isSuperAdmin = user?.role === 'SUPER_ADMIN'
              const sections: Section[] = [
                {
                  title: 'Usuários',
                  items: [
                    { id: 'users', label: 'Usuários', icon: Users },
                    // só SUPER_ADMIN pode gerenciar outros admins (Rafael 22/07 20:56)
                    ...(isSuperAdmin
                      ? [{ id: 'admins', label: 'Administradores', icon: Shield } as Item]
                      : []),
                  ],
                },
                {
                  title: 'Administração',
                  items: [
                    { id: 'plans', label: 'Planos', icon: Tag },
                    { id: 'credits', label: 'Créditos', icon: Wallet },
                    // 🆕 22/07 21:08 — cupons + parceiros + comissões (Rafael pediu)
                    { id: 'partners', label: 'Parceiros', icon: UserPlus },
                    { id: 'coupons', label: 'Cupons', icon: Tag },
                    { id: 'commissions', label: 'Comissões', icon: Receipt },
                  ],
                },
                {
                  title: 'Conteúdo',
                  items: [
                    { id: 'knowledge', label: 'Conhecimento', icon: FileText },
                    { id: 'alma', label: 'ALMA', icon: Sparkles },
                  ],
                },
                {
                  title: 'Monitoramento',
                  items: [
                    { id: 'supervision', label: 'Supervisão', icon: Activity },
                    { id: 'logs', label: 'Logs', icon: AlertTriangle },
                  ],
                },
                {
                  title: 'Sistema',
                  items: [
                    { id: 'settings', label: 'Configurações', icon: Cpu },
                  ],
                },
              ]
              return sections.map((section, i) => (
                <div key={i}>
                  <div className="px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-ayria-muted opacity-60">
                    {section.title}
                  </div>
                  {section.items.map((t) => {
                    const isActive = tab === t.id
                    return (
                      <button
                        key={t.id}
                        onClick={() => setTab(t.id as Tab)}
                        className={`w-full px-4 py-2.5 text-sm flex items-center gap-3 transition-colors text-left rounded-lg ${
                          isActive
                            ? 'text-ayria-text font-medium'
                            : 'text-ayria-muted hover:bg-[#1a1a2e] hover:text-ayria-text'
                        }`}
                        style={
                          isActive
                            ? { borderLeft: '3px solid #f1c961', background: 'rgba(99, 102, 241, 0.15)' }
                            : { borderLeft: '3px solid transparent' }
                        }
                      >
                        <t.icon size={15} />
                        <span>{t.label}</span>
                      </button>
                    )
                  })}
                </div>
              ))
            })()}
          </nav>
        </aside>

        {/* Conteúdo principal */}
        <main className="flex-1 min-w-0 px-6 py-6 overflow-x-auto">

        {/* Content */}
        {loading && <div className="text-ayria-muted">Carregando...</div>}

        {/* USERS — exclui admins (admin/SUPER_ADMIN) — eles ficam na aba "Administradores" */}
        {tab === 'users' && !loading && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm text-ayria-muted">
                <span className="text-ayria-text font-medium">
                  {users.filter((u: any) => u.role === 'user').length}
                </span>{' '}
                usuário(s) comum(ns)
                {users.filter((u: any) => u.role !== 'user').length > 0 && (
                  <span className="ml-2 text-xs">
                    • {users.filter((u: any) => u.role !== 'user').length} admin(s) na aba{' '}
                    <a
                      href="#"
                      onClick={(e) => { e.preventDefault(); setTab('admins') }}
                      className="text-indigo-400 hover:underline"
                    >
                      Administradores
                    </a>
                  </span>
                )}
              </div>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 rounded-xl text-white font-medium flex items-center gap-2 hover:opacity-90"
                style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
              >
                <UserPlus size={16} />
                Criar usuário
              </button>
            </div>

            <ListWithControls
              data={users.filter((u: any) => u.role === 'user')}
              itemName="usuário"
              searchPlaceholder="Buscar por email, nome..."
              emptyMessage="Nenhum usuário comum encontrado"
              filters={[
                {
                  key: 'plan',
                  label: 'Plano',
                  options: [
                    { value: 'all', label: 'Todos os planos' },
                    { value: 'basico', label: 'Básico' },
                    { value: 'intermediario', label: 'Intermediário' },
                    { value: 'premium', label: 'Premium' },
                    { value: '__none__', label: 'Sem plano' },
                  ],
                  getValue: (u: any) => u.selected_plan_slug || '__none__',
                },
                {
                  key: 'billing',
                  label: 'Status',
                  options: [
                    { value: 'all', label: 'Todos os status' },
                    { value: 'active', label: '✅ Ativo (Stripe)' },
                    { value: 'billing_not_enabled', label: '⚪ Sem assinatura' },
                    { value: 'past_due', label: '⚠️ Pendente' },
                    { value: 'canceled', label: '❌ Cancelado' },
                  ],
                  getValue: (u: any) => u.billing_status || 'billing_not_enabled',
                },
                {
                  key: 'verified',
                  label: 'Verificação',
                  options: [
                    { value: 'all', label: 'Todos' },
                    { value: 'verified', label: 'Verificados' },
                    { value: 'pending', label: 'Pendentes' },
                  ],
                  getValue: (u: any) => (u.is_verified ? 'verified' : 'pending'),
                },
              ]}
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
                      style={{ background: u.role === 'SUPER_ADMIN' ? 'linear-gradient(135deg, #F59E0B, #EF4444)' : 'linear-gradient(135deg, #f1c961, #da950b)' }}
                    >
                      {u.email[0].toUpperCase()}
                    </div>
                    <div>
                      <div className="text-ayria-text font-medium">{u.email}</div>
                      <div className="text-xs text-ayria-muted">
                        {u.full_name || '-'} · {u.role} · {u.message_count} msgs
                      </div>
                      <div className="text-xs text-ayria-muted mt-0.5 flex flex-wrap gap-1.5">
                        {u.selected_plan_slug ? (
                          <span
                            className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                            style={{
                              background:
                                u.selected_plan_slug === 'premium' ? 'rgba(212,175,55,0.18)'
                                : u.selected_plan_slug === 'intermediario' ? 'rgba(241,201,97,0.18)'
                                : 'rgba(156,163,175,0.18)',
                              color:
                                u.selected_plan_slug === 'premium' ? '#D4AF37'
                                : u.selected_plan_slug === 'intermediario' ? '#A5B4FC'
                                : '#9CA3AF',
                              border: '1px solid rgba(255,255,255,0.08)',
                            }}
                            title="Plano do usuário"
                          >
                            📋 {u.selected_plan_name || u.selected_plan_slug}
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[10px] text-ayria-muted" style={{ background: 'rgba(255,255,255,0.04)' }}>
                            Sem plano
                          </span>
                        )}
                        {!u.is_verified && (
                          <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'rgba(245,158,11,0.18)', color: '#F59E0B' }}>
                            ⚠️ Não verificado
                          </span>
                        )}
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
                        background: u.onboarding_status === 'completed' ? 'rgba(241,201,97,0.15)' : 'rgba(218,149,11,0.15)',
                        color: u.onboarding_status === 'completed' ? '#f1c961' : '#da950b',
                      }}
                    >
                      {u.onboarding_status}
                    </span>
                    {u.id !== user?.id && (
                      <>
                        <button
                          onClick={() => openUserDetails(u.id)}
                          className="text-xs px-3 py-1 rounded flex items-center gap-1"
                          style={{ background: 'rgba(218,149,11,0.15)', color: '#da950b' }}
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
                          style={{ background: 'rgba(241,201,97,0.15)', color: '#f1c961' }}
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

        {/* 🆕 22/07 21:08 — PARCEIROS, CUPONS, COMISSÕES (cupom de desconto + pagamento de cupom) */}
        {tab === 'partners' && <PartnersTabInline />}
        {tab === 'coupons' && <CouponsTabInline />}
        {tab === 'commissions' && <CommissionsTabInline />}

        {/* ═══════════════════════════════════════════════
            🆕 MODAL: Admin resetar senha do usuário
            ═══════════════════════════════════════════════ */}
        <AdminChangePasswordModal
          open={!!passwordTarget}
          onClose={() => setPasswordTarget(null)}
          user={passwordTarget}
          onSuccess={() => reloadUsers()}
        />

        {/* 🆕 23/07 16:03 — ADMIN trocar a PRÓPRIA senha (botão no header) */}
        <ChangePasswordModal
          open={selfPasswordOpen}
          onClose={() => setSelfPasswordOpen(false)}
        />
{/* KNOWLEDGE */}
        {tab === 'knowledge' && !loading && (
          <div>
            <div className="mb-4">
              <label className="inline-block px-4 py-2 rounded-xl cursor-pointer text-white font-medium"
                style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}>
                + Upload de documento
                <input type="file" accept=".pdf,.txt,.md" onChange={handleUpload} className="hidden" />
              </label>
            </div>
            <ListWithControls
              data={docs}
              itemName="documento"
              searchPlaceholder="Buscar por título ou arquivo..."
              emptyMessage="Nenhum documento cadastrado"
            >
              {(d) => (
                <div
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
                          color: d.storage_provider === 'azure' ? '#38BDF8' : '#da950b',
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
              )}
            </ListWithControls>
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
                  style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
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
                  style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
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
