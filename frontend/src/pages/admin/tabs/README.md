# `frontend/src/pages/admin/tabs/` — Abas do Admin

## Convenções

- 1 arquivo = 1 aba (quando quebrada)
- Componente recebe props do pai (state + callbacks)
- Helpers compartilhados ficam em `helpers.tsx`

## Status atual (25/07/2026)

- ✅ `helpers.tsx` — componentes auxiliares reutilizáveis
- ✅ `UserHeader.tsx` — header do modal de detalhes
- ❌ Abas grandes ainda inline em `AdminPage.tsx` (UsersTab, CreditsTab, etc)

## Próxima quebra (quando voltar)

Extrair cada aba em arquivo próprio:
- `UsersTab.tsx`
- `CreditsTab.tsx`
- `PlansTab.tsx`
- `SystemSettingsTab.tsx`
- `SupervisionTab.tsx`
- `AdminsManagementTab.tsx`
- `PartnersTab.tsx`
- `CouponsTab.tsx`
- `CommissionsTab.tsx`
- `KnowledgeTab.tsx`
- `OnboardingTab.tsx`
- `AttributesTab.tsx`

Cada uma vira arquivo próprio com mesma assinatura de props.
