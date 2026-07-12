---
title: Análise de Viabilidade Técnica — Assistente RAG para NovaTech
versão: 1.1 (revisada)
data: 2026-06-23
autor: Engenharia de Sistemas RAG
revisão: Revisão crítica independente incorporada
---

# Análise de Viabilidade Técnica — Assistente RAG para NovaTech

---

## Sumário Executivo

A NovaTech possui um corpus heterogêneo de ~1.250 documentos com volume estimado entre 6,4M e 9M tokens brutos (a faixa superior ocorre se planilhas forem completamente desnormalizadas). Cada tipo de fonte exige pipeline de ingestão especializado — não existe abordagem genérica que atenda os três. O orçamento de contexto de 128k tokens é tecnicamente suficiente para queries típicas (projeção de 13.000–16.000 tokens por consulta considerando chunks de tamanho heterogêneo), mas a qualidade do sistema depende mais da fidelidade do chunking, da escolha do modelo de embeddings para português técnico, e da relevância da recuperação do que da janela de contexto em si. O risco mais crítico não é técnico: é o processo de atualização mensal sem revisão unificada, que pode introduzir inconsistências silenciosas no corpus e degradar respostas sem alertas visíveis. A recomendação é construir o pipeline por fases, priorizando PDFs estruturados antes de atacar planilhas e OCR.

---

## 1. Desafios por Tipo de Fonte

### 1.1 PDFs com Tabelas Complexas

**Desafio**

Tabelas de frete com 15+ colunas estabelecem relacionamentos implícitos entre cabeçalhos e células. Um chunker que divide por tamanho fixo quase certamente corta essa estrutura no meio: o chunk resultante pode conter células da linha 8 à linha 15, mas o cabeçalho que define o que cada coluna significa ficou no chunk anterior. Para o modelo de linguagem, isso equivale a receber uma planilha sem a primeira linha — os dados existem, mas o significado foi perdido.

O problema se agrava com tabelas que têm cabeçalhos em múltiplos níveis (ex: "Região Sul" com subcolunas "Expresso / Econômico / Fracionado"). Nesses casos, a relação semântica entre células e cabeçalhos requer mais de uma linha de contexto para ser reconstituída.

Fluxogramas embutidos como imagens são invisíveis para embeddings textuais — eles simplesmente não existem no corpus indexado. Se um procedimento de reclamação estiver descrito majoritariamente em um fluxograma, a pergunta do atendente não encontrará resposta.

**Impacto na qualidade do RAG**

Um chunk sem cabeçalho de tabela gera respostas com dados corretos mas sem contexto semântico. O modelo pode retornar "R$45,00" sem conseguir explicar que isso corresponde ao frete expresso para a Região Sul, peso entre 5 e 10 kg. Pior: o modelo pode alucinar o contexto ausente com plausibilidade alta, já que os dados numéricos constroem aparência de precisão.

Fluxogramas ausentes criam lacunas silenciosas: a busca por embeddings não indica que o documento existe mas o conteúdo é inacessível — a query simplesmente não retorna nenhum chunk relevante, forçando o modelo a responder com base em texto periférico ou admitir desconhecimento.

**Tratamento técnico recomendado**

1. **Extração estruturada de tabelas**: usar bibliotecas com detecção de layout (ex: `pdfplumber`, `camelot`, ou `unstructured.io` com estratégia `hi_res`) para identificar regiões tabulares antes do chunking.
2. **Serialização com cabeçalho repetido**: cada linha da tabela vira um mini-chunk autossuficiente no formato `"[Cabeçalho N1 > Cabeçalho N2]: Valor"`. Exemplo: `"Região: Sul | Tipo: Expresso | Peso: 5–10kg | Valor: R$45,00"`. Isso torna cada row recuperável de forma independente.
3. **Chunk de tabela completa**: além dos mini-chunks por linha, indexar a tabela inteira serializada como um único chunk de metadados, marcado com `tipo: tabela`. Usado quando a query exige compreensão da estrutura completa (ex: "qual a política de frete para todos os pesos acima de 20kg?").
4. **Alt-text para imagens**: extrair imagens e gerar descrições via modelo multimodal (ex: Claude com visão). As descrições substituem as imagens no corpus indexado, com marcação `[conteúdo gerado por visão computacional — verificar manualmente]`.

**Autocrítica desta subseção**

A serialização linha-a-linha resolve o problema de recuperação granular, mas cria um corpus com muitos chunks pequenos e altamente repetitivos (o cabeçalho aparece em cada linha). Isso pode inflar o corpus em 3–5× para tabelas grandes e introduzir ruído de duplicação nos embeddings. A solução de chunk-de-tabela-completa não escala para tabelas que excedem 1.000 tokens — nesses casos, o chunk ultrapassa o limite e precisa ser dividido por grupo de colunas, o que reintroduz parcialmente o problema original. Não existe solução perfeita; a escolha é qual tipo de falha é menos custoso.

---

### 1.2 PDFs Escaneados (OCR)

