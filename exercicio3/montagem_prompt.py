"""Montagem do prompt final do pipeline de RAG da NovaTech."""

from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """Você é o assistente de atendimento da NovaTech.

Instruções obrigatórias:
- Responder SOMENTE com base nos trechos de documentação fornecidos.
- Citar sempre a fonte (doc_id e nome do documento).
- Se houver chunks de versões diferentes do mesmo documento (ex: PROC-042 v1 e v2 juntos), alertar explicitamente sobre o conflito e indicar qual é a versão mais recente.
- Se algum chunk vier de documento com classificacao="informal" ou confiavel=False, avisar que aquela informação vem de fonte não validada.
- Se os chunks não cobrirem a pergunta, responder exatamente:
  "Não encontrei essa informação na documentação disponível."
"""


def _formatar_chunk(indice: int, chunk: dict[str, Any]) -> str:
    """Formata um chunk no padrão esperado para o prompt."""
    doc_id = str(chunk.get("doc_id") or chunk.get("fonte") or "desconhecido")
    titulo = str(chunk.get("titulo") or "Sem título")
    versao = str(chunk.get("versao") or "N/A")
    titulo_secao = str(chunk.get("titulo_secao") or "N/A")
    texto = str(chunk.get("texto") or "")

    score_raw = chunk.get("score")
    if isinstance(score_raw, (int, float)):
        score = f"{score_raw:.2f}"
    else:
        score = "0.00"

    return (
        f"[CHUNK {indice}] Fonte: {doc_id} — {titulo} (versão {versao})\n"
        f"Seção: {titulo_secao}\n"
        f"Score de similaridade: {score}\n"
        f"{texto}"
    )


def montar_prompt(pergunta: str, chunks: list[dict]) -> str:
    """Monta o prompt final em 3 partes para o pipeline de RAG.

    Args:
        pergunta: Pergunta original do atendente.
        chunks: Lista de chunks retornados por ``buscar_chunks()``.

    Returns:
        Prompt completo, contendo system prompt, contexto e pergunta.
    """
    contexto = (
        "\n\n".join(_formatar_chunk(indice, chunk) for indice, chunk in enumerate(chunks, start=1))
        if chunks
        else "Nenhum chunk recuperado."
    )

    return (
        "PARTE 1 — System prompt\n"
        f"{SYSTEM_PROMPT.strip()}\n\n"
        "PARTE 2 — Contexto\n"
        f"{contexto}\n\n"
        "PARTE 3 — Pergunta do atendente\n"
        f"Pergunta: {pergunta}"
    )


if __name__ == "__main__":
    # Exemplo de uso:
    # 1) Importe buscar_chunks de busca.py
    # 2) Gere os chunks relevantes para uma pergunta
    # 3) Monte o prompt final e envie para o LLM
    from busca import buscar_chunks

    pergunta_exemplo = "Qual é o prazo de devolução para produtos com defeito?"
    chunks_exemplo = buscar_chunks(pergunta_exemplo)
    prompt_final = montar_prompt(pergunta_exemplo, chunks_exemplo)

    print(prompt_final)
