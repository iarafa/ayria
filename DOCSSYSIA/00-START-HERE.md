# 00-START-HERE — Onboarding pra outra IA mexer na AYRIA

**Sobre:** Esta pasta documenta o sistema **AYRIA** em produção (chat IA de autoconhecimento).
**Servidor:** VPS Hostinger (179.198.127.230), Ubuntu 26.04, nativo (sem Docker).

## Quem é você (a IA)

Você vai assumir o suporte/manutenção do sistema AYRIA. Esta pasta te dá TUDO que precisa.

## Se for a primeira vez aqui, leia nesta ordem

| # | Doc | Tempo |
|---|---|---|
| 1 | [01-STATUS-ATUAL.md](01-STATUS-ATUAL.md) | 2min |
| 2 | [02-ARQUITETURA.md](02-ARQUITETURA.md) | 5min |
| 3 | [08-HISTORICO-DECISOES-14082026.md](08-HISTORICO-DECISOES-14082026.md) | 5min |
| 4 | [14-REGRAS-MEMORY.md](14-REGRAS-MEMORY.md) | 5min |
| 5 | [03-DEPLOY.md](03-DEPLOY.md) | 5min |
| 6 | [04-CREDENCIAIS-LOCALIZACAO.md](04-CREDENCIAIS-LOCALIZACAO.md) | 3min |
| 7 | [07-TROUBLESHOOTING.md](07-TROUBLESHOOTING.md) | 5min |
| 8 | Os outros conforme precisar | — |

**Total: ~30 min** pra entender tudo.

## Se for emergência (sistema caiu)

1. [07-TROUBLESHOOTING.md](07-TROUBLESHOOTING.md) — busca o sintoma
2. [03-DEPLOY.md](03-DEPLOY.md) — procedimentos de restart
3. [01-STATUS-ATUAL.md](01-STATUS-ATUAL.md) — ver o que deveria estar rodando

## Se for mudar credencial

[04-CREDENCIAIS-LOCALIZACAO.md](04-CREDENCIAIS-LOCALIZACAO.md) — onde tá cada (sem expor valor).

## Se for deploy de novo código AYRIA

[03-DEPLOY.md](03-DEPLOY.md) — passo-a-passo completo (git pull + pip + npm build + systemctl restart).

## Se for restaurar banco

[11-BACKUP-PLANO.md](11-BACKUP-PLANO.md) — procedimento de restore.

## Se for configurar SSL Strict real

[15-CLOUDFLARE-ORIGIN-CERT.md](15-CLOUDFLARE-ORIGIN-CERT.md) — passo-a-passo completo.

## Escopo deste sistema (o que ESTÁ documentado)

✅ Deploy em VPS Hostinger
✅ Backend FastAPI/uvicorn (AYRIA)
✅ Frontend React/Vite (AYRIA)
✅ PostgreSQL 18 (banco do AYRIA)
✅ Qdrant vector DB (vector store do AYRIA)
✅ TurboSMTP (email transacional do AYRIA)
✅ Stripe (billing do AYRIA, modo test)
✅ Cloudflare (DNS do ayria.online)
✅ SSL/TLS (auto-assinado, pendente Origin Cert)
✅ Caddy (reverse proxy)
✅ systemd (units ayria-backend e staging)
✅ MiniMax IA + Telegram (mapa completo em [16-MINIMAX-TELEGRAM-MAP.md](16-MINIMAX-TELEGRAM-MAP.md))

## Escopo deste sistema (o que NÃO está documentado)

❌ **Outros projetos** (JUJU marketing, ZE infra, sorteio-soedil, etc) — NÃO confundem
❌ **Credenciais reais** (só localização, sem valor)
❌ **Lógica de negócio específica do AYRIA** (chat IA, alma, créditos) — ver código fonte em `/opt/ayria/backend/routers/` e `/opt/ayria/backend/services/`

## Regras absolutas (NUNCA violar)

Ver [14-REGRAS-MEMORY.md](14-REGRAS-MEMORY.md). As 5 mais críticas:

1. **"Mesma versão que temos local" = EXATAMENTE a mesma.** Sem downgrade proativo.
2. **Sempre commit + push.** Nunca local sem push.
3. **NÃO mexer no Mikrotik** (rede do Rafael). Jamais.
4. **AYRIA em produção = NATIVO.** Nunca Docker.
5. **NÃO misturar contextos.** Quando o tema é AYRIA, só AYRIA.

## Estrutura do workspace

```
/home/peron/.openclaw/workspace/   ← você tá aqui
├── DOCSSYSIA/                     ← esta pasta (16 docs)
├── MEMORY.md                       ← regras duras + lições (curated)
├── memory/YYYY-MM-DD.md            ← diário diário
├── AGENTS.md, SOUL.md, etc         ← config do agente
└── ...

/home/peron/projects/ayria/        ← repo git do código AYRIA
├── backend/                         ← FastAPI
├── frontend/                        ← React/Vite
└── DOCSSYSIA/                      ← cópia

/Área de trabalho/OBSIDIANDATA/PERON/
└── DOCSSYSIA/                      ← outra cópia no Obsidian
```

## Quem é o dono

**Rafael Peron** (telegram @Perontrader, id 779495783). Mora em Itatiba/SP.

Ele cobra **direto** quando erra. Quando ele tá bravo:
- ❌ Não explique como chegou na resposta
- ❌ Não ofereça ajuda extra
- ❌ Não liste opções
- ✅ Resposta curta, só o dado pedido
- ✅ Se errou, corrigir seco no próximo turno

## Verificação rápida (saber se tudo tá OK)

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"

echo "caddy:    $($VPS 'systemctl is-active caddy')"
echo "ayria:    $($VPS 'systemctl is-active ayria-backend')"
echo "staging:  $($VPS 'systemctl is-active ayria-backend-staging')"
echo "postgres: $($VPS 'pg_lsclusters | grep main | awk "{print \$3, \$4}"')"
echo "qdrant:   $($VPS 'pgrep -f /opt/qdrant/qdrant && echo \"OK\"')"

curl -sk --connect-timeout 5 https://ayria.online/health
echo ""
```

Esperado:
- caddy: **active**
- ayria: **active**
- staging: **active**
- postgres: **5432 online**
- qdrant: **OK**
- `/health`: `{"status":"ok","database":"ok","environment":"production"}`

## Pronto

Se leu os 7 primeiros docs (01 → 02 → 08 → 14 → 03 → 04 → 07), você sabe tudo que precisa pra:
- Diagnosticar problemas
- Fazer deploy de código
- Rotacionar credenciais
- Restaurar backup
- Tomar decisões baseado nas regras

Boa sorte. Sem floreio.