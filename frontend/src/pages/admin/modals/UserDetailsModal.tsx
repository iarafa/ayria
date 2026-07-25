/**
 * admin/modals/UserDetailsModal.tsx — Modal completo de detalhes do usuário
 * Mostra: header, stats, visão geral, onboarding, numerologia, astrologia, atributos dinâmicos.
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, Eye, ExternalLink, MessageCircle, MessageSquare, Wallet, Receipt, Shield, ClipboardList, Sparkles, Star, Tag, Calendar, Clock, MapPin, User, Calculator, Briefcase } from 'lucide-react'
import { Section, Field, StatCard, DataRow, EmptyState, NumberCard, PlanetCard, humanizeKey, formatValue, capitalize } from '../tabs/helpers'
import { UserHeader } from '../tabs/UserHeader'

export function UserDetailsModal({ userId, data, loading, onClose }: {
  userId: string | null
  data: any
  loading: boolean
  onClose: () => void
}) {
  const navigate = useNavigate()
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    basics: true, onboarding: true, numerology: true, astrology: true,
    dynamic: false, stats: true,
  })

  const toggle = (k: string) => setExpandedSections((s) => ({ ...s, [k]: !s[k] }))

  if (!userId) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center px-4 py-8 overflow-y-auto"
      style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(6px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl rounded-2xl p-6 my-auto"
        style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-ayria-border">
          <div>
            <h2 className="text-2xl font-bold gradient-text">
              {data?.full_name || data?.email || 'Detalhes do usuário'}
            </h2>
            <div className="text-xs text-ayria-muted mt-1">
              {data?.email} · {data?.role}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {userId && (
              <button
                onClick={() => navigate(`/admin/observe/${userId}`)}
                className="px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 text-white"
                style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}
                title="Abrir modo observador (read-only, auditado) - mesma aba"
              >
                <Eye size={14} />
                Modo Observador
                <ExternalLink size={11} />
              </button>
            )}
            <button onClick={onClose} className="text-ayria-muted hover:text-white">
              <X size={24} />
            </button>
          </div>
        </div>

        {loading || !data ? (
          <div className="py-12 text-center text-ayria-muted">Carregando detalhes...</div>
        ) : (
          <div className="space-y-5">
            <UserHeader data={data} onClose={onClose} navigate={navigate} />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard
                icon={<MessageCircle size={18} />}
                label="Chats"
                value={data.chats_count || 0}
                color="#da950b"
              />
              <StatCard
                icon={<MessageSquare size={18} />}
                label="Mensagens"
                value={data.message_count || 0}
                color="#f1c961"
              />
              <StatCard
                icon={<Wallet size={18} />}
                label="Saldo"
                value={`${(data.credit_balance || 0).toLocaleString('pt-BR')}`}
                subtitle="créditos"
                color={data.credit_balance > 0 ? '#10B981' : '#EF4444'}
              />
              <StatCard
                icon={<Receipt size={18} />}
                label="Transações"
                value={data.credit_transactions_count || 0}
                color="#F59E0B"
              />
            </div>

            <Section title="Visão geral" icon={<Shield size={16} />} expanded={expandedSections.basics} onToggle={() => toggle('basics')}>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-4">
                <Field label="Plano" value={data.selected_plan_name || '- sem plano -'} highlight={!!data.selected_plan_slug} />
                <Field label="Status onboarding" value={data.onboarding_status} highlight={data.onboarding_status === 'completed' ? 'success' : 'danger'} />
                <Field label="Status perfil" value={data.profile_status || '-'} />
                <Field label="Role" value={data.role} highlight={data.role === 'SUPER_ADMIN' || data.role === 'admin'} />
                <Field label="Conta ativa" value={data.is_active ? 'Sim' : 'Não'} highlight={data.is_active ? 'success' : 'danger'} />
                <Field label="Cadastro" value={data.created_at ? new Date(data.created_at).toLocaleDateString('pt-BR') : '-'} />
                <Field label="Último login" value={data.last_login_at ? new Date(data.last_login_at).toLocaleString('pt-BR') : 'Nunca'} />
                <Field label="Último chat" value={data.last_chat_at ? new Date(data.last_chat_at).toLocaleString('pt-BR') : 'Nunca'} />
                <Field label="Avatar" value={data.avatar_url ? 'Configurado' : 'Sem foto'} />
              </div>
            </Section>

            {data.profile_attributes && Object.keys(data.profile_attributes).length > 0 && (
              <Section title="Dados de onboarding" icon={<ClipboardList size={16} />} expanded={expandedSections.onboarding} onToggle={() => toggle('onboarding')}>
                <div className="space-y-2">
                  {Object.entries(data.profile_attributes).map(([key, value]) => (
                    <DataRow
                      key={key}
                      icon={<Tag size={12} />}
                      label={humanizeKey(key)}
                      value={formatValue(value)}
                    />
                  ))}
                </div>
              </Section>
            )}

            {data.numerology_data && Object.keys(data.numerology_data).length > 0 && (
              <Section title="Numerologia" icon={<Sparkles size={16} />} expanded={expandedSections.numerology} onToggle={() => toggle('numerology')}>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {data.numerology_data.caminho_vida && (
                    <NumberCard label="Caminho de Vida" numero={data.numerology_data.caminho_vida.numero} ehMestre={data.numerology_data.caminho_vida.eh_mestre} />
                  )}
                  {data.numerology_data.alma && (
                    <NumberCard label="Alma" numero={data.numerology_data.alma.numero} />
                  )}
                  {data.numerology_data.expressao && (
                    <NumberCard label="Expressão" numero={data.numerology_data.expressao.numero} ehMestre={data.numerology_data.expressao.eh_mestre} />
                  )}
                  {data.numerology_data.personalidade && (
                    <NumberCard label="Personalidade" numero={data.numerology_data.personalidade.numero} />
                  )}
                  {data.numerology_data.ano_pessoal && (
                    <NumberCard label={`Ano Pessoal ${data.numerology_data.ano_pessoal.ano || new Date().getFullYear()}`} numero={data.numerology_data.ano_pessoal.numero} />
                  )}
                </div>
                {data.numerology_data.dados_usados && (
                  <div className="mt-4 pt-3 border-t border-ayria-border">
                    <div className="text-xs font-semibold text-ayria-text mb-2">Dados usados no cálculo</div>
                    <div className="space-y-1">
                      {data.numerology_data.dados_usados.nome_completo && (
                        <DataRow icon={<User size={12} />} label="Nome completo" value={data.numerology_data.dados_usados.nome_completo} />
                      )}
                      {data.numerology_data.dados_usados.data_nascimento && (
                        <DataRow icon={<Calendar size={12} />} label="Data de nascimento" value={data.numerology_data.dados_usados.data_nascimento} />
                      )}
                      {data.numerology_data.dados_usados.hora_nascimento && (
                        <DataRow icon={<Clock size={12} />} label="Hora" value={data.numerology_data.dados_usados.hora_nascimento} />
                      )}
                      {data.numerology_data.dados_usados.local_nascimento && (
                        <DataRow icon={<MapPin size={12} />} label="Local" value={data.numerology_data.dados_usados.local_nascimento} />
                      )}
                      {data.numerology_data.calculado_em && (
                        <DataRow icon={<Calculator size={12} />} label="Calculado em" value={new Date(data.numerology_data.calculado_em).toLocaleString('pt-BR')} />
                      )}
                    </div>
                  </div>
                )}
              </Section>
            )}

            {data.astrology_data && Object.keys(data.astrology_data).length > 0 && (
              <Section title="Mapa Astral" icon={<Star size={16} />} expanded={expandedSections.astrology} onToggle={() => toggle('astrology')}>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                  {data.astrology_data.sol && (
                    <PlanetCard nome="☀️ Sol" signo={data.astrology_data.sol.signo_pt} elemento={data.astrology_data.sol.elemento} casa={data.astrology_data.sol.casa} destaque />
                  )}
                  {data.astrology_data.lua && (
                    <PlanetCard nome="🌙 Lua" signo={data.astrology_data.lua.signo_pt} elemento={data.astrology_data.lua.elemento} casa={data.astrology_data.lua.casa} destaque />
                  )}
                  {data.astrology_data.ascendente && (
                    <PlanetCard nome="⬆️ Ascendente" signo={data.astrology_data.ascendente.signo_pt} destaque />
                  )}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
                  {['mercurio', 'venus', 'marte', 'jupiter', 'saturno'].map((p) => {
                    const info = data.astrology_data[p]
                    if (!info) return null
                    const emoji = p === 'mercurio' ? '☿' : p === 'venus' ? '♀' : p === 'marte' ? '♂' : p === 'jupiter' ? '♃' : '♄'
                    return <PlanetCard key={p} nome={`${emoji} ${capitalize(p)}`} signo={info.signo_pt} elemento={info.elemento} casa={info.casa} />
                  })}
                </div>
                {data.astrology_data.coordenadas && (
                  <div className="pt-3 border-t border-ayria-border">
                    <div className="text-xs font-semibold text-ayria-text mb-2">Dados do cálculo</div>
                    <div className="space-y-1">
                      {data.astrology_data.cidade_usada && (
                        <DataRow icon={<MapPin size={12} />} label="Cidade" value={data.astrology_data.cidade_usada} />
                      )}
                      {data.astrology_data.coordenadas && (
                        <DataRow icon={<MapPin size={12} />} label="Lat / Lon" value={`${data.astrology_data.coordenadas.lat} / ${data.astrology_data.coordenadas.lon}`} />
                      )}
                      {data.astrology_data.data_calculo && (
                        <DataRow icon={<Calculator size={12} />} label="Calculado em" value={new Date(data.astrology_data.data_calculo).toLocaleString('pt-BR')} />
                      )}
                    </div>
                  </div>
                )}
              </Section>
            )}

            {data.dynamic_attributes && data.dynamic_attributes.length > 0 && (
              <Section title="Atributos dinâmicos" icon={<Briefcase size={16} />} expanded={expandedSections.dynamic} onToggle={() => toggle('dynamic')}>
                <div className="space-y-2">
                  {data.dynamic_attributes.map((a: any, i: number) => (
                    <DataRow
                      key={i}
                      icon={<Tag size={12} />}
                      label={`${a.attribute_name}`}
                      sublabel={a.attribute_code}
                      value={formatValue(a.value)}
                    />
                  ))}
                </div>
              </Section>
            )}

            {!data.profile_attributes && !data.numerology_data && !data.astrology_data && !data.dynamic_attributes?.length && (
              <EmptyState />
            )}
          </div>
        )}
      </div>
    </div>
  )
}
