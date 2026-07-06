/**
 * AYRIA - App Router Principal
 */
import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './store/auth'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { ChatPage } from './pages/ChatPage'
import { AdminPage } from './pages/AdminPage'
import { AdminLoginPage } from './pages/AdminLoginPage'
import { ObserveUserPage } from './pages/ObserveUserPage'
import CreatingProfilePage from './pages/CreatingProfilePage'

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
      <Route path="/" element={<Navigate to="/chat" replace />} />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  )
}