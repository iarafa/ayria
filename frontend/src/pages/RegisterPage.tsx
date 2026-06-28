/**
 * AYRIA - Register Page (com upload de foto)
 */
import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { Logo } from '../components/Logo'
import { UserAvatar } from '../components/UserAvatar'
import { Camera, Upload } from 'lucide-react'

export function RegisterPage() {
  const { register, loading, error, uploadAvatar } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Valida tipo
    if (!file.type.startsWith('image/')) {
      setUploadError('Arquivo precisa ser uma imagem')
      return
    }
    // Valida tamanho (5MB)
    if (file.size > 5 * 1024 * 1024) {
      setUploadError('Imagem deve ter no máximo 5MB')
      return
    }

    setUploadError(null)
    setAvatarFile(file)

    // Preview local
    const reader = new FileReader()
    reader.onload = (ev) => setAvatarPreview(ev.target?.result as string)
    reader.readAsDataURL(file)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const ok = await register(email, password, fullName || undefined)
    if (!ok) return

    // Upload avatar (se houver) — depois do register pq precisa estar autenticado
    if (avatarFile) {
      setUploading(true)
      await uploadAvatar(avatarFile)
      setUploading(false)
    }

    navigate('/onboarding')
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: '#050505' }}
    >
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <Logo size={80} showText={false} />
        </div>

        <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
          Crie sua conta
        </h1>
        <p className="text-center text-ayria-muted mb-8">
          Comece sua jornada de autoconhecimento
        </p>

        {/* Upload de foto */}
        <div className="flex flex-col items-center mb-6">
          <div className="relative">
            <UserAvatar
              src={avatarPreview}
              name={fullName || email}
              email={email}
              size={100}
              glow={false}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="absolute bottom-0 right-0 w-9 h-9 rounded-full flex items-center justify-center text-white shadow-lg transition-transform hover:scale-110"
              style={{
                background: 'linear-gradient(135deg, #6366F1, #A855F7)',
                border: '3px solid #050505',
              }}
              title="Enviar foto"
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
          <p className="text-xs text-ayria-muted mt-2">
            {avatarFile ? (
              <span className="text-ayria-success flex items-center gap-1">
                <Upload size={12} />
                {avatarFile.name}
              </span>
            ) : (
              'Toque na câmera para enviar sua foto (opcional)'
            )}
          </p>
          {uploadError && (
            <p className="text-xs text-red-400 mt-1">{uploadError}</p>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Nome completo</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: '#111111', border: '1px solid #1E1E2E' }}
            />
          </div>

          <div>
            <label className="block text-sm text-ayria-muted mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: '#111111', border: '1px solid #1E1E2E' }}
            />
          </div>

          <div>
            <label className="block text-sm text-ayria-muted mb-2">Senha (mín 6 chars)</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
              style={{ background: '#111111', border: '1px solid #1E1E2E' }}
            />
          </div>

          {error && (
            <div
              className="px-4 py-2 rounded-lg text-sm"
              style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444' }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || uploading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
          >
            {loading ? 'Criando...' : uploading ? 'Enviando foto...' : 'Criar conta'}
          </button>
        </form>

        <p className="text-center text-ayria-muted mt-6">
          Já tem conta?{' '}
          <Link to="/login" className="text-ayria-primary hover:underline">
            Entrar
          </Link>
        </p>
      </div>
    </div>
  )
}