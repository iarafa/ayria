/**
 * AYRIA - System Admins Tab
 *
 * Gerencia ADMINISTRADORES do sistema (SUPER_ADMIN) — separado dos users comuns.
 *
 * Backend: /api/admin/admins/{GET, POST, PUT, DELETE, /password}
 * - Lista todos os admins do sistema
 * - Cria novo admin (senha min 8 chars)
 * - Edita nome/email de admin
 * - Reseta senha
 * - Remove admin (com proteção: não pode remover self, nem último admin)
 *
 * 🆕 22/07/2026 — Rafael cobrava a separação de admin da aba Usuários (regra de 19/07
 *    nunca chegou a ser implementada no frontend, só endpoints backend).
 */
import { useEffect, useState } from 'react'
import { Shield, Plus, Edit3, Trash2, KeyRound, RefreshCw, X, AlertTriangle, CheckCircle2, User } from 'lucide-react'
import { adminApi } from '../lib/api'

interface Admin {
  id: string
  email: string
  full_name?: string | null
  role: string
  is_active: boolean
  created_at?: string
  last_login_at?: string | null
  is_self?: boolean
}

export function SystemAdminsTab() {
  const [admins, setAdmins] = useState<Admin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Modais
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Admin | null>(null)
  const [passwordTarget, setPasswordTarget] = useState<Admin | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Admin | null>(null)

  // Loading por ação
  const [acting, setActing] = useState(false)
  const [confirmText, setConfirmText] = useState('') // confirmação dupla de delete

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await adminApi.listAdmins()
      setAdmins(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao carregar admins')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  // Limpa success depois de 4s
  useEffect(() => {
    if (success) {
      const t = setTimeout(() => setSuccess(null), 4000)
      return () => clearTimeout(t)
    }
  }, [success])

  const handleDelete = async () => {
    if (!deleteTarget) return
    if (confirmText !== 'EXCLUIR') return
    setActing(true)
    try {
      await adminApi.deleteAdmin(deleteTarget.id)
      setSuccess(`✅ Admin ${deleteTarget.email} removido`)
      setDeleteTarget(null)
      setConfirmText('')
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao remover')
    } finally {
      setActing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div
        className="p-5 rounded-2xl"
        style={{
          background: 'linear-gradient(135deg, rgba(168,85,247,0.10), rgba(99,102,241,0.10))',
          border: '1px solid rgba(212, 175, 55, 0.3)',
        }}
      >
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
            >
              <Shield size={18} className="text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold gradient-text mb-1">Administradores do Sistema</h2>
              <p className="text-sm text-ayria-muted leading-relaxed">
                {admins.length === 0
                  ? 'Nenhum admin cadastrado.'
                  : `${admins.length} admin${admins.length > 1 ? 's' : ''} com acesso ao painel.`}
                {' '}Separei de <strong className="text-ayria-text">Usuários</strong> pra não misturar cliente com admin.
              </p>
            </div>
          </div>
          <button
            onClick={() => setCreateOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-white font-semibold"
            style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
          >
            <Plus size={16} />
            Novo admin
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-3 rounded-xl flex items-start gap-2 text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--ayria-error)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
          <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
          <div className="flex-1">{error}</div>
          <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100">
            <X size={14} />
          </button>
        </div>
      )}
      {success && (
        <div className="p-3 rounded-xl flex items-start gap-2 text-sm" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--ayria-success)', border: '1px solid rgba(16, 185, 129, 0.3)'}}>
          <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5" />
          <div>{success}</div>
        </div>
      )}

      {/* Lista */}
      <div className="space-y-2">
        {admins.map((a) => (
          <AdminCard
            key={a.id}
            admin={a}
            onEdit={() => setEditTarget(a)}
            onResetPassword={() => setPasswordTarget(a)}
            onDelete={() => setDeleteTarget(a)}
          />
        ))}
        {admins.length === 0 && (
          <div className="text-ayria-muted text-center py-12 rounded-xl" style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}>
            Nenhum admin cadastrado. Clique em "Novo admin" pra começar.
          </div>
        )}
      </div>

      {/* Modal: Criar */}
      {createOpen && (
        <CreateAdminModal
          onClose={() => setCreateOpen(false)}
          onSaved={() => {
            setCreateOpen(false)
            setSuccess('✅ Admin criado com sucesso')
            load()
          }}
        />
      )}

      {/* Modal: Editar */}
      {editTarget && (
        <EditAdminModal
          admin={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            setEditTarget(null)
            setSuccess('✅ Admin atualizado')
            load()
          }}
        />
      )}

      {/* Modal: Reset senha */}
      {passwordTarget && (
        <ResetPasswordModal
          admin={passwordTarget}
          onClose={() => setPasswordTarget(null)}
          onSaved={() => {
            setPasswordTarget(null)
            setSuccess('✅ Senha redefinida')
          }}
        />
      )}

      {/* Modal: Excluir (confirmação dupla) */}
      {deleteTarget && (
        <DeleteAdminModal
          admin={deleteTarget}
          acting={acting}
          confirmText={confirmText}
          setConfirmText={setConfirmText}
          onClose={() => {
            setDeleteTarget(null)
            setConfirmText('')
          }}
          onConfirm={handleDelete}
        />
      )}
    </div>
  )
}

// =============================================================
// Card de admin
// =============================================================
function AdminCard({ admin, onEdit, onResetPassword, onDelete }: {
  admin: Admin
  onEdit: () => void
  onResetPassword: () => void
  onDelete: () => void
}) {
  const isRoot = admin.role === 'SUPER_ADMIN'
  return (
    <div
      className="p-4 rounded-xl flex items-center gap-4 flex-wrap"
      style={{
        background: admin.is_self ? 'rgba(168, 85, 247, 0.08)' : '#0a0a0a',
        border: admin.is_self ? '1px solid rgba(168, 85, 247, 0.3)' : '1px solid #1E1E2E',
      }}
    >
      {/* Avatar */}
      <div
        className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0"
        style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
      >
        <User size={20} className="text-white" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-ayria-text">
            {admin.full_name || admin.email.split('@')[0]}
          </span>
          <span
            className="text-[10px] px-2 py-0.5 rounded uppercase tracking-wider font-semibold"
            style={{
              background: isRoot ? 'rgba(245, 158, 11, 0.15)' : 'rgba(148, 163, 184, 0.15)', color: isRoot ? '#F59E0B' : '#94A3B8',
            }}
          >
            {isRoot ? '👑 ROOT' : '🛡️ Admin'}
          </span>
          {admin.is_self && (
            <span className="text-[10px] px-2 py-0.5 rounded font-semibold" style={{ background: 'rgba(212, 175, 55, 0.2)', color: '#E8C768' }}>
              você
            </span>
          )}
        </div>
        <div className="text-xs text-ayria-muted mt-0.5 truncate">{admin.email}</div>
        <div className="text-[11px] text-ayria-muted/60 mt-1 flex gap-3 flex-wrap">
          {admin.last_login_at && (
            <span>Último login: {new Date(admin.last_login_at).toLocaleString('pt-BR')}</span>
          )}
          {admin.created_at && (
            <span>Criado: {new Date(admin.created_at).toLocaleDateString('pt-BR')}</span>
          )}
        </div>
      </div>

      {/* Ações */}
      <div className="flex gap-1 flex-shrink-0">
        <button
          onClick={onEdit}
          className="p-2 rounded-lg text-ayria-muted hover:text-ayria-text hover:bg-purple-500/10"
          title="Editar nome/email"
        >
          <Edit3 size={16} />
        </button>
        <button
          onClick={onResetPassword}
          className="p-2 rounded-lg text-ayria-muted hover:text-ayria-text hover:bg-purple-500/10"
          title="Resetar senha"
        >
          <KeyRound size={16} />
        </button>
        <button
          onClick={onDelete}
          className="p-2 rounded-lg text-ayria-muted hover:text-red-400 hover:bg-red-500/10 disabled:opacity-30 disabled:cursor-not-allowed"
          title={admin.is_self ? 'Você não pode remover a si mesmo' : 'Remover admin'}
          disabled={admin.is_self}
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  )
}

