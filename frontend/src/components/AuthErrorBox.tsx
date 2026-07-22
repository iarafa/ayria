/**
 * AYRIA - AuthErrorBox (20/07/2026)
 *
 * Mostra erros de auth (forgot/reset password) com diagnóstico útil:
 * - Status HTTP
 * - URL que falhou
 * - Mensagem específica por status (400/401/404/410/422/429/500/502/503/504)
 *
 * Renderiza como um box com cor por severidade.
 */
import type { ReactNode } from 'react'

interface AxiosLikeError {
  message?: string
  response?: {
    status?: number
    data?: { detail?: string; [k: string]: unknown }
  }
  config?: { url?: string }
  code?: string
}

function describe(e: unknown, action: 'envio' | 'redefinição'): {
  title: string
  body: ReactNode
  severity: 'warn' | 'error' | 'info'
} {
  const err = e as AxiosLikeError
  const status = err?.response?.status
  const detail = err?.response?.data?.detail
  const url = err?.config?.url

  // Network puro (sem response)
  if (!status && err?.message) {
    return {
      title: 'Sem conexão com o servidor',
      body: (
        <>
          Não conseguimos falar com o servidor agora. Ele pode estar reiniciando — tente{' '}
          {action === 'envio' ? 'enviar' : 'redefinir'} de novo em alguns segundos.
          <div className="mt-2 text-xs text-ayria-muted">{err.message}</div>
        </>
      ),
      severity: 'warn',
    }
  }

  switch (status) {
    case 400:
      return {
        title: 'Dados inválidos',
        body: (
          <>
            {detail || 'Revise os campos e tente de novo.'}
            {url && <div className="mt-2 text-xs text-ayria-muted">{url}</div>}
          </>
        ),
        severity: 'warn',
      }
    case 401:
      return {
        title: 'Não autorizado',
        body: <>Sua sessão pode ter expirado. Faça login de novo e tente {action === 'envio' ? 'enviar' : 'redefinir'}.</>,
        severity: 'warn',
      }
    case 404:
      return {
        title: action === 'envio' ? 'Email não cadastrado' : 'Link inválido',
        body: (
          <>
            {detail ||
              (action === 'envio'
                ? 'Esse email não está cadastrado. Confira e tente de novo.'
                : 'Este link de redefinição não existe ou já foi usado.')}
          </>
        ),
        severity: 'warn',
      }
    case 410:
      return {
        title: 'Link expirado',
        body: 'O link de redefinição venceu. Peça um novo e use em até 1 hora.',
        severity: 'warn',
      }
    case 422:
      return {
        title: 'Senha não atende os requisitos',
        body: <>A senha precisa ter pelo menos 8 caracteres.</>,
        severity: 'warn',
      }
    case 429:
      return {
        title: 'Muitas tentativas',
        body: 'Aguarde alguns minutos antes de tentar de novo.',
        severity: 'warn',
      }
    case 500:
    case 502:
    case 503:
    case 504:
      return {
        title: 'Erro no servidor',
        body: (
          <>
            Tivemos um problema técnico. Tente de novo em alguns minutos.
            {detail && <div className="mt-2 text-xs text-ayria-muted">{detail}</div>}
          </>
        ),
        severity: 'error',
      }
    default:
      return {
        title: 'Algo deu errado',
        body: <>{detail || err?.message || 'Tente de novo em alguns segundos.'}</>,
        severity: 'error',
      }
  }
}

export function AuthErrorBox({
  error,
  action,
}: {
  error: unknown
  action: 'envio' | 'redefinição'
  context?: Record<string, unknown>
}) {
  if (!error) return null
  const d = describe(error, action)
  const bg =
    d.severity === 'warn'
      ? 'rgba(245, 158, 11, 0.10)'
      : 'rgba(239, 68, 68, 0.10)'
  const fg = d.severity === 'warn' ? '#F59E0B' : '#EF4444'
  return (
    <div
      role="alert"
      className="mt-3 p-3 rounded-xl text-sm"
      style={{ background: bg, color: fg, border: `1px solid ${fg}55` }}
    >
      <div className="font-semibold">{d.title}</div>
      <div className="mt-1">{d.body}</div>
    </div>
  )
}
