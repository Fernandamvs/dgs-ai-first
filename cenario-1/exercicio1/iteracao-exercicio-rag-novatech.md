# Registro de Iteração — Exercício RAG NovaTech

**Data:** 2026-06-23
**Exercício:** Análise de Viabilidade Técnica de Assistente RAG

---

## Visão Geral da Iteração

```
[TURNO 1]  Prompt de análise técnica (persona: engenheiro sênior RAG)
              ↓
           Raciocínio interno por seção (desafios → estimativas → orçamento → chunking → validação)
              ↓
           Write → analise-viabilidade-rag-novatech.md  (v1.0)

[TURNO 2]  Prompt de revisão crítica (persona: revisor técnico sênior)
              ↓
           Leitura cruzada das seções em 3 dimensões
              ↓
           10 problemas identificados e rankeados
              ↓
           Write → cenario-1/analise-viabilidade-rag-novatech-final.md  (v1.1)

[TURNO 3]  "Gere um arquivo da iteração da nossa conversa"
              ↓
           Write → exercicio1/iteracao-exercicio-rag-novatech.md  (este arquivo)
```

---

## Turno 1 — Geração da Análise Inicial

### Prompt enviado (íntegra)

```
# Análise de Viabilidade Técnica — Assistente RAG para NovaTech

## Quem você é

Você é um engenheiro sênior de sistemas RAG com experiência em projetos corporativos de IA para operações e logística. Sua função aqui não é produzir um relatório executivo — é entregar uma análise técnica que um time de desenvolvimento consiga usar diretamente para tomar decisões de arquitetura.

RAG (Retrieval-Augmented Generation) é uma arquitetura em que o modelo de linguagem não responde apenas com base no seu treinamento, mas consulta documentos recuperados dinamicamente a cada pergunta. A qualidade do sistema depende de como esses documentos são processados, fragmentados e posicionados dentro da janela de contexto do modelo.

## Contexto do Projeto

A NovaTech é uma empresa de logística com 1.200 funcionários. Sua equipe de atendimento (45 pessoas) gasta em média 12 minutos por chamado consultando documentação interna. O objetivo é reduzir esse tempo para menos de 2 minutos com um assistente de IA integrado ao Microsoft Teams e SharePoint.

Fontes de documentação:
- SharePoint: ~800 documentos, PDF e Word
- Confluence: ~400 páginas wiki, HTML com macros e links internos
- Pasta de rede: ~50 planilhas, Excel com fórmulas interdependentes

Características técnicas relevantes:
- PDFs com tabelas de frete de 15+ colunas, fluxogramas embutidos como imagens, e alguns documentos escaneados que exigem OCR
- Wiki com links internos entre páginas e macros customizadas
- Planilhas com fórmulas interdependentes
- Atualização mensal por 3 áreas (Operações, Compliance, Comercial) sem processo unificado de revisão

Conceito-chave — Context Engineering aplicado a RAG:
1. Relevância — quais chunks são recuperados
2. Orçamento de atenção — quantos chunks cabem na janela de contexto
3. Posicionamento — onde os chunks ficam no prompt (efeito lost in the middle)
4. Competição por atenção — o que mais ocupa o contexto

## Modo de Trabalho

Antes de escrever cada seção, responda mentalmente:
- O que pode dar errado aqui especificamente para este tipo de documento?
- Estou sendo otimista demais nesta estimativa?
- Esta recomendação é consistente com o que escrevi nas seções anteriores?

Registre essa autocrítica dentro de cada seção — não apenas no final.

## Estrutura da Análise

### 1. Desafios por Tipo de Fonte
Para cada tipo: Desafio → Impacto na qualidade do RAG → Tratamento técnico recomendado
1.1 PDFs com tabelas complexas
1.2 PDFs escaneados (OCR)
1.3 Wiki Confluence com links internos
1.4 Planilhas com fórmulas interdependentes

### 2. Estimativa do Corpus em Tokens
Use: tokens ≈ palavras ÷ 0,75
Calcule para: ~800 PDFs (10 págs cada), ~400 páginas wiki (1.500 palavras cada), ~50 planilhas
Requisito: cálculos explícitos e verificáveis, todas as suposições declaradas.

### 3. Análise de Orçamento de Contexto
Parâmetros: janela 128k tokens, reserva ~2k, tokens efetivos ~126k.
Calcule chunks por query, efeito lost in the middle, ponto de limitação.

### 4. Estratégia de Chunking
Parâmetros por tipo de documento. Diferença hierárquico vs. flat e quando usar cada um.

### 5. Validação Crítica
Estimativas otimistas? Contradições entre seções? Itens em aberto? Risco mais subestimado?

## Formato de Saída
Arquivo Markdown `analise-viabilidade-rag-novatech.md`, sumário executivo ≤ 150 palavras.
```

