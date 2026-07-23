/**
 * AYRIA - App Router Principal
 */
import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './store/auth'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { VerifyEmailPage } from './pages/VerifyEmailPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { ChatPage } from './pages/ChatPage'
import { AdminPage } from './pages/AdminPage'
import { AdminLoginPage } from './pages/AdminLoginPage'
import { ObserveUserPage } from './pages/ObserveUserPage'
import CreatingProfilePage from './pages/CreatingProfilePage'
import { PlanosPage } from './pages/PlanosPage'  // 🆕 22/07 21:10 — cupom de desconto

function PrivateRoute({ children, adminOnly = false, requireOnboarding = false }: { children: React.ReactNode; adminOnly?: boolean; requireOnboarding?: boolean }) {
  const { user, token, loadUser } = useAuth()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token && !user) {
      loadUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [token, user])

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: '#050505' }}
      >
        <div className="text-ayria-muted">Carregando...</div>
      </div>
    )
  }

  if (!token) return <Navigate to="/login" replace />
  if (adminOnly && user?.role !== 'admin' && user?.role !== 'SUPER_ADMIN') {
    return <Navigate to="/chat" replace />
  }

  // BLOQUEIO: se rota exige onboarding completo e user não tem, manda pro onboarding
  // ADMIN (role 'admin' ou 'SUPER_ADMIN') NUNCA precisa de onboarding
  if (
    requireOnboarding &&
    user?.role !== 'SUPER_ADMIN' &&
    user?.role !== 'admin' &&
    user?.onboarding_status !== 'completed'
  ) {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}

function OnboardingRedirect({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (!user) return <>{children}</>  // ainda carregando, mostra o children (que vai redirecionar)

  const isAdmin = user.role === 'SUPER_ADMIN' || user.role === 'admin'
  if (isAdmin) return <Navigate to="/admin" replace />
  if (user.onboarding_status === 'completed') return <Navigate to="/chat" replace />

  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route
        path="/onboarding"
        element={
          <PrivateRoute>
            <OnboardingRedirect>
              <OnboardingPage />
            </OnboardingRedirect>
          </PrivateRoute>
        }
      />
      <Route
        path="/criando-perfil"
        element={
          <PrivateRoute>
            <CreatingProfilePage />
          </PrivateRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <PrivateRoute requireOnboarding>
            <ChatPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <PrivateRoute adminOnly>
            <AdminPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/admin/observe/:userId"
        element={
          <PrivateRoute adminOnly>
            <ObserveUserPage />
          </PrivateRoute>
        }
      />
      {/* 🆕 22/07 21:10 — Planos + cupom de desconto (Rafael pediu) */}
      <Route
        path="/planos"
        element={
          <PrivateRoute>
            <PlanosPage />
          </PrivateRoute>
        }
      />
      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<RootRedirect />} />
    </Routes>
  )
}

// 🛡️ ADMIN → /admin | SEMPRE Stripe PRIMEIRO, onboard SÓ DEPOIS de pagar
// Rafael pediu 22/07 21:41: user comum só cai no /chat DEPOIS de assinar Stripe.
// Se não tem subscription Stripe ativa, manda pra /planos SEMPRE.
function RootRedirect() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'SUPER_ADMIN' || user?.role === 'admin'
  if (isAdmin) return <Navigate to="/admin" replace />
  // User sem assinatura Stripe ativa (external_subscription_id null OU billing_status diferente de 'active') → /planos
  const hasActiveSubscription = !!user?.external_subscription_id && user?.billing_status === 'active'
  if (!user || !hasActiveSubscription) return <Navigate to="/planos" replace />
  return <Navigate to="/chat" replace />
}