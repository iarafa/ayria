#!/bin/bash
# AYRIA - AI Usage Monitor (cron hourly)
# Verifica uso da MiniMax e alerta no Telegram se passar dos limites.
set -uo pipefail

cd /opt/ayria/backend
/opt/ayria/.venv/bin/python3 -c "
import asyncio
from services.ai_usage_monitor import send_usage_alert_if_needed, get_stats

stats = get_stats()
print(f'AI usage check: {stats[\"calls_last_hour\"]} chamadas/hora')

asyncio.run(send_usage_alert_if_needed())
" >> /var/log/ayria/ai_usage.log 2>&1
