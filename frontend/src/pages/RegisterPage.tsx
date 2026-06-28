/**
 * AYRIA - Register Page
 */
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { Logo } from '../components/Logo'

export function RegisterPage() {
  const { register, loading, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const ok = await register(email, password, fullName || undefined)
    if (ok) navigate('/onboarding')
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

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Nome</label>
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
            disabled={loading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
          >
            {loading ? 'Criando...' : 'Criar conta'}
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
