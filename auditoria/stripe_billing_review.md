Aqui está a auditoria cirúrgica do código de produção do roteador de faturamento do Stripe.

## [api/stripe/billing.py]

🔴 [Linhas 418-431 e 511-531]: **Duplo crédito de tokens (Double Provisioning) ou Limbo de créditos**
   * **Severidade:** 🔴 CRÍTICO
   * **Descrição:** O código tenta creditar tokens em dois momentos: na criação da assinatura (`customer.subscription.created`) e no pagamento da fatura (`invoice.paid`). 
     1. Se a assinatura for criada como `active` (ex: trial ou cupom de 100%), o usuário ganha créditos no `created` e novamente quando a fatura de R$ 0 for paga no `invoice.paid`.
     2. Se a assinatura for criada como `incomplete` (comportamento padrão do Stripe para pagamentos que requerem 3DS/confirmação), o `created` não concede créditos. Se o pagamento for bem-sucedido, o `invoice.paid` concede os créditos, mas o comentário diz que "não deveria conceder na primeira". Se o desenvolvedor futuramente bloquear a primeira fatura no `invoice.paid`, o usuário de fluxo padrão `incomplete -> active` ficará com **zero** créditos.
   * **Fix:** Centralize a concessão de créditos **apenas** no `invoice.paid` (que garante que o dinheiro entrou ou a transação de R$ 0 foi autorizada) e remova completamente a concessão de créditos do `customer.subscription.created`. Use o ID da fatura (`stripe_invoice_id`) como chave de idempotência no `grant_credits`.

   ```python
   # 1. Remova o bloco de concessão de créditos de _handle_subscription_created (linhas 418-431)

   # 2. Simplifique e garanta a concessão segura em _handle_invoice_paid:
   async def _handle_invoice_paid(event_obj, db):
       # ... (código anterior de busca de user e inserção de invoice) ...

       # Credita tokens para QUALQUER fatura paga com sucesso (seja primeira ou renovação)
       sub_id = event_obj.get("subscription")
       if sub_id:
           res = await db.execute(
               select(models.StripeSubscription)
               .where(models.StripeSubscription.stripe_subscription_id == sub_id)
           )
           sub = res.scalars().first()
           if sub and sub.plan_slug:
               plan_cfg = PLANS.get(sub.plan_slug, {})
               if plan_cfg.get("tokens") and user:
                   # O credit_service deve usar reference_id=inv_id para evitar duplicidade no DB
                   await grant_credits(
                       db,
                       user,
                       plan_cfg["tokens"],
                       f"Créditos do plano {plan_cfg.get('name', sub.plan_slug)}",
                       reference_type="stripe_invoice",
                       reference_id=inv_id,
                   )
                   user.credits_last_granted_at = datetime.now(timezone.utc)
                   logger.info(f"Créditos concedidos via invoice {inv_id} para user {user.id}")
   ```

---

🟡 [Linha 196]: **Crash por comparação de Datetime Naive vs Aware no Cupom**
   * **Severidade:** 🟡 MÉDIO
   * **Descrição:** Se o campo `coupon.expires_at` no banco de dados PostgreSQL/SQLAlchemy for do tipo `DateTime` sem fuso horário (naive), a comparação `coupon.expires_at < datetime.now(timezone.utc)` lançará um `TypeError: can't compare offset-naive and offset-aware datetimes`, quebrando o checkout.
   * **Fix:** Force a comparação segura convertendo ambos para UTC naive ou aware.

   ```python
   # Linha 196
   if coupon.expires_at:
       expires_at_utc = coupon.expires_at.replace(tzinfo=timezone.utc) if coupon.expires_at.tzinfo is None else coupon.expires_at
       if expires_at_utc < datetime.now(timezone.utc):
           raise HTTPException(400, "Cupom expirado")
   ```

---

