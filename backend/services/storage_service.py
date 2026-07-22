"""
AYRIA - Storage Service (Azure Blob Storage)

Gerencia upload, listagem e deleção de documentos.

Variáveis de ambiente:
- AZURE_STORAGE_CONNECTION_STRING: string de conexão completa (preferred)
- OU AZURE_STORAGE_SAS_URL: URL SAS completa
- AZURE_STORAGE_CONTAINER: nome do container
- AZURE_STORAGE_LOCAL_FALLBACK: se "true", usa local mesmo tendo Azure
"""
import os
import logging
from typing import Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class StorageService:
    """Service de storage com Azure Blob primário e fallback local"""

    def __init__(self):
        # 19/07/2026: agora lê de `settings` (pydantic carrega .env) — antes usava
        # os.getenv direto, que não carrega o .env, então o Azure aparecia "Não configurado"
        # mesmo com AZURE_STORAGE_SAS_URL setado.
        from database import settings
        self.container_name = settings.AZURE_STORAGE_CONTAINER or "ayria"
        self.use_local = bool(settings.AZURE_STORAGE_LOCAL_FALLBACK)

        # Tenta Azure via SAS URL (mais simples, sem precisar da connection string)
        self.sas_url = (settings.AZURE_STORAGE_SAS_URL or "").strip()
        self.connection_string = (settings.AZURE_STORAGE_CONNECTION_STRING or "").strip()

        self._azure_client = None
        self._azure_container = None

        if not self.use_local:
            self._init_azure()

    def _init_azure(self):
        """Inicializa cliente Azure Blob"""
        try:
            from azure.storage.blob import BlobServiceClient, BlobClient

            if self.connection_string:
                self._azure_client = BlobServiceClient.from_connection_string(self.connection_string)
                logger.info("✅ Azure Blob: usando connection string")
            elif self.sas_url:
                # SAS URL especifica do container: https://acct.blob.core.windows.net/ayria?sp=...
                # Nesse caso o SAS soh autoriza esse container especifico (resource=c)
                # Entao pegamos direto o ContainerClient a partir da URL completa (com SAS)
                # O ContainerClient ja existe dentro de um service, mas como a SAS eh soh do container,
                # criamos o service client a partir da URL base + SAS como credential
                base_url = self.sas_url.split("?")[0]
                sas_token = self.sas_url.split("?")[1] if "?" in self.sas_url else None
                self._azure_client = BlobServiceClient(
                    account_url=base_url,
                    credential=sas_token,
                )
                logger.info("✅ Azure Blob: usando SAS URL de container")

            if self._azure_client:
                # Pega container direto (SAS ja autoriza o container)
                try:
                    self._azure_container = self._azure_client.get_container_client(self.container_name)
                    # Nao tenta exists() pq com SAS de container nao da pra listar containers
                    logger.info(f"📦 Container client '{self.container_name}' OK")
                except Exception as e:
                    logger.warning(f"⚠️ Nao consegui acessar container: {e}")
                    self._azure_container = None

        except ImportError:
            logger.warning("❌ azure-storage-blob nao instalado. Fallback local.")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar Azure: {e}")

    async def upload(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
        folder: str = "",
    ) -> dict:
        """
        Upload de arquivo. Retorna dict com:
        - url: URL pública
        - path: path/blob name
        - size_bytes: tamanho
        - storage: "azure" ou "local"
        - folder: pasta onde foi salvo

        Args:
            folder: subpasta dentro do container (ex: "avatar", "knowledge/conhecimento_geral")
                    NUNCA começa com /. Sempre termina sem /.
        """
        # Gera nome único (filename pode ser SpooledTemporaryFile ou str)
        if hasattr(filename, 'name'):
            filename = filename.name
        # 19/07/2026: preserva filename original (ex: backups com timestamp)
        # Para backups a gente quer ler pelo timestamp, não por UUID
        import re as _re
        safe_name = _re.sub(r'[^A-Za-z0-9._-]', '_', os.path.basename(str(filename)))
        ext = os.path.splitext(safe_name)[1]
        if ext:
            unique_name = safe_name
        else:
            unique_name = f"{uuid.uuid4()}{ext}"

        # Monta path final: {folder}/{uuid}.{ext} (se folder)
        folder_clean = folder.strip().strip("/").strip()
        if folder_clean:
            blob_path = f"{folder_clean}/{unique_name}"
        else:
            blob_path = unique_name

        # Tenta Azure primeiro
        if not self.use_local and self._azure_container:
            try:
                blob_client = self._azure_container.get_blob_client(blob_path)
                blob_client.upload_blob(
                    file_bytes,
                    overwrite=True,
                    content_type=content_type or "application/octet-stream",
                )
                url = blob_client.url
                logger.info(f"✅ Upload Azure OK: {blob_path} ({len(file_bytes)} bytes)")
                # Verificação: tenta HEAD no blob pra confirmar que existe
                try:
                    props = blob_client.get_blob_properties()
                    logger.info(f"   ✅ Blob verificado: size={props.size}, etag={props.etag}")
                except Exception as verify_err:
                    logger.warning(f"   ⚠️ Upload retornou OK mas HEAD falhou: {verify_err}")
                return {
                    "url": url,
                    "path": blob_path,
                    "size_bytes": len(file_bytes),
                    "storage": "azure",
                    "folder": folder_clean or None,
                    "uploaded_at": datetime.utcnow().isoformat() + "Z",
                }
            except Exception as e:
                logger.error(f"❌ Upload Azure falhou: {e}. Fallback local.")

        # Fallback local (só se Azure desabilitado OU upload falhou)
        local_path = f"/app/uploads/{blob_path}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        logger.warning(f"⚠️ FALLBACK LOCAL usado (Azure falhou ou desabilitado): {local_path}")

        return {
            "url": f"/uploads/{blob_path}",  # URL local (servida pelo FastAPI static)
            "path": local_path,
            "size_bytes": len(file_bytes),
            "storage": "local",
            "folder": folder_clean or None,
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        }

    async def delete(self, path: str) -> bool:
        """
        Deleta arquivo. Aceita:
        - URL completa do blob (com ou sem SAS): https://acct.blob.core.windows.net/ayria/folder/file.pdf?...
        - Blob path relativo: folder/file.pdf
        - Path local: /app/uploads/folder/file.pdf

        Extrai o blob_name correto (com pasta) antes de deletar.
        """
        blob_path = self._extract_blob_path(path)

        if not self.use_local and self._azure_container and not blob_path.startswith("/"):
            try:
                blob_client = self._azure_container.get_blob_client(blob_path)
                blob_client.delete_blob()
                logger.info(f"🗑️ Azure blob deletado: {blob_path}")
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao deletar do Azure: {e}")
                return False

        # Local
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"🗑️ Arquivo local deletado: {path}")
                return True
        except Exception as e:
            logger.error(f"❌ Erro ao deletar local: {e}")
        return False

    async def list_all(self, prefix: str = "") -> list:
        """Lista blobs (apenas Azure)"""
        if self._azure_container:
            try:
                blobs = []
                for blob in self._azure_container.list_blobs(name_starts_with=prefix):
                    blobs.append({
                        "name": blob.name,
                        "size": blob.size,
                        "created": blob.creation_time.isoformat() if blob.creation_time else None,
                        "url": f"{self._azure_container.url}/{blob.name}",
                    })
                return blobs
            except Exception as e:
                logger.error(f"❌ Erro listando Azure: {e}")
        return []

    @property
    def is_azure_active(self) -> bool:
        return not self.use_local and self._azure_container is not None

    def _extract_blob_path(self, path_or_url: str) -> str:
        """
        Extrai o blob_name (com pasta) de uma URL ou path.

        Aceita:
        - URL Azure: https://acct.blob.core.windows.net/ayria/folder/file.pdf?sig=...
        - Blob path: folder/file.pdf
        - Path local: /app/uploads/folder/file.pdf

        Retorna SEMPRE o blob_path relativo ao container (folder/file.pdf),
        sem query string (SAS).
        """
        s = (path_or_url or "").strip()
        if not s:
            return ""

        # Remove query string (SAS)
        if "?" in s:
            s = s.split("?", 1)[0]

        # Se for URL Azure (http/https), extrai path depois do container
        if s.startswith("http://") or s.startswith("https://"):
            # Formato: https://acct.blob.core.windows.net/{container}/{path}
            # ou: https://acct.blob.core.windows.net/{container}
            try:
                # Pega path depois do host
                without_scheme = s.split("://", 1)[1]  # acct.blob.core.windows.net/{container}/...
                path_part = without_scheme.split("/", 1)[1] if "/" in without_scheme else ""  # {container}/...
                # Remove container name do início
                container_prefix = f"{self.container_name}/"
                if path_part.startswith(container_prefix):
                    return path_part[len(container_prefix):]
                # fallback: tenta remover primeira pasta
                parts = path_part.split("/", 1)
                return parts[1] if len(parts) > 1 else ""
            except Exception:
                return ""

        # Se for path local (/app/uploads/folder/file.pdf)
        if s.startswith("/app/uploads/"):
            return s[len("/app/uploads/"):]

        # Senão, retorna como tá (já é blob path relativo)
        return s.lstrip("/")

    def get_status(self) -> dict:
        return {
            "storage_active": "azure" if self.is_azure_active else "local",
            "container": self.container_name,
            "use_local": self.use_local,
            "has_sas_url": bool(self.sas_url),
            "has_connection_string": bool(self.connection_string),
        }


# Singleton
storage_service = StorageService()

async def upload_user_avatar(
    user_id: str,
    filename: str,
    content_type: str,
    data: bytes,
    previous_url: Optional[str] = None,
) -> str:
    """
    Upload de foto de perfil do usuário.

    - Salva no Azure Blob Storage no path avatar/{user_id}/{uuid}.{ext}
    - Se previous_url for fornecida, deleta o avatar antigo
    - Retorna URL pública

    Path interno:
    storage_service.upload(folder="avatar/{user_id}") é usado (já lida com Azure/local fallback)
    """
    import re

    # Sanitiza filename pra evitar caracteres estranhos no path
    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)[:50] or "avatar"

    # Upload usando folder=avatar/{user_id} — upload() gera o UUID + extensão sozinho
    result = await storage_service.upload(
        file_bytes=data,
        filename=safe_filename,
        content_type=content_type,
        folder=f"avatar/{user_id}",
    )

    public_url = result.get("url") if isinstance(result, dict) else result

    # Tenta deletar avatar antigo (best-effort)
    if previous_url and previous_url != public_url:
        try:
            await storage_service.delete(previous_url)
        except Exception as e:
            logger.warning(f"Não conseguiu deletar avatar antigo {previous_url}: {e}")

    return public_url