**Desafio**

OCR aplicado a documentos escaneados produz erros característicos que têm impacto assimétrico em embeddings: alguns erros são benignos (um "0" virou "O" em uma frase narrativa), outros são críticos (um "0" virou "O" em um CEP ou código de produto, tornando o documento irrecuperável para aquela query específica).

Erros típicos em OCR de documentos corporativos escaneados:

| Tipo de erro | Exemplo | Impacto em embedding |
|---|---|---|
| Confusão de caracteres similares | `1` → `l` ou `I`, `0` → `O` | Baixo em prosa, alto em códigos |
| **Diacríticos do português BR** | `ã` → `ā`, `ç` → `c&`, `é` → `e'` | **Alto em qualquer contexto — altera o significado da palavra** |
| Hifenização incorreta | `pro-cedimento` (sem merge) | Quebra tokens semânticos |
| Espaçamento perdido | `fretezone` em vez de `frete zone` | Token desconhecido, embedding degradado |
| Ruído de digitalização | Linhas espúrias, pontos, artefatos | Polui o contexto sem sinal semântico |
| Tabelas desestruturadas | Colunas fundidas, células trocadas | Mesmo problema da seção 1.1, amplificado |

> **Atenção ao português BR**: caracteres como `ã`, `ç`, `é`, `ê`, `õ` são sistematicamente problemáticos em OCR de documentos digitalizados em baixa resolução. Para um corpus em português técnico de logística, erros nesses caracteres afetam palavras-chave críticas: "situação" → "situacão", "reclamação" → "reclamac&ão", "região" → "regiāo". O modelo de embeddings vai gerar vetores divergentes para a versão correta (na query do atendente) e a corrompida (no chunk indexado). O dicionário de correção fuzzy precisa cobrir especificamente esse padrão — não apenas confusões de caracteres ASCII.

O problema mais insidioso é que o OCR não falha uniformemente: um documento pode ter 95% de qualidade excelente e 5% de seções críticas completamente ilegíveis. O pipeline não tem como distinguir os dois sem análise explícita.

**Impacto na qualidade do RAG**

Erros de OCR em termos-chave do domínio (nomes de regiões, códigos de produto, valores monetários) fazem com que embeddings do documento fiquem semanticamente distantes das queries dos usuários. O documento existe no índice, mas nunca é recuperado porque o vetor gerado não corresponde ao vetor da pergunta. É uma falha silenciosa — o sistema responde "não encontrei informação" quando a informação existe, só está corrompida.

**Tratamento técnico recomendado**

1. **Pipeline de pré-processamento com score de confiança**: motores OCR como Tesseract e AWS Textract expõem scores de confiança por palavra. Calcular um score médio por página e sinalizar páginas abaixo de 80% de confiança para revisão manual.
2. **Dicionário de domínio para pós-processamento**: criar lista de termos críticos do domínio (nomes de cidades, regiões de frete, códigos internos) e aplicar correção fuzzy após OCR para termos com distância de edição ≤ 2 do dicionário. Incluir explicitamente variantes com diacríticos incorretos (ex: `reclamacao` → `reclamação`).
3. **Metadado de qualidade no chunk**: indexar junto ao chunk um campo `ocr_confidence` (ex: `0.87`). Durante a recuperação, usar esse campo para penalizar o score de similaridade de chunks com baixa confiança ou exibir um aviso ao atendente: *"Este trecho foi extraído de documento escaneado — verifique o original antes de usar como base para decisão."*
4. **Reprocessamento periódico com modelos multimodais**: para documentos com score abaixo do limiar, enviar a imagem do PDF para um modelo com visão para extração direta, contornando o OCR tradicional.

**Autocrítica desta subseção**

O score de confiança do OCR é uma heurística, não uma garantia. Um documento pode ter alta confiança média mas erros localizados em células de tabela — exatamente onde os erros são mais críticos para o domínio de logística. A abordagem de dicionário de domínio precisa ser mantida ativamente pelas três áreas (Operações, Compliance, Comercial), o que cria dependência do mesmo processo de governança que hoje não existe. Se esse dicionário não for mantido, sua eficácia decai conforme novos produtos e regiões são adicionados.

---

### 1.3 Wiki Confluence com Links Internos

**Desafio**

Páginas Confluence frequentemente funcionam como nós de uma rede: uma página de "Política de Devolução" referencia "Prazos Regionais" que por sua vez referencia "Tabela de Exceções por Sazonalidade". Um chunk extraído da primeira página pode conter a frase *"ver regras de prazo na página de Prazos Regionais"* — informação que é completamente inútil sem o conteúdo daquela outra página.

Macros customizadas do Confluence (ex: `{jira}`, `{status}`, `{include}`) criam dois problemas adicionais: (a) o exportador HTML deixa artefatos de marcação que poluem o texto extraído, e (b) macros do tipo `{include}` referenciam conteúdo de outras páginas que pode não estar presente na extração.

**Impacto na qualidade do RAG**

