/**
 * AYRIA - Forgot Password Page (19/07/2026)
 *
 * Fluxo:
 * 1. User digita email + clica "Enviar link de redefinição"
 * 2. Backend chama /api/auth/forgot-password → gera token + manda email TurboSMTP
 * 3. Tela mostra confirmação genérica ("Se o email existir, você receberá...")
 *    (anti-enumeração — sempre retorna 200 mesmo com email inválido)
 * 4. User confere inbox e clica no link → /reset-password?token=X
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { LogoIcon } from '../components/Logo'
import { api } from '../lib/api'
import { AuthErrorBox } from '../components/AuthErrorBox'
import { ArrowLeft, Mail, Loader2 } from 'lucide-react'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  // Guarda o OBJETO de erro inteiro (não só string) pra <AuthErrorBox>
  // conseguir mostrar diagnóstico: code, status, URL, etc.
  const [error, setError] = useState<unknown>(null)
  const [resendCooldown, setResendCooldown] = useState(0)

  // Cooldown pra reenvio (60s)
  useEffect(() => {
    if (resendCooldown <= 0) return
    const t = setTimeout(() => setResendCooldown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [resendCooldown])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || resendCooldown > 0) return
    setLoading(true)
    setError(null)
    try {
      await api.post('/api/auth/forgot-password', { email })
      setSent(true)
      setResendCooldown(60)
    } catch (e: any) {
      console.error('[forgot-password] error', {
        hasResponse: !!e?.response,
        status: e?.response?.status,
        data: e?.response?.data,
        code: e?.code,
        message: e?.message,
      })
      setError(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: 'var(--ayria-bg)' }}
    >
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <LogoIcon size={80} variant="circular" />
        </div>

        {sent ? (
          /* ======== Tela pós-envio ======== */
          <div className="space-y-6 text-center">
            <div className="flex justify-center">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(212, 175, 55, 0.15)' }}
              >
                <Mail size={40} className="text-ayria-primary" />
              </div>
            </div>
            <h1 className="text-3xl font-bold gradient-text">Email enviado</h1>
            <p className="text-ayria-muted max-w-md mx-auto leading-relaxed">
              Se <strong className="text-ayria-text">{email}</strong> estiver cadastrado,
              você receberá um link de redefinição em instantes.
            </p>
            <div
              className="px-6 py-4 rounded-xl text-sm"
              style={{
                background: 'rgba(212, 175, 55, 0.08)', border: '1px solid rgba(212, 175, 55, 0.2)', color: '#E8C768',
              }}
            >
              ⏰ O link expira em <strong>1 hora</strong>. Verifique também a caixa de spam.
            </div>
            <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={resendCooldown > 0 || loading}
                className="px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #E8C768 100%)' }}
              >
                {resendCooldown > 0
                  ? `Reenviar em ${resendCooldown}s`
                  : loading
                  ? 'Reenviando...'
                  : 'Reenviar email'}
              </button>
              <Link
                to="/login"
                className="px-6 py-3 rounded-xl font-semibold text-center transition-opacity hover:opacity-90"
                style={{ background: 'var(--ayria-bg-high)', color: 'var(--ayria-white)' }}
              >
                Ir pro login
              </Link>
            </div>
          </div>
        ) : (
          /* ======== Form de email ======== */
          <>
            <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
              Esqueci minha senha
            </h1>
            <p className="text-center text-ayria-muted mb-8">
              Digite seu email e enviaremos um link pra você criar uma nova senha.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-ayria-muted mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="seu@email.com"
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none focus:border-ayria-primary transition-colors"
                  style={{ background: 'var(--ayria-bg-mid)', border: '1px solid var(--ayria-bg-high)' }}
                />
              </div>

              {error && (
                <AuthErrorBox
                  error={error}
                  action="envio"
                  context={{ pagina: '/forgot-password', email_digitado: email }}
                />
              )}

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #E8C768 100%)' }}
              >
                {loading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Enviando...
                  </>
                ) : (
                  'Enviar link de redefinição'
                )}
              </button>
            </form>

            <Link
              to="/login"
              className="mt-6 flex items-center justify-center gap-2 text-ayria-muted hover:text-ayria-text transition-colors text-sm"
            >
              <ArrowLeft size={14} />
              Voltar pro login
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
