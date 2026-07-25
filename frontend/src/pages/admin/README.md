# Pasta `frontend/src/pages/admin/` — Admin Page (quebrada por componente)

## O que mora aqui

A página `/admin`, separada em arquivos por componente.

## Estrutura

```
admin/
├── README.md                     # este arquivo
├── AdminPage.tsx                 # orquestrador (sidebar + roteador de tab) ~3000 linhas
├── tabs/
│   ├── README.md                 # convenção de tabs
│   ├── helpers.tsx               # Section, Field, Badge, StatCard, DataRow, EmptyState, NumberCard, PlanetCard + utilitários (humanizeKey, formatValue, capitalize)
│   └── UserHeader.tsx            # Header grande do modal de detalhes (avatar + identidade + ação Observar)
└── modals/
    ├── README.md                 # convenção de modais
    └── UserDetailsModal.tsx      # modal completo: header + stats + onboarding + numerologia + astrologia + atributos
```

## Histórico de mudanças

- **2026-07-25** — DE quebrou `pages/AdminPage.tsx` (3512 linhas) em `pages/admin/`. Comportamento idêntico.
  - Extraídos: `helpers.tsx` (10 componentes), `UserHeader.tsx`, `UserDetailsModal.tsx`.
  - AdminPage.tsx agora tem 3008 linhas (tabs inline continuam aqui até próxima quebra).

## Pegadinhas conhecidas

- `AdminPage.tsx` ainda é grande (3008 linhas) porque várias tabs inline (UsersTab, CreditsTab, PlansTab, SystemSettingsTab, SupervisionTab, AdminsManagementTab, PartnersTabInline, CouponsTabInline, CommissionsTabInline).
- Próxima quebra: extrair cada tab em arquivo separado (próxima sessão).
- Todos os imports dos componentes quebrados devem usar caminho RELATIVO a partir de `admin/` (`./tabs/helpers`).
- `../` aponta pra `frontend/src/` (store/auth, lib/api, components/*).

## Como adicionar tab nova

1. Adiciona em `tabs/NovaTab.tsx` (criar arquivo)
2. Importa no `AdminPage.tsx`
3. Adiciona no array `tabs` (state union type)
4. Adiciona no sidebar `sections` em `AdminPage.tsx`
5. Renderiza com `{tab === 'nova' && <NovaTab />}`

## Como adicionar modal novo

1. Adiciona em `modals/NovoModal.tsx`
2. Importa no `AdminPage.tsx`
3. Renderiza condicionalmente no final do JSX

## Compatibilidade

- `App.tsx` foi atualizado pra importar de `./pages/admin/AdminPage`.
- Rota `/admin` continua a mesma.
- Backend inalterado.
