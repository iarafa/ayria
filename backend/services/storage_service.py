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
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER", "ayria")
        self.use_local = os.getenv("AZURE_STORAGE_LOCAL_FALLBACK", "false").lower() == "true"

        # Tenta Azure via SAS URL (mais simples, sem precisar da connection string)
        self.sas_url = os.getenv("AZURE_STORAGE_SAS_URL", "").strip()
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()

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
    ) -> dict:
        """
        Upload de arquivo. Retorna dict com:
        - url: URL pública
        - path: path/blob name
        - size_bytes: tamanho
        - storage: "azure" ou "local"
        """
        # Gera nome único (filename pode ser SpooledTemporaryFile ou str)
        if hasattr(filename, 'name'):
            filename = filename.name
        ext = os.path.splitext(str(filename))[1]
        unique_name = f"{uuid.uuid4()}{ext}"

        # Tenta Azure primeiro
        if not self.use_local and self._azure_container:
            try:
                blob_client = self._azure_container.get_blob_client(unique_name)
                blob_client.upload_blob(
                    file_bytes,
                    overwrite=True,
                    content_type=content_type or "application/octet-stream",
                )
                url = blob_client.url
                logger.info(f"✅ Upload Azure: {unique_name} ({len(file_bytes)} bytes)")
                return {
                    "url": url,
                    "path": unique_name,
                    "size_bytes": len(file_bytes),
                    "storage": "azure",
                    "uploaded_at": datetime.utcnow().isoformat() + "Z",
                }
            except Exception as e:
                logger.error(f"❌ Upload Azure falhou: {e}. Fallback local.")

        # Fallback local
        local_path = f"/app/uploads/{unique_name}"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        return {
            "url": f"/uploads/{unique_name}",  # URL local (servida pelo FastAPI static)
            "path": local_path,
            "size_bytes": len(file_bytes),
            "storage": "local",
            "uploaded_at": datetime.utcnow().isoformat() + "Z",
        }

    async def delete(self, path: str) -> bool:
        """Deleta arquivo"""
        if not self.use_local and self._azure_container and not path.startswith("/"):
            try:
                blob_client = self._azure_container.get_blob_client(path)
                blob_client.delete_blob()
                logger.info(f"🗑️ Azure blob deletado: {path}")
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