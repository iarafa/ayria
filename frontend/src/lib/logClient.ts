/**
 * AYRIA - Frontend Log Client
 *
 * Captura erros do frontend e envia pro backend gravar no log.
 * Assim o módulo `logs` da ALMA vê TUDO: backend + frontend.
 *
 * Uso:
 *   import { logError, logWarn, logInfo } from '../lib/logClient'
 *   logError('ChatPage', 'sendMessage', 'API retornou 500', { chatId: 123 })
 *
 * Tudo é fire-and-forget — não bloqueia UI.
 */

const LOG_ENDPOINT = '/api/admin/log/event'
const MAX_QUEUE_SIZE = 50  // não acumula infinito se backend offline

let queue: Array<{
  level: 'error' | 'warn' | 'info'
  source: string
  context: string
  message: string
  data?: any
  url?: string
}> = []
let flushing = false

function flush() {
  if (flushing || queue.length === 0) return
  flushing = true

  const batch = queue.splice(0, MAX_QUEUE_SIZE)
  const token = localStorage.getItem('ayria_token') || ''

  fetch(LOG_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      level: batch[0].level,
      source: batch[0].source,
      context: batch[0].context,
      message: batch[0].message,
      data: batch[0].data ? { batch_size: batch.length, items: batch } : undefined,
      url: window.location.href,
      user_agent: navigator.userAgent,
    }),
    keepalive: true,
  })
    .catch(() => {
      // Backend offline — descarta silenciosamente (não enche console)
    })
    .finally(() => {
      flushing = false
      // Se encheu a fila de novo, agenda próximo flush
      if (queue.length > 0) setTimeout(flush, 1000)
    })
}

function push(level: 'error' | 'warn' | 'info', source: string, context: string, message: string, data?: any) {
  queue.push({ level, source, context, message, data })
  if (queue.length > MAX_QUEUE_SIZE) queue.shift()  // descarta o mais antigo
  // Debounce 300ms — junta rajadas
  setTimeout(flush, 300)
}

export function logError(source: string, context: string, message: string, data?: any) {
  push('error', source, context, message, data)
}

export function logWarn(source: string, context: string, message: string, data?: any) {
  push('warn', source, context, message, data)
}

export function logInfo(source: string, context: string, message: string, data?: any) {
  push('info', source, context, message, data)
}

// Captura erros globais não-tratados (window.onerror, unhandledrejection)
window.addEventListener('error', (e) => {
  logError('window', 'onerror', e.message || 'Erro JS não-tratado', {
    filename: e.filename,
    lineno: e.lineno,
    colno: e.colno,
    stack: e.error?.stack,
  })
})

window.addEventListener('unhandledrejection', (e) => {
  const reason = e.reason
  logError('window', 'unhandledrejection', reason?.message || String(reason), {
    stack: reason?.stack,
    name: reason?.name,
  })
})