# DOCSSYSIA — Índice

Pasta interna de documentação do sistema AYRIA em produção.
**Localização:** `/home/peron/.openclaw/workspace/DOCSSYSIA/` (local) + VPS `/opt/ayria/DOCSSYSIA/` + Obsidian.

## Índice

| # | Arquivo | Conteúdo |
|---|---|---|
| 00 | [00-START-HERE.md](00-START-HERE.md) | **PÁGINA DE ENTRADA** — leia primeiro |
| 00 | [00-INDICE.md](00-INDICE.md) | Este índice |
| 01 | [01-STATUS-ATUAL.md](01-STATUS-ATUAL.md) | O que tá rodando AGORA (4 serviços, URLs, banco) |
| 02 | [02-ARQUITETURA.md](02-ARQUITETURA.md) | Diagrama de fluxo, stack, ports, paths |
| 03 | [03-DEPLOY.md](03-DEPLOY.md) | Como restart, deploy código, health check |
| 04 | [04-CREDENCIAIS-LOCALIZACAO.md](04-CREDENCIAIS-LOCALIZACAO.md) | ONDE tá cada credencial (sem expor valor) |
| 05 | [05-DNS-CLOUDFLARE.md](05-DNS-CLOUDFLARE.md) | DNS records, proxy, Origin Cert |
| 06 | [06-SEGURANCA.md](06-SEGURANCA.md) | UFW, fail2ban, SSH, perms |
| 07 | [07-TROUBLESHOOTING.md](07-TROUBLESHOOTING.md) | Problemas comuns + soluções |
| 08 | [08-HISTORICO-DECISOES-14082026.md](08-HISTORICO-DECISOES-14082026.md) | O que fizemos HOJE + decisões |
| 09 | [09-COMANDOS-UTEIS.md](09-COMANDOS-UTEIS.md) | Cheatsheet de comandos |
| 10 | [10-SETUP-DO-ZERO.md](10-SETUP-DO-ZERO.md) | Setup completo do zero (VPS nova do zero) |
| 11 | [11-BACKUP-IMPLEMENTADO.md](11-BACKUP-IMPLEMENTADO.md) | Backup implementado (banco + TUDO, 2x/dia) |
| 12 | [12-MONITOR-PLANO.md](12-MONITOR-PLANO.md) | Plano de monitor (não implementado) |
| 13 | [13-USUARIOS-SSH.md](13-USUARIOS-SSH.md) | Como adicionar/remover usuários SSH |
| 14 | [14-REGRAS-MEMORY.md](14-REGRAS-MEMORY.md) | 15 regras críticas do MEMORY.md (sobre AYRIA) |
| 15 | [15-CLOUDFLARE-ORIGIN-CERT.md](15-CLOUDFLARE-ORIGIN-CERT.md) | Como gerar Origin Cert (SSL Strict real) |
| 16 | [16-MINIMAX-TELEGRAM-MAP.md](16-MINIMAX-TELEGRAM-MAP.md) | Mapa completo de TODOS os locais que usam MiniMax (IA) e Telegram (notificações) |

**Total:** 17 documentos (incluindo este índice).

## Pra que serve

Pra qualquer IA (ou pessoa) que abrir o sistema AYRIA saber:
- O que tá rodando e onde
- Como reiniciar/debugar/restaurar
- Onde estão credenciais
- Decisões tomadas e por quê
- Procedimentos completos do zero

## Fontes complementares

- `/home/peron/.openclaw/workspace/MEMORY.md` — regras duras + lições (curated, sobre AYRIA e tudo)
- `~/Área de trabalho/OBSIDIANDATA/PERON/02_Projects/PROJETO_AYRIA_DEPLOY_*.md` — histórico do projeto
- `~/Área de trabalho/OBSIDIANDATA/PERON/DOCSSYSIA/` — cópia no Obsidian (mesmos 16 docs)
- VPS: `/opt/ayria/DOCSSYSIA/` — outra cópia de segurança