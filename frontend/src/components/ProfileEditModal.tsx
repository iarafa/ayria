/**
 * AYRIA - Modal de Edição de Perfil
 *
 * Abre quando user clica no avatar+nome no header do chat.
 * Permite editar:
 * - Foto (avatar) — upload direto
 * - Nome completo
 *
 * Salva via PATCH /api/auth/me e POST /api/auth/me/avatar
 */
import { useState, useRef, useEffect } from 'react'
import { X, Camera, Save, Upload } from 'lucide-react'
import { useAuth } from '../store/auth'

interface ProfileEditModalProps {
  open: boolean
  onClose: () => void
}

export function ProfileEditModal({ open, onClose }: ProfileEditModalProps) {
  const { user, updateProfile, uploadAvatar } = useAuth()
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(user?.avatar_url || null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Reset quando modal abre
  useEffect(() => {
    if (open) {
      setFullName(user?.full_name || '')
      setAvatarPreview(user?.avatar_url || null)
      setAvatarFile(null)
      setError(null)
      setSuccess(false)
    }
  }, [open, user])

  // ESC fecha o modal
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const initials = (() => {
    if (fullName.trim()) {
      const parts = fullName.trim().split(/\s+/)
      if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      return fullName[0].toUpperCase()
    }
    return user?.email?.[0]?.toUpperCase() || '?'
  })()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Arquivo precisa ser uma imagem')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('Imagem deve ter no máximo 5MB')
      return
    }
    setError(null)
    setAvatarFile(file)
    const reader = new FileReader()
    reader.onload = (ev) => setAvatarPreview(ev.target?.result as string)
    reader.readAsDataURL(file)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      // 1. Salva nome se mudou
      const nameChanged = fullName.trim() !== (user?.full_name || '')
      if (nameChanged) {
        const ok = await updateProfile({ full_name: fullName.trim() || undefined })
        if (!ok) {
          setError('Erro ao salvar nome')
          setSaving(false)
          return
        }
      }

      // 2. Upload avatar (se houver)
      if (avatarFile) {
        const url = await uploadAvatar(avatarFile)
        if (!url) {
          setError('Erro ao enviar foto')
          setSaving(false)
          return
        }
      }

      setSuccess(true)
      setTimeout(() => {
        onClose()
      }, 800)
    } catch (e: any) {
      setError(e?.message || 'Erro inesperado')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 relative"
        style={{
          background: '#111111',
          border: '1px solid #1E1E2E',
          boxShadow: '0 20px 60px rgba(99, 102, 241, 0.2)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold gradient-text">Editar perfil</h2>
          <button
            onClick={onClose}
            className="text-ayria-muted hover:text-ayria-text transition-colors p-1"
          >
            <X size={20} />
          </button>
        </div>

        {/* Avatar com botão de trocar */}
        <div className="flex flex-col items-center mb-6">
          <div className="relative">
            <div
              className="w-28 h-28 rounded-full flex items-center justify-center text-white font-bold text-3xl overflow-hidden flex-shrink-0"
              style={{
                background: user?.role === 'SUPER_ADMIN' || user?.role === 'admin'
                  ? 'linear-gradient(135deg, #F59E0B, #EF4444)'
                  : 'linear-gradient(135deg, #6366F1, #A855F7)',
                boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
                border: '3px solid rgba(99, 102, 241, 0.3)',
              }}
            >
              {avatarPreview ? (
                <img
                  src={avatarPreview}
                  alt="preview"
                  style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                />
              ) : (
                initials
              )}
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="absolute bottom-0 right-0 w-9 h-9 rounded-full flex items-center justify-center text-white shadow-lg transition-transform hover:scale-110"
              style={{
                background: 'linear-gradient(135deg, #6366F1, #A855F7)',
                border: '3px solid #111111',
              }}
              title="Trocar foto"
            >
              <Camera size={16} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
          </div>
          {avatarFile && (
            <p className="text-xs text-ayria-success mt-2 flex items-center gap-1">
              <Upload size={12} />
              {avatarFile.name}
            </p>
          )}
          <p className="text-xs text-ayria-muted mt-2 text-center">
            Clique na câmera para enviar nova foto (max 5MB)
          </p>
        </div>

        {/* Nome */}
        <div className="mb-4">
          <label className="block text-sm text-ayria-muted mb-2">Nome completo</label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Seu nome"
            className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
            style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
          />
        </div>

        {/* Email (read-only) */}
        <div className="mb-6">
          <label className="block text-sm text-ayria-muted mb-2">Email</label>
          <input
            type="email"
            value={user?.email || ''}
            disabled
            className="w-full px-4 py-3 rounded-xl text-ayria-muted outline-none cursor-not-allowed"
            style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
          />
          <p className="text-xs text-ayria-muted/60 mt-1">
            Email não pode ser alterado
          </p>
        </div>

        {/* Status */}
        {error && (
          <div
            className="px-4 py-2 rounded-lg text-sm mb-4"
            style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444' }}
          >
            {error}
          </div>
        )}
        {success && (
          <div
            className="px-4 py-2 rounded-lg text-sm mb-4"
            style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10B981' }}
          >
            ✓ Perfil atualizado com sucesso!
          </div>
        )}

        {/* Botões */}
        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="flex-1 py-3 rounded-xl text-ayria-muted hover:text-ayria-text font-semibold transition-colors disabled:opacity-50"
            style={{ background: '#1E1E2E' }}
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
          >
            <Save size={16} />
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
        </div>

        {/* 🆕 SECURITY: botão de trocar senha (separado pra UX melhor) */}
        <div className="mt-4 pt-4 border-t border-ayria-border">
          <button
            onClick={() => {
              onClose()
              window.dispatchEvent(new CustomEvent('ayria:open-change-password'))
            }}
            className="w-full py-2 rounded-xl text-sm text-amber-400 hover:bg-amber-900/20 transition flex items-center justify-center gap-2"
          >
            🔒 Trocar senha
          </button>
        </div>
      </div>
    </div>
  )
}