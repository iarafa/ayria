"""
AYRIA - Storage Service
Upload de documentos pro Azure Blob Storage.
Fallback local (filesystem) quando Azure não tá configurado.
"""
import os
import hashlib
from pathlib import Path
from typing import Optional, BinaryIO
import logging

from database import settings

logger = logging.getLogger(__name__)

# Path local de fallback
LOCAL_STORAGE = Path("/app/uploads")


class StorageService:
    """Cliente Azure Blob com fallback local"""
    
    def __init__(self):
        self.azure_client = None
        self.container_client = None
        self.use_local = True
        
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            try:
                from azure.storage.blob import BlobServiceClient
                self.azure_client = BlobServiceClient.from_connection_string(
                    settings.AZURE_STORAGE_CONNECTION_STRING
                )
                self.container_client = self.azure_client.get_container_client(
                    settings.AZURE_STORAGE_CONTAINER
                )
                # Garante container existe
                try:
                    self.container_client.create_container()
                    logger.info(f"Container Azure criado: {settings.AZURE_STORAGE_CONTAINER}")
                except Exception:
                    pass  # já existe
                
                self.use_local = False
                logger.info(f"Azure Blob Storage configurado: {settings.AZURE_STORAGE_CONTAINER}")
            except Exception as e:
                logger.warning(f"Azure Blob falhou, usando local: {e}")
                self.use_local = True
        else:
            logger.info("Azure Blob não configurado, usando storage local")
            LOCAL_STORAGE.mkdir(parents=True, exist_ok=True)
    
    async def upload(
        self,
        file_name: str,
        file_data: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> dict:
        """
        Upload arquivo. Retorna dict com url, provider, hash, size.
        """
        # Lê conteúdo pra calcular hash
        content = file_data.read()
        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)
        
        if self.use_local:
            # Fallback local
            dest = LOCAL_STORAGE / f"{file_hash[:16]}_{file_name}"
            dest.write_bytes(content)
            return {
                "url": f"local://{dest}",
                "provider": "local",
                "hash": file_hash,
                "size": file_size,
                "path": str(dest),
            }
        
        # Azure Blob
        blob_name = f"{file_hash[:16]}_{file_name}"
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(content, content_type=content_type, overwrite=True)
        
        return {
            "url": blob_client.url,
            "provider": "azure_blob",
            "hash": file_hash,
            "size": file_size,
            "blob_name": blob_name,
        }
    
    async def download(self, blob_name: str) -> bytes:
        """Baixa arquivo"""
        if self.use_local:
            return (LOCAL_STORAGE / blob_name).read_bytes()
        
        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.download_blob().readall()
    
    async def delete(self, blob_name: str):
        """Deleta arquivo"""
        if self.use_local:
            path = LOCAL_STORAGE / blob_name
            if path.exists():
                path.unlink()
            return
        
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.delete_blob()


# Singleton
storage_service = StorageService()
