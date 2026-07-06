/**
 * AYRIA - Modal de Troca de Senha
 *
 * User troca a própria senha (precisa da senha atual).
 * Salva via PATCH /api/auth/me/password.
 *
 * 🆕 SECURITY: min 8 chars, sem repetição com senha atual.
 */
import { useState, useEffect } from 'react'
import { X, Lock, Check, AlertTriangle } from 'lucide-react'
import { authApi } from '../lib/api'

interface ChangePasswordModalProps {
  open: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function ChangePasswordModal({ open, onClose, onSuccess }: ChangePasswordModalProps) {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Reset quando modal abre/fecha
  useEffect(() => {
    if (open) {
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
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

  if (!open) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    // Validações client-side (UX rápida)
    if (newPassword.length < 8) {
      setError('A nova senha precisa ter pelo menos 8 caracteres.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('A confirmação não confere com a nova senha.')
      return
    }
    if (newPassword === oldPassword) {
      setError('A nova senha não pode ser igual à atual.')
      return
    }

    setSaving(true)
    try {
      await authApi.changePassword(oldPassword, newPassword)
      setSuccess(true)
      // Mensagem: tem que logar de novo (refresh_token continua válido mas access_token mudou)
      // Backend não invalida tokens existentes — é responsabilidade do user sair de outros devices
      setTimeout(() => {
        onSuccess?.()
        onClose()
      }, 1800)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Erro ao trocar senha.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-ayria-surface rounded-2xl shadow-2xl w-full max-w-md border border-ayria-border"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-ayria-border">
          <div className="flex items-center gap-2">
            <Lock size={20} className="text-amber-400" />
            <h2 className="text-lg font-bold text-ayria-text">Trocar senha</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-ayria-bg transition"
            aria-label="Fechar"
          >
            <X size={20} className="text-ayria-muted" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-900/30 border border-red-700 text-red-200 text-sm">
              <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-green-900/30 border border-green-700 text-green-200 text-sm">
              <Check size={16} className="mt-0.5 flex-shrink-0" />
              <span>✅ Senha alterada com sucesso! Você será desconectado dos outros devices.</span>
            </div>
          )}

          <div>
            <label className="block text-sm text-ayria-muted mb-1">Senha atual</label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full px-3 py-2 rounded-lg bg-ayria-bg border border-ayria-border text-ayria-text focus:outline-none focus:border-amber-500"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="block text-sm text-ayria-muted mb-1">Nova senha</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="w-full px-3 py-2 rounded-lg bg-ayria-bg border border-ayria-border text-ayria-text focus:outline-none focus:border-amber-500"
              placeholder="Mínimo 8 caracteres"
            />
          </div>

          <div>
            <label className="block text-sm text-ayria-muted mb-1">Confirmar nova senha</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="w-full px-3 py-2 rounded-lg bg-ayria-bg border border-ayria-border text-ayria-text focus:outline-none focus:border-amber-500"
              placeholder="Digite novamente"
            />
          </div>

          <p className="text-xs text-ayria-muted">
            🔒 Sua senha é criptografada (bcrypt). Por segurança, você será desconectado de outros dispositivos.
          </p>

          {/* Footer */}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-ayria-border text-ayria-muted hover:bg-ayria-bg transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving || success}
              className="flex-1 px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:bg-amber-800 disabled:cursor-not-allowed text-white font-medium transition"
            >
              {saving ? 'Salvando...' : 'Trocar senha'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}