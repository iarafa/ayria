/**
 * AYRIA - Logo component
 *
 * - <Logo /> — logo + texto "AYRIA" em gradient (fallback ao wide)
 * - <LogoIcon variant="wide" /> — banner horizontal AYRIA+subtítulo (default p/ landing/login)
 * - <LogoIcon variant="symbol" /> — só símbolo circular neon, sem texto (sidebar)
 *
 * History:
 * 23/07/2026 — variant 'circular' foi introduzida apontando pro wide AYRIA-only.
 *              Login/Register/Onboarding/Numerology usam com size grande.
 * 26/07/2026 — Rafael pediu pra tirar texto AYRIA da sidebar. Adicionei variant
 *              'symbol' (quadrada, neon, sem texto) em vez de reapontar 'circular'
 *              (que quebraria o layout das outras páginas — tamanho vira width×width).
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
      <LogoIcon size={size} variant="wide" glow={glow} />
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
  variant?: 'plain' | 'wide' | 'circular' | 'symbol'
}

// Logo wide aspect ratio (1536 / 360) — inclui AYRIA + subtítulo + ornamento
const ASPECT_WIDE = 1536 / 360
// Logo circular quadrada (26/07/2026)
const ASPECT_SQUARE = 1

export function LogoIcon({ size = 40, glow = true, className = '', variant = 'plain' }: LogoIconProps) {
  const [err, setErr] = useState(false)

  // Glow: neon cyan/magenta p/ 'symbol'; branco+dourado p/ wide (original)
  const goldGlow = glow
    ? variant === 'symbol'
      ? 'drop-shadow(0 0 12px rgba(34,211,238,0.55)) drop-shadow(0 0 24px rgba(236,72,153,0.45)) drop-shadow(0 0 4px rgba(255,255,255,0.4))'
      : 'drop-shadow(0 0 20px rgba(255,255,255,0.85)) drop-shadow(0 0 40px rgba(255,255,255,0.5)) drop-shadow(0 0 8px rgba(241,201,97,0.9)) drop-shadow(0 0 18px rgba(218,149,11,0.5))'
    : undefined

  // Responsivo: limita largura em telas pequenas (mobile)
  const maxWidth = size >= 300 ? '90vw' : size >= 150 ? '70vw' : size >= 80 ? '50vw' : undefined

  // Wide (default histórico): size = LARGURA, altura proporcional
  // Symbol (26/07): quadrada, width = height = size
  const isSquare = variant === 'symbol'
  const width = size
  const height = isSquare ? size : Math.round(size / ASPECT_WIDE)

  // 'symbol' — só o símbolo neon circular, sem texto (sidebar)
  if (variant === 'symbol') {
    const v = '20260726a'  // cache-bust: symbol circular neon
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

  // 'wide' (novo nome, sinônimo do antigo 'circular' que era wide) — banner AYRIA + subtítulo
  // 'plain' (legacy default) — idem
  const wideSrc = '/ayria-logo-lovable.png'
  const wideV = '20260723b'

  return (
    <img
      src={`${err ? wideSrc : wideSrc}?v=${wideV}`}
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
