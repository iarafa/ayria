/**
 * AYRIA - Admin Quick Login
 *
 * Página dedicada pro botão de login rápido admin.
 * SEM link visível em lugar nenhum — acesso direto por URL:
 *   http://localhost:5173/admin/login
 *
 * Mesma função login() do form normal, só com credencial hardcoded.
 */

import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { useChat } from '../store/chat'
import { LogoIcon } from '../components/Logo'
import { Shield, ArrowLeft } from 'lucide-react'

const ADMIN_EMAIL = 'admin@ayria.local'
const ADMIN_PASSWORD = '***'

export function AdminLoginPage() {
  const { login, loading, error } = useAuth()
  const { createChat } = useChat()
  const navigate = useNavigate()

  const handleAdminQuickLogin = async () => {
    const ok = await login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if (ok) {
      await createChat()
      navigate('/chat')
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: '#050505' }}
    >
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <LogoIcon size={400} variant="circular" className="max-w-[85vw]" />
        </div>

        <div className="flex justify-center mb-4">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold"
            style={{
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(239, 68, 68, 0.15))',
              color: '#F59E0B',
              border: '1px solid rgba(245, 158, 11, 0.3)',
            }}
          >
            <Shield size={12} />
            ACESSO RESTRITO
          </div>
        </div>

        <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
          Painel Administrativo
        </h1>
        <p className="text-center text-ayria-muted mb-8">
          Login dedicado para administradores
        </p>

        <button
          type="button"
          onClick={handleAdminQuickLogin}
          disabled={loading}
          className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
          style={{
            background: 'linear-gradient(135deg, #F59E0B, #EF4444)',
          }}
          title="Login rápido como administrador"
        >
          <Shield size={18} />
          {loading ? 'Entrando...' : 'Entrar como Admin'}
        </button>

        {error && (
          <div
            className="mt-4 px-4 py-2 rounded-lg text-sm"
            style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444' }}
          >
            {error}
          </div>
        )}

        <div className="mt-6 flex items-center justify-center gap-2 text-sm text-ayria-muted">
          <ArrowLeft size={14} />
          <a href="/login" className="hover:text-ayria-primary transition-colors">
            Voltar para login normal
          </a>
        </div>
      </div>
    </div>
  )
}