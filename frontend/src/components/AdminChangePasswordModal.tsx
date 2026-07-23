/**
 * AYRIA - Admin Change Password Modal
 *
 * Admin reseta a senha de qualquer usuário (sem precisar da senha antiga).
 * - Validação: mínimo 8 caracteres
 * - Confirmação dupla (digitação da nova senha pra evitar typo)
 * - Auditoria: motivo é logado
 *
 * Endpoint: POST /api/admin/users/{user_id}/password
 *   Body: { new_password: str, reason?: str }
 */
import { useState, useEffect } from 'react'
import { KeyRound, Loader2, X, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { adminApi } from '../lib/api'

interface AdminChangePasswordModalProps {
  open: boolean
  onClose: () => void
  user: { id: string; email: string; full_name?: string | null } | null
  onSuccess?: () => void
}

export function AdminChangePasswordModal({
  open,
  onClose,
  user,
  onSuccess,
}: AdminChangePasswordModalProps) {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [reason, setReason] = useState('')
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Reset quando modal abre/fecha
  useEffect(() => {
    if (open) {
      setNewPassword('')
      setConfirmPassword('')
      setReason('')
      setError(null)
      setSuccess(false)
    }
  }, [open])

  // ESC fecha
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open || !user) return null

  const validate = (): string | null => {
    if (newPassword.length < 8) {
      return 'Senha deve ter no mínimo 8 caracteres.'
    }
    if (newPassword !== confirmPassword) {
      return 'A confirmação não confere com a senha digitada.'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }
    setWorking(true)
    setError(null)
    try {
      await adminApi.changeUserPassword(user.id, {
        new_password: newPassword,
        reason: reason || undefined,
      })
      setSuccess(true)
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1500)
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        'Erro ao trocar senha'
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
      setWorking(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={working ? undefined : onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6"
        style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <KeyRound size={20} className="text-amber-400" />
            <h3 className="text-lg font-bold text-ayria-text">Resetar senha</h3>
          </div>
          <button
            onClick={onClose}
            disabled={working}
            className="text-ayria-muted hover:text-white disabled:opacity-30"
          >
            <X size={20} />
          </button>
        </div>

        {/* User alvo */}
        <div
          className="rounded-lg p-3 mb-4 text-sm"
          style={{ background: 'rgba(218,149,11,0.08)', border: '1px solid rgba(218,149,11,0.2)' }}
        >
          <div className="text-ayria-muted text-xs mb-1">Usuário alvo:</div>
          <div className="font-medium text-ayria-text">{user.full_name || '—'}</div>
          <div className="text-ayria-muted text-xs">{user.email}</div>
        </div>

        {success ? (
          <div
            className="text-center py-8 rounded-lg"
            style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)' }}
          >
            <CheckCircle2 size={32} className="mx-auto mb-2 text-green-400" />
            <div className="text-green-300 font-medium">Senha resetada com sucesso!</div>
            <div className="text-ayria-muted text-xs mt-1">Fechando...</div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            {/* Nova senha */}
            <div>
              <label className="block text-xs text-ayria-muted mb-1">
                Nova senha (mínimo 8 caracteres)
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={working}
                autoFocus
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: '#141420',
                  border: '1px solid #1E1E2E',
                  color: 'white',
                }}
                placeholder="Ex: MinhaSenh@2026"
              />
            </div>

            {/* Confirmar */}
            <div>
              <label className="block text-xs text-ayria-muted mb-1">
                Confirmar nova senha
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={working}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: '#141420',
                  border: '1px solid #1E1E2E',
                  color: 'white',
                }}
                placeholder="Digite novamente"
              />
            </div>

            {/* Motivo (auditoria) */}
            <div>
              <label className="block text-xs text-ayria-muted mb-1">
                Motivo (opcional, registrado em auditoria)
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                disabled={working}
                rows={2}
                className="w-full px-3 py-2 rounded-lg text-sm resize-none"
                style={{
                  background: '#141420',
                  border: '1px solid #1E1E2E',
                  color: 'white',
                }}
                placeholder="Ex: usuário esqueceu a senha"
              />
            </div>

            {/* Aviso */}
            <div
              className="rounded p-2 text-xs flex gap-2"
              style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}
            >
              <AlertTriangle size={14} className="text-amber-400 flex-shrink-0 mt-0.5" />
              <span className="text-amber-200/90">
                O usuário deve ser notificado da nova senha por canal seguro (não envie por email).
              </span>
            </div>

            {error && (
              <div
                className="rounded p-2 text-xs text-red-300"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}
              >
                {error}
              </div>
            )}

            {/* Botões */}
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={working}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-ayria-muted hover:text-white disabled:opacity-30"
                style={{ background: '#141420', border: '1px solid #1E1E2E' }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={working || !newPassword || !confirmPassword}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium text-white flex items-center justify-center gap-2 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}
              >
                {working ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Resetando...
                  </>
                ) : (
                  <>
                    <KeyRound size={14} />
                    Resetar senha
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
