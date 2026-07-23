/**
 * AYRIA - Login Page
 *
 * Fluxo de login:
 * 1. Usuário entra email + senha
 * 2. Se sucesso: navega pra /chat
 * 3. ChatPage decide o que mostrar:
 *    - Tem chats anteriores? → abre o mais recente
 *    - Sem chats? → mostra tela de boas-vindas (user clica "+ Novo Tema" pra começar)
 *
 * (Antes: sempre criava chat novo vazio no login. Rafael pediu pra mudar em 08/07/2026
 * — o user já tem conversas, ele quer cair nelas, não em chat em branco.)
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { LogoIcon } from '../components/Logo'

export function LoginPage() {
  const { login, loading, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const ok = await login(email, password)
    if (ok) {
      // 🛡️ ADMIN → /admin | User sem Stripe → /planos (SEMPRE) | User com Stripe → /chat
      // Rafael 22/07 21:41: user comum só cai no chat DEPOIS de assinar Stripe.
      const u = useAuth.getState().user
      const isAdmin = u?.role === 'SUPER_ADMIN' || u?.role === 'admin'
      if (isAdmin) {
        navigate('/admin', { replace: true })
        return
      }
      const hasActiveSubscription = !!u?.external_subscription_id && u?.billing_status === 'active'
      navigate(hasActiveSubscription ? '/chat' : '/planos', { replace: true })
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: '#050505' }}
    >
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <LogoIcon size={200} variant="circular" />
        </div>

        <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
          Bem-vindo de volta
        </h1>
        <p className="text-center text-ayria-muted mb-8">
          Entre na sua jornada de autoconhecimento
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none focus:border-ayria-primary transition-colors"
              style={{ background: '#111111', border: '1px solid #1E1E2E' }}
            />
          </div>

          <div>
            <label className="block text-sm text-ayria-muted mb-2">Senha</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none focus:border-ayria-primary transition-colors"
              style={{ background: '#111111', border: '1px solid #1E1E2E' }}
            />
          </div>

          {error && (
            <div
              className="px-4 py-2 rounded-lg text-sm"
              style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444' }}
            >
              {error}
              {error.includes('Confirme seu email') && (
                <div className="mt-2">
                  <Link to="/register" className="underline text-ayria-primary">
                    Reenviar email de verificação
                  </Link>
                </div>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
          >
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>

        <p className="text-center text-ayria-muted mt-6">
          Não tem conta?{' '}
          <Link to="/register" className="text-ayria-primary hover:underline">
            Criar conta
          </Link>
        </p>
      </div>
    </div>
  )
}
