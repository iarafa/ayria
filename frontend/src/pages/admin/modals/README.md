# `frontend/src/pages/admin/modals/` — Modais do Admin

## Convenções

- 1 arquivo = 1 modal
- Modal renderiza condicionalmente (early return se `!open` ou `!userId`)
- Estado de visibilidade controlado pelo pai (AdminPage.tsx)

## Status atual (25/07/2026)

- ✅ `UserDetailsModal.tsx` — modal completo de detalhes do usuário

## Próxima quebra (quando voltar)

Extrair modais que ainda estão inline em outros lugares:
- Modal de criar usuário
- Modal de editar usuário
- Modal de troca de senha admin
