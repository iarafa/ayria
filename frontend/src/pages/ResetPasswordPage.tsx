/**
 * AYRIA - Reset Password Page (20/08/2026)
 *
 * Usuário clicou no link do email de "esqueci minha senha".
 * URL: /#/reset-password?token=XXX  (HashRouter, ? fica dentro do fragmento!)
 *
 * 🆕 21/08/2026 — FIX: token vem DEPOIS do #, não na query string.
 * URL é tipo: https://ayria.online/#/reset-password?token=XXX
 *              [scheme]            [fragmento: '/reset-password?token=XXX']
 *                              ↑ urlparse() não vê o ? como query, vê como parte do fragmento
 *
 * Fluxo:
 * 1. Pega fragmento da URL (depois do #)
 * 2. Extrai ?token=XXX do fragmento manualmente
 * 3. User digita nova senha (2x pra confirmar)
 * 4. POST /api/auth/reset-password com { token, new_password }
 * 5. Backend valida token (single-use, 1h) + aplica hash
 * 6. Mostra "Senha alterada!" + link pro login
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { LogoIcon } from '../components/Logo'

export function ResetPasswordPage() {
  const navigate = useNavigate()

  // � 21/08/2026 — Extrai token do FRAGMENTO (depois do #) pq HashRouter usa #/path?query
  const token = useMemo(() => {
    const hash = window.location.hash  // ex: "#/reset-password?token=XXX"
    const queryStart = hash.indexOf('?')
    if (queryStart === -1) return null
    const queryString = hash.substring(queryStart + 1)  // "token=XXX"
    const params = new URLSearchParams(queryString)
    return params.get('token')
  }, [])

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Se não tem token na URL, volta pro login
  useEffect(() => {
    if (!token) {
      navigate('/login', { replace: true })
    }
  }, [token, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validação cliente
    if (newPassword.length < 8) {
      setError('A senha deve ter pelo menos 8 caracteres.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('As senhas não conferem.')
      return
    }

    setLoading(true)
    try {
      const r = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword }),
      })
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}))
        const msg = detail.detail || 'Erro ao redefinir senha'
        if (typeof msg === 'string') setError(msg)
        else setError('Token inválido ou expirado. Solicite um novo link.')
        return
      }
      setSuccess(true)
    } catch (err: any) {
      setError(err.message || 'Erro de conexão. Tente novamente.')
    } finally {
      setLoading(false)
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

        {success ? (
          // ✅ Tela de sucesso
          <div className="text-center">
            <div className="text-5xl mb-4">✅</div>
            <h1 className="text-3xl font-bold text-white mb-3">
              Senha alterada!
            </h1>
            <p className="text-ayria-muted mb-6 leading-relaxed">
              Agora você pode entrar com sua nova senha.
            </p>
            <Link
              to="/login"
              className="inline-block px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
            >
              Ir pra o login
            </Link>
          </div>
        ) : (
          // 📝 Form de nova senha
          <>
            <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
              Crie uma nova senha
            </h1>
            <p className="text-center text-ayria-muted mb-8">
              Digite sua nova senha abaixo pra recuperar o acesso.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-ayria-muted mb-2">
                  Nova senha (mínimo 8 caracteres)
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  autoFocus
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none focus:border-ayria-primary transition-colors"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                />
              </div>

              <div>
                <label className="block text-sm text-ayria-muted mb-2">
                  Confirme a nova senha
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
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
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
              >
                {loading ? 'Salvando...' : 'Redefinir senha'}
              </button>

              <p className="text-center text-sm text-ayria-muted">
                <Link to="/login" className="text-ayria-primary hover:underline">
                  Voltar pro login
                </Link>
              </p>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