### Passos executados para geração do arquivo

**Passo 1 — Raciocínio por seção antes de escrever**

Para cada subseção de desafios, a análise respondeu internamente às três perguntas do "Modo de Trabalho" antes de produzir o texto. Esse raciocínio alimentou diretamente as autocríticas embutidas ao final de cada subseção — o documento registra as dúvidas do autor, não apenas as certezas.

**Passo 2 — Seção 1: Desafios por tipo de fonte**

- *PDFs tabulares*: identificou que chunking por tamanho fixo quase certamente corta tabelas no meio, separando cabeçalhos de células. Recomendou serialização linha-a-linha com cabeçalho repetido. Autocrítica: serialização linha-a-linha infla o corpus 3–5× e pode introduzir ruído de duplicação.
- *OCR*: catalogou erros por tipo (confusão de caracteres, hifenização, espaçamento) e seu impacto assimétrico em embeddings. Recomendou score de confiança por chunk e dicionário de domínio. Autocrítica: score médio de confiança não detecta erros localizados em células críticas.
- *Confluence*: mapeou a cadeia de dependência entre páginas linkadas. Recomendou resolução de links até profundidade 2 e grafo de dependência. Autocrítica: resolução em profundidade 2 pode causar explosão combinatória.
- *Planilhas*: separou o problema de fórmulas opacas do problema de estrutura espacial perdida. Recomendou avaliação prévia das fórmulas e desnormalização. Autocrítica: VBA e referências externas falhariam silenciosamente.

**Passo 3 — Seção 2: Estimativas de tokens**

Declarou todas as suposições antes dos cálculos (500 palavras/página PDF, 3 abas/planilha, 240 células não-vazias/aba, razão palavras÷0,75). Realizou três cálculos em blocos separados e explícitos. Total apurado: ~6,4M tokens brutos.

**Passo 4 — Seção 3: Orçamento de contexto**

Calculou capacidade teórica (252 chunks) e identificou que ela não é operacional. Montou tabela de distribuição por query usando **500 tokens uniformes** para todos os tipos de chunk — esta escolha seria identificada como inconsistência na revisão do Turno 2. Descreveu o efeito *lost in the middle* e propôs estratégia de ordenação em sanduíche.

**Passo 5 — Seção 4: Chunking**

Definiu parâmetros distintos por tipo (PDFs estruturados: 400–500 tokens; OCR: 700–750; Confluence: 400–500; Excel: 300–600 por região lógica). Justificou a preferência por chunking hierárquico vs. flat com tabela comparativa.

**Passo 6 — Seção 5: Validação crítica**

Releu as seções anteriores e identificou: estimativas otimistas (500 palavras/página para OCR, volume de planilhas conservador), uma contradição entre Seções 3 e 4 que ficou apenas na autocrítica sem corrigir a tabela principal, e cinco itens em aberto. O risco de governança foi posicionado como risco dominante.

**Passo 7 — Geração do arquivo**

