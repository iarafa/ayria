## credit_service.py

🔴 **[linha 76]**: Race Condition (Double Spending) no consumo de créditos em `consume_credits`.
   Como o objeto `user` é alterado diretamente na memória sem lock pessimista no banco de dados, requisições concorrentes (ex: cliques rápidos ou chamadas paralelas de API) lerão o mesmo saldo antes do commit, permitindo que o usuário gaste mais créditos do que possui.
   **Fix**:
   ```python
   # No início de consume_credits, recupere o usuário com lock de escrita (FOR UPDATE)
   res = await db.execute(
       select(models.User)
       .where(models.User.id == user.id)
       .with_for_update()
   )
   locked_user = res.scalar_one()
   
   # Use locked_user no restante da função ao invés do parâmetro user
   ```

🔴 **[linha 228]**: Race Condition na concessão de créditos em `grant_credits`.
   Webhooks concorrentes do Stripe ou retentativas rápidas podem causar condições de corrida ao ler e atualizar o saldo simultaneamente.
   **Fix**:
   ```python
   # Trava a linha do usuário para garantir atomicidade na atualização do saldo
   res = await db.execute(
       select(models.User)
       .where(models.User.id == user.id)
       .with_for_update()
   )
   locked_user = res.scalar_one()
   
   balance_before = locked_user.credit_balance or 0
   locked_user.credit_balance = balance_before + amount
   # ... aplicar as demais alterações em locked_user
   ```

🟡 **[linha 111]**: Possível `TypeError` se `user.credit_balance` for nulo.
   Se o saldo do usuário for `None` no banco de dados, a linha `balance_before = user.credit_balance` atribuirá `None` à variável, quebrando com `TypeError: unsupported operand type(s) for -: 'NoneType' and 'int'` na linha seguinte.
   **Fix**:
   ```python
   balance_before = user.credit_balance or 0
   user.credit_balance = balance_before - amount
   ```

🟡 **[linha 199]**: Falta de validação de paginação em `get_transactions`.
   Se o parâmetro `page` for menor que 1, o cálculo do `offset` resultará em um número negativo, gerando um erro de sintaxe SQL no PostgreSQL/SQLAlchemy. Além disso, a falta de limite em `page_size` permite ataques de negação de serviço (DoS) por exaustão de memória.
   **Fix**:
   ```python
   page = max(1, page)
   page_size = min(max(1, page_size), 100)  # limita a um teto seguro de 100 itens
   offset = (page - 1) * page_size
   ```

🟢 **[linha 254]**: Duplicação de lógica e bypass de validação de plano ativo em `grant_credits`.
   A função busca o plano diretamente via query ad-hoc ignorando se o plano está ativo (`active == True`), violando a regra de negócio centralizada em `get_plan_by_slug`.
   **Fix**:
   ```python
   if plan_slug and user.selected_plan_id is None:
       plan_db = await get_plan_by_slug(db, plan_slug)
       if plan_db:
           user.selected_plan_id = plan_db.id
           logger.info(f"User {user.email} plano setado via grant_credits → {plan_slug}")
   ```