Quando um chunk referencia uma página não recuperada, o modelo tem três opções ruins: ignorar a referência, tentar inferir o conteúdo (alucinação) ou responder com incompletude sem indicar a causa. Em todos os casos, o atendente recebe uma resposta tecnicamente "fundamentada" em documentação, mas com lacunas ocultas.

O problema é especialmente grave para procedimentos de múltiplas etapas distribuídos em páginas diferentes — exatamente o tipo de conteúdo que governa reclamações e devoluções.

**Tratamento técnico recomendado**

1. **Resolução de links durante a ingestão**: ao processar uma página, seguir todos os links internos Confluence (não externos) até profundidade 2 e incluir um resumo automático da página linkada como metadado do chunk pai. Exemplo: o chunk da "Política de Devolução" recebe um campo `linked_summaries` com resumos das páginas que ela referencia.
2. **Chunking hierárquico com breadcrumb**: cada chunk inclui no início o caminho de navegação da página: `[Espaço] > [Seção] > [Subseção]`. Isso permite ao modelo entender o contexto hierárquico mesmo quando chunks vizinhos não são recuperados.
3. **Grafo de dependência — decisão arquitetural**: construir um grafo de adjacência entre páginas para co-recuperação de páginas dependentes é uma decisão arquitetural de segunda ordem, não um detalhe de implementação. Requer componente de infraestrutura dedicado (grafo em banco relacional, Neo4j, ou estrutura customizada), redefinição do contrato da camada de recuperação, e reconciliação entre o ranker de similaridade e o traversal de grafo. A alternativa para MVP: co-recuperação simplificada por metadado de link (`linked_page_ids` no chunk) sem grafo completo — menos precisa, mas implementável em horas em vez de semanas.
4. **Stripping de macros**: pré-processar o HTML Confluence com parser específico (ex: `beautifulsoup4` + regras para namespaces de macros Atlassian) antes de qualquer extração textual. Macros `{include}` devem ser expandidas durante a coleta, não ignoradas.

**Autocrítica desta subseção**

A resolução de links até profundidade 2 pode criar explosão combinatória: se cada página referencia 5 páginas que referenciam outras 5, temos 25 páginas adicionais por ingestão. Para um corpus de 400 páginas isso pode ser gerenciável, mas o custo computacional de ingestão aumenta 5–10× no pior caso. A abordagem de grafo de dependência com co-retrieval exige manutenção contínua — cada vez que um link é adicionado ou removido em uma página Confluence, o grafo precisa ser atualizado, o que pressupõe um webhook ou indexação incremental, não apenas re-indexação mensal. Recomenda-se implementar a versão simplificada (metadado de link) no MVP e avaliar a necessidade de grafo completo após validação com usuários reais.

---

### 1.4 Planilhas com Fórmulas Interdependentes

**Desafio**

Fórmulas como `=VLOOKUP(B2, TabelaFrete!A:D, 3, FALSE)` são completamente opacas para um modelo de linguagem: o texto literal não carrega o valor calculado nem o raciocínio por trás da lógica. Pior, fórmulas interdependentes criam cadeias onde `=C5*D5` referencia `=SOMA(A1:A10)` que referencia uma célula em outra aba — a cadeia de dependência só faz sentido quando avaliada pelo Excel, não quando lida como texto.

O segundo problema é de estrutura: ao exportar para CSV ou texto plano, a relação espacial entre células é perdida. Uma tabela de frete onde o preço depende da combinação de "linha (origem)" e "coluna (destino)" vira uma lista de valores sem contexto posicional.

**Impacto na qualidade do RAG**

Se as fórmulas são indexadas como texto literal, o modelo recupera instruções de cálculo, não resultados. Um atendente perguntando "qual o frete de São Paulo para Porto Alegre, 15kg?" não vai encontrar utilidade em `=INDICE(C3:G10, CORRESP(B2, A3:A10, 0), CORRESP(D1, C2:G2, 0))`. Se as planilhas são simplesmente ignoradas, um percentual significativo das políticas de precificação de frete não estará acessível no sistema.

**Tratamento técnico recomendado**

1. **Avaliação prévia das fórmulas**: usar uma engine de execução Python (ex: `openpyxl` + `formulas` ou execução direta via `xlwings`) para calcular todos os valores antes da ingestão. O corpus recebe os resultados calculados, não as fórmulas.
2. **Desnormalização de tabelas de referência cruzada**: tabelas com lógica "origem × destino" devem ser desnormalizadas para pares explícitos: cada célula vira um registro `"Origem: SP | Destino: POA | Peso: 15kg | Frete: R$112,00"`. O número de registros cresce, mas cada um é autossuficiente.
3. **Descrição em linguagem natural da lógica de cálculo**: além dos valores calculados, gerar um chunk descritivo que explica o modelo de precificação. Esse chunk responde perguntas do tipo "como é calculado?" que os valores tabelados sozinhos não respondem. **Atenção ao processo**: se a descrição for gerada por LLM, é obrigatória revisão humana por especialista de domínio antes da indexação — uma descrição incorreta da lógica de cálculo indexada com alta confiança é mais perigosa do que a ausência de descrição. Se for escrita manualmente pelas áreas, esse esforço precisa estar dimensionado no planejamento do projeto.
4. **Classificação por tipo de planilha**: nem toda planilha contém lógica de cálculo — algumas são apenas tabelas de dados (cadastros, listas). Classificar automaticamente planilhas por densidade de fórmulas (> 30% de células com fórmulas = planilha calculada) e aplicar pipeline diferenciado.

