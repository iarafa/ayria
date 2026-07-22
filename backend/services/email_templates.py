"""
AYRIA - Email Templates
Templates HTML responsivos para emails transacionais.
"""
from typing import Optional


def verification_email_html(
    full_name: Optional[str],
    verify_url: str,
    expires_hours: int = 24,
) -> str:
    """
    Email de verificação de cadastro.
    """
    greeting = f"Oi, {full_name}! 👋" if full_name else "Olá! 👋"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Confirme seu email - AYRIA</title>
</head>
<body style="margin:0;padding:0;background-color:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:#0f172a;padding:40px 20px;">
    <tr>
      <td align="center">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width:600px;background-color:#1e293b;border-radius:16px;overflow:hidden;border:1px solid #334155;">
          <!-- Header -->
          <tr>
            <td style="padding:40px 40px 20px 40px;text-align:center;background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);">
              <h1 style="margin:0;color:#ffffff;font-size:32px;font-weight:700;">✨ AYRIA</h1>
              <p style="margin:8px 0 0 0;color:#cbd5e1;font-size:14px;">Sua jornada de autoconhecimento começa aqui</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 16px 0;color:#f1f5f9;font-size:22px;font-weight:600;">{greeting}</h2>
              <p style="margin:0 0 24px 0;color:#cbd5e1;font-size:16px;line-height:1.6;">
                Falta pouco! Confirme seu email pra ativar sua conta e começar a explorar tudo que a AYRIA preparou pra você.
              </p>
              <!-- CTA Button -->
              <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:32px 0;">
                <tr>
                  <td align="center">
                    <a href="{verify_url}" target="_blank" style="display:inline-block;padding:16px 40px;background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);color:#ffffff;text-decoration:none;font-size:16px;font-weight:600;border-radius:8px;box-shadow:0 4px 14px rgba(99,102,241,0.4);">
                      ✅ Confirmar meu email
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:24px 0 8px 0;color:#94a3b8;font-size:13px;line-height:1.5;">
                Ou copie e cole este link no navegador:
              </p>
              <p style="margin:0;padding:12px;background-color:#0f172a;border:1px solid #334155;border-radius:6px;color:#94a3b8;font-size:12px;word-break:break-all;font-family:monospace;">
                {verify_url}
              </p>
              <p style="margin:24px 0 0 0;color:#94a3b8;font-size:13px;line-height:1.5;">
                ⏰ Este link expira em <strong style="color:#cbd5e1;">{expires_hours} horas</strong>.
              </p>
              <hr style="margin:32px 0;border:none;border-top:1px solid #334155;">
              <p style="margin:0;color:#64748b;font-size:12px;line-height:1.5;">
                Se você não criou essa conta, pode ignorar este email com segurança.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;background-color:#0f172a;text-align:center;border-top:1px solid #334155;">
              <p style="margin:0;color:#64748b;font-size:12px;">
                © AYRIA · Enviado via TurboSMTP
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def verification_email_text(
    full_name: Optional[str],
    verify_url: str,
    expires_hours: int = 24,
) -> str:
    """Versão texto plano (fallback)."""
    greeting = f"Oi, {full_name}!" if full_name else "Olá!"
    return f"""AYRIA — Confirme seu email

{greeting}

Falta pouco! Confirme seu email pra ativar sua conta e começar a explorar tudo que a AYRIA preparou pra você.

Clique no link abaixo:
{verify_url}

Este link expira em {expires_hours} horas.

Se você não criou essa conta, pode ignorar este email com segurança.

— Equipe AYRIA
"""


def password_reset_email_html(full_name: Optional[str], reset_url: str, expires_minutes: int = 60) -> str:
    """Email de reset de senha. Versão HTML."""
    greeting = f"Oi, {full_name}!" if full_name else "Olá!"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>AYRIA — Redefinir sua senha</title>
