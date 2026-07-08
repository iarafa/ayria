"""
AYRIA - Email Service (TurboSMTP API v2)
Envia emails transacionais via API REST do TurboSMTP v2.

Auth: Headers separados consumerKey + consumerSecret (NÃO Basic Auth).
Endpoint: https://api.turbo-smtp.com/api/v2/mail/send

Formato do payload (string-based, NÃO objeto):
  {
    "from": "Name <email@domain.com>",
    "to": "email1@domain.com,email2@domain.com",
    "subject": "...",
    "content": "plain text",        # text/plain
    "html_content": "HTML",         # text/html
    "cc": "...", "bcc": "...",
    "custom_headers": {...},
    "attachments": [...]
  }

Config (env vars):
  TURBOSMTP_CONSUMER_KEY     required
  TURBOSMTP_CONSUMER_SECRET  required
  MAIL_FROM                   required (ex: ayria@tecia.app)
  MAIL_FROM_NAME              optional (default: "AYRIA")
  PUBLIC_BASE_URL             optional (override; senão usa detector)

Doc oficial: https://serversmtp.com/turbo-api/
"""
import os
import logging
import httpx
from typing import Optional, List

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Erro ao enviar email via TurboSMTP."""


class TurboSMTPClient:
    """Cliente TurboSMTP API v2."""

    def __init__(self):
        self.consumer_key = os.getenv("TURBOSMTP_CONSUMER_KEY")
        self.consumer_secret = os.getenv("TURBOSMTP_CONSUMER_SECRET")
        self.mail_from = os.getenv("MAIL_FROM", "ayria@tecia.app")
        self.mail_from_name = os.getenv("MAIL_FROM_NAME", "AYRIA")
        self.api_base = "https://api.turbo-smtp.com/api/v2"
        self.timeout = float(os.getenv("TURBOSMTP_TIMEOUT", "30"))

        if not self.consumer_key or not self.consumer_secret:
            logger.warning(
                "⚠️ TurboSMTP credenciais não configuradas. "
                "Defina TURBOSMTP_CONSUMER_KEY e TURBOSMTP_CONSUMER_SECRET."
            )

    def _format_from(self) -> str:
        """Formato: 'Name <email@domain>' ou só 'email@domain'."""
        if self.mail_from_name:
            return f"{self.mail_from_name} <{self.mail_from}>"
        return self.mail_from

    def _format_recipients(self, emails: List[str]) -> str:
        """Vários emails separados por vírgula."""
        return ",".join(emails)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> dict:
        """
        Envia email via TurboSMTP API v2.

        Returns: dict com `message` ("OK") e `mid` (message ID).
        Raises: EmailServiceError em caso de falha.
        """
        if not self.consumer_key or not self.consumer_secret:
            raise EmailServiceError(
                "TurboSMTP não configurado. Email NÃO foi enviado. "
                "Verifique TURBOSMTP_CONSUMER_KEY e TURBOSMTP_CONSUMER_SECRET."
            )

        # Payload no formato da API v2 (string-based, NÃO objeto)
        payload = {
            "from": self._format_from(),
            "to": to_email,
            "subject": subject,
            "content": body_text or self._html_to_text(body_html),
            "html_content": body_html,
        }
        if cc:
            payload["cc"] = self._format_recipients(cc)
        if bcc:
            payload["bcc"] = self._format_recipients(bcc)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_base}/mail/send",
                    json=payload,
                    headers={
                        "consumerKey": self.consumer_key,
                        "consumerSecret": self.consumer_secret,
                        "Content-Type": "application/json",
                    },
                )

            if resp.status_code >= 400:
                logger.error(f"TurboSMTP error {resp.status_code}: {resp.text}")
                raise EmailServiceError(
                    f"TurboSMTP retornou {resp.status_code}: {resp.text[:300]}"
                )

            data = resp.json() if resp.text else {}
            logger.info(f"✅ Email enviado pra {to_email}: {subject} (mid={data.get('mid')})")
            return data

        except httpx.TimeoutException:
            raise EmailServiceError(f"Timeout ({self.timeout}s) ao chamar TurboSMTP")
        except httpx.RequestError as e:
            raise EmailServiceError(f"Erro de rede TurboSMTP: {e}")

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Strip HTML básico pra gerar text/plain."""
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text


# Singleton
_client: Optional[TurboSMTPClient] = None


def get_email_client() -> TurboSMTPClient:
    global _client
    if _client is None:
        _client = TurboSMTPClient()
    return _client