**Autocrítica desta subseção**

A avaliação de fórmulas via Python falha silenciosamente com planilhas que usam funções VBA ou funções de array legadas do Excel. Referências externas (`=[OutroArquivo.xlsx]Aba!A1`) não serão resolvidas a menos que todos os arquivos estejam disponíveis simultaneamente durante a ingestão — o que pode não ser o caso em uma pasta de rede. A desnormalização de tabelas de referência cruzada pode gerar dezenas de milhares de mini-chunks para uma única planilha de frete com muitas origens e destinos (ver impacto no volume estimado, Seção 2.3).

---

## 2. Estimativa do Corpus em Tokens

### Suposições utilizadas

| Suposição | Valor adotado | Justificativa |
|---|---|---|
| Palavras por página PDF | 500 | Mix de texto narrativo, tabelas e espaço em branco — documentos corporativos raramente chegam a 700 palavras/página com layout padronizado |
| Palavras por página wiki | 1.500 | Dado fornecido no briefing |
| Abas por planilha | 3 | Estimativa conservadora para planilhas de frete multirregião |
| Células por aba (cenário base) | ~400 (20 linhas × 20 colunas) | Estrutura mínima de referência cruzada |
| Células por aba (cenário real logística) | até 5.000 pares desnormalizados | Tabelas com 100 origens × 10 destinos × 5 faixas de peso |
| Palavras por célula serializada | ~5 | `"Campo: Valor"` em formato de desnormalização |
| Células não-vazias por aba | ~60% | Planilhas de frete têm muitas células vazias nos cabeçalhos e bordas |
| Razão tokens/palavras | palavras ÷ 0,75 | Padrão para português BR com terminologia técnica |

> **Nota**: PDFs com conteúdo predominantemente tabular têm densidade de palavras menor que documentos narrativos. A estimativa de 500 palavras/página já incorpora esse efeito. PDFs escaneados que exigem OCR podem ter rendimento real menor — 20–40% das palavras podem ser perdidas ou corrompidas, afetando a cobertura efetiva do corpus (não o orçamento de contexto, que tem folga ampla).

---

### 2.1 PDFs (SharePoint)

```
Documentos:        800
Páginas/doc:        10
Total de páginas: 8.000

Palavras/página:    500
Total de palavras: 8.000 × 500 = 4.000.000

Tokens = 4.000.000 ÷ 0,75 = 5.333.333 tokens
```

### 2.2 Wiki Confluence

```
Páginas:             400
Palavras/página:   1.500
Total de palavras: 400 × 1.500 = 600.000

Tokens = 600.000 ÷ 0,75 = 800.000 tokens
```

> **Nota**: macros customizadas e conteúdo dinâmico podem fazer com que 20–30% das páginas resultem em conteúdo parcial ou corrompido na extração. Volume efetivo: 560.000–640.000 tokens.

### 2.3 Planilhas Excel

**Cenário base** (estrutura conservadora):

```
Planilhas:             50
Abas/planilha:          3
Total de abas:        150

Células/aba:          400
Células não-vazias:   400 × 60% = 240
Palavras/célula:        5
Palavras/aba:         240 × 5 = 1.200
Total de palavras:    150 × 1.200 = 180.000

Tokens = 180.000 ÷ 0,75 = 240.000 tokens
```

**Cenário real — desnormalização de tabelas de frete** (planilhas com dimensões típicas de logística):

```
Exemplo: 1 planilha com 100 origens × 5 destinos × 10 faixas de peso
Pares desnormalizados: 5.000
Tokens por par (~10 tokens): 50.000 tokens por planilha

Com 10 planilhas desse perfil: 500.000 tokens apenas de pares de frete
Total estimado (cenário real): 500.000–3.000.000 tokens
```

---

### Tabela-Resumo do Corpus

| Fonte | Volume | Palavras estimadas | Tokens — cenário base | Tokens — cenário real |
|---|---|---|---|---|
| PDFs (SharePoint) | 800 docs / 8.000 páginas | 4.000.000 | **5.333.333** | **5.333.333** |
| Wiki Confluence | 400 páginas | 600.000 | **800.000** | **640.000–800.000** |
| Planilhas Excel | 50 arquivos / 150 abas | 180.000–4.500.000 | **240.000** | **500.000–3.000.000** |
| **TOTAL** | **1.250 itens** | — | **~6,4M tokens** | **~6,5M–9,1M tokens** |

