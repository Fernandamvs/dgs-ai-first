"""Executa testes de validacao do pipeline de RAG da NovaTech."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from busca import buscar_chunks
from montagem_prompt import montar_prompt


PERGUNTAS_TESTE: list[str] = [
    "Qual o prazo para solicitar devolução de mercadoria?",
    "Posso devolver uma carga perigosa?",
    "Qual o SLA do cliente Gold para incidentes críticos?",
    "Qual o multiplicador de frete especial para o Nordeste?",
    "Qual o frete para uma carga de 300kg para São Paulo?",
]

SEPARADOR = "=" * 90
MENSAGEM_CHROMA_NAO_INICIALIZADO = (
    "Nao foi possivel executar a busca no ChromaDB. "
    "Verifique se a ingestao foi executada e rode ingestao.py primeiro."
)


def _detectar_erro_chromadb_nao_inicializado(error: Exception) -> bool:
    """Identifica erros comuns de banco vetorial nao inicializado."""
    class_name = error.__class__.__name__.lower()
    message = str(error).lower()
    return (
        "collection" in message
        or "does not exist" in message
        or "not found" in message
        or "no such table" in message
        or "invalidcollection" in class_name
        or "notfound" in class_name
    )


def _serializar_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    """Mantem apenas os campos necessarios no JSON de saida."""
    score_raw = chunk.get("score")
    score = float(score_raw) if isinstance(score_raw, (int, float)) else None
    return {
        "texto": str(chunk.get("texto") or ""),
        "fonte": str(chunk.get("fonte") or ""),
        "versao": str(chunk.get("versao") or ""),
        "score": score,
        "classificacao": str(chunk.get("classificacao") or ""),
    }


def executar_testes() -> list[dict[str, Any]]:
    """Executa os testes de perguntas e retorna resultados brutos."""
    resultados: list[dict[str, Any]] = []

    for indice, pergunta in enumerate(PERGUNTAS_TESTE, start=1):
        print(SEPARADOR)
        print(f"TESTE {indice}/{len(PERGUNTAS_TESTE)}")
        print(f"Pergunta: {pergunta}\n")

        try:
            chunks = buscar_chunks(pergunta)
        except Exception as error:
            if _detectar_erro_chromadb_nao_inicializado(error):
                print(MENSAGEM_CHROMA_NAO_INICIALIZADO)
                raise RuntimeError(MENSAGEM_CHROMA_NAO_INICIALIZADO) from error
            raise

        print("Chunks recuperados:")
        if not chunks:
            print("- Nenhum chunk recuperado.")
        for chunk_index, chunk in enumerate(chunks, start=1):
            print(
                f"- [{chunk_index}] score={chunk.get('score')} "
                f"fonte={chunk.get('fonte')} "
                f"versao={chunk.get('versao')} "
                f"classificacao={chunk.get('classificacao')}"
            )

        prompt = montar_prompt(pergunta, chunks)
        print("\nPrompt completo:")
        print(prompt)
        print(SEPARADOR)
        print()

        resultados.append(
            {
                "pergunta": pergunta,
                "chunks": [_serializar_chunk(chunk) for chunk in chunks],
                "prompt": prompt,
            }
        )

    return resultados


def salvar_resultados(resultados: list[dict[str, Any]]) -> Path:
    """Persiste os resultados no arquivo JSON esperado."""
    output_path = Path(__file__).resolve().parent / "resultados-brutos.json"
    output_path.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


if __name__ == "__main__":
    resultados_brutos = executar_testes()
    arquivo_saida = salvar_resultados(resultados_brutos)
    print(f"Resultados salvos em: {arquivo_saida}")
