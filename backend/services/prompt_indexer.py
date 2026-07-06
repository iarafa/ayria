"""
AYRIA - Prompt Indexer

Indexa os arquivos .md em backend/prompts/ na coleção Qdrant `conhecimento_geral`
para que o RAG possa consultá-los em tempo real.

Por que indexar?
- A Ayria consulta a coleção `conhecimento_geral` em cada mensagem.
- Os .md de prompt são a "constituição cognitiva" — devem ser encontrados semanticamente.
- Se não indexar, o RAG pode retornar lixo.

Estratégia:
- Cada .md vira 1-3 chunks (split por seção ## ou por tamanho ~2000 chars).
- Cada chunk recebe metadata {source: 'prompt_xxx', type: 'prompt_module', key, version}.
- Permite filtrar/recuperar por key no Qdrant.
"""
from pathlib import Path
from typing import List, Dict
import logging
import uuid

from services.pdf_processor import PDFProcessor
from services.vector_service import VectorService

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def chunk_markdown(text: str, max_chars: int = 2000) -> List[str]:
    """
    Divide markdown em chunks por seção (## ou maior).
    Se uma seção for muito grande, divide por parágrafos.
    """
    chunks = []
    sections: List[str] = []
    current: List[str] = []

    for line in text.split("\n"):
        if line.startswith("## ") and current:
            sections.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))

    for sec in sections:
        if len(sec) <= max_chars:
            chunks.append(sec.strip())
        else:
            # divide por parágrafos
            paragraphs = sec.split("\n\n")
            buf: List[str] = []
            for p in paragraphs:
                if sum(len(x) for x in buf) + len(p) > max_chars and buf:
                    chunks.append("\n\n".join(buf).strip())
                    buf = [p]
                else:
                    buf.append(p)
            if buf:
                chunks.append("\n\n".join(buf).strip())

    return [c for c in chunks if len(c) > 50]  # descarta pedaços minúsculos


async def index_all_prompts(recreate: bool = False) -> Dict:
    """
    Indexa todos os .md de backend/prompts/ na coleção conhecimento_geral.

    Args:
        recreate: se True, deleta docs antigos da fonte 'prompt_*' antes de reindexar.

    Returns:
        dict com stats: {files, chunks, errors}
    """
    pdf_proc = PDFProcessor()
    vec = VectorService()
    files = sorted(PROMPTS_DIR.glob("*.md"))

    if recreate:
        try:
            vec.client.delete(
                collection_name="conhecimento_geral",
                points_selector={
                    "filter": {
                        "must": [{"key": "type", "match": {"value": "prompt_module"}}]
                    }
                },
            )
            logger.info("🗑️ Docs antigos do tipo 'prompt_module' removidos.")
        except Exception as e:
            logger.warning(f"Erro limpando docs antigos (continuando): {e}")

    total_chunks = 0
    errors: List[str] = []

    for md in files:
        key = md.stem  # ex: prompt_numerologia → 'prompt_numerologia'
        short_key = key.replace("prompt_", "", 1)  # 'numerologia'
        if key == "prompt_base":
            short_key = "constituicao_base"
            type_label = "constituicao"
        else:
            type_label = "modulo"

        content = md.read_text(encoding="utf-8")
        chunks = chunk_markdown(content)

        logger.info(f"📄 {key}: {len(chunks)} chunks")

        for idx, chunk in enumerate(chunks):
            try:
                emb = await pdf_proc.generate_embedding(chunk)
                # UUID determinístico pra permitir reindex sem duplicar
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{key}#chunk{idx}"))
                await vec.upsert(
                    collection="conhecimento_geral",
                    text=chunk,
                    embedding=emb,
                    payload={
                        "source": key,
                        "type": "prompt_module",
                        "key": short_key,
                        "type_label": type_label,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "version": "1.0",
                        "path": str(md.relative_to(PROMPTS_DIR.parent)),
                    },
                    point_id=point_id,
                )
                total_chunks += 1
            except Exception as e:
                errors.append(f"{key} chunk {idx}: {e}")
                logger.error(f"❌ Erro indexando {key}#{idx}: {e}")

    return {
        "files": len(files),
        "chunks": total_chunks,
        "errors": errors,
        "sources": [f.stem for f in files],
    }


async def _index_single(md_path: Path) -> dict:
    """Indexa um único .md (helper pra endpoints admin)."""
    pdf_proc = PDFProcessor()
    vec = VectorService()
    key = md_path.stem
    short_key = (
        "constituicao_base" if key == "prompt_base" else key.replace("prompt_", "", 1)
    )
    type_label = "constituicao" if key == "prompt_base" else "modulo"

    content = md_path.read_text(encoding="utf-8")
    chunks = chunk_markdown(content)
    errors: List[str] = []

    for idx, chunk in enumerate(chunks):
        try:
            emb = await pdf_proc.generate_embedding(chunk)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{key}#chunk{idx}"))
            await vec.upsert(
                collection="conhecimento_geral",
                text=chunk,
                embedding=emb,
                payload={
                    "source": key,
                    "type": "prompt_module",
                    "key": short_key,
                    "type_label": type_label,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "version": "1.0",
                    "path": f"prompts/{key}.md",
                },
                point_id=point_id,
            )
        except Exception as e:
            errors.append(f"chunk {idx}: {e}")

    return {"chunks": len(chunks), "errors": errors}


async def list_indexed_prompts() -> List[Dict]:
    """Lista todos os docs indexados com metadata."""
    vec = VectorService()
    try:
        points, _ = vec.client.scroll(
            collection_name="conhecimento_geral",
            scroll_filter={
                "must": [{"key": "type", "match": {"value": "prompt_module"}}]
            },
            limit=200,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as e:
        logger.warning(f"scroll falhou: {e}")
        return []

    by_source: Dict[str, Dict] = {}
    for p in points:
        src = p.payload.get("source", "?")
        if src not in by_source:
            by_source[src] = {
                "source": src,
                "key": p.payload.get("key"),
                "type_label": p.payload.get("type_label"),
                "version": p.payload.get("version"),
                "chunks": 0,
                "first_chunk": p.payload.get("text", "")[:200],
            }
        by_source[src]["chunks"] += 1

    return sorted(by_source.values(), key=lambda x: x["source"])


async def delete_prompt_source(source: str) -> int:
    """Remove do Qdrant todos os chunks de uma fonte (ex: 'prompt_numerologia')."""
    vec = VectorService()
    try:
        before = vec.client.count(
            collection_name="conhecimento_geral",
            count_filter={"must": [{"key": "source", "match": {"value": source}}]},
        ).count
        vec.client.delete(
            collection_name="conhecimento_geral",
            points_selector={
                "filter": {
                    "must": [{"key": "source", "match": {"value": source}}]
                }
            },
        )
        return before
    except Exception as e:
        logger.warning(f"Erro deletando {source}: {e}")
        return 0