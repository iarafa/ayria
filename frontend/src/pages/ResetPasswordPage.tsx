/**
 * AYRIA - Reset Password Page (19/07/2026)
 *
 * User clicou no link do email → /reset-password?token=X
 * Página pede senha nova (2x) e submete /api/auth/reset-password.
 *
 * Estados:
 *  - Sem token na URL → "Token inválido" + link pro /forgot-password
 *  - 200 OK → mostra sucesso + botão ir pro login
 *  - 404 → token não existe / já usado
 *  - 410 → token expirado (>1h)
 */
import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { LogoIcon } from '../components/Logo'
import { api } from '../lib/api'
import { AuthErrorBox } from '../components/AuthErrorBox'
import { CheckCircle2, Lock, Loader2, Eye, EyeOff, AlertTriangle } from 'lucide-react'

type Status = 'idle' | 'success' | 'invalid' | 'expired'

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<Status>('idle')
  // Guarda o OBJETO de erro inteiro (não só string) pra <AuthErrorBox>
  const [errorObj, setErrorObj] = useState<unknown>(null)

  const passwordsMatch = password && password === confirm
  const passwordValid = password.length >= 8
  const canSubmit = !!token && passwordValid && passwordsMatch && !loading

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token || !canSubmit) return
    setLoading(true)
    setErrorObj(null)
    try {
      await api.post('/api/auth/reset-password', {
        token,
        new_password: password,
      })
      setStatus('success')
      // Auto-redireciona pro login depois de 3s
      setTimeout(() => navigate('/login'), 3000)
    } catch (e: any) {
      console.error('[reset-password] error', {
        hasResponse: !!e?.response,
        status: e?.response?.status,
        data: e?.response?.data,
        code: e?.code,
        message: e?.message,
      })
      const code = e?.response?.status
      if (code === 410) {
        setStatus('expired')
      } else if (code === 404) {
        setStatus('invalid')
      } else {
        setErrorObj(e)
      }
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-4"
        style={{ background: 'var(--ayria-bg)' }}
      >
        <div className="w-full max-w-md text-center space-y-6">
          <div className="flex justify-center">
            <LogoIcon size={80} variant="circular" />
          </div>
          <div className="flex justify-center">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center"
              style={{ background: 'rgba(239, 68, 68, 0.15)' }}
            >
              <AlertTriangle size={40} className="text-red-400" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-ayria-text">Token inválido</h1>
          <p className="text-ayria-muted">
            Esta página exige um token válido. Solicite um novo link de redefinição.
          </p>
          <Link
            to="/forgot-password"
            className="inline-block px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #E8C768 100%)' }}
          >
            Solicitar novo link
          </Link>
        </div>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-4"
        style={{ background: 'var(--ayria-bg)' }}
      >
        <div className="w-full max-w-md text-center space-y-6">
          <div className="flex justify-center">
            <LogoIcon size={80} variant="circular" />
          </div>
          <div className="flex justify-center">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center"
              style={{ background: 'rgba(16, 185, 129, 0.15)' }}
            >
              <CheckCircle2 size={40} className="text-green-400" />
            </div>
          </div>
          <h1 className="text-3xl font-bold gradient-text">Senha redefinida!</h1>
          <p className="text-ayria-muted">
            Sua senha foi atualizada com sucesso. Você será redirecionado pro login em instantes.
          </p>
          <Link
            to="/login"
            className="inline-block px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #E8C768 100%)' }}
          >
            Ir pro login agora
          </Link>
        </div>
      </div>
    )
  }

  if (status === 'invalid' || status === 'expired') {
    const title = status === 'invalid' ? 'Token inválido ou já usado' : 'Link expirado'
    const desc =
      status === 'invalid'
        ? 'Este link não existe mais ou já foi utilizado. Solicite um novo abaixo.'
        : 'Links de redefinição expiram em 1 hora. Solicite um novo abaixo.'
    return (
      <div
        className="min-h-screen flex items-center justify-center px-4"
        style={{ background: 'var(--ayria-bg)' }}
      >
        <div className="w-full max-w-md text-center space-y-6">
          <div className="flex justify-center">
            <LogoIcon size={80} variant="circular" />
          </div>
          <div className="flex justify-center">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center"
              style={{ background: 'rgba(245, 158, 11, 0.15)' }}
            >
              <AlertTriangle size={40} className="text-yellow-400" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-ayria-text">{title}</h1>
          <p className="text-ayria-muted">{desc}</p>
          <Link
            to="/forgot-password"
            className="inline-block px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #E8C768 100%)' }}
          >
            Solicitar novo link
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: 'var(--ayria-bg)' }}
    >
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-8">
          <LogoIcon size={80} variant="circular" />
        </div>

        <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
          Criar nova senha
        </h1>
        <p className="text-center text-ayria-muted mb-8">
          Defina uma senha nova pra sua conta. Mínimo 8 caracteres.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-ayria-muted mb-2">Nova senha</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                placeholder="••••••••"
                className="w-full px-4 py-3 pr-12 rounded-xl text-ayria-text outline-none focus:border-ayria-primary transition-colors"
                style={{ background: 'var(--ayria-bg-mid)', border: '1px solid var(--ayria-bg-high)' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-ayria-muted hover:text-ayria-text transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {password && !passwordValid && (
              <p className="text-xs text-yellow-400 mt-1">Mínimo 8 caracteres</p>
            )}
          </div>

          <div>
            <label className="block text-sm text-ayria-muted mb-2">Confirmar senha</label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              minLength={8}
              placeholder="••••••••"
              className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none focus:border-ayria-primary transition-colors"
              style={{
                background: 'var(--ayria-bg-mid)', border: confirm && !passwordsMatch ? '1px solid #EF4444' : '1px solid #1E1E2E',
              }}
            />
            {confirm && !passwordsMatch && (
              <p className="text-xs text-red-400 mt-1">As senhas não coincidem</p>
            )}
            {passwordsMatch && (
              <p className="text-xs text-green-400 mt-1 flex items-center gap-1">
                <Lock size={12} /> Senhas coincidem ✓
              </p>
            )}
          </div>

          {errorObj && (
            <AuthErrorBox
              error={errorObj}
              action="redefinição"
              context={{ pagina: '/reset-password', tokenPrefix: token?.slice(0, 8) + '…' }}
            />
          )}

          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #E8C768 100%)' }}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Redefinindo...
              </>
            ) : (
              'Redefinir senha'
            )}
          </button>
        </form>

        <Link
          to="/login"
          className="mt-6 flex items-center justify-center text-ayria-muted hover:text-ayria-text transition-colors text-sm"
        >
          Voltar pro login
        </Link>
      </div>
    </div>
  )
}