// =============================================================
// Modal: Criar admin
// =============================================================
function CreateAdminModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!email || !password) {
      setError('Email e senha são obrigatórios')
      return
    }
    if (password.length < 8) {
      setError('Senha mínima de 8 caracteres')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await adminApi.createAdmin({ email, password, full_name: fullName || undefined })
      onSaved()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao criar admin')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 relative"
        style={{ background: 'var(--ayria-bg-mid)', border: '1px solid var(--ayria-bg-high)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-ayria-muted hover:text-ayria-text">
          <X size={20} />
        </button>

        <h2 className="text-2xl font-bold mb-2 gradient-text">Novo administrador</h2>
        <p className="text-sm text-ayria-muted mb-6">
          Cria conta com acesso total ao painel. Use só pra pessoas de confiança.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Nome completo</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="João Silva"
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}
            />
          </div>
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Email *</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@empresa.com"
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}
            />
          </div>
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Senha * (mín 8 chars)</label>
            <input
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="senha-forte-2026"
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none font-mono"
              style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}
            />
            <p className="text-xs text-ayria-muted mt-1">Você vê a senha digitada — passe pro novo admin por canal seguro.</p>
          </div>

          {error && (
            <div className="p-3 rounded-lg text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--ayria-error)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              {error}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 rounded-xl text-ayria-muted"
              style={{ border: '1px solid var(--ayria-bg-high)' }}
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 px-4 py-3 rounded-xl text-white font-semibold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
            >
              {saving ? 'Criando...' : 'Criar admin'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================
// Modal: Editar admin
// =============================================================
function EditAdminModal({ admin, onClose, onSaved }: { admin: Admin; onClose: () => void; onSaved: () => void }) {
  const [email, setEmail] = useState(admin.email)
  const [fullName, setFullName] = useState(admin.full_name || '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await adminApi.updateAdmin(admin.id, { email, full_name: fullName })
      onSaved()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao atualizar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 relative"
        style={{ background: 'var(--ayria-bg-mid)', border: '1px solid var(--ayria-bg-high)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-ayria-muted hover:text-ayria-text">
          <X size={20} />
        </button>

        <h2 className="text-2xl font-bold mb-2 gradient-text">Editar admin</h2>
        <p className="text-sm text-ayria-muted mb-6">
          Você pode editar seu próprio admin ou outro.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Nome completo</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}
            />
          </div>
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}
            />
          </div>

          {error && (
            <div className="p-3 rounded-lg text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--ayria-error)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              {error}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 rounded-xl text-ayria-muted"
              style={{ border: '1px solid var(--ayria-bg-high)' }}
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 px-4 py-3 rounded-xl text-white font-semibold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
            >
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================
// Modal: Reset senha
// =============================================================
function ResetPasswordModal({ admin, onClose, onSaved }: { admin: Admin; onClose: () => void; onSaved: () => void }) {
  const [newPassword, setNewPassword] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (newPassword.length < 8) {
      setError('Senha mínima de 8 caracteres')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await adminApi.resetAdminPassword(admin.id, { new_password: newPassword })
      onSaved()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao resetar senha')
    } finally {
      setSaving(false)
    }
  }

  const generateStrong = () => {
    const chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789!@#$%&*'
    let pwd = ''
    for (let i = 0; i < 16; i++) pwd += chars[Math.floor(Math.random() * chars.length)]
    setNewPassword(pwd)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 relative"
        style={{ background: 'var(--ayria-bg-mid)', border: '1px solid var(--ayria-bg-high)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-ayria-muted hover:text-ayria-text">
          <X size={20} />
        </button>

        <h2 className="text-2xl font-bold mb-2 gradient-text">Resetar senha</h2>
        <p className="text-sm text-ayria-muted mb-6">
          Resetando senha de <strong className="text-ayria-text">{admin.email}</strong>. Use pra casos de admin esqueceu a senha.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Nova senha * (mín 8 chars)</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="senha-nova-2026"
                className="flex-1 px-4 py-3 rounded-xl text-ayria-text outline-none font-mono"
                style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}
              />
              <button
                onClick={generateStrong}
                className="px-3 py-3 rounded-xl text-ayria-muted hover:text-ayria-text"
                style={{ border: '1px solid var(--ayria-bg-high)' }}
                title="Gerar senha forte"
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Motivo (opcional, vai pro log)</label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ex: admin esqueceu senha"
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: 'var(--ayria-bg)', border: '1px solid var(--ayria-bg-high)' }}
            />
          </div>

          {error && (
            <div className="p-3 rounded-lg text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--ayria-error)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              {error}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 rounded-xl text-ayria-muted"
              style={{ border: '1px solid var(--ayria-bg-high)' }}
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 px-4 py-3 rounded-xl text-white font-semibold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
            >
              {saving ? 'Resetando...' : 'Resetar senha'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================
// Modal: Excluir admin (confirmação dupla)
// =============================================================
function DeleteAdminModal({ admin, acting, confirmText, setConfirmText, onClose, onConfirm }: {
  admin: Admin
  acting: boolean
  confirmText: string
  setConfirmText: (s: string) => void
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 relative"
        style={{ background: 'var(--ayria-bg-mid)', border: '1px solid rgba(239, 68, 68, 0.5)'}}
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-ayria-muted hover:text-ayria-text">
          <X size={20} />
        </button>

        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(239, 68, 68, 0.15)' }}>
            <AlertTriangle size={20} className="text-red-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-red-300 mb-1">Remover admin</h2>
            <p className="text-sm text-ayria-muted">
              Remover <strong className="text-ayria-text">{admin.email}</strong>?
            </p>
          </div>
        </div>

        <div className="space-y-3 mb-4">
          <p className="text-sm text-red-300">
            ⚠️ Essa ação é <strong>irreversível</strong>. O admin perde acesso ao painel imediatamente.
          </p>
          <p className="text-xs text-ayria-muted">
            Você não pode remover a si mesmo. Se for o último SUPER_ADMIN do sistema, o backend também vai recusar.
          </p>
          <div>
            <label className="block text-xs text-ayria-muted mb-1">
              Digite <strong className="text-red-300">EXCLUIR</strong> pra confirmar:
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none font-mono"
              style={{ background: 'var(--ayria-bg)', border: '1px solid rgba(239, 68, 68, 0.3)' }}
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 rounded-xl text-ayria-muted"
            style={{ border: '1px solid var(--ayria-bg-high)' }}
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={acting || confirmText !== 'EXCLUIR'}
            className="flex-1 px-4 py-3 rounded-xl text-white font-semibold disabled:opacity-30"
            style={{ background: confirmText === 'EXCLUIR' ? '#EF4444' : '#1E1E2E' }}
          >
            {acting ? 'Removendo...' : 'Remover admin'}
          </button>
        </div>
      </div>
    </div>
  )
}