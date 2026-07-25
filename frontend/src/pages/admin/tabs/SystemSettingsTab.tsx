import { useState, useEffect } from 'react'
import { AlertCircle, CheckCircle2, Cloud, Cpu, Database, Settings, Shield } from 'lucide-react'
import { adminApi, api } from '../../../lib/api'

/**
 * SystemSettingsTab - quebrado de AdminPage.tsx em 25/07/2026
 * Mantém comportamento idêntico, agora isolado em arquivo próprio.
 */

export function SystemSettingsTab() {
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadConfig()
  }, [])

  async function loadConfig() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.get('/api/admin/config/ai')
      setConfig(res.data)
    } catch (e: any) {
      setError(e.message || 'Erro ao carregar config')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-2 border-ayria-admin border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-red-900/20 border border-red-500/30 text-red-300">
        ❌ {error}
      </div>
    )
  }

  const ai = config?.ai
  const azure = config?.azure_storage
  const env = config?.environment
  const rules = config?.rules || []

  return (
    <div className="space-y-6">
      {/* HEADER: qual IA tá rodando */}
      <div
        className="p-6 rounded-2xl"
        style={{ background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)', border: '1px solid #2a2a3e' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}
            >
              <Cpu size={24} className="text-white" />
            </div>
            <div>
              <div className="text-xs text-ayria-muted uppercase tracking-wider">Modelo de IA em uso</div>
              <div className="text-2xl font-bold text-ayria-text mt-1">
                {ai?.model || '(não configurado)'}
              </div>
              <div className="text-sm text-ayria-muted mt-1">
                Provider: <span className="text-ayria-text font-medium">{ai?.provider || '-'}</span>
              </div>
            </div>
          </div>
          {ai?.configured ? (
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/30">
              <CheckCircle2 size={14} />
              ATIVO
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/30">
              <AlertCircle size={14} />
              NÃO CONFIGURADO
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Base URL</div>
            <div className="text-sm text-ayria-text font-mono break-all">{ai?.base_url || '-'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">API Key</div>
            <div className="text-sm text-ayria-text font-mono">{ai?.api_key_preview || '(vazio)'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Status</div>
            <div className="text-sm text-ayria-text">
              {ai?.api_key_set ? '✅ Chave configurada' : '❌ Sem chave'}
            </div>
          </div>
        </div>
      </div>

      {/* REGRAS DO SISTEMA */}
      <div
        className="p-5 rounded-2xl"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Shield size={16} className="text-ayria-admin" />
          <div className="text-sm font-semibold text-ayria-text">Regras do Sistema</div>
        </div>
        <ul className="space-y-2">
          {rules.map((r: string, i: number) => (
            <li key={i} className="flex items-start gap-2 text-sm text-ayria-muted">
              <CheckCircle2 size={14} className="text-green-400 mt-0.5 flex-shrink-0" />
              <span>{r}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* AZURE STORAGE */}
      <div
        className="p-5 rounded-2xl"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Cloud size={16} className="text-blue-400" />
          <div className="text-sm font-semibold text-ayria-text">Azure Blob Storage</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Status</div>
            <div className="text-sm text-ayria-text">
              {azure?.configured ? '✅ Configurado' : '❌ Não configurado'}
            </div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Container</div>
            <div className="text-sm text-ayria-text font-mono">{azure?.container || '-'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">SAS expira em</div>
            <div className="text-sm text-ayria-text">{azure?.sas_expires || '-'}</div>
          </div>
          <div className="p-3 rounded-lg" style={{ background: '#0f0f1e' }}>
            <div className="text-xs text-ayria-muted mb-1">Fallback local</div>
            <div className="text-sm text-ayria-text">
              {azure?.use_local_fallback ? '⚠️ Ativo (debug)' : '✅ Desativado (produção)'}
            </div>
          </div>
        </div>
      </div>

      {/* AMBIENTE */}
      <div
        className="p-5 rounded-2xl"
        style={{ background: '#111111', border: '1px solid #1E1E2E' }}
      >
        <div className="flex items-center gap-2 mb-3">
          <Database size={16} className="text-purple-400" />
          <div className="text-sm font-semibold text-ayria-text">Ambiente</div>
        </div>
        <div className="text-sm text-ayria-muted">
          Modo: <span className="text-ayria-text font-mono">{env || '-'}</span>
        </div>
      </div>

      {/* BOTÃO REFRESH */}
      <div className="flex justify-end">
        <button
          onClick={loadConfig}
          className="px-4 py-2 rounded-lg text-sm bg-ayria-admin/10 text-ayria-admin border border-ayria-admin/30 hover:bg-ayria-admin/20 transition-colors flex items-center gap-2"
        >
          <Settings size={14} />
          Atualizar
        </button>
      </div>
    </div>
  )
}


// ============================================================
// SUPERVISION TAB - Monitoramento de risco psicossocial
// ============================================================