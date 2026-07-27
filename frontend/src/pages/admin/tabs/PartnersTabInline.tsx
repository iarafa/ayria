import { useState, useEffect } from 'react'
import { KeyRound, Trash2, UserPlus, X, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ListWithControls } from '../../../components/ListWithControls'
import { adminApi, api } from '../../../lib/api'

/**
 * PartnersTabInline - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function PartnersTabInline() {
  const [partners, setPartners] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', phone: '', document_type: 'CPF', document_number: '', pix_key: '', notes: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // 🆕 23/07 2026 — modal de senha temporária gerada (admin vê 1x)
  const [tempPwd, setTempPwd] = useState<{ partner_name: string; partner_email: string; password: string } | null>(null)
  const [createdTempPwd, setCreatedTempPwd] = useState<string | null>(null)

  const reload = async () => {
    setLoading(true)
    try {
      const r = await api.get<any[]>('/api/admin/partners')
      setPartners(r.data || [])
    } catch (e: any) { setError(e.response?.data?.detail || 'Erro ao carregar') }
    finally { setLoading(false) }
  }
  useEffect(() => { reload() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      const resp = await api.post('/api/admin/partners', form)
      // Limpa form + FECHA tela ANTES de qualquer coisa (mesmo se reload falhar)
      setShowCreate(false)
      setForm({ name: '', email: '', phone: '', document_type: 'CPF', document_number: '', pix_key: '', notes: '' })
      // Tenta recarregar lista (best-effort, se falhar não trava o sucesso)
      reload().catch(() => {})
      // Modal da senha temporária — só abre se veio no payload
      if (resp.data?.temporary_password) {
        setCreatedTempPwd(resp.data.temporary_password)
      } else {
        // Fallback: avisa que foi criado
        alert('✅ Parceiro criado! Senha temporária não gerada — use "Resetar senha" para gerar uma.')
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message)
      // NÃO fecha a tela em caso de erro — deixa usuário corrigir
    } finally {
      setBusy(false)
    }
  }

  const handleResetPassword = async (p: any) => {
    if (!confirm(`Resetar a senha de ${p.name} (${p.email})?\n\nUma senha temporária será gerada. O parceiro será obrigado a trocar no próximo login.`)) return
    try {
      const resp = await api.post(`/api/admin/partners/${p.id}/reset-password`)
      if (resp.data?.temporary_password) {
        setTempPwd({
          partner_name: resp.data.partner_name || p.name,
          partner_email: resp.data.partner_email || p.email,
          password: resp.data.temporary_password,
        })
      } else {
        alert('❌ Backend não retornou senha temporária')
      }
    } catch (e: any) {
      alert('❌ ' + (e.response?.data?.detail || e.message))
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-ayria-text flex items-center gap-2"><UserPlus size={24}/>Parceiros</h2>
        <button onClick={() => setShowCreate(true)} className="px-4 py-2 rounded-xl text-white font-medium" style={{ background: '#f1c961' }}>+ Novo Parceiro</button>
      </div>
      {error && <div className="mb-4 p-3 rounded-xl bg-red-900/20 border border-red-500/30 text-red-300 text-sm">{error}</div>}
      <ListWithControls data={partners} itemName="parceiro" searchPlaceholder="Buscar por nome, email..." emptyMessage="Nenhum parceiro cadastrado">
        {(p) => (
          <div className="p-4 rounded-xl flex items-center justify-between" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <div>
              <div className="text-ayria-text font-medium">{p.name}</div>
              <div className="text-xs text-ayria-muted">{p.email} · {p.document_type}: {p.document_number || '-'} · {p.coupons_count} cupom(ns) · R$ {(p.total_commission_cents || 0) / 100}</div>
            </div>
            <div className="flex gap-2">
              <Link to={`/partner/${p.id}`} target="_blank" title="Ver portal do parceiro"
                className="text-blue-400 hover:text-blue-300 p-1 inline-flex items-center">
                <ExternalLink size={16}/>
              </Link>
              <button onClick={() => handleResetPassword(p)} className="text-yellow-400 hover:text-yellow-300 p-1" title="Resetar senha"><KeyRound size={16} /></button>
              <button onClick={async () => {
                if (!confirm('Desativar parceiro ' + p.name + '?')) return
                try {
                  await api.delete(`/api/admin/partners/${p.id}`)
                  reload().catch(() => {})
                  setError(null)
                } catch (e: any) { alert('❌ ' + (e.response?.data?.detail || e.message)) }
              }} className="text-red-400 hover:text-red-300 p-1" title="Desativar"><Trash2 size={16} /></button>
            </div>
          </div>
        )}
      </ListWithControls>

      {/* 🆕 23/07 2026 — Modal: senha temporária gerada no RESET */}
      {tempPwd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6" style={{ background: '#1a1a2e', border: '1px solid #da950b' }}>
            <div className="flex items-center gap-2 mb-3">
              <KeyRound size={22} className="text-ayria-gold" />
              <h3 className="text-xl font-bold text-ayria-text">Senha temporária gerada</h3>
            </div>
            <p className="text-sm text-ayria-muted mb-4">
              Anote e envie ao parceiro de forma segura. Ele será obrigado a trocar no próximo login.
            </p>
            <div className="space-y-2 mb-4 p-3 rounded-xl" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e' }}>
              <div className="text-xs text-ayria-muted">PARCEIRO</div>
              <div className="text-ayria-text font-medium">{tempPwd.partner_name}</div>
              <div className="text-xs text-ayria-muted">{tempPwd.partner_email}</div>
            </div>
            <div className="space-y-2 mb-5">
              <div className="text-xs text-ayria-muted uppercase">SENHA TEMPORÁRIA</div>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-4 py-3 rounded-lg font-mono text-lg font-bold select-all" style={{ background: '#050505', border: '1px solid #da950b', color: '#f1c961' }}>
                  {tempPwd.password}
                </code>
                <button onClick={() => { navigator.clipboard.writeText(tempPwd.password); alert('✅ Senha copiada!') }}
                  className="px-3 py-3 rounded-lg text-ayria-text hover:text-ayria-gold" style={{ background: '#1E1E2E', border: '1px solid #2a2a3e' }} title="Copiar">
                  📋
                </button>
              </div>
            </div>
            <button onClick={() => setTempPwd(null)}
              className="w-full py-2.5 rounded-xl text-white font-semibold" style={{ background: '#f1c961' }}>
              Fechar
            </button>
          </div>
        </div>
      )}

      {/* 🆕 23/07 2026 — Modal: senha temporária gerada no CREATE */}
      {createdTempPwd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6" style={{ background: '#1a1a2e', border: '1px solid #da950b' }}>
            <div className="flex items-center gap-2 mb-3">
              <KeyRound size={22} className="text-ayria-gold" />
              <h3 className="text-xl font-bold text-ayria-text">Parceiro criado!</h3>
            </div>
            <p className="text-sm text-ayria-muted mb-4">
              Senha temporária gerada. O parceiro será obrigado a trocar no primeiro login.
            </p>
            <div className="flex items-center gap-2 mb-5">
              <code className="flex-1 px-4 py-3 rounded-lg font-mono text-lg font-bold select-all" style={{ background: '#050505', border: '1px solid #da950b', color: '#f1c961' }}>
                {createdTempPwd}
              </code>
              <button onClick={() => { navigator.clipboard.writeText(createdTempPwd); alert('✅ Senha copiada!') }}
                className="px-3 py-3 rounded-lg text-ayria-text hover:text-ayria-gold" style={{ background: '#1E1E2E', border: '1px solid #2a2a3e' }} title="Copiar">
                📋
              </button>
            </div>
            <button onClick={() => setCreatedTempPwd(null)}
              className="w-full py-2.5 rounded-xl text-white font-semibold" style={{ background: '#f1c961' }}>
              Fechar
            </button>
          </div>
        </div>
      )}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
          <div className="w-full max-w-md rounded-2xl p-6" style={{ background: '#1a1a2e', border: '1px solid #2a2a3e' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-ayria-text">Novo Parceiro</h3>
              <button onClick={() => setShowCreate(false)} className="text-ayria-muted hover:text-ayria-text"><X size={20}/></button>
            </div>
            <form onSubmit={handleCreate} className="space-y-3">
              {(['name', 'email', 'phone', 'pix_key'] as const).map((k) => (
                <div key={k}>
                  <label className="block text-xs text-ayria-muted mb-1">{k.charAt(0).toUpperCase() + k.slice(1)}</label>
                  <input type="text" required={k==='name'||k==='email'} value={(form as any)[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} />
                </div>
              ))}
              <div>
                <label className="block text-xs text-ayria-muted mb-1">CPF/CNPJ</label>
                <input type="text" value={form.document_number} onChange={(e) => setForm({ ...form, document_number: e.target.value })} className="w-full px-3 py-2 rounded-lg text-sm" style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }} placeholder="123.456.789-00" />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 py-2 rounded-xl text-ayria-muted hover:text-ayria-text" style={{ border: '1px solid #2a2a3e' }}>Cancelar</button>
                <button type="submit" disabled={busy} className="flex-1 py-2 rounded-xl text-white font-semibold disabled:opacity-50" style={{ background: '#f1c961' }}>{busy ? 'Criando...' : 'Criar'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