🟡 [Linhas 364-368]: **Falha ao associar assinatura se o Metadata do Stripe falhar**
   * **Severidade:** 🟡 MÉDIO
   * **Descrição:** No handler `_handle_subscription_created`, se `_resolve_user_id_from_event` retornar `None` (o que acontece se o Stripe falhar em propagar o metadata ou se a assinatura for criada manualmente pelo admin), o código apenas loga um aviso e retorna. Ele deveria fazer o fallback buscando o usuário pelo `customer_id`, exatamente como faz no `checkout.session.completed`.
   * **Fix:**

   ```python
   async def _handle_subscription_created(event_obj, db):
       sub_id = event_obj["id"]
       user_id = await _resolve_user_id_from_event(event_obj)
       
       # Fallback robusto via customer_id se metadata falhar
       if not user_id:
           customer_id = event_obj.get("customer")
           if customer_id:
               user = await _get_user_by_customer(customer_id, db)
               if user:
                   user_id = str(user.id)
                   
       if not user_id:
           logger.warning(f"customer.subscription.created {sub_id} sem ayria_user_id e sem customer correspondente")
           return
   ```

---

🟡 [Linhas 610-645]: **Bloqueio do Event Loop com `subprocess.run` e I/O síncrono**
   * **Severidade:** 🟡 MÉDIO
   * **Descrição:** A função `_notify_payment_failed` roda em background via `asyncio.create_task`. No entanto, ela executa `subprocess.run(["curl", ...])` e lê um arquivo de configuração de forma síncrona. Isso bloqueia completamente a thread única do event loop do FastAPI, congelando todas as outras requisições concorrentes da API enquanto o processo do `curl` não terminar.
   * **Fix:** Use um cliente HTTP assíncrono (como `httpx`, que já é dependência padrão do FastAPI) para enviar o alerta ao Telegram.

   ```python
   import httpx

   async def _notify_payment_failed(user: models.User, event_obj: dict) -> None:
       # ... (código de envio de email) ...

       # Telegram assíncrono sem subprocess/curl
       try:
           # Tenta ler token de forma segura (idealmente deveria estar no settings)
           avisos_token = os.environ.get("AVISOS_TOKEN")
           if not avisos_token:
               # Fallback síncrono de arquivo (apenas se estritamente necessário, ideal ler no startup)
               try:
                   with open("/home/peron/.telegram_bots.env") as f:
                       for line in f:
                           if line.startswith("AVISOS_TOKEN="):
                               avisos_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                               break
               except Exception:
                   pass

           if avisos_token:
               chat_id = 779495783
               text = (
                   "⚠️ *FALHA DE PAGAMENTO*\n\n"
                   f"User: {user.email}\n"
                   f"Tentativa: #{attempt}\n"
                   f"Valor: R$ {amount_due:.2f}\n"
                   f"Status: past_due · bloqueio em 3 dias\n"
               )
               async with httpx.AsyncClient() as client:
                   await client.post(
                       f"https://api.telegram.org/bot{avisos_token}/sendMessage",
                       json={
                           "chat_id": chat_id,
                           "text": text,
                           "parse_mode": "Markdown"
                       },
                       timeout=5.0
                   )
               logger.info(f"Telegram alerta payment_failed enviado para {chat_id}")
       except Exception as e:
           logger.error(f"Erro inesperado no Telegram payment_failed: {e}")
   ```

---

🟢 [Linhas 368, 407, 432, 493, 508, 553]: **Crash potencial por UUID inválido vindo do Stripe**
   * **Severidade:** 🟢 POLISH
   * **Descrição:** O código assume que o `user_id` extraído do metadata do Stripe é sempre um UUID válido e chama `uuid.UUID(user_id)` diretamente. Se houver qualquer erro de digitação manual no Stripe Dashboard ou payload corrompido, a API lançará um `ValueError` não tratado, quebrando o processamento do webhook (retornando HTTP 500).
   * **Fix:** Crie um helper para conversão segura de UUID.

   ```python
   def _safe_uuid(val: Optional[str]) -> Optional[uuid.UUID]:
       if not val:
           return None
       try:
           return uuid.UUID(str(val))
       except ValueError:
           return None

   # Exemplo de uso:
   user_uuid = _safe_uuid(user_id)
   if not user_uuid:
       logger.error(f"UUID inválido recebido: {user_id}")
       return
   user = await db.get(models.User, user_uuid)
   ```
