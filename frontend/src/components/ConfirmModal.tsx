/**
 * AYRIA - Modal de Confirmação
 *
 * Substitui `confirm()` do navegador por um popup in-app (mais íntimo).
 * Usado em: deletar conversa, deletar módulo, etc.
 */
import { useEffect } from 'react'
import { X, AlertTriangle } from 'lucide-react'

interface ConfirmModalProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void | Promise<void>
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'info'
  working?: boolean
}

export function ConfirmModal({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirmar',
  cancelText = 'Cancelar',
  variant = 'danger',
  working = false,
}: ConfirmModalProps) {
  // ESC fecha
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const colors = {
    danger: {
      bg: 'rgba(239, 68, 68, 0.08)',
      border: 'rgba(239, 68, 68, 0.4)',
      icon: 'text-red-400',
      iconBg: 'bg-red-900/30',
      button: 'bg-red-600 hover:bg-red-500',
    },
    warning: {
      bg: 'rgba(245, 158, 11, 0.08)',
      border: 'rgba(245, 158, 11, 0.4)',
      icon: 'text-amber-400',
      iconBg: 'bg-amber-900/30',
      button: 'bg-amber-600 hover:bg-amber-500',
    },
    info: {
      bg: 'rgba(99, 102, 241, 0.08)',
      border: 'rgba(99, 102, 241, 0.4)',
      icon: 'text-indigo-400',
      iconBg: 'bg-indigo-900/30',
      button: 'bg-indigo-600 hover:bg-indigo-500',
    },
  }[variant]

  const handleConfirm = async () => {
    await onConfirm()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-ayria-surface rounded-2xl shadow-2xl w-full max-w-md border border-ayria-border"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-ayria-border">
          <div className="flex items-center gap-2">
            <div className={`w-9 h-9 rounded-full ${colors.iconBg} flex items-center justify-center`}>
              <AlertTriangle size={18} className={colors.icon} />
            </div>
            <h2 className="text-base font-bold text-ayria-text">{title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-ayria-bg transition"
            aria-label="Fechar"
          >
            <X size={20} className="text-ayria-muted" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5">
          <p className="text-sm text-ayria-muted leading-relaxed whitespace-pre-line">
            {message}
          </p>
        </div>

        {/* Footer */}
        <div className="flex gap-2 p-4 border-t border-ayria-border">
          <button
            type="button"
            onClick={onClose}
            disabled={working}
            className="flex-1 px-4 py-2 rounded-lg border border-ayria-border text-ayria-muted hover:bg-ayria-bg transition disabled:opacity-50"
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={working}
            className={`flex-1 px-4 py-2 rounded-lg text-white font-medium transition disabled:opacity-50 ${colors.button}`}
          >
            {working ? 'Processando...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}