import { useState } from 'react'
import { adminApi } from '../lib/api'
import {
  Shield, ShieldOff, Clock, Ban, AlertCircle, Loader2, X, CheckCircle2,
} from 'lucide-react'

interface BlockUserModalProps {
  open: boolean
  onClose: () => void
  /** Dados do user que vai bloquear/desbloquear */
  user: {
    id: string
    email: string
    full_name?: string | null
    blocked_at?: string | null
    blocked_until?: string | null
    block_reason?: string | null
  } | null
  /** Callback após sucesso (pode recarregar contadores/alertas) */
  onSuccess?: () => void
}

/**
 * Modal de bloqueio/desbloqueio de usuário.
 * Opções:
 *   - 1h (temporário)
 *   - 24h (temporário)
 *   - Permanente
 *   - Desbloquear (se já bloqueado)
 *
 * Comportamento ao bloquear:
 *   - is_active = false (não loga)
 *   - login retorna 403 com detalhe do bloqueio
 *   - alertas em open/acknowledged viram resolved automaticamente
 */
export function BlockUserModal({ open, onClose, user, onSuccess }: BlockUserModalProps) {
  const [duration, setDuration] = useState<'1h' | '24h' | 'permanent' | 'unblock'>('24h')
  const [reason, setReason] = useState('')
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  if (!open || !user) return null

  const isCurrentlyBlocked = !!user.blocked_at

  const handleConfirm = async () => {
    setError(null)
    setSuccess(null)
    setWorking(true)
    try {
      await adminApi.blockUser(user.id, { duration, reason: reason || undefined })
      setSuccess(
        duration === 'unblock'
          ? '✅ Usuário desbloqueado.'
          : `✅ Bloqueado ${duration === '1h' ? 'por 1 hora' : duration === '24h' ? 'por 24 horas' : 'permanentemente'}.`
      )
      onSuccess?.()
      setTimeout(() => {
        onClose()
        // reseta state
        setReason('')
        setDuration('24h')
        setSuccess(null)
      }, 1000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao bloquear/desbloquear')
    } finally {
      setWorking(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={() => { if (!working) onClose() }}
    >
      <div
        className="w-full max-w-md rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        style={{
          background: '#0a0a0a',
          border: `1px solid ${isCurrentlyBlocked ? 'rgba(74,222,128,0.4)' : 'rgba(239,68,68,0.4)'}`,
          boxShadow: `0 0 40px ${isCurrentlyBlocked ? 'rgba(74,222,128,0.15)' : 'rgba(239,68,68,0.2)'}`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* HEADER */}
        <div
          className="flex items-center justify-between px-5 py-3 border-b"
          style={{ borderColor: '#1E1E2E' }}
        >
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{
                background: isCurrentlyBlocked
                  ? 'linear-gradient(135deg, #22C55E, #16A34A)'
                  : 'linear-gradient(135deg, #EF4444, #DC2626)',
              }}
            >
              {isCurrentlyBlocked
                ? <ShieldOff size={16} className="text-white" />
                : <Ban size={16} className="text-white" />
              }
            </div>
            <div>
              <h3 className="text-sm font-bold text-ayria-text">
                {isCurrentlyBlocked ? 'Desbloquear usuário' : 'Bloquear acesso'}
              </h3>
              <div className="text-[10px] text-ayria-muted truncate max-w-[260px]">
                {user.full_name || user.email}
              </div>
            </div>
          </div>
          <button
            onClick={() => { if (!working) onClose() }}
            className="p-1.5 rounded-lg hover:bg-white/5 text-ayria-muted hover:text-ayria-text"
            disabled={working}
          >
            <X size={16} />
          </button>
        </div>

        {/* BODY */}
        <div className="p-5 space-y-4">
          {/* Estado atual */}
          {isCurrentlyBlocked && (
            <div
              className="p-3 rounded-lg text-xs space-y-1"
              style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)' }}
            >
              <div className="font-bold text-red-300 flex items-center gap-1">
                <Shield size={12} />
                Já bloqueado
              </div>
              <div className="text-ayria-muted">
                {user.blocked_until ? (
                  <>Até <strong className="text-red-200">{new Date(user.blocked_until).toLocaleString('pt-BR')}</strong></>
                ) : (
                  <strong className="text-red-200">Permanentemente</strong>
                )}
              </div>
              {user.block_reason && (
                <div className="text-ayria-muted italic">"{user.block_reason}"</div>
              )}
            </div>
          )}

          {/* Escolha de duração */}
          {!isCurrentlyBlocked && (
            <>
              <div>
                <label className="block text-xs font-semibold text-ayria-text mb-2">
                  Duração do bloqueio
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={() => setDuration('1h')}
                    className="px-3 py-3 rounded-lg text-center transition-all"
                    style={{
                      background: duration === '1h' ? 'rgba(245,158,11,0.15)' : 'rgba(0,0,0,0.3)',
                      border: `1px solid ${duration === '1h' ? 'rgba(245,158,11,0.5)' : '#1E1E2E'}`,
                      color: duration === '1h' ? '#FBBF24' : '#94A3B8',
                    }}
                  >
                    <Clock size={14} className="mx-auto mb-1" />
                    <div className="text-xs font-bold">1 hora</div>
                  </button>
                  <button
                    onClick={() => setDuration('24h')}
                    className="px-3 py-3 rounded-lg text-center transition-all"
                    style={{
                      background: duration === '24h' ? 'rgba(239,68,68,0.15)' : 'rgba(0,0,0,0.3)',
                      border: `1px solid ${duration === '24h' ? 'rgba(239,68,68,0.5)' : '#1E1E2E'}`,
                      color: duration === '24h' ? '#FCA5A5' : '#94A3B8',
                    }}
                  >
                    <Clock size={14} className="mx-auto mb-1" />
                    <div className="text-xs font-bold">24 horas</div>
                  </button>
                  <button
                    onClick={() => setDuration('permanent')}
                    className="px-3 py-3 rounded-lg text-center transition-all"
                    style={{
                      background: duration === 'permanent' ? 'rgba(168,85,247,0.15)' : 'rgba(0,0,0,0.3)',
                      border: `1px solid ${duration === 'permanent' ? 'rgba(168,85,247,0.5)' : '#1E1E2E'}`,
                      color: duration === 'permanent' ? '#C084FC' : '#94A3B8',
                    }}
                  >
                    <Ban size={14} className="mx-auto mb-1" />
                    <div className="text-xs font-bold">Permanente</div>
                  </button>
                </div>
              </div>

              {/* Motivo */}
              <div>
                <label className="block text-xs font-semibold text-ayria-text mb-2">
                  Motivo (opcional)
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="ex: Reincidência em mensagens de risco Nível 1"
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg text-sm text-ayria-text outline-none"
                  style={{ background: '#050505', border: '1px solid #1E1E2E' }}
                />
              </div>

              <div
                className="p-3 rounded-lg text-[11px] text-ayria-muted space-y-1"
                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid #1E1E2E' }}
              >
                <div className="font-bold text-ayria-text">⏱️ Efeitos do bloqueio:</div>
                <div>• Login retorna <strong>403</strong> com mensagem do motivo</div>
                <div>• Não consegue enviar mensagens via <strong>/api/chat</strong></div>
                <div>• Alertas em aberto viram <strong>resolved</strong> automaticamente</div>
                <div>• Auto-desbloqueio quando a duração expirar</div>
              </div>
            </>
          )}

          {/* CONFIRMAÇÃO UNBLOCK */}
          {isCurrentlyBlocked && (
            <div
              className="p-3 rounded-lg text-xs text-ayria-muted"
              style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.3)' }}
            >
              <div className="font-bold text-green-300 mb-1">Após desbloquear:</div>
              <div>• User volta a conseguir logar</div>
              <div>• Pode enviar mensagens normalmente</div>
              <div>• is_active = true restaurado</div>
            </div>
          )}

          {error && (
            <div
              className="p-3 rounded-lg flex items-start gap-2 text-xs"
              style={{ background: 'rgba(239,68,68,0.1)', color: '#FCA5A5', border: '1px solid rgba(239,68,68,0.3)' }}
            >
              <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}
          {success && (
            <div
              className="p-3 rounded-lg flex items-start gap-2 text-xs"
              style={{ background: 'rgba(74,222,128,0.1)', color: '#86EFAC', border: '1px solid rgba(74,222,128,0.3)' }}
            >
              <CheckCircle2 size={14} className="flex-shrink-0 mt-0.5" />
              {success}
            </div>
          )}
        </div>

        {/* FOOTER */}
        <div
          className="flex items-center justify-end gap-2 px-5 py-3 border-t"
          style={{ borderColor: '#1E1E2E', background: 'rgba(0,0,0,0.3)' }}
        >
          <button
            onClick={() => { if (!working) onClose() }}
            disabled={working}
            className="px-4 py-2 rounded-lg text-xs font-medium text-ayria-muted hover:text-ayria-text"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            disabled={working}
            className="px-5 py-2 rounded-lg text-sm font-semibold text-white flex items-center gap-2 disabled:opacity-50"
            style={{
              background: isCurrentlyBlocked
                ? 'linear-gradient(135deg, #22C55E, #16A34A)'
                : duration === 'permanent'
                  ? 'linear-gradient(135deg, #A855F7, #6366F1)'
                  : duration === '24h'
                    ? 'linear-gradient(135deg, #EF4444, #DC2626)'
                    : 'linear-gradient(135deg, #F59E0B, #D97706)',
            }}
          >
            {working ? (
              <Loader2 size={14} className="animate-spin" />
            ) : isCurrentlyBlocked ? (
              <ShieldOff size={14} />
            ) : (
              <Ban size={14} />
            )}
            {working
              ? (isCurrentlyBlocked ? 'Desbloqueando...' : 'Bloqueando...')
              : (isCurrentlyBlocked ? 'Desbloquear' : 'Bloquear acesso')}
          </button>
        </div>
      </div>
    </div>
  )
}
