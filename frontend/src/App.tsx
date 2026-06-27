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
import { NumerologyReveal } from './pages/NumerologyReveal'

function PrivateRoute({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
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
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/onboarding"
        element={
          <PrivateRoute>
            <OnboardingPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/numerology"
        element={
          <PrivateRoute>
            <NumerologyReveal />
          </PrivateRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <PrivateRoute>
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
      <Route path="/" element={<Navigate to="/chat" replace />} />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  )
}