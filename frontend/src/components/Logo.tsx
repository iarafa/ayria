/**
 * AYRIA - Logo component
 *
 * Visual alinhado com a landing Lovable:
 * - Logo wordmark "AYRIA" com fundo transparente
 * - Texto "AYRIA" do Logo em serif (Cormorant Garamond)
 *
 * Logo wide (aspect 1536:220 ≈ 7:1) — apenas o wordmark,
 * sem o subtítulo "CLAREZA PRA DECIDIR" (que é redundante com H1 da página).
 *
 * - <Logo /> — logo + texto "AYRIA" em gradient
 * - <LogoIcon variant="circular" /> — só PNG do logo wide
 */
import { useState } from 'react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  glow?: boolean
}

export function Logo({ size = 48, showText = true, className = '', glow = true }: LogoProps) {
  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <LogoIcon size={size} variant="circular" glow={glow} />
      {showText && (
        <span
          className="font-display font-medium tracking-[0.25em] gradient-text"
          style={{ fontSize: size * 0.14 }}
        >
          AYRIA
        </span>
      )}
    </div>
  )
}

interface LogoIconProps {
  size?: number
  glow?: boolean
  className?: string
  variant?: 'plain' | 'circular' | 'square'
}

// Logo wide aspect ratio (1536 / 360) — inclui AYRIA + subtítulo + ornamento
// (23/07/2026: Rafael pediu pra restaurar o subtítulo que eu tinha cortado)
const ASPECT_WIDE = 1536 / 360
// Logo circular quadrada (26/07/2026: Rafael pediu pra tirar texto AYRIA + melhorar logo)
const ASPECT_SQUARE = 1

export function LogoIcon({ size = 40, glow = true, className = '', variant = 'plain' }: LogoIconProps) {
  const [err, setErr] = useState(false)

  // Glow branco ATRÁS + dourado no contorno (Rafael 25/07: logo ilegível, precisa esfumaçar branco atrás)
  // 'square' usa glow neon (cyan/magenta) que combina com a imagem circular
  const goldGlow = glow
    ? variant === 'square'
      ? 'drop-shadow(0 0 12px rgba(34,211,238,0.55)) drop-shadow(0 0 24px rgba(236,72,153,0.45)) drop-shadow(0 0 4px rgba(255,255,255,0.4))'
      : 'drop-shadow(0 0 20px rgba(255,255,255,0.85)) drop-shadow(0 0 40px rgba(255,255,255,0.5)) drop-shadow(0 0 8px rgba(241,201,97,0.9)) drop-shadow(0 0 18px rgba(218,149,11,0.5))'
    : undefined

  // Responsivo: limita largura em telas pequenas (mobile)
  const maxWidth = size >= 300 ? '90vw' : size >= 150 ? '70vw' : size >= 80 ? '50vw' : undefined

  // Wide: size = LARGURA. Altura proporcional (size / ~4.27)
  // Square: width = height = size
  const width = variant === 'square' ? size : size
  const height = variant === 'square' ? size : Math.round(size / ASPECT_WIDE)

  // 'square' = logo circular (sem texto AYRIA, neon) — 26/07/2026 Rafael pediu
  if (variant === 'square') {
    const v = '20260726a'  // cache-bust: square circular neon
    return (
      <img
        src={`/ayria-logo-circular.png?v=${v}`}
        alt="AYRIA"
        width={width}
        height={height}
        className={className}
        style={{
          display: 'block',
          width,
          height,
          maxWidth,
          objectFit: 'contain',
          filter: goldGlow,
        }}
        onError={() => setErr(true)}
      />
    )
  }

  if (variant === 'circular') {
    const v = '20260723b'  // cache-bust: wide AYRIA-only
    return (
      <img
        src={`${err ? '/ayria-logo-lovable.png' : '/ayria-logo-lovable.png'}?v=${v}`}
        alt="AYRIA"
        width={width}
        height={height}
        className={className}
        style={{
          display: 'block',
          width,
          height,
          maxWidth,
          objectFit: 'contain',
          filter: goldGlow,
        }}
        onError={() => setErr(true)}
      />
    )
  }

  return (
    <img
      src={`${err ? '/ayria-logo-lovable.png' : '/ayria-logo-lovable.png'}?v=20260723b`}
      alt="AYRIA"
      width={width}
      height={height}
      className={className}
      style={{
        display: 'block',
        maxWidth,
        filter: goldGlow,
      }}
      onError={() => setErr(true)}
    />
  )
}
