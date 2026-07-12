"""Etapa de busca semantica para o pipeline de RAG da NovaTech."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

try:
    from config import CHROMA_DIR, COLLECTION_NAME, DEFAULT_TOP_K, EMBEDDING_MODEL
except ImportError:
    from config import (  # type: ignore
        CHROMA_PATH as CHROMA_DIR,
        COLLECTION_NAME,
        EMBEDDING_MODEL,
        TOP_K as DEFAULT_TOP_K,
    )


ALLOWED_CLASSIFICATIONS = {"normativo", "procedimento", "contratual", "informal"}
BASE_DIR = Path(__file__).resolve().parent


def resolve_path(base_dir: Path | str, target_dir: Path | str) -> Path:
    """Resolve caminho absoluto com base em um diretorio base."""
    base = Path(base_dir)
    target = Path(target_dir)
    if target.is_absolute():
        return target
    return (base / target).resolve()


def normalize_distances(distances: list[float]) -> list[float]:
    """Normaliza distancias para o intervalo [0, 1]."""
    if not distances:
        return []

    min_distance = min(distances)
    max_distance = max(distances)
    if max_distance == min_distance:
        return [0.0 for _ in distances]

    scale = max_distance - min_distance
    return [(distance - min_distance) / scale for distance in distances]


def build_result_item(document: str, metadata: dict[str, Any], score: float) -> dict[str, Any]:
    """Monta o dicionario padrao de retorno da busca."""
    raw_classification = str(metadata.get("classificacao", "informal")).lower()
    classification = raw_classification if raw_classification in ALLOWED_CLASSIFICATIONS else "informal"

    result: dict[str, Any] = {
        "texto": document,
        "fonte": metadata.get("doc_id"),
        "titulo": metadata.get("titulo"),
        "classificacao": classification,
        "confiavel": bool(metadata.get("confiavel", False)),
        "versao": metadata.get("versao"),
        "titulo_secao": metadata.get("titulo_secao"),
        "score": round(score, 4),
    }

    if "obsoleto_por" in metadata:
        result["obsoleto_por"] = metadata["obsoleto_por"]

    return result


def buscar_chunks(pergunta: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """Busca os chunks mais similares no ChromaDB para uma pergunta."""
    if not pergunta.strip():
        raise ValueError("A pergunta nao pode ser vazia.")
    if top_k <= 0:
        raise ValueError("top_k deve ser maior que zero.")

    chroma_dir = resolve_path(BASE_DIR, CHROMA_DIR)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_collection(name=COLLECTION_NAME)

    model = SentenceTransformer(EMBEDDING_MODEL)
    query_embedding = model.encode(pergunta).tolist()

    query_result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = (query_result.get("documents") or [[]])[0]
    metadatas = (query_result.get("metadatas") or [[]])[0]
    distances = [float(distance) for distance in (query_result.get("distances") or [[]])[0]]
    normalized_distances = normalize_distances(distances)

    results: list[dict] = []
    for document, metadata, normalized_distance in zip(documents, metadatas, normalized_distances):
        safe_metadata = metadata or {}
        similarity_score = 1.0 - normalized_distance
        results.append(build_result_item(document, safe_metadata, similarity_score))

    return results


def format_results(pergunta: str, resultados: list[dict[str, Any]]) -> str:
    """Formata resultados para exibicao em linha de comando."""
    if not resultados:
        return f"Pergunta: {pergunta}\nNenhum resultado encontrado."

    lines = [f"Pergunta: {pergunta}", ""]
    for idx, item in enumerate(resultados, start=1):
        lines.extend(
            [
                f"[{idx}] score={item['score']}",
                f"  titulo: {item['titulo']}",
                f"  fonte: {item['fonte']}",
                f"  classificacao: {item['classificacao']}",
                f"  confiavel: {item['confiavel']}",
                f"  versao: {item['versao']}",
                f"  titulo_secao: {item['titulo_secao']}",
            ]
        )
        if "obsoleto_por" in item:
            lines.append(f"  obsoleto_por: {item['obsoleto_por']}")
        lines.append(f"  texto: {item['texto']}")
        lines.append("")

    return "\n".join(lines).strip()


def parse_args() -> argparse.Namespace:
    """Processa argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description="Busca semantica no ChromaDB da NovaTech.")
    parser.add_argument("pergunta", nargs="+", help="Pergunta para buscar chunks relevantes.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Quantidade de chunks a retornar.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    pergunta_cli = " ".join(args.pergunta).strip()
    resultados_cli = buscar_chunks(pergunta_cli, top_k=args.top_k)
    print(format_results(pergunta_cli, resultados_cli))