</head>
<body style="margin:0; padding:0; background:#050505; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#050505; padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:linear-gradient(135deg,#1a0a2e 0%,#0a0a0a 100%); border-radius:16px; overflow:hidden; box-shadow:0 8px 40px rgba(99,102,241,0.2);">
          <tr>
            <td align="center" style="padding:40px 32px 24px;">
              <div style="width:64px; height:64px; background:linear-gradient(135deg,#6366F1,#A855F7); border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:32px; box-shadow:0 0 24px rgba(99,102,241,0.4);">🔑</div>
              <h1 style="margin:24px 0 0; font-size:28px; font-weight:bold; color:#FFFFFF; letter-spacing:-0.5px;">Redefinir senha</h1>
              <p style="margin:8px 0 0; font-size:14px; color:#A5B4FC; letter-spacing:0.5px;">AYRIA · Acesso seguro</p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 32px;">
              <p style="margin:0 0 24px; font-size:16px; line-height:1.6; color:#E5E7EB;">{greeting}</p>
              <p style="margin:0 0 24px; font-size:16px; line-height:1.6; color:#E5E7EB;">
                Recebemos um pedido pra redefinir a senha da sua conta AYRIA. Se foi você, clique no botão abaixo pra escolher uma senha nova.
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:8px 0 24px;">
                    <a href="{reset_url}" target="_blank" rel="noopener" style="display:inline-block; padding:16px 40px; background:linear-gradient(135deg,#6366F1,#A855F7); color:#FFFFFF; text-decoration:none; font-weight:bold; font-size:16px; border-radius:12px; box-shadow:0 4px 16px rgba(99,102,241,0.3);">
                      Redefinir senha
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 16px; font-size:14px; line-height:1.6; color:#9CA3AF;">
                Ou cole este link no seu navegador:
              </p>
              <p style="margin:0 0 24px; padding:12px 16px; background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3); border-radius:8px; word-break:break-all; font-size:12px; color:#A5B4FC; font-family:monospace;">
                {reset_url}
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); border-radius:8px; margin:8px 0 24px;">
                <tr>
                  <td style="padding:12px 16px;">
                    <p style="margin:0; font-size:13px; line-height:1.5; color:#FBBF24;">
                      ⏰ <strong>Este link expira em {expires_minutes} minutos.</strong> Por segurança, links de redefinição têm vida curta.
                    </p>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 8px; font-size:14px; line-height:1.6; color:#9CA3AF;">
                <strong>Não pediu isso?</strong> Pode ignorar este email com segurança — sua senha continua a mesma.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px 32px; border-top:1px solid rgba(99,102,241,0.15);">
              <p style="margin:0; font-size:12px; color:#6B7280; text-align:center;">
                AYRIA — Sabedoria numerológica com IA 🤖✨
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def password_reset_email_text(full_name: Optional[str], reset_url: str, expires_minutes: int = 60) -> str:
    """Email de reset de senha. Versão texto plano."""
    greeting = f"Oi, {full_name}!" if full_name else "Olá!"
    return f"""AYRIA — Redefinir sua senha

{greeting}

Recebemos um pedido pra redefinir a senha da sua conta AYRIA. Se foi você, clique no link abaixo pra escolher uma senha nova:

{reset_url}

⏰ Este link expira em {expires_minutes} minutos.

Não pediu isso? Pode ignorar este email com segurança — sua senha continua a mesma.

— Equipe AYRIA
"""


