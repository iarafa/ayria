/**
 * AYRIA - Admin Page
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { adminApi } from '../lib/api'
import { Logo } from '../components/Logo'
import { Users, FileText, Settings, ListChecks, LogOut } from 'lucide-react'

type Tab = 'users' | 'knowledge' | 'onboarding' | 'attributes'

export function AdminPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('users')
  const [users, setUsers] = useState<any[]>([])
  const [docs, setDocs] = useState<any[]>([])
  const [attributes, setAttributes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user?.role !== 'admin' && user?.role !== 'SUPER_ADMIN') {
      navigate('/chat')
      return
    }
    if (tab === 'users') {
      setLoading(true)
      adminApi.listUsers().then((r) => {
        setUsers(r.data)
        setLoading(false)
      })
    } else if (tab === 'knowledge') {
      setLoading(true)
      adminApi.listDocuments().then((r) => {
        setDocs(r.data)
        setLoading(false)
      })
    } else if (tab === 'attributes') {
      setLoading(true)
      adminApi.listAttributes().then((r) => {
        setAttributes(r.data)
        setLoading(false)
      })
    }
  }, [tab, user])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('title', file.name)
    formData.append('file', file)
    await adminApi.uploadDocument(formData)
    alert('Upload feito! (Indexação em background - próxima fase)')
    const { data } = await adminApi.listDocuments()
    setDocs(data)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Deletar documento?')) return
    await adminApi.deleteDocument(id)
    setDocs(docs.filter((d) => d.id !== id))
  }

  return (
    <div className="min-h-screen" style={{ background: '#0A0A1A' }}>
      {/* Header */}
      <header className="glass px-6 py-4 flex items-center justify-between border-b border-ayria-border">
        <div className="flex items-center gap-3">
          <Logo size={32} />
          <span
            className="px-2 py-1 rounded text-xs font-semibold"
            style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#F59E0B' }}
          >
            ADMIN
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/chat')} className="text-ayria-muted hover:text-ayria-text text-sm">
            Ir pro Chat
          </button>
          <button onClick={logout} className="text-ayria-muted hover:text-red-400">
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-ayria-border">
          {[
            { id: 'users', label: 'Usuários', icon: Users },
            { id: 'knowledge', label: 'Conhecimento', icon: FileText },
            { id: 'onboarding', label: 'Onboarding', icon: ListChecks },
            { id: 'attributes', label: 'Atributos', icon: Settings },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as Tab)}
              className={`px-4 py-3 text-sm flex items-center gap-2 border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-ayria-admin text-ayria-text'
                  : 'border-transparent text-ayria-muted hover:text-ayria-text'
              }`}
            >
              <t.icon size={14} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading && <div className="text-ayria-muted">Carregando...</div>}

        {tab === 'users' && !loading && (
          <div className="space-y-2">
            {users.map((u) => (
              <div
                key={u.id}
                className="p-4 rounded-xl flex items-center justify-between"
                style={{ background: '#111111', border: '1px solid #1E1E2E' }}
              >
                <div>
                  <div className="text-ayria-text font-medium">{u.email}</div>
                  <div className="text-xs text-ayria-muted">
                    {u.full_name || '—'} · {u.role} · {u.message_count} mensagens
                  </div>
                </div>
                <span
                  className="text-xs px-2 py-1 rounded"
                  style={{
                    background: u.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                    color: u.is_active ? '#10B981' : '#EF4444',
                  }}
                >
                  {u.is_active ? 'Ativo' : 'Inativo'}
                </span>
              </div>
            ))}
          </div>
        )}

        {tab === 'knowledge' && !loading && (
          <div>
            <div className="mb-4">
              <label className="inline-block px-4 py-2 rounded-xl cursor-pointer text-white font-medium"
                style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}>
                + Upload de documento
                <input type="file" accept=".pdf,.txt,.md" onChange={handleUpload} className="hidden" />
              </label>
            </div>
            <div className="space-y-2">
              {docs.map((d) => (
                <div
                  key={d.id}
                  className="p-4 rounded-xl flex items-center justify-between"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                >
                  <div>
                    <div className="text-ayria-text font-medium">{d.title}</div>
                    <div className="text-xs text-ayria-muted">
                      {d.file_name} · {(d.file_size_bytes / 1024).toFixed(1)}KB · {d.status}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(d.id)}
                    className="text-red-400 hover:text-red-300 text-sm"
                  >
                    Deletar
                  </button>
                </div>
              ))}
              {docs.length === 0 && (
                <div className="text-center text-ayria-muted py-8">
                  Nenhum documento ainda.
                </div>
              )}
            </div>
          </div>
        )}

        {tab === 'onboarding' && (
          <div className="text-center text-ayria-muted py-12">
            <p>Editor de onboarding dinâmico - configurar via backend</p>
            <p className="text-sm mt-2">Endpoint: <code>PUT /api/admin/onboarding/config</code></p>
          </div>
        )}

        {tab === 'attributes' && !loading && (
          <div className="space-y-2">
            {attributes.map((a) => (
              <div
                key={a.id}
                className="p-4 rounded-xl"
                style={{ background: '#111111', border: '1px solid #1E1E2E' }}
              >
                <div className="text-ayria-text font-medium">{a.label}</div>
                <div className="text-xs text-ayria-muted">
                  {a.code} · {a.attribute_type} {a.is_required ? '· obrigatório' : ''}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