Ferramenta usada: `Write` — criou `analise-viabilidade-rag-novatech.md` na raiz do projeto (`c:\treinamento\dgs-ai-first\`).

### Arquivo gerado

- `analise-viabilidade-rag-novatech.md` (raiz do projeto) — 421 linhas

---

## Turno 2 — Revisão Crítica Independente + Versão Final

### Prompt enviado (íntegra)

```
# Revisão Crítica da Análise de Viabilidade RAG — NovaTech

## Sua função nesta etapa

Você é um revisor técnico sênior — não o autor do documento abaixo.
Sua função é exclusivamente identificar problemas. Não reescreva o documento.
Não produza uma versão melhorada. Apenas aponte falhas com precisão cirúrgica.

## O que procurar

Analise o documento em três dimensões:

1. Estimativas otimistas ou sem fundamento
   - Algum número foi assumido sem justificativa explícita?
   - Existe suposição implícita que não foi declarada?
   - Alguma projeção ignora variação real (ex: PDFs com 3 páginas vs. 80 páginas foram tratados como iguais)?

2. Riscos técnicos não considerados
   - Há etapas do pipeline onde a qualidade pode degradar silenciosamente?
   - OCR, tabelas e fórmulas foram tratados como problemas resolvíveis com uma única técnica — isso é realista para todos os casos?
   - O efeito lost in the middle foi tratado apenas teoricamente ou com implicações práticas reais na estratégia de chunking?

3. Inconsistências internas
   - Alguma recomendação da Seção X contradiz a Seção Y?
   - O orçamento de contexto calculado é compatível com a estratégia de chunking recomendada?
   - A estratégia de retrieval é compatível com os tamanhos de chunk sugeridos?

## Formato da revisão

Para cada problema encontrado:
Problema: [descrição objetiva em uma frase]
Localização: [seção ou trecho específico]
Impacto potencial: [o que pode falhar em produção por causa disso]
Sugestão de correção: [o que revisar — sem reescrever o trecho]

Ao final, indique:
- Os 3 problemas mais críticos para o sucesso do projeto
- O ponto mais forte da análise (o que foi bem tratado)

## Documento para revisão

@cenario-1/analise-viabilidade-rag-novatech.md

## Formato de saída

Após incorporar o feedback desta revisão ao documento original, salve a versão final corrigida como `analise-viabilidade-rag-novatech-final.md`.
```

### Passos executados para revisão e geração do arquivo final

**Passo 1 — Leitura cruzada em três dimensões**

O documento foi analisado de forma não-linear: para identificar inconsistências internas, cada seção foi comparada com as demais (Seção 3 vs. 4, Seção 1.4 vs. 2, Seção 5.2 vs. 2). Para identificar riscos técnicos, foi feita uma varredura por componente de pipeline (embedding → retrieval → re-ranking → ordenação → geração).

**Passo 2 — Identificação dos 10 problemas**

| # | Como foi descoberto |
|---|---|
| P1 (Budget vs. Chunking) | Comparação direta entre tabela da Seção 3.2 (15 × 500 tok) e parâmetros da Seção 4.2 (OCR=750, tabelas=800–1.000). A Seção 5.2 já havia identificado o problema mas não corrigiu a tabela principal. |
| P2 (Embeddings ausentes) | Varredura de todas as seções buscando menção a modelo de embeddings — nenhuma encontrada. Lacuna crítica que invalida estimativas de qualidade. |
| P3 (Grafo Confluence) | Seção 1.3 recomendava grafo de dependência em uma frase, sem nomear componentes, trade-offs ou alternativa MVP — subestimava o esforço em 2–4×. |
| P4 (Diacríticos PT-BR) | Tabela de erros OCR listava confusões ASCII mas não mencionava `ã`, `ç`, `é`, `ê`, `õ` — o padrão mais frequente em português. |
| P5 (Re-ranker) | Estratégia de sanduíche pressupunha re-ranking mas não especificava tipo (bi-encoder vs. cross-encoder), latência esperada, nem interação com `ocr_confidence`. |
| P6 (Descrições LLM) | Seção 1.4 recomendava geração de descrições de fórmulas sem definir: geração manual ou automática? Se LLM, quem revisa antes de indexar? |
| P7 (Chunks obsoletos) | Item 1 da Seção 5.3 misturava detecção de alteração de arquivo com invalidação de chunks no vector store — dois problemas operacionais distintos. |
| P8 (Query quality) | Nenhuma seção mencionava que atendentes usam linguagem informal ("frete rj 15k") — impacto direto na qualidade do embedding da query. |
| P9 (Fallback de headings) | Estratégia hierárquica dependia de headings no PDF sem quantificar quantos PDFs corporativos não têm essa estrutura. |
| P10 (Range de planilhas) | Cenário real de desnormalização estava na Seção 5.2 mas a tabela-resumo da Seção 2 ainda usava só o valor base (240k tokens). |

**Passo 3 — Ranking dos 3 mais críticos**

Critério aplicado: qual problema tem maior impacto em produção sem alertas visíveis nas métricas de retrieval?
1. P1 — afeta dimensionamento direto de infraestrutura e custo por query
2. P2 — a escolha do modelo de embeddings afeta tudo; sem ela, nenhuma estimativa de qualidade é verificável
3. P3 — subestimar a recuperação em grafo é o caminho mais provável para abandono de feature em produção

**Passo 4 — Identificação do ponto mais forte**

A Seção 5.4 (risco de governança) foi o único insight que não aparece em análises RAG convencionais: identificar que o risco dominante é organizacional e invisível para métricas técnicas. Preservado na v1.1 sem modificações.

**Passo 5 — Revisão como texto**

Os 10 problemas foram apresentados em resposta de texto com o formato solicitado (Problema / Localização / Impacto potencial / Sugestão de correção), seguidos do ranking dos 3 críticos e do ponto mais forte.

**Passo 6 — Incorporação cirúrgica na v1.1**

Cada correção foi aplicada no ponto exato do documento original, sem reescrever seções inteiras:

| # | Correção aplicada |
|---|---|
| P1 | Seção 3.2: tabela substituída por cenário misto (10×500 + 5×750 tokens); total atualizado para 13.450 tokens |
| P2 | Seção 3.5: nova subseção criada com critérios de seleção e processo de avaliação comparativa |
| P3 | Seção 1.3: parágrafo do grafo reescrito para decisão arquitetural com alternativa MVP e custo de implementação |
| P4 | Seção 1.2: linha de diacríticos PT-BR adicionada à tabela + nota explicativa sobre impacto em palavras-chave |
| P5 | Seção 3.3: cross-encoder especificado, latência estimada (150–400ms), fórmula de penalização OCR adicionada |
| P6 | Seção 1.4: parágrafo explicitando revisão humana obrigatória para descrições LLM-geradas |
| P7 | Seção 5.3: item 1 dividido em dois itens distintos; itens 6 e 7 adicionados (query understanding + acesso) |
| P8 | Seção 4.1: nota sobre query quality; Seção 5.3 item 6: query understanding como item em aberto |
| P9 | Seção 4.2: bloco de risco de fallback com recomendação de classificação prévia dos PDFs |
| P10 | Seção 2.3: cálculo de cenário real adicionado; tabela-resumo com coluna "cenário real" e range |

**Passo 7 — Geração do arquivo final**

Ferramenta usada: `Write` — criou `analise-viabilidade-rag-novatech-final.md` no diretório `cenario-1/`.

### Arquivo gerado

- `cenario-1/analise-viabilidade-rag-novatech-final.md` (v1.1)

---

## Artefatos Produzidos

| Arquivo | Versão | Turno | Ferramenta | Linhas |
|---|---|---|---|---|
| `analise-viabilidade-rag-novatech.md` | v1.0 | 1 | Write | 421 |
| `cenario-1/analise-viabilidade-rag-novatech-final.md` | v1.1 | 2 | Write | ~470 |
| `exercicio1/iteracao-exercicio-rag-novatech.md` | — | 3 | Write | este arquivo |

---

## Aprendizados Técnicos da Iteração

### O que a primeira persona (engenheiro) fez bem
- Autocrítica embutida em cada seção, não apenas no final — forçou honestidade durante a escrita
- Identificação do risco de governança como risco dominante e não-técnico (Seção 5.4)
- Cálculos explícitos e verificáveis com suposições declaradas antes dos números
- Distinção prática entre capacidade teórica (252 chunks) e operacional (~15 chunks)

### O que a segunda persona (revisor) forçou a corrigir
- Inconsistência entre orçamento calculado com chunks uniformes e chunking heterogêneo — o autor havia notado (Seção 5.2) mas não corrigiu a tabela principal
- Ausência completa do modelo de embeddings — decisão que afeta tudo e estava invisível
- Diferença entre gerenciar versões de documentos e gerenciar chunks obsoletos no vector store — dois problemas distintos tratados como um

### Padrão de iteração aplicado

```
Prompt com persona específica + modo de trabalho explícito
  → Geração com autocrítica embutida por seção
    → Prompt com persona oposta + restrição de não reescrever
      → Revisão em dimensões nomeadas → problemas rankeados por criticidade
        → Incorporação cirúrgica (correção no ponto exato, sem reescrita total)
          → Registro do delta entre versões com prompts e passos
```

### Por que separar as personas funciona

O autor conhece as intenções por trás de cada escolha — isso cria ponto cego. A instrução explícita de assumir a persona de revisor (com a restrição "apenas aponte falhas") força uma leitura diferente: em vez de defender escolhas, o modelo busca ativamente onde elas falham. A restrição impede que o revisor simplesmente reescreva o documento com suas próprias preferências — preserva o trabalho original e expõe apenas os problemas reais.
