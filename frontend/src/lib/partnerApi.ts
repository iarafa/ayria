/**
 * AYRIA - API Client para PARCEIROS (axios instance SEM auth de user)
 *
 * 🆕 26/07/2026 23:30 — Instância SEPARADA porque o interceptor de
 * `api.ts` sempre injeta `Authorization: Bearer <ayria_token>` (token de user/admin)
 * em TODA requisição, sobrescrevendo o header Authorization explícito da chamada.
 *
 * Resultado: parceiro logado tentava `api.post('/api/partner/...', ...,
 * {headers:{Authorization:'Bearer <partner_token>'}})` → interceptor sobrescrevia
 * com token de admin → backend rejeitava com 401 "Token não é de parceiro".
 *
 * Esta instância NÃO tem o interceptor de user-token, então o header Authorization
 * explícito da chamada é respeitado.
 */
import axios from 'axios'
import { logError } from './logClient'

const API_URL = import.meta.env.VITE_API_URL || ''

export const partnerApi = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Sem interceptor de Authorization — quem chama passa o header explicitamente
// (PartnerLoginPage: usa o Authorization pra trocar senha).
//
// Mas se no futuro o backend emitir 401, ainda logamos no logClient.
partnerApi.interceptors.response.use(
  (response) => response,
  (error) => {
    logError(
      'partnerApi',
      `${error.config?.method?.toUpperCase() || ''} ${error.config?.url || ''}`,
      error.message,
      {
        status: error.response?.status,
        data: error.response?.data,
      },
    )
    return Promise.reject(error)
  }
)