> **O número oficial do sumário é o range 6,4M–9,1M tokens.** Usar o valor base (6,4M) para decisões de infraestrutura sem auditar a estrutura real das planilhas é otimismo não fundamentado.

Em produção, cada query recupera tipicamente 10–20 chunks, ou seja, menos de 0,2% do corpus total por consulta.

---

## 3. Análise de Orçamento de Contexto

### 3.1 Parâmetros e capacidade bruta

| Parâmetro | Valor |
|---|---|
| Janela de contexto total | 128.000 tokens |
| Reserva: system prompt + instruções | −2.000 tokens |
| **Tokens efetivos para RAG** | **126.000 tokens** |
| Tamanho de chunk (documentos estruturados) | 500 tokens |
| Tamanho de chunk (OCR) | 750 tokens |
| Tamanho de chunk (tabelas / planilhas) | 800–1.000 tokens |
| Chunks que cabem teoricamente (500 tok) | 126.000 ÷ 500 = **252 chunks** |

### 3.2 Distribuição do orçamento em uma query típica

> **Atenção**: os tamanhos de chunk recomendados na Seção 4.2 são heterogêneos (500, 750, 800–1.000 tokens por tipo). A tabela abaixo usa um cenário híbrido realista — não chunks uniformes de 500 tokens. O cenário uniforme subestima o retrieved content em 40–100% para queries que atingem OCR ou tabelas.

| Componente | Tokens | Justificativa |
|---|---|---|
| System prompt + instruções | 2.000 | Fixo: persona, regras de resposta, disclaimers |
| Query do atendente | 200 | Consulta típica: "Qual o prazo de entrega para o interior do Paraná?" |
| Histórico de conversa (últimas 3 trocas) | 1.500 | Contexto conversacional mínimo |
| Chunks estruturados (10 × 500 tokens) | 5.000 | PDFs e wiki com estrutura preservada |
| Chunks OCR (5 × 750 tokens) | 3.750 | Documentos escaneados com chunk maior para diluir ruído |
| Buffer de geração da resposta | 1.000 | Resposta esperada: 3–5 parágrafos |
| **Total projetado por query (cenário misto)** | **13.450 tokens** | 10,5% da janela disponível |

**Capacidade ociosa por query: ~114.550 tokens (~89% da janela)**

A janela de 128k é confortavelmente suficiente. O gargalo não é o tamanho da janela — é a qualidade da recuperação, o design dos chunks, e a escolha do modelo de embeddings (Seção 3.5).

### 3.3 O efeito *Lost in the Middle* e compensação por posicionamento

Estudos empíricos (Liu et al., 2023) demonstram que modelos exibem desempenho superior para informação no início ou no final do contexto, com queda para informação no meio. Para 15 chunks, os das posições 6–10 têm menor probabilidade de influenciar a resposta.

**Estratégia de inserção em sanduíche:**

Após recuperação e re-ranking, inserir chunks em ordem de relevância alternada entre início e fim:

```
Posição 1:  Chunk com maior score de relevância    ← atenção máxima
Posição 2:  Chunk com 3º maior score
Posição 3:  Chunk com 5º maior score
...         (menos relevantes no meio)
Posição 14: Chunk com 4º maior score
Posição 15: Chunk com 2º maior score               ← atenção alta
```

**Requisito de implementação — re-ranker**: a estratégia de sanduíche só tem valor com re-ranking real. O ranker recomendado é um **cross-encoder leve** (ex: `cross-encoder/ms-marco-MiniLM-L-6-v2` ou equivalente treinado em português) que pontua cada par (query, chunk) individualmente. Impacto de latência esperado: 150–400ms por query para 20 candidatos. Para o SLA de atendimento (< 2 minutos por chamado), isso é aceitável, mas deve ser medido em produção.

**Limitação da estratégia de sanduíche**: a ordenação é por relevância semântica, não por qualidade do chunk. Um chunk OCR com `ocr_confidence: 0.71` pode ter score de similaridade alto (o tópico foi capturado mesmo com ruído) mas qualidade textual baixa. Colocá-lo na posição 1 é subótimo. A correção recomendada é incorporar o `ocr_confidence` como fator de penalização no score do re-ranker:

```
score_final = score_cross_encoder × (0.8 + 0.2 × ocr_confidence)
```

Isso rebaixa chunks de baixa qualidade OCR sem eliminá-los da recuperação.

### 3.4 Ponto de limitação do orçamento

O orçamento se torna limitante em dois cenários:

1. **Queries que exigem síntese de muitas fontes**: ex. *"Qual a política completa de devolução para todas as regiões e tipos de produto?"* — pode exigir 30–40 chunks. Solução: dividir em sub-queries ou indicar fontes omitidas na resposta.

2. **Chunks de tabelas grandes**: serialização completa de uma tabela de frete pode chegar a 2.000–4.000 tokens. Limitar a 3 chunks de tabela por query, priorizando os mais específicos para a pergunta.

