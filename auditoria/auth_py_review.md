## [auth.py]

🔴 [Linha 339]: **Vazamento Crítico de Credenciais em Log de Produção**
   O log de aviso para falha de login expõe a senha do usuário em texto plano (`payload.password!r`). Isso viola conformidades de segurança (LGPD, PCI-DSS) e expõe credenciais caso os logs sejam centralizados (ex: Kibana, Datadog, CloudWatch).
   Fix:
   ```python
   # Remova completamente a senha do log
   logging.warning(
       f"[AUTH-DEBUG] login falhou p/ {payload.email} | user_found={bool(user)}"
   )
   ```

🟡 [Linha 441]: **Vulnerabilidade de DoS por estouro de memória (OOM) no upload de avatar**
   O método `await file.read()` carrega o arquivo inteiro diretamente na memória RAM antes de validar o seu tamanho. Se um atacante enviar um arquivo de múltiplos gigabytes, a API sofrerá esgotamento de memória e a instância será derrubada pelo sistema operacional (Out-Of-Memory killer).
   Fix:
   ```python
   # Valide o tamanho usando o metadado do Starlette antes de ler o arquivo para a memória
   if file.size and file.size > 5 * 1024 * 1024:
       raise HTTPException(
           status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
           detail="Imagem deve ter no máximo 5MB"
       )
   contents = await file.read()
   ```

🟡 [Linha 125 e 142]: **Commit duplo no registro cria estado inconsistente (Limbo)**
   O fluxo de registro realiza um `await db.commit()` na linha 125 (após criar usuário/perfil) e outro na linha 142 (após gerar o token de verificação). Se o servidor cair ou houver falha de rede entre os dois commits, o usuário será criado no banco, mas sem o token de verificação. Ele ficará impossibilitado de ativar a conta ou de solicitar reenvio (pois o registro falhou pela metade).
   Fix:
   ```python
   # Remova o primeiro commit da linha 125 e faça apenas um commit consolidado no final
   # ... (criação do user, profile e grant_initial_credits usando await db.flush())
   
   verification_token = _secrets.token_urlsafe(32)
   user.verification_token = verification_token
   user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
   user.verification_sent_at = datetime.now(timezone.utc)
   
   await db.commit() # Único commit para toda a transação
   await db.refresh(user)
   ```

🟡 [Múltiplas Linhas]: **Crash por mistura de Datetime Naive e Aware (TypeError)**
   O código mistura `datetime.utcnow()` (naive, sem fuso horário) com `datetime.now(timezone.utc)` (aware, com fuso horário). No SQLAlchemy/PostgreSQL, tentar subtrair ou comparar esses dois tipos (como feito na linha 237: `datetime.now(timezone.utc) - user.verification_sent_at`) causará um crash imediato: `TypeError: can't subtract offset-naive and offset-aware datetimes`.
   Fix:
   ```python
   # Padronize TODAS as atribuições de data para usar timezone-aware (timezone.utc)
   # Substitua datetime.utcnow() por datetime.now(timezone.utc) em todo o arquivo:
   
   # Linha 355:
   user.last_login_at = datetime.now(timezone.utc)
   
   # Linhas 414, 427, 459:
   user.updated_at = datetime.now(timezone.utc)
   ```
