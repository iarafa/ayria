/**
 * AYRIA - UserAvatar
 *
 * Mostra a foto do usuário (avatar_url) com fallback automático:
 * 1. Se tem avatar_url → mostra a foto
 * 2. Se não tem → mostra a inicial do nome (gradient circle)
 */
import { useState } from 'react'

interface UserAvatarProps {
  src?: string | null
  name?: string | null
  email?: string | null
  size?: number
  className?: string
  glow?: boolean
  onClick?: () => void
}

export function UserAvatar({
  src,
  name,
  email,
  size = 40,
  className = '',
  glow = true,
  onClick,
}: UserAvatarProps) {
  const [err, setErr] = useState(false)

  // Determina texto da inicial
  const initial = (() => {
    if (name && name.trim()) {
      const parts = name.trim().split(/\s+/)
      if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      }
      return name[0].toUpperCase()
    }
    if (email && email.trim()) {
      return email[0].toUpperCase()
    }
    return '?'
  })()

  const showImage = src && !err

  return (
    <div
      className={className}
      onClick={onClick}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: showImage
          ? 'transparent'
          : 'linear-gradient(135deg, #6366F1, #A855F7)',
        boxShadow: glow
          ? '0 0 12px rgba(99, 102, 241, 0.4)'
          : 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        overflow: 'hidden',
        cursor: onClick ? 'pointer' : 'default',
        border: '2px solid rgba(99, 102, 241, 0.3)',
        userSelect: 'none',
      }}
    >
      {showImage ? (
        <img
          src={src}
          alt={name || email || 'avatar'}
          onError={() => setErr(true)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      ) : (
        <span
          style={{
            color: '#fff',
            fontWeight: 700,
            fontSize: size * 0.4,
            letterSpacing: '0.05em',
          }}
        >
          {initial}
        </span>
      )}
    </div>
  )
}