**Política de overflow**: quando chunks relevantes excedem 15, priorizar por score e incluir nota na resposta: *"Encontrei X fontes adicionais relevantes. Deseja explorar algum ponto específico?"*

### 3.5 Seleção do Modelo de Embeddings

> **Esta é uma decisão de projeto crítica, ausente na versão anterior da análise.**

A qualidade de recuperação do sistema inteiro depende da capacidade do modelo de embeddings de capturar semântica em português técnico de logística. Os critérios de seleção relevantes para este projeto:

| Critério | Consideração |
|---|---|
| Cobertura do português BR técnico | Modelos multilíngues genéricos (ex: `text-embedding-3-large`) cobrem português, mas podem ter desempenho inferior para terminologia logística especializada (CTE, DANFE, romaneio, fracionado) |
| Vocabulário e tokenização | Modelos com tokenização ruim para acentuação do português aumentam o número de tokens por chunk, afetando os cálculos de orçamento desta seção |
| Custo de indexação | Para ~6–9M tokens de corpus, o custo de geração de embeddings é não-trivial e deve ser orçado para re-indexações mensais |
| Necessidade de fine-tuning | Se queries e documentos usam terminologia muito específica não presente em corpora de treinamento públicos, fine-tuning em exemplos do domínio pode ser necessário |
| Modelo open-source vs. API | Embeddings via API introduzem latência de rede por documento durante indexação; modelos locais eliminam essa latência mas exigem infraestrutura |

