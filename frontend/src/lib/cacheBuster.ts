/**
 * AYRIA - Cache Buster
 *
 * Garante que QUALQUER mudança de código limpa o localStorage e força
 * novo login. Sem isso, mudanças em stores/types quebram silenciosamente
 * porque dados antigos persistem no navegador.
 *
 * - BUILD_VERSION: muda em CADA deploy (alterar manualmente)
 * - No boot: se versão salva ≠ versão atual → limpa TUDO e reload
 */

// IMPORTANTE: incrementar este número em CADA mudança significativa de código
const BUILD_VERSION = '2026-06-29-13-05'  // YYYY-MM-DD-HH-MM

const VERSION_KEY = 'ayria:build-version'

export function checkCacheBust(): void {
  if (typeof window === 'undefined') return

  const savedVersion = localStorage.getItem(VERSION_KEY)

  if (savedVersion !== BUILD_VERSION) {
    console.log(`🔄 [CacheBust] Versão mudou: ${savedVersion} → ${BUILD_VERSION}`)
    console.log('🔄 [CacheBust] Limpando localStorage...')

    // Limpa TUDO: tokens, dados de user, preferências
    localStorage.clear()

    // Salva a nova versão
    localStorage.setItem(VERSION_KEY, BUILD_VERSION)

    console.log('🔄 [CacheBust] Reload forçado')

    // Hard reload pra garantir que JS novo é carregado
    window.location.reload()
  }
}
