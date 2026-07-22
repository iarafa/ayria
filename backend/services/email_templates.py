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
