/**
 * AYRIA - Forgot Password Modal (20/08/2026)
 *
 * Modal disparado pelo botão "Esqueci minha senha" no LoginPage.
 * 1. User digita email
 * 2. POST /api/auth/forgot-password
 * 3. Backend envia email com link /#/reset-password?token=XXX
 * 4. Modal mostra "Se o email existir, você receberá um link em breve"
 *    (não revela se email existe ou não, pra evitar enumeração)
 */
import { useState } from 'react'

interface ForgotPasswordModalProps {
  isOpen: boolean
  onClose: () => void
}

export function ForgotPasswordModal({ isOpen, onClose }: ForgotPasswordModalProps) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      // Sempre mostra sucesso (não revela se email existe)
      setSubmitted(true)
    } catch (err: any) {
      setError(err.message || 'Erro ao processar. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  function handleClose() {
    setEmail('')
    setSubmitted(false)
    setError(null)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={handleClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-8 relative"
        style={{
          background: 'linear-gradient(135deg, #1a0a2e, #0a0518)',
          border: '1px solid rgba(168, 85, 247, 0.3)',
          boxShadow: '0 0 60px rgba(168, 85, 247, 0.2)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 text-ayria-muted hover:text-white text-2xl leading-none"
          aria-label="Fechar"
        >
          ×
        </button>

        {submitted ? (
          // ✅ Confirmação genérica (não revela se email existe)
          <div className="text-center py-4">
            <div className="text-5xl mb-4">📬</div>
            <h2 className="text-2xl font-bold text-white mb-3">
              Verifique seu email
            </h2>
            <p className="text-ayria-muted mb-6 leading-relaxed">
              Se o email <strong className="text-white">{email}</strong> estiver
              cadastrado, você receberá um link pra redefinir sua senha em alguns minutos.
            </p>
            <button
              onClick={handleClose}
              className="w-full py-3 rounded-lg font-semibold text-white text-base transition hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
            >
              Fechar
            </button>
            <p className="text-xs text-ayria-muted mt-4">
              Não chegou? Verifique a caixa de spam.
            </p>
          </div>
        ) : (
          // 📝 Form de email
          <>
            <div className="text-center mb-4">
              <div className="text-4xl mb-2">🔑</div>
            </div>
            <h2 className="text-2xl font-bold text-white text-center mb-2">
              Esqueceu sua senha?
            </h2>
            <p className="text-ayria-muted text-center mb-6">
              Digite seu email e enviaremos um link pra você redefinir.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-ayria-muted mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoFocus
                  placeholder="seu@email.com"
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
                disabled={loading || !email}
                className="w-full py-3 rounded-lg font-semibold text-white text-base transition hover:opacity-90 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
              >
                {loading ? 'Enviando...' : 'Enviar link'}
              </button>
              <button
                type="button"
                onClick={handleClose}
                className="w-full py-2 text-ayria-muted hover:text-white text-sm"
              >
                Cancelar
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