**Recomendação de processo**: antes de definir a arquitetura, executar uma avaliação comparativa de embeddings com 50–100 pares (query, documento relevante) extraídos do corpus real. Modelos candidatos: `text-embedding-3-large` (OpenAI), `multilingual-e5-large`, `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, e se disponível, modelo fine-tuned em domínio logístico português.

---

## 4. Estratégia de Chunking

### 4.1 Princípios gerais

O perfil de perguntas dos atendentes da NovaTech concentra-se em quatro categorias:

| Categoria | Exemplos | Implicação para chunking |
|---|---|---|
| **Consulta factual direta** | "Qual o prazo para interior do PR?" | Chunk pequeno e específico recupera melhor |
| **Regra de cálculo** | "Como calcula o frete para grandes volumes?" | Chunk com contexto de regra completa |
| **Procedimento sequencial** | "Qual o passo a passo para registrar reclamação?" | Chunks que preservam ordem e numeração |
| **Exceção ou condição** | "Há alguma regra especial para prazos no RJ?" | Chunk com contexto suficiente para identificar condicionais |

Isso orienta para uma estratégia predominantemente **hierárquica** (preserva estrutura semântica) em vez de **flat** (divide por tamanho fixo). Chunking flat é adequado quando o texto é homogêneo e cada parágrafo tem similar importância; para o corpus da NovaTech, onde cabeçalhos de seção carregam metadados críticos, flat chunking sistematicamente destrói informação estrutural.

**Nota sobre query quality**: atendentes sob pressão frequentemente formulam queries informais e abreviadas ("frete rj 15k", "prazo pr interior"). Queries curtas têm menor qualidade de embedding — a distância cosine entre "frete rj 15k" e um chunk sobre "tabela de fretes Rio de Janeiro, peso 15kg" pode ser significativamente menor do que para a versão bem formulada. A estratégia de chunking deve ser complementada com um estágio de query expansion ou reformulação antes do retrieval (ver Seção 5.3, item 6).

### 4.2 Por tipo de documento

#### PDFs com tabelas complexas

| Parâmetro | Valor recomendado |
|---|---|
| Tamanho alvo (prosa) | 400–500 tokens |
| Tamanho máximo (tabelas) | 800–1.000 tokens (não cortar tabelas) |
| Overlap (prosa) | 10% (~50 tokens) — repetição da última frase do chunk anterior |
| Overlap (tabelas) | 0% + repetição do cabeçalho em cada chunk de tabela partida |
| Critério de corte | **Estrutural** (limite de seção/subseção detectado por heading PDF) |
| Fallback | Flat com overlap para PDFs sem estrutura semântica de headings detectada |

**Regra especial**: tabelas nunca devem ser partidas dentro de uma linha. Se a tabela excede o tamanho máximo, partir entre linhas completas, repetindo os cabeçalhos no início de cada chunk continuado. Marcar com metadado `continuação: true` e `parte: 2/3`.

> **Risco de fallback**: PDFs sem headings semânticos (gerados de Word sem estilos, ou convertidos de formulários) são comuns em ambientes corporativos. Recomenda-se classificar os PDFs por qualidade estrutural antes da ingestão (ex: % do texto sob headings detectados pelo parser). PDFs com < 20% de conteúdo estruturado pelo parser devem usar flat+overlap como estratégia primária, não como fallback excepcional. A proporção de PDFs nessa categoria deve ser auditada na fase de piloto.

#### PDFs escaneados (OCR)

| Parâmetro | Valor recomendado |
|---|---|
| Tamanho alvo | 700–750 tokens |
| Overlap | 15–20% (~120 tokens) |
| Critério de corte | **Híbrido**: estrutural quando possível (pós-OCR), fixo como fallback |
| Metadado obrigatório | `ocr_confidence`, `requer_verificacao` (bool) |

Chunks maiores diluem o impacto de erros localizados de OCR — um erro em 750 tokens causa menos degradação de embedding do que o mesmo erro em 200 tokens. O overlap maior compensa a incerteza nas fronteiras semânticas que o OCR pode ter corrompido.

#### Wiki Confluence

| Parâmetro | Valor recomendado |
|---|---|
| Tamanho alvo | 400–500 tokens |
| Overlap | 0% (corte por seção; semanticamente coerente) |
| Critério de corte | **Hierárquico** por seção (H1 > H2 > H3) |
| Prefixo obrigatório | Breadcrumb: `[Espaço Confluence > Título da Página > Seção]` |
| Metadado obrigatório | `url_fonte`, `ultima_atualizacao`, `linked_page_ids` (lista) |

O breadcrumb no início de cada chunk é obrigatório — ele fornece ao modelo o contexto hierárquico mesmo quando chunks vizinhos não são recuperados, e permite ao atendente localizar o documento original se precisar. Impacto de tokens: o breadcrumb adiciona ~15–20 tokens por chunk; para 15 chunks por query, isso representa ~225–300 tokens não contabilizados no orçamento da Seção 3.2 — irrelevante dada a folga de 91% da janela.

#### Planilhas Excel

| Parâmetro | Valor recomendado |
|---|---|
| Tamanho alvo | 300–600 tokens (variável por região lógica) |
| Overlap | Não aplicável (chunks por região de dados, não por tamanho) |
| Critério de corte | **Semântico por região lógica** (ex: tabela de uma combinação origem-tipo) |
| Metadado obrigatório | `arquivo_origem`, `aba`, `tipo: [tabela_dados \| regra_calculo \| descricao]` |

Chunks de planilha não seguem a lógica de tamanho dos outros tipos. A unidade de chunking é a **região lógica de dados**: uma tabela de frete por estado, uma lista de exceções, uma descrição de regra de cálculo. Cada região vira um chunk independente do seu tamanho, com a tolerância de não ultrapassar 1.000 tokens por região.

### 4.3 Chunking hierárquico vs. flat — resumo da escolha

| Critério | Chunking Hierárquico | Chunking Flat |
|---|---|---|
| Preservação de estrutura | Alta | Baixa |
| Complexidade de implementação | Alta | Baixa |
| Adequação para documentos estruturados | Excelente | Ruim |
| Adequação para texto homogêneo (narrativa contínua) | Boa | Boa |
| Risco de chunks vazios | Médio (seções podem ser muito curtas) | Baixo |
| Impacto em *lost in the middle* | Menor (chunks mais informativos → menos volume necessário) | Maior |
| Sensibilidade à qualidade do PDF | Alta (depende de headings) | Baixa |

**Para NovaTech**: hierárquico para PDFs e wiki com estrutura semântica confirmada; flat com overlap para PDFs sem headings detectados e para seções narrativas homogêneas.

---

## 5. Validação Crítica

Esta seção não resume as seções anteriores. Ela as contesta.

---

### 5.1 Estimativas excessivamente otimistas

**Estimativa de 500 palavras/página PDF**

Este valor é razoável para documentos bem formatados, mas documentos escaneados podem ter rendimento real de 250–350 palavras/página após OCR com qualidade média. Se 30–40% dos PDFs forem documentos escaneados (o briefing menciona "alguns" sem quantificar), a estimativa de tokens para PDFs pode estar superestimada em 15–25% em termos de cobertura efetiva.

**Volume de planilhas**

A estimativa base de 240.000 tokens foi calculada com estrutura conservadora (20×20 células, 60% preenchidas). Planilhas de frete real de empresas de logística frequentemente têm 500–2.000 linhas por aba com 10+ abas. Após desnormalização, o volume real pode ser 5–10× maior. A tabela-resumo da Seção 2 apresenta o range completo (240k–3M tokens) — não usar apenas o valor base para dimensionamento de infraestrutura. **Recomendação imperativa**: auditar manualmente 5 planilhas representativas antes de qualquer decisão de arquitetura de vector store.

**Qualidade da extração Confluence**

A estimativa de 800.000 tokens assume extração limpa do HTML. Macros customizadas e conteúdo dinâmico podem fazer com que 20–30% das páginas resultem em conteúdo parcial ou corrompido. Volume efetivo estimado: 560.000–640.000 tokens.

---

### 5.2 Contradições entre seções

**Chunks grandes para OCR (Seção 4) vs. orçamento da Seção 3**

A Seção 4 recomenda chunks de 700–750 tokens para documentos OCR. A Seção 3 foi atualizada para refletir um cenário misto (10 chunks × 500 + 5 chunks × 750 = 8.750 tokens de retrieved content). Esta contradição da versão anterior foi resolvida: o orçamento na Seção 3.2 agora usa o cenário heterogêneo como padrão.

**Desnormalização de planilhas (Seção 1.4) vs. volume do corpus (Seção 2)**

Esta contradição foi resolvida na Seção 2.3: a tabela-resumo agora apresenta um range (cenário base vs. cenário real) em vez de um único valor. O cenário real (desnormalização completa de planilhas de frete multidimensionais) pode gerar até 3M tokens apenas de planilhas.

---

### 5.3 O que ficou em aberto para o time de desenvolvimento

1. **Gerenciamento de chunks obsoletos no vector store**: quando um documento é atualizado, os chunks da versão antiga permanecem no índice até serem explicitamente removidos. Queries vão recuperar chunks da versão velha e da nova simultaneamente, produzindo sínteses contraditórias. Isso é um problema diferente do versionamento de arquivo: exige uma estratégia de deleção por `document_id` no vector store, não apenas detecção de alteração.

2. **Detecção de alteração e re-indexação incremental**: o sistema precisa de um mecanismo para identificar documentos alterados (hash de arquivo, webhook do SharePoint/Confluence, data de modificação) e re-indexar apenas esses documentos. Re-indexação total mensal é tecnicamente viável mas custosa e introduz janelas de inconsistência.

3. **Gestão de conflitos entre documentos**: documentos de Operações e Compliance podem conter regras contraditórias para o mesmo cenário. O RAG recupera ambos e o modelo pode gerar síntese inconsistente. É necessário definir hierarquia de autoridade por tipo de documento e implementá-la como metadado de peso na recuperação.

4. **Threshold de confiança para resposta**: quando o sistema não encontra evidência documental suficiente, deve responder "não encontrei esta informação" ou tentar uma resposta baseada em raciocínio? Esta decisão de produto tem implicações diretas na taxa de alucinação percebida.

5. **Ciclo de feedback dos atendentes**: sem um mecanismo de feedback (ex: "esta resposta foi útil?"), é impossível detectar falhas silenciosas onde o sistema retorna uma resposta plausível mas incorreta. Este loop é crítico para manutenção da qualidade ao longo do tempo.

6. **Query understanding e expansão**: atendentes usam linguagem informal e abreviada ("frete rj 15k", "prazo pr interior"). É necessário definir se haverá um estágio de reformulação/expansão de query antes do retrieval (usando o próprio LLM em modo de pré-processamento) e como isso afeta a latência total do sistema.

7. **Autenticação e controle de acesso**: documentos de Compliance podem ter restrições de acesso. O pipeline RAG precisa respeitar ACLs do SharePoint e Confluence, não indexar tudo globalmente.

---

### 5.4 Risco mais subestimado nesta análise

**O processo de atualização mensal sem governança unificada é o risco mais crítico e o menos endereçável por meios técnicos.**

Três áreas publicando documentos de forma independente significa:

- Versões contraditórias do mesmo procedimento podem coexistir no corpus (uma área atualiza, outra não)
- Documentos obsoletos não são removidos — o sistema indexa versões antigas e novas simultaneamente
- Não há indicador para o RAG distinguir "documento atualizado" de "documento substituído"

Nenhuma das soluções técnicas desta análise resolve esse problema. Chunking hierárquico não detecta contradição entre documentos. Re-ranking por relevância não prioriza versão mais recente por padrão. OCR de alta qualidade em um documento desatualizado produz informação errada com alta confiança. O modelo de embeddings perfeito para português BR técnico ancora respostas incorretas com precisão ideal.

**A recomendação é implementar, em paralelo ao desenvolvimento técnico, um processo mínimo de versionamento**: (a) convenção de nomenclatura que inclua data de versão no nome do arquivo, (b) campo de metadado `valido_ate` preenchido durante a publicação, (c) filtro de expiração na recuperação, e (d) estratégia de deleção de chunks obsoletos no vector store ao publicar nova versão. Sem isso, a qualidade do assistente vai degradar progressivamente a cada ciclo de atualização — e o time de desenvolvimento terá dificuldade em diagnosticar o motivo, porque as métricas de embedding e retrieval parecerão saudáveis.

---

## Apêndice — Histórico de Revisão

| Versão | Data | Mudanças |
|---|---|---|
| 1.0 | 2026-06-22 | Versão inicial |
| 1.1 | 2026-06-23 | Revisão crítica independente incorporada: correção do orçamento de contexto (cenário heterogêneo), adição da Seção 3.5 (modelo de embeddings), elevação da recuperação em grafo a decisão arquitetural, diacríticos PT-BR na tabela de erros OCR, penalização de OCR no re-ranking, processo de revisão para descrições LLM-geradas, separação de chunks obsoletos vs. versionamento de documentos, query understanding como item em aberto, risco de fallback em detecção de headings, range de volume para planilhas. |

---

*Documento gerado como artefato técnico de projeto. Revisão recomendada após auditoria de amostra do corpus real.*
