/**
 * AYRIA - Frontend Error Reporter (21/07/2026 00:35)
 *
 * Captura erros globais do browser e envia pro backend automaticamente.
 * Tolerante a falhas (se backend cair, não trava o front).
 *
 * Tipos:
 * - js_error: window.onerror / unhandledrejection
 * - axios_error: capturado pelo interceptor do api.ts
 * - react_error: ErrorBoundary (ver App.tsx se quiser)
 * - manual: chamar frontendErrors.report(msg) explicitamente
 */
const ENDPOINT = '/api/errors/frontend'
const BATCH_ENDPOINT = '/api/errors/frontend/batch'

interface ErrorReport {
  type: 'js_error' | 'axios_error' | 'react_error' | 'manual'
  message: string
  stack?: string
  url?: string
  user_agent?: string
  extra?: Record<string, any>
  timestamp?: string
}

const queue: ErrorReport[] = []
let flushing = false
let installed = false

function send(report: ErrorReport): Promise<boolean> {
  report.url = window.location.href
  report.user_agent = navigator.userAgent
  report.timestamp = report.timestamp || new Date().toISOString()

  // try fetch direto (tolerante a CORS porque endpoint não exige auth)
  return fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(report),
    // Não usar credentials — endpoint não exige e envia evita CORS preflight
    keepalive: true,
  })
    .then(r => r.ok)
    .catch(() => false)
}

export async function flushQueue() {
  if (flushing || queue.length === 0) return
  flushing = true
  const items = queue.splice(0, queue.length)
  try {
    await fetch(BATCH_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ errors: items }),
      keepalive: true,
    })
  } catch {
    // Re-enqueue if falhou
    queue.unshift(...items)
  } finally {
    flushing = false
  }
}

function enqueue(report: ErrorReport) {
  queue.push(report)
  if (queue.length >= 10) {
    void flushQueue()
  } else {
    setTimeout(flushQueue, 2000)
  }
}

export const frontendErrors = {
  report(message: string, extra?: Record<string, any>) {
    enqueue({
      type: 'manual',
      message,
      extra,
    })
  },

  reportError(e: unknown, type: ErrorReport['type'] = 'js_error', extra?: Record<string, any>) {
    if (!(e instanceof Error) && typeof e !== 'object') {
      enqueue({ type, message: String(e), extra })
      return
    }
    const err = e as Error
    enqueue({
      type,
      message: err.message || String(e),
      stack: err.stack,
      extra,
    })
  },

  install() {
    if (installed) return
    installed = true

    // 1. Capturar erro síncrono (window.onerror)
    window.addEventListener('error', (event) => {
      enqueue({
        type: 'js_error',
        message: event.message || 'Unknown error',
        stack: event.error?.stack,
        extra: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      })
    })

    // 2. Capturar promise rejeitada (unhandledrejection)
    window.addEventListener('unhandledrejection', (event) => {
      const reason = event.reason
      const message =
        reason instanceof Error ? reason.message :
        typeof reason === 'string' ? reason : JSON.stringify(reason)
      const stack = reason instanceof Error ? reason.stack : undefined
      enqueue({
        type: 'js_error',
        message: `[unhandledrejection] ${message}`,
        stack,
      })
    })

    // 3. Quando sair da página, tenta flush
    window.addEventListener('beforeunload', () => {
      void flushQueue()
    })

    // 4. Quando voltar online
    window.addEventListener('online', () => {
      void flushQueue()
    })

    // 5. Detectar online/offline
    window.addEventListener('offline', () => {
      frontendErrors.report('Frontend offline', { online: false })
    })
  },
}
