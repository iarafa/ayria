import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, LogIn, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { api } from '../lib/api'

const PARTNER_TOKEN_KEY = 'ayria_partner_token'
const PARTNER_INFO_KEY = 'ayria_partner_info'

/**
 * 🆕 26/07/2026 22:43 — Tela de login do PARCEIRO
 *
 * Fluxo:
 *  1. Parceiro recebe email + senha temporária quando admin cria ele
 *  2. Entra aqui com email + senha → JWT próprio (token type=partner, 7d)
 *  3. Se must_change_password=true → redireciona pra /partner/change-password
 *  4. Senão vai direto pra /partner/<seu_id>
 *
 * Endpoint: POST /api/partner/login
 *  Body: { email, password }
 *  Retorna: { access_token, partner_id, partner_name, partner_email, must_change_password }
 */
export function PartnerLoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.post('/api/partner/login', { email: email.trim(), password })
      localStorage.setItem(PARTNER_TOKEN_KEY, data.access_token)
      localStorage.setItem(PARTNER_INFO_KEY, JSON.stringify({
        id: data.partner_id,
        name: data.partner_name,
        email: data.partner_email,
        must_change_password: data.must_change_password,
      }))
      if (data.must_change_password) {
        navigate(`/partner/change-password?first=1`)
      } else {
        navigate(`/partner/${data.partner_id}`)
      }
    } catch (e: any) {
      const detail = e.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Erro ao entrar. Confira email e senha.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: '#0A0A1A' }}>
      <div className="w-full max-w-md">
        <Link to="/" className="text-ayria-muted hover:text-ayria-text flex items-center gap-2 text-sm mb-6">
          <ArrowLeft size={14}/>Voltar
        </Link>

        <div className="p-8 rounded-3xl" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
          {/* Header */}
          <div className="flex flex-col items-center mb-6">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
              style={{ background: 'linear-gradient(135deg, #f1c961 0%, #f59e0b 100%)' }}>
              <LogIn size={28} className="text-white"/>
            </div>
            <h1 className="text-2xl font-bold text-ayria-text">Portal do Parceiro</h1>
            <p className="text-sm text-ayria-muted mt-1">Entre com seu email e senha</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-ayria-muted uppercase tracking-wide">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full mt-1 px-4 py-3 rounded-xl text-ayria-text placeholder:text-ayria-muted/40 outline-none focus:ring-2 focus:ring-amber-400/40"
                style={{ background: '#0A0A1A', border: '1px solid #2a2a3e' }}
                placeholder="seuemail@exemplo.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="text-xs text-ayria-muted uppercase tracking-wide">Senha</label>
              <div className="relative mt-1">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-3 pr-12 rounded-xl text-ayria-text placeholder:text-ayria-muted/40 outline-none focus:ring-2 focus:ring-amber-400/40"
                  style={{ background: '#0A0A1A', border: '1px solid #2a2a3e' }}
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                <button type="button" onClick={() => setShowPassword(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ayria-muted hover:text-ayria-text p-1">
                  {showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}
                </button>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl flex items-start gap-2 text-sm"
                style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
                <AlertCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5"/>
                <div className="text-red-300">{error}</div>
              </div>
            )}

            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #f1c961 0%, #f59e0b 100%)' }}>
              {loading ? 'Entrando...' : (<><LogIn size={16}/>Entrar</>)}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-ayria-muted/10 text-center text-xs text-ayria-muted">
            Esqueceu a senha? Fale com o administrador do programa de parceiros.
          </div>
        </div>
      </div>
    </div>
  )
}


/**
 * Tela de troca de senha (forçada após primeiro login com senha temporária).
 */
export function PartnerChangePasswordPage() {
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const token = localStorage.getItem(PARTNER_TOKEN_KEY)
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6" style={{ background: '#0A0A1A' }}>
        <div className="text-ayria-muted">Sessão expirou. <Link to="/partner/login" className="text-amber-400 underline">Faça login novamente</Link></div>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (newPassword.length < 6) {
      setError('Nova senha precisa ter no mínimo 6 caracteres.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Confirmação não confere com a nova senha.')
      return
    }
    setLoading(true)
    try {
      await api.post('/api/partner/me/change-password',
        { current_password: currentPassword, new_password: newPassword },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const info = JSON.parse(localStorage.getItem(PARTNER_INFO_KEY) || '{}')
      info.must_change_password = false
      localStorage.setItem(PARTNER_INFO_KEY, JSON.stringify(info))
      navigate(`/partner/${info.id}`)
    } catch (e: any) {
      const detail = e.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Erro ao trocar senha.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: '#0A0A1A' }}>
      <div className="w-full max-w-md">
        <div className="p-8 rounded-3xl" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
          <h1 className="text-2xl font-bold text-ayria-text mb-1">Trocar senha</h1>
          <p className="text-sm text-ayria-muted mb-6">É sua primeira entrada — defina uma senha nova antes de continuar.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs text-ayria-muted uppercase tracking-wide">Senha atual (temporária)</label>
              <input type="password" required value={currentPassword} onChange={e => setCurrentPassword(e.target.value)}
                className="w-full mt-1 px-4 py-3 rounded-xl text-ayria-text outline-none focus:ring-2 focus:ring-amber-400/40"
                style={{ background: '#0A0A1A', border: '1px solid #2a2a3e' }} placeholder="••••••••"/>
            </div>
            <div>
              <label className="text-xs text-ayria-muted uppercase tracking-wide">Nova senha</label>
              <input type="password" required value={newPassword} onChange={e => setNewPassword(e.target.value)} minLength={6}
                className="w-full mt-1 px-4 py-3 rounded-xl text-ayria-text outline-none focus:ring-2 focus:ring-amber-400/40"
                style={{ background: '#0A0A1A', border: '1px solid #2a2a3e' }} placeholder="mínimo 6 caracteres"/>
            </div>
            <div>
              <label className="text-xs text-ayria-muted uppercase tracking-wide">Confirmar nova senha</label>
              <input type="password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} minLength={6}
                className="w-full mt-1 px-4 py-3 rounded-xl text-ayria-text outline-none focus:ring-2 focus:ring-amber-400/40"
                style={{ background: '#0A0A1A', border: '1px solid #2a2a3e' }}/>
            </div>

            {error && (
              <div className="p-3 rounded-xl text-sm" style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
                <div className="text-red-300">{error}</div>
              </div>
            )}

            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl text-white font-semibold disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #f1c961 0%, #f59e0b 100%)' }}>
              {loading ? 'Salvando...' : 'Salvar e entrar'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}