def payment_failed_email_html(full_name: Optional[str], grace_days: int, retry_count: Optional[int] = None, update_url: Optional[str] = None) -> str:
    """Email avisando que cartão foi recusado e o user tem N dias pra atualizar."""
    greeting = f"Oi, {full_name}!" if full_name else "Olá!"
    retry_info = f" Esta foi a tentativa nº {retry_count}." if retry_count else ""
    button_html = (
        f'<a href="{update_url}" target="_blank" rel="noopener" style="display:inline-block; padding:16px 40px; background:linear-gradient(135deg,#6366F1,#A855F7); color:#FFFFFF; text-decoration:none; font-weight:bold; font-size:16px; border-radius:12px; box-shadow:0 4px 16px rgba(99,102,241,0.3); margin-top:8px;">Atualizar cartão agora</a>' if update_url else ''
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>AYRIA — Problema com seu pagamento</title>
</head>
<body style="margin:0; padding:0; background:#050505; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#050505; padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:linear-gradient(135deg,#1a0a2e 0%,#0a0a0a 100%); border-radius:16px; overflow:hidden; box-shadow:0 8px 40px rgba(245,158,11,0.2);">
          <tr>
            <td align="center" style="padding:40px 32px 24px; background:rgba(245,158,11,0.1);">
              <div style="width:64px; height:64px; background:linear-gradient(135deg,#F59E0B,#EF4444); border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-size:32px; box-shadow:0 0 24px rgba(245,158,11,0.4);">⚠️</div>
              <h1 style="margin:24px 0 0; font-size:24px; font-weight:bold; color:#FBBF24; letter-spacing:-0.5px;">Problema no pagamento</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 32px;">
              <p style="margin:24px 0 16px; font-size:16px; line-height:1.6; color:#E5E7EB;">{greeting}</p>
              <p style="margin:0 0 16px; font-size:16px; line-height:1.6; color:#E5E7EB;">
                O cartão da sua assinatura AYRIA foi <strong>recusado</strong>.{retry_info}
                Isso geralmente acontece porque o cartão expirou, foi bloqueado pelo banco, ou não tem limite disponível.
              </p>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2); border-radius:8px; margin:8px 0 24px;">
                <tr>
                  <td style="padding:16px;">
                    <p style="margin:0 0 8px; font-size:14px; line-height:1.5; color:#FBBF24;">
                      ⏰ <strong>Você tem {grace_days} dias</strong> pra atualizar o cartão antes do acesso ser bloqueado.
                    </p>
                    <p style="margin:0; font-size:13px; line-height:1.5; color:#9CA3AF;">
                      Se você não fizer nada, a Stripe vai tentar de novo automaticamente. Mas atualizar agora evita perda de acesso.
                    </p>
                  </td>
                </tr>
              </table>
              {f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:8px 0 24px;">{button_html}</td></tr></table>' if button_html else ''}
              <p style="margin:0 0 8px; font-size:14px; line-height:1.6; color:#9CA3AF;">
                <strong>O que fazer agora:</strong>
              </p>
              <ol style="margin:0 0 16px; padding-left:20px; font-size:14px; line-height:1.8; color:#D1D5DB;">
                <li>Acesse sua conta AYRIA</li>
                <li>Abra o menu <strong>"Minha conta"</strong></li>
                <li>Clique em <strong>"Atualizar forma de pagamento"</strong></li>
                <li>Coloque um cartão válido</li>
              </ol>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px 32px; border-top:1px solid rgba(99,102,241,0.15);">
              <p style="margin:0; font-size:12px; color:#6B7280; text-align:center;">
                AYRIA — Sabedoria numerológica com IA 🤖✨
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def payment_failed_email_text(full_name: Optional[str], grace_days: int, retry_count: Optional[int] = None, update_url: Optional[str] = None) -> str:
    greeting = f"Oi, {full_name}!" if full_name else "Olá!"
    retry = f" Esta foi a tentativa nº {retry_count}." if retry_count else ""
    return f"""AYRIA — Problema no seu pagamento

{greeting}

O cartão da sua assinatura AYRIA foi RECUSADO.{retry}

⏰ Você tem {grace_days} dias pra atualizar o cartão antes do acesso ser bloqueado.

O que fazer agora:
1. Acesse sua conta AYRIA
2. Abra o menu "Minha conta"
3. Clique em "Atualizar forma de pagamento"
4. Coloque um cartão válido

{f"Ou acesse direto: {update_url}" if update_url else ""}

Se você não fizer nada, a Stripe vai tentar de novo automaticamente.

— Equipe AYRIA
"""
