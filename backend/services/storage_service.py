"""
AYRIA - Storage Service (Local Filesystem)
Salva arquivos em /app/uploads (volume Docker persistente).
"""
import os
import hashlib
from pathlib import Path
from typing import BinaryIO
import logging

logger = logging.getLogger(__name__)

# Path local de armazenamento
STORAGE_DIR = Path(os.environ.get("AYRIA_STORAGE_DIR", "/app/uploads"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class StorageService:
    """Storage local em filesystem"""

    async def upload(
        self,
        file_name: str,
        file_data: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> dict:
        """Upload arquivo. Retorna dict com path, hash, size."""
        content = file_data.read()
        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # Nome do arquivo: hash + nome original (evita colisão + dedup)
        safe_name = f"{file_hash[:16]}_{Path(file_name).name}"
        dest = STORAGE_DIR / safe_name
        dest.write_bytes(content)

        return {
            "path": str(dest),
            "provider": "local",
            "hash": file_hash,
            "size": file_size,
            "file_name": file_name,
            "stored_name": safe_name,
        }

    async def download(self, stored_name: str) -> bytes:
        """Lê arquivo do storage"""
        path = STORAGE_DIR / stored_name
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {stored_name}")
        return path.read_bytes()

    async def delete(self, stored_name: str) -> bool:
        """Deleta arquivo"""
        path = STORAGE_DIR / stored_name
        if path.exists():
            path.unlink()
            return True
        return False

    def get_path(self, stored_name: str) -> Path:
        """Retorna Path do arquivo"""
        return STORAGE_DIR / stored_name


storage_service = StorageService()
