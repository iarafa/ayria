/**
 * admin/tabs/UserHeader.tsx — Header do modal de detalhes do user
 * Avatar grande + identidade + badges + ação "Observar"
 */
import React from 'react'
import { Shield, Star, CheckCircle2, AlertCircle, Eye, ExternalLink, Calendar, User } from 'lucide-react'
import { Badge } from './helpers'

export function UserHeader({ data, onClose, navigate }: {
  data: any
  onClose: () => void
  navigate: any
}) {
  const initials = (data.full_name || data.email || '?')
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s.charAt(0).toUpperCase())
    .join('')

  const planColor =
    data.selected_plan_slug === 'premium' ? '#F59E0B' :
    data.selected_plan_slug === 'intermediario' ? '#da950b' :
    '#f1c961'

  const onboardingColors: Record<string, string> = {
    completed: '#10B981',
    in_progress: '#F59E0B',
    pending: '#94A3B8',
    skipped: '#64748B',
  }
  const obColor = onboardingColors[data.onboarding_status] || '#94A3B8'

  return (
    <div
      className="rounded-2xl p-5 sm:p-6"
      style={{
        background: 'linear-gradient(135deg, rgba(241,201,97,0.10), rgba(218,149,11,0.10))',
        border: '1px solid rgba(99, 102, 241, 0.3)',
      }}
    >
      <div className="flex items-start gap-4">
        {data.avatar_url ? (
          <img src={data.avatar_url} alt="avatar" className="w-16 h-16 sm:w-20 sm:h-20 rounded-full object-cover flex-shrink-0" onError={(e) => (e.currentTarget.style.display = 'none')} />
        ) : (
          <div
            className="w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center font-bold text-2xl flex-shrink-0"
            style={{
              background: `linear-gradient(135deg, ${planColor}, #da950b)`,
              color: '#FFFFFF',
            }}
          >
            {initials}
          </div>
        )}

        <div className="flex-1 min-w-0">
          <h3 className="text-xl sm:text-2xl font-bold text-ayria-text truncate">
            {data.full_name || data.email}
          </h3>
          <div className="text-sm text-ayria-muted truncate mt-0.5">{data.email}</div>

          <div className="flex flex-wrap gap-2 mt-3">
            {data.role && (
              <Badge color="#da950b" icon={<Shield size={11} />}>
                {data.role}
              </Badge>
            )}
            {data.selected_plan_name ? (
              <Badge color={planColor} icon={<Star size={11} />}>
                {data.selected_plan_name}
              </Badge>
            ) : (
              <Badge color="#64748B">Sem plano</Badge>
            )}
            <Badge color={obColor} icon={<CheckCircle2 size={11} />}>
              Onboarding: {data.onboarding_status || '-'}
            </Badge>
            {data.is_active ? (
              <Badge color="#10B981" icon={<CheckCircle2 size={11} />}>Ativo</Badge>
            ) : (
              <Badge color="#EF4444" icon={<AlertCircle size={11} />}>Inativo</Badge>
            )}
          </div>
        </div>

        {data?.id && (
          <button
            onClick={() => navigate(`/admin/observe/${data.id}`)}
            className="flex-shrink-0 px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 text-white shadow-lg hover:scale-105 transition-transform"
            style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}
            title="Abrir modo observador (read-only, auditado)"
          >
            <Eye size={14} />
            <span className="hidden sm:inline">Observar</span>
            <ExternalLink size={11} />
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-ayria-muted mt-4 pt-4 border-t" style={{ borderColor: 'rgba(99, 102, 241, 0.2)' }}>
        <span><Calendar size={11} className="inline mr-1" />Cadastrado em {data.created_at ? new Date(data.created_at).toLocaleDateString('pt-BR') : '-'}</span>
        <span><User size={11} className="inline mr-1" />Último login {data.last_login_at ? new Date(data.last_login_at).toLocaleString('pt-BR') : 'nunca'}</span>
      </div>
    </div>
  )
}
