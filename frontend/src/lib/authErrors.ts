/**
 * AYRIA - auth errors helper (20/07/2026 — REFATORADO)
 *
 * Esta versão classifica o erro de forma CIRÚRGICA e retorna um objeto
 * tipado (não só string) pra UI ter controle.
 *
 * Tipos detectados:
 *   - canceled  : axios cancelou (saiu da página, navegação)
 *   - offline   : navigator.onLine === false (sem WiFi/4G)
 *   - timeout   : ECONNABORTED ou message=timeout
 *   - network   : ERR_NETWORK (axios não recebeu response, causa raiz opaca)
 *                 ↳ Pode ser: CORS, DNS, hairpin NAT, drop no proxy, etc
 *   - http_5xx  : servidor respondeu 5xx (problema interno real)
 *   - http_4xx  : servidor respondeu 4xx (validação / token ruim)
 *   - unknown   : fallback
 *
 * Renderização fica em <AuthErrorBox> (com botão "Copiar diagnóstico").
 */

type Action = 'envio' | 'redefinição' | 'login' | 'cadastro'
export type { Action }

export interface AuthError {
  type:
    | 'canceled'
    | 'offline'
    | 'timeout'
    | 'network'
    | 'http_5xx'
    | 'http_4xx'
    | 'unknown'
  message: string
  hint?: string
}

/** Verbo padrão pra mensagem de fallback quando não temos response do servidor. */
function verbFor(action: Action): string {
  switch (action) {
    case 'envio': return 'enviar'
    case 'redefinição': return 'redefinir'
    case 'login': return 'entrar'
    case 'cadastro': return 'cadastrar'
  }
}

export function classifyAuthError(e: any, action: Action): AuthError {
  // 0. Cancelamento explícito
  if (e?.code === 'ERR_CANCELED' || /aborted/i.test(e?.message || '')) {
    return {
      type: 'canceled',
      message: 'A requisição foi cancelada.',
    }
  }

  // 1. Sem internet no navegador
  if (typeof navigator !== 'undefined' && navigator.onLine === false) {
    return {
      type: 'offline',
      message: 'Você está sem internet.',
      hint: 'Conecte-se numa rede Wi-Fi ou use dados móveis, depois tente de novo.',
    }
  }

  // 2. SEM response = axios morreu antes do servidor responder
  if (!e?.response) {
    const axiosMsg: string = e?.message || ''
    const verb = verbFor(action)

    // 2a. Timeout puro
    if (e?.code === 'ECONNABORTED' || /timeout/i.test(axiosMsg)) {
      return {
        type: 'timeout',
        message: 'O servidor demorou pra responder.',
        hint: `Pode ser conexão lenta. Tente ${verb} de novo em alguns segundos.`,
      }
    }

    // 2b. ERR_NETWORK — motivo raiz opaco pra gente (axios só sabe que
    //     o request morreu; a causa real pode ser CORS, DNS, NAT, drop, proxy corporativo…)
    if (e?.code === 'ERR_NETWORK' || /network error/i.test(axiosMsg)) {
      return {
        type: 'network',
        message: 'Não conseguimos alcançar o servidor agora.',
        hint:
          `O servidor pode estar reiniciando ou sua rede/proxy pode estar bloqueando. ` +
          `Tente ${verb} de novo em alguns segundos. ` +
          `Se o problema persistir, copie o diagnóstico pro suporte.`,
      }
    }

    // 2c. Fallback (sem response, sem code reconhecível)
    return {
      type: 'network',
      message: `Não foi possível ${verb} agora.`,
      hint: 'Tente de novo em alguns segundos.',
    }
  }

  // 3. COM response = servidor respondeu (mesmo que com erro)
  const status: number = e.response.status
  const detail = e?.response?.data?.detail
  const detailFromArray = Array.isArray(detail) ? detail[0]?.msg : undefined
  const backendMsg = detailFromArray || (typeof detail === 'string' ? detail : null)

  // 3a. 5xx = problema do servidor
  if (status >= 500 && status <= 599) {
    return {
      type: 'http_5xx',
      message: `Erro interno do servidor (HTTP ${status}).`,
      hint: 'Tente de novo em alguns segundos.',
    }
  }

  // 3b. 4xx = problema do cliente
  switch (status) {
    case 400:
      return {
        type: 'http_4xx',
        message: backendMsg || 'Dados inválidos. Confira os campos e tente de novo.',
      }
    case 401:
      // 401 em /login ou /register = credenciais erradas (não sessão expirada)
      if (action === 'login' || action === 'cadastro') {
        return {
          type: 'http_4xx',
          message: backendMsg || 'Email ou senha inválidos.',
          hint: 'Confira email e senha e tente de novo.',
        }
      }
      // 401 em qualquer outro contexto (refresh, me, etc) = sessão expirada
      return {
        type: 'http_4xx',
        message: 'Sua sessão expirou.',
        hint: 'Faça login de novo.',
      }
    case 404:
      return {
        type: 'http_4xx',
        message: 'Token inválido ou já utilizado.',
        hint: 'Solicite um novo link de redefinição.',
      }
    case 410:
      return {
        type: 'http_4xx',
        message: 'Link de redefinição expirado.',
        hint: 'Links duram 1 hora. Solicite um novo.',
      }
    case 422: {
      // Validação Pydantic — backendMsg geralmente tem a regra específica
      // (ex: "senha: ensure this value has at least 8 characters")
      const clean = (backendMsg || '').replace(/^Value error,\s*/i, '')
      return {
        type: 'http_4xx',
        message: clean || 'Senha precisa ter no mínimo 8 caracteres.',
      }
    }
    case 429:
      return {
        type: 'http_4xx',
        message: 'Muitas tentativas em pouco tempo.',
        hint: 'Aguarde alguns minutos e tente de novo.',
      }
    default:
      if (backendMsg) {
        return { type: 'http_4xx', message: backendMsg }
      }
      const verb = action === 'envio' ? 'enviar o email' : 'redefinir a senha'
      return {
        type: 'unknown',
        message: `Não foi possível ${verb} agora (HTTP ${status}).`,
        hint: 'Tente de novo.',
      }
  }
}

/** Helper legado — só pra manter chamadas antigas funcionando */
export function formatAuthError(e: any, action: Action): string {
  return classifyAuthError(e, action).message
}

/** Monta o payload de diagnóstico que o <AuthErrorBox> copia pro clipboard */
export function buildAuthDiagnostic(e: any, action: Action, context?: Record<string, any>) {
  const cls = classifyAuthError(e, action)
  return {
    classificacao: cls.type,
    mensagem: cls.message,
    axiosCode: e?.code ?? null,
    axiosMessage: e?.message ?? null,
    responseStatus: e?.response?.status ?? null,
    responseData: e?.response?.data ?? null,
    requestUrl: e?.config?.url ?? null,
    requestMethod: e?.config?.method?.toUpperCase() ?? null,
    requestBaseURL: e?.config?.baseURL ?? null,
    navigator_onLine: typeof navigator !== 'undefined' ? navigator.onLine : null,
    pagina_origem: typeof window !== 'undefined' ? window.location.href : null,
    user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
    timestamp: new Date().toISOString(),
    ...context,
  }
}
