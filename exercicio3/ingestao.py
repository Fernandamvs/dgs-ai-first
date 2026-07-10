"""Etapa de ingestao para o pipeline de RAG da NovaTech."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

try:
    from config import (
        BASE_DIR,
        CHROMA_DIR,
        COLLECTION_NAME,
        DOC_METADATA,
        DOCS_DIR,
        EMBEDDING_MODEL,
        SOURCE_FILES,
    )
except ImportError:
    from config import (  # type: ignore
        CHROMA_PATH as CHROMA_DIR,
        COLLECTION_NAME,
        DOCS_PATH as DOCS_DIR,
        DOCS_PARA_INGERIR as SOURCE_FILES,
        EMBEDDING_MODEL,
    )

    BASE_DIR = Path(__file__).resolve().parent
    DOC_METADATA: dict[str, dict[str, Any]] = {file_name: {} for file_name in SOURCE_FILES}


CHUNK_MAX_TOKENS = 600
HEADING_RE = re.compile(r"^(##|###)\s+(.*)$")


def estimate_tokens(text: str) -> int:
    """Estima tokens com base em palavras/4."""
    words = len(re.findall(r"\S+", text))
    if words == 0:
        return 0
    return math.ceil(words / 4)


def split_markdown_sections(content: str, source_name: str) -> list[tuple[str, list[str]]]:
    """Separa markdown por secoes iniciadas em heading ## ou ###."""
    lines = content.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = source_name
    current_lines: list[str] = []

    for line in lines:
        match = HEADING_RE.match(line.strip())
        if match:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    return sections


def build_blocks(section_lines: list[str]) -> list[list[str]]:
    """Cria blocos de linhas preservando tabelas markdown inteiras."""
    blocks: list[list[str]] = []
    i = 0

    while i < len(section_lines):
        line = section_lines[i]
        if line.lstrip().startswith("|"):
            table_block: list[str] = []
            while i < len(section_lines) and section_lines[i].lstrip().startswith("|"):
                table_block.append(section_lines[i])
                i += 1
            blocks.append(table_block)
            continue

        blocks.append([line])
        i += 1

    return blocks


def split_section_chunks(section_lines: list[str], max_tokens: int) -> list[str]:
    """Quebra uma secao em sub-chunks sem dividir blocos de tabela."""
    blocks = build_blocks(section_lines)
    chunks: list[str] = []
    current_lines: list[str] = []

    for block in blocks:
        candidate_lines = current_lines + block
        candidate_text = "\n".join(candidate_lines).strip()
        if current_lines and estimate_tokens(candidate_text) > max_tokens:
            chunks.append("\n".join(current_lines).strip())
            current_lines = block
            continue

        current_lines = candidate_lines

    if current_lines:
        chunks.append("\n".join(current_lines).strip())

    return [chunk for chunk in chunks if chunk]


def resolve_path(base_dir: Path | str, target_dir: Path | str) -> Path:
    """Resolve caminho absoluto com base em um diretorio base."""
    base = Path(base_dir)
    target = Path(target_dir)
    if target.is_absolute():
        return target
    return (base / target).resolve()


def ingest_documents() -> None:
    """Executa ingestao, embedding e persistencia dos chunks no ChromaDB."""
    docs_dir = resolve_path(BASE_DIR, DOCS_DIR)
    chroma_dir = resolve_path(BASE_DIR, CHROMA_DIR)

    all_chunks: list[str] = []
    all_metadatas: list[dict[str, Any]] = []
    all_ids: list[str] = []
    chunk_count_by_doc: dict[str, int] = {}

    for source_file in SOURCE_FILES:
        file_path = docs_dir / source_file
        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"[AVISO] Arquivo nao encontrado: {file_path}")
            chunk_count_by_doc[source_file] = 0
            continue

        section_chunks: list[tuple[str, str]] = []
        for section_title, section_lines in split_markdown_sections(content, source_file):
            chunks = split_section_chunks(section_lines, CHUNK_MAX_TOKENS)
            for chunk in chunks:
                section_chunks.append((section_title, chunk))

        chunk_count_by_doc[source_file] = len(section_chunks)
        fixed_metadata = DOC_METADATA.get(source_file, {})

        for chunk_index, (section_title, chunk_text) in enumerate(section_chunks):
            metadata = {
                **fixed_metadata,
                "titulo_secao": section_title,
                "chunk_index": chunk_index,
            }
            all_chunks.append(chunk_text)
            all_metadatas.append(metadata)
            all_ids.append(f"{source_file}::chunk::{chunk_index}")

    if not all_chunks:
        print("Nenhum chunk foi gerado. Nada para persistir no ChromaDB.")
        print("\nResumo de ingestao:")
        for doc_name, count in chunk_count_by_doc.items():
            print(f"- {doc_name}: {count} chunk(s)")
        print("- Total geral: 0 chunk(s)")
        return

    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(all_chunks, show_progress_bar=True).tolist()

    client = chromadb.PersistentClient(path=str(chroma_dir))
    existing_collections = {collection.name for collection in client.list_collections()}
    if COLLECTION_NAME in existing_collections:
        client.delete_collection(name=COLLECTION_NAME)
    collection = client.create_collection(name=COLLECTION_NAME)

    collection.add(
        ids=all_ids,
        documents=all_chunks,
        metadatas=all_metadatas,
        embeddings=embeddings,
    )

    print("\nResumo de ingestao:")
    for doc_name, count in chunk_count_by_doc.items():
        print(f"- {doc_name}: {count} chunk(s)")
    print(f"- Total geral: {len(all_chunks)} chunk(s)")


if __name__ == "__main__":
    ingest_documents()
