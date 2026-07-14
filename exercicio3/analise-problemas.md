# Análise de Problemas — Pipeline de RAG NovaTech

> Baseado em `resultados-testes.md` (5 testes) e na inspeção do código-fonte do pipeline (`config.py`, `ingestao.py`, `busca.py`, `montagem_prompt.py`) e dos documentos originais em `../docs/`. Sempre que possível, a causa raiz foi confirmada lendo o código real, não apenas inferida a partir do sintoma.

---

## Problema 1 — Metadados de origem nunca chegam ao chunk (fonte/versão/classificação sempre vazios)

### Evidência
Em **100% dos chunks dos 5 testes**, `fonte = desconhecido`, `versão = N/A` e `classificacao = informal`, como o próprio `resultados-testes.md` observa na introdução e no resumo final. Isso acontece mesmo para chunks que vêm de documentos claramente normativos ou contratuais — ex.: no Teste 3, o chunk "3. Definição de incidente crítico" (que é da **SLA-2024**, um documento explicitamente marcado como *"Documento contratual — os SLAs listados aqui são compromissos formais com o cliente"* em `docs/SLA-2024-tabela-sla-clientes.md:6`) chega ao LLM classificado como `informal`, no mesmo nível de confiança que uma nota do FAQ.

### Causa raiz
É um bug de **configuração/ingestão**, não de chunking nem de modelo de embedding. Em [ingestao.py:13-33](ingestao.py#L13-L33):

```python
try:
    from config import (
        BASE_DIR, CHROMA_DIR, COLLECTION_NAME, DOC_METADATA,
        DOCS_DIR, EMBEDDING_MODEL, SOURCE_FILES,
    )
except ImportError:
    from config import (
        CHROMA_PATH as CHROMA_DIR, COLLECTION_NAME,
        DOCS_PATH as DOCS_DIR, DOCS_PARA_INGERIR as SOURCE_FILES,
        EMBEDDING_MODEL,
    )
    BASE_DIR = Path(__file__).resolve().parent
    DOC_METADATA: dict[str, dict[str, Any]] = {file_name: {} for file_name in SOURCE_FILES}
```

`config.py` atual só define `CHROMA_PATH`, `COLLECTION_NAME`, `EMBEDDING_MODEL`, `DOCS_PATH`, `CHUNK_MAX_TOKENS`, `TOP_K` e `DOCS_PARA_INGERIR` — **não existe `DOC_METADATA`, `BASE_DIR`, `CHROMA_DIR`, `DOCS_DIR` nem `SOURCE_FILES`**. O `try` sempre falha com `ImportError` e o código cai silenciosamente no `except`, que gera `DOC_METADATA` como um **dicionário vazio para cada arquivo**. Ou seja: o pipeline foi desenhado para receber `doc_id`, `titulo`, `versao`, `classificacao` e `confiavel` por documento (esses campos são consumidos em [busca.py:57-67](busca.py#L57-L67), inclusive um campo `obsoleto_por` já preparado para indicar substituição de versão), mas essa configuração nunca foi escrita em `config.py` — e o fallback mascara o erro em vez de falhar de forma visível.

Essa informação, aliás, já existe nos documentos-fonte (ex. `docs/POL-001-politica-devolucao.md` tem cabeçalho `**Versão:** 3.1` / `**Classificação:** Documento normativo`), só não é lida por `ingestao.py`, que extrai apenas `titulo_secao` e `chunk_index` ([ingestao.py:151-159](ingestao.py#L151-L159)).

### Proposta de correção
1. Popular `DOC_METADATA` em `config.py` com os dados reais de cada documento (refletindo os cabeçalhos que já existem nos `.md`), e alinhar os nomes das constantes para que o `try` principal do `ingestao.py` funcione sem cair no fallback:

```python
# config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "novatech_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DOCS_DIR = "../docs"
CHUNK_MAX_TOKENS = 600
DEFAULT_TOP_K = 4

SOURCE_FILES = [
    "FAQ-atendimento.md",
    "POL-001-politica-devolucao.md",
    "PROC-042-frete-especial-v1.md",
    "PROC-042-v2-frete-especial-revisado.md",
    "SLA-2024-tabela-sla-clientes.md",
]

DOC_METADATA = {
    "FAQ-atendimento.md": {
        "doc_id": "FAQ-atendimento", "titulo": "FAQ — Perguntas Frequentes do Time de Suporte",
        "versao": "não controlada", "classificacao": "informal", "confiavel": False,
    },
    "POL-001-politica-devolucao.md": {
        "doc_id": "POL-001", "titulo": "Política de Devolução de Mercadorias",
        "versao": "3.1", "classificacao": "normativo", "confiavel": True,
    },
    "PROC-042-frete-especial-v1.md": {
        "doc_id": "PROC-042", "titulo": "Procedimento de Cálculo de Frete Especial",
        "versao": "1.0", "classificacao": "procedimento", "confiavel": True,
        "obsoleto_por": "PROC-042 v2.0 (emitido em 10/11/2023)",
    },
    "PROC-042-v2-frete-especial-revisado.md": {
        "doc_id": "PROC-042", "titulo": "Procedimento de Cálculo de Frete Especial (Revisado)",
        "versao": "2.0", "classificacao": "procedimento", "confiavel": True,
    },
    "SLA-2024-tabela-sla-clientes.md": {
        "doc_id": "SLA-2024", "titulo": "Tabela de SLA por Tipo de Cliente",
        "versao": "2024.1", "classificacao": "contratual", "confiavel": True,
    },
}
```

2. Remover o `try/except ImportError` de `ingestao.py` e importar diretamente de `config` — um `ImportError` deve quebrar a ingestão em vez de silenciosamente gerar metadados vazios. Isso transforma uma falha silenciosa (dados errados persistidos no ChromaDB) em uma falha rápida e visível (`ingestao.py` não roda até `config.py` estar correto).
3. Depois de corrigir, **reindexar** (`python ingestao.py`) — o banco vetorial atual em `chroma_db/` já foi persistido com os metadados vazios e precisa ser regenerado.

---

## Problema 2 — Chunk normativo com a resposta exata não é recuperado; FAQ informal domina o ranking

### Evidência
No **Teste 3** ("Qual o SLA do cliente Gold para incidentes críticos?"), os 4 chunks recuperados foram: "Item 41 — SLA de resposta vs. resolução" (FAQ, score 1.00), "3. Definição de incidente crítico" (0.89), "5. Medição e reportes" (0.73) e "Item 15 — tier Platinum não existe" (0.00, irrelevante).

O problema: a resposta exata **existe** em `docs/SLA-2024-tabela-sla-clientes.md`, seção "2. Tabela de SLAs" — uma tabela markdown com a linha `Tempo de primeira resposta (incidentes críticos) | Até 30min | Até 1h | Até 2h` e `Tempo de resolução (incidentes críticos) | Até 4h | Até 8h | Até 24h`. Essa tabela **não aparece entre os 4 chunks recuperados**. Em vez disso, quem ocupou o score mais alto (1.00) foi o "Item 41" do FAQ — uma nota informal e não validada que apenas parafraseia o assunto sem os números exatos de incidente crítico. O resultado: o Claude respondeu corretamente "Não encontrei o valor exato" (bom guardrail), mas isso só foi necessário porque **o chunk certo nunca chegou ao contexto** — não é um gap real da documentação, é uma falha de recuperação.

### Causa raiz
Não é chunking (confirmado em código: `build_blocks`/`split_section_chunks` em [ingestao.py:71-111](ingestao.py#L71-L111) tratam qualquer sequência de linhas iniciadas por `|` como um bloco atômico e nunca quebram uma tabela no meio — a tabela do SLA-2024 vira um chunk único e íntegro). O problema é **retrieval puramente vetorial, sem reranking, com `top_k` fixo e baixo**:
- `busca.py` faz apenas `collection.query(..., n_results=top_k)` ([busca.py:86-90](busca.py#L86-L90)) com `TOP_K = 4` ([config.py:6](config.py#L6)) e nenhum passo de reranking ou boost por classificação depois disso.
- O modelo de embedding (`all-MiniLM-L6-v2`, um modelo pequeno e genérico) tende a favorecer texto conversacional que repete o vocabulário da pergunta ("SLA de resposta e resolução... Gold tem 2h de resposta e 24h de resolução") — exatamente o estilo do FAQ — em detrimento de uma tabela densa com rótulos curtos e números, mesmo que a tabela contenha literalmente "incidentes críticos" e "Gold".
- Como a `classificacao` de todo chunk está sempre "informal" (Problema 1), não há sinal nenhum, hoje, para o sistema preferir a fonte contratual sobre a nota informal — mesmo que os metadados fossem corrigidos, não existe lógica de repriorização que os use.

### Proposta de correção
1. **Reranking em duas etapas**: buscar um pool maior de candidatos (`fetch_k`, ex. 15) e reordenar com um cross-encoder antes de cortar para `top_k`:

```python
from sentence_transformers import CrossEncoder

_reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def buscar_chunks(pergunta: str, top_k: int = DEFAULT_TOP_K, fetch_k: int = 15) -> list[dict]:
    ...
    query_result = collection.query(query_embeddings=[query_embedding], n_results=fetch_k, ...)
    candidatos = [build_result_item(doc, meta, 1.0) for doc, meta in zip(documents, metadatas)]

    pares = [(pergunta, c["texto"]) for c in candidatos]
    rerank_scores = _reranker.predict(pares)
    for candidato, score in zip(candidatos, rerank_scores):
        candidato["score"] = float(score)

    candidatos.sort(key=lambda c: c["score"], reverse=True)
    return candidatos[:top_k]
```

2. **Boost por classificação** (depende do Problema 1 estar corrigido) para reduzir o risco de uma nota informal superar uma fonte contratual/normativa quando os scores forem próximos:

```python
CLASSIFICATION_BOOST = {"normativo": 0.15, "contratual": 0.15, "procedimento": 0.10, "informal": 0.0}
resultado["score"] = round(resultado["score"] + CLASSIFICATION_BOOST.get(resultado["classificacao"], 0.0), 4)
```

3. **Contextualizar o chunk antes de embedar** (técnica de "contextual retrieval"): prefixar cada chunk com o título do documento + título da seção antes de gerar o embedding, para que uma tabela enxuta como a de SLA carregue contexto textual suficiente:

```python
texto_para_embedding = f"{titulo_documento} — {section_title}\n\n{chunk_text}"
```

---

## Problema 3 — Desambiguação de versão do PROC-042 funciona "por sorte", não por design

### Evidência
No Teste 4, a resposta correta (Nordeste = 1.5, versão de nov/2023) só foi possível porque o chunk "Item 8" do FAQ — que explica que existem duas versões da PROC-042 e que a mais recente tem multiplicadores mais altos — foi recuperado com **score 0.01**, o menor de todos os chunks do teste, e porque a seção da v2 por acaso tem "(atualizados em novembro/2023)" no próprio título, enquanto a v1 não tem data nenhuma no título (confirmado em `docs/PROC-042-v2-frete-especial-revisado.md:133` vs. `docs/PROC-042-frete-especial-v1.md:89`).

### Causa raiz
Combinação de dois fatores, ambos ligados à ausência de metadados estruturados de versão (Problema 1):
- Sem `doc_id`/`versao` populados, não há como o sistema saber programaticamente que dois chunks pertencem ao mesmo documento em versões diferentes — a única pista disponível é textual e incidental (a data no título de uma seção, presente em um documento e ausente no outro).
- O chunk que resolve o conflito (Item 8 do FAQ) tem score de similaridade **quase nulo** (0.01) e só entrou no contexto porque `top_k = 4` é generoso o bastante. Qualquer otimização futura comum em produção — reduzir `top_k`, aplicar um corte mínimo de score, ou o próprio reranking proposto no Problema 2 sem cuidado — pode descartar justamente esse chunk, e a desambiguação de versão deixaria de acontecer de forma silenciosa.

### Proposta de correção
Tratar conflito de versão como uma regra determinística no pipeline, não como algo que depende do LLM "encontrar por acaso" um chunk de baixo score:

```python
def detectar_conflito_de_versao(chunks: list[dict]) -> list[dict]:
    """Agrupa chunks por doc_id; se houver mais de uma versao do mesmo doc_id,
    garante que a nota de obsolescencia (obsoleto_por) entre no contexto."""
    por_doc_id: dict[str, list[dict]] = {}
    for chunk in chunks:
        por_doc_id.setdefault(chunk.get("fonte"), []).append(chunk)

    for doc_id, grupo in por_doc_id.items():
        versoes = {c.get("versao") for c in grupo if c.get("versao")}
        if len(versoes) > 1:
            for chunk in grupo:
                if chunk.get("obsoleto_por"):
                    chunk["_alerta_versao"] = (
                        f"ATENÇÃO: {doc_id} versão {chunk['versao']} foi substituída por "
                        f"{chunk['obsoleto_por']}. Use a versão mais recente como referência."
                    )
    return chunks
```

E reforçar no system prompt (`montagem_prompt.py`) que esse sinal estruturado tem prioridade sobre inferência textual:

```
- Se um chunk tiver o campo "obsoleto_por" preenchido, trate isso como sinal definitivo de
  qual versão é a vigente — não dependa de inferir a versão mais recente a partir do texto
  do chunk quando esse metadado estiver disponível.
```

Isso não invalida o comportamento atual do prompt (que já pede para alertar sobre conflitos de versão e funcionou nos testes) — o ponto é parar de depender de um chunk de score 0.01 sobreviver ao corte de `top_k` para que essa regra funcione.

---

## Sobre o caso 300kg / São Paulo (Teste 5)

Verificado especificamente por pedido: **não houve alucinação**. O Claude respondeu corretamente `"Não encontrei essa informação na documentação disponível"`, justificando que a PROC-042 só cobre cargas acima de 500kg (confirmado em `docs/PROC-042-v2-frete-especial-revisado.md:120`: *"aplicável a cargas com peso acima de 500kg"*) e que não há, na amostra de documentos, uma tabela de frete padrão para cargas abaixo desse limite (confirmado em `docs/anexo-a-documentacao-simulada-novatech.md:262`, que lista esse gap explicitamente). Esse teste valida o guardrail de "gap de cobertura" funcionando como esperado — não é um problema do pipeline, é a evidência de que a instrução do system prompt (`montagem_prompt.py:15-16`) está correta e sendo seguida.

---

## Resumo de causas raiz

| Problema | Chunking | Metadado ausente | Retrieval/embedding | Instrução de prompt |
|---|---|---|---|---|
| 1. Metadados sempre vazios | não | **sim (bug de import em `ingestao.py`)** | não | não |
| 2. FAQ supera tabela normativa | não | contribui (sem classificação, não dá pra repriorizar) | **sim (sem reranking, top_k baixo)** | não |
| 3. Versão do PROC-042 resolvida "por sorte" | não | **sim (sem doc_id/versao estruturado)** | contribui (chunk-chave com score 0.01) | reforço recomendado |
