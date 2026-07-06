/**
 * useAutoScroll — Hook para autoscroll inteligente em containers de chat.
 *
 * Comportamento:
 * - Detecta se o usuário está "no fundo" do container (com tolerância)
 * - Quando `trigger` muda E o usuário tava no fundo → faz autoscroll
 * - Quando o usuário rola manualmente pra cima → NÃO força scroll
 *   (respeita o que ele quer ler)
 *
 * Uso típico:
 *   const containerRef = useRef<HTMLDivElement>(null)
 *   const { scrollToBottomIfAtBottom, scrollToBottomInstant } = useAutoScroll(containerRef)
 *
 *   // Quando TypingIndicator aparece:
 *   scrollToBottomInstant()
 *
 *   // Quando nova mensagem chega:
 *   scrollToBottomIfAtBottom()
 *
 * Tolerância padrão: 100px (considera "no fundo" se scrollTop + clientHeight
 * está a até 100px do scrollHeight)
 */
import { useCallback, useEffect, useRef } from 'react'

const DEFAULT_BOTTOM_TOLERANCE_PX = 100

export function useAutoScroll<T extends HTMLElement>(
  containerRef: React.RefObject<T>,
  options: { tolerancePx?: number } = {}
) {
  const { tolerancePx = DEFAULT_BOTTOM_TOLERANCE_PX } = options

  // Guarda se o usuário tá no fundo
  const isAtBottomRef = useRef(true)

  // Listener pra detectar scroll manual do usuário
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight
      isAtBottomRef.current = distanceFromBottom <= tolerancePx
    }

    container.addEventListener('scroll', handleScroll, { passive: true })
    // Inicializa
    handleScroll()

    return () => container.removeEventListener('scroll', handleScroll)
  }, [containerRef, tolerancePx])

  // Scroll SUAVE até o fim (só faz se o usuário tava no fundo)
  const scrollToBottomIfAtBottom = useCallback(() => {
    const container = containerRef.current
    if (!container) return
    if (!isAtBottomRef.current) return // usuário tá lendo em cima, não rola
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth',
    })
  }, [containerRef])

  // Scroll INSTANTÂNEO até o fim (sempre rola — use pra TypingIndicator)
  const scrollToBottomInstant = useCallback(() => {
    const container = containerRef.current
    if (!container) return
    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'auto',
    })
    // Marca como "no fundo" depois de rolar
    isAtBottomRef.current = true
  }, [containerRef])

  return {
    scrollToBottomIfAtBottom,
    scrollToBottomInstant,
    isAtBottom: isAtBottomRef.current,
  }
}