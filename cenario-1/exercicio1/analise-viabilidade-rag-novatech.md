---
title: Análise de Viabilidade Técnica — Assistente RAG para NovaTech
versão: 1.0
data: 2026-06-22
autor: Engenharia de Sistemas RAG
---

# Análise de Viabilidade Técnica — Assistente RAG para NovaTech

---

## Sumário Executivo

A NovaTech possui um corpus heterogêneo de ~1.250 documentos (~6,7M tokens brutos) distribuídos em três tipos com complexidades distintas: PDFs com tabelas densas e conteúdo escaneado, páginas Confluence com dependências de links, e planilhas com fórmulas interdependentes. Cada tipo exige pipeline de ingestão especializado — não existe abordagem genérica que atenda os três. O orçamento de contexto de 128k tokens é tecnicamente suficiente para queries típicas (projeção de 12.500 tokens por consulta), mas a qualidade do sistema depende mais da fidelidade do chunking e da relevância da recuperação do que da janela de contexto em si. O risco mais crítico não é técnico: é o processo de atualização mensal sem revisão unificada, que pode introduzir inconsistências silenciosas no corpus e degradar respostas sem alertas visíveis. A recomendação é construir o pipeline por fases, priorizando PDFs estruturados antes de atacar planilhas e OCR.

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
| Hifenização incorreta | `pro-cedimento` (sem merge) | Quebra tokens semânticos |
| Espaçamento perdido | `fretezone` em vez de `frete zone` | Token desconhecido, embedding degradado |
| Ruído de digitalização | Linhas espúrias, pontos, artefatos | Polui o contexto sem sinal semântico |
| Tabelas desestruturadas | Colunas fundidas, células trocadas | Mesmo problema da seção 1.1, amplificado |

O problema mais insidioso é que o OCR não falha uniformemente: um documento pode ter 95% de qualidade excelente e 5% de seções críticas completamente ilegíveis. O pipeline não tem como distinguir os dois sem análise explícita.

**Impacto na qualidade do RAG**

Erros de OCR em termos-chave do domínio (nomes de regiões, códigos de produto, valores monetários) fazem com que embeddings do documento fiquem semanticamente distantes das queries dos usuários. O documento existe no índice, mas nunca é recuperado porque o vetor gerado não corresponde ao vetor da pergunta. É uma falha silenciosa — o sistema responde "não encontrei informação" quando a informação existe, só está corrompida.

**Tratamento técnico recomendado**

1. **Pipeline de pré-processamento com score de confiança**: motores OCR como Tesseract e AWS Textract expõem scores de confiança por palavra. Calcular um score médio por página e sinalizar páginas abaixo de 80% de confiança para revisão manual.
2. **Dicionário de domínio para pós-processamento**: criar lista de termos críticos do domínio (nomes de cidades, regiões de frete, códigos internos) e aplicar correção fuzzy após OCR para termos com distância de edição ≤ 2 do dicionário.
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
3. **Grafo de dependência**: construir um grafo de adjacência entre páginas durante a ingestão. Ao recuperar um chunk, verificar se suas páginas dependentes têm alta relevância para a query — se sim, co-recuperá-las com prioridade. Isso é recuperação baseada em grafo, mais complexa que cosine similarity pura, mas necessária para este corpus.
4. **Stripping de macros**: pré-processar o HTML Confluence com parser específico (ex: `beautifulsoup4` + regras para namespaces de macros Atlassian) antes de qualquer extração textual. Macros `{include}` devem ser expandidas durante a coleta, não ignoradas.

**Autocrítica desta subseção**

A resolução de links até profundidade 2 pode criar explosão combinatória: se cada página referencia 5 páginas que referenciam outras 5, temos 25 páginas adicionais por ingestão. Para um corpus de 400 páginas isso pode ser gerenciável, mas o custo computacional de ingestão aumenta 5–10× no pior caso. A abordagem de grafo de dependência exige manutenção contínua — cada vez que um link é adicionado ou removido em uma página Confluence, o grafo precisa ser atualizado, o que pressupõe um webhook ou indexação incremental, não apenas re-indexação mensal.

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
3. **Descrição em linguagem natural da lógica de cálculo**: além dos valores calculados, gerar um chunk descritivo que explica o modelo de precificação: *"O frete é calculado multiplicando o peso bruto (arredondado para cima) pela tarifa da tabela, com acréscimo de 12% para regiões Norte e Nordeste e 8% para remessas acima de 50kg."* Esse chunk responde perguntas do tipo "como é calculado?" que os valores tabelados sozinhos não respondem.
4. **Classificação por tipo de planilha**: nem toda planilha contém lógica de cálculo — algumas são apenas tabelas de dados (cadastros, listas). Classificar automaticamente planilhas por densidade de fórmulas (> 30% de células com fórmulas = planilha calculada) e aplicar pipeline diferenciado.

**Autocrítica desta subseção**

A avaliação de fórmulas via Python falha silenciosamente com planilhas que usam funções VBA ou funções de array legadas do Excel. Referências externas (`=[OutroArquivo.xlsx]Aba!A1`) não serão resolvidas a menos que todos os arquivos estejam disponíveis simultaneamente durante a ingestão — o que pode não ser o caso em uma pasta de rede. A desnormalização de tabelas de referência cruzada pode gerar dezenas de milhares de mini-chunks para uma única planilha de frete com muitas origens e destinos, potencialmente inflando o corpus e aumentando o ruído na recuperação.

---

## 2. Estimativa do Corpus em Tokens

### Suposições utilizadas

| Suposição | Valor adotado | Justificativa |
|---|---|---|
| Palavras por página PDF | 500 | Mix de texto narrativo, tabelas e espaço em branco — documentos corporativos raramente chegam a 700 palavras/página com layout padronizado |
| Palavras por página wiki | 1.500 | Dado fornecido no briefing |
| Abas por planilha | 3 | Estimativa conservadora para planilhas de frete multirregião |
| Células por aba | ~400 (20 linhas × 20 colunas) | Planilhas de referência cruzada típicas de logística |
| Palavras por célula serializada | ~5 | `"Campo: Valor"` em formato de desnormalização |
| Células não-vazias por aba | ~60% | Planilhas de frete têm muitas células vazias nos cabeçalhos e bordas |
| Razão tokens/palavras | palavras ÷ 0,75 | Padrão para português BR com terminologia técnica |

> **Nota**: PDFs com conteúdo predominantemente tabular têm densidade de palavras menor que documentos narrativos. A estimativa de 500 palavras/página já incorpora esse efeito. PDFs escaneados que exigem OCR podem ter rendimento real menor — 20–40% das palavras podem ser perdidas ou corrompidas.

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

### 2.3 Planilhas Excel

```
Planilhas:             50
Abas/planilha:          3
Total de abas:        150

Células/aba:          400
Células não-vazias:   400 × 60% = 240

Palavras por célula serializada: 5
Palavras/aba:         240 × 5 = 1.200
Total de palavras:    150 × 1.200 = 180.000

Tokens = 180.000 ÷ 0,75 = 240.000 tokens
```

> **Obs**: Este cálculo é para o conteúdo serializado pós-desnormalização. Se a estratégia de descrição em linguagem natural for adotada (Seção 1.4, item 3), o volume pode aumentar 2–3× por planilha, chegando a ~600.000 tokens.

---

### Tabela-Resumo do Corpus

| Fonte | Volume | Páginas/Itens | Palavras estimadas | Tokens estimados |
|---|---|---|---|---|
| PDFs (SharePoint) | 800 documentos | 8.000 páginas | 4.000.000 | **5.333.333** |
| Wiki Confluence | 400 páginas | — | 600.000 | **800.000** |
| Planilhas Excel | 50 arquivos | 150 abas | 180.000 | **240.000** |
| **TOTAL** | **1.250 itens** | — | **4.780.000** | **~6.373.333** |

**Corpus total estimado: ~6,4M tokens brutos**

Este é o volume total indexado. Em produção, cada query recupera tipicamente 10–20 chunks de 500 tokens, ou seja, 5.000–10.000 tokens por consulta — menos de 0,2% do corpus total.

---

## 3. Análise de Orçamento de Contexto

### 3.1 Parâmetros e capacidade bruta

| Parâmetro | Valor |
|---|---|
| Janela de contexto total | 128.000 tokens |
| Reserva: system prompt + instruções | −2.000 tokens |
| **Tokens efetivos para RAG** | **126.000 tokens** |
| Tamanho de chunk adotado (alvo) | 500 tokens |
| Chunks que cabem teoricamente | 126.000 ÷ 500 = **252 chunks** |

### 3.2 Distribuição do orçamento em uma query típica

A capacidade teórica de 252 chunks não é operacional. Inserir 252 chunks de 500 tokens torna o contexto extenso demais para que o modelo mantenha coerência de raciocínio — e amplifica diretamente o efeito *lost in the middle* (ver Seção 3.3). A distribuição prática recomendada para uma query de atendimento típica:

| Componente | Tokens | Justificativa |
|---|---|---|
| System prompt + instruções | 2.000 | Fixo: persona, regras de resposta, disclaimers |
| Query do atendente | 200 | Consulta típica: "Qual o prazo de entrega para o interior do Paraná?" |
| Histórico de conversa (últimas 3 trocas) | 1.500 | Contexto conversacional mínimo |
| Chunks recuperados (15 × 500 tokens) | 7.500 | Volume recomendado: qualidade sem excesso de ruído |
| Buffer de geração da resposta | 1.000 | Resposta esperada: 3–5 parágrafos |
| **Total projetado por query** | **12.200 tokens** | 9,7% da janela disponível |

**Capacidade ociosa por query: ~115.800 tokens (~91% da janela)**

A janela de 128k é confortavelmente suficiente para o caso de uso descrito. O gargalo não é o tamanho da janela — é a qualidade da recuperação e o design dos chunks.

### 3.3 O efeito *Lost in the Middle* e compensação por posicionamento

Estudos empíricos em modelos de linguagem (Liu et al., 2023) demonstram que a capacidade de recuperar informação relevante a partir de contextos longos não é uniforme: modelos exibem desempenho consistentemente superior para informação posicionada no **início** ou no **final** do contexto, com queda expressiva para informação no meio. Para 15 chunks de igual relevância semântica, os chunks nas posições 6–10 têm probabilidade significativamente menor de influenciar a resposta do que os chunks nas posições 1–2 e 14–15.

**Estratégia de inserção para compensação:**

Após a recuperação e re-ranking por relevância (score de similaridade cosine + eventual re-ranker cruzado), inserir os chunks **não** em ordem decrescente de relevância, mas em padrão de sanduíche:

```
Posição 1:  Chunk com maior score de relevância    ← lido com atenção máxima
Posição 2:  Chunk com 3º maior score
Posição 3:  Chunk com 5º maior score
...         (menos relevantes no meio)
Posição 14: Chunk com 4º maior score
Posição 15: Chunk com 2º maior score               ← lido com atenção alta
```

O resultado é que os dois chunks mais relevantes ficam em posições privilegiadas (início e fim), e os menos relevantes ocupam o meio onde a atenção do modelo é naturalmente mais baixa.

### 3.4 Ponto de limitação do orçamento

O orçamento se torna um fator limitante em dois cenários específicos:

1. **Queries que exigem síntese de muitas fontes**: ex. *"Qual a política completa de devolução para todas as regiões e tipos de produto?"* — a resposta correta pode exigir 30–40 chunks de fontes diferentes. Solução: dividir em sub-queries sequenciais ou aceitar que a resposta será parcial com indicação das fontes omitidas.

2. **Chunks de tabelas grandes**: uma tabela de frete serializada completamente pode chegar a 2.000–4.000 tokens. Inserir 5 dessas tabelas já ocupa 10.000–20.000 tokens. Solução: limitar chunks de tabela a no máximo 3 por query, priorizando os mais específicos para a pergunta.

**Compromisso necessário**: o sistema deve ter uma política explícita de seleção quando o número de chunks relevantes excede 15 — por exemplo, priorizar chunks com maior score de similaridade e incluir no rodapé da resposta uma nota: *"Encontrei X fontes adicionais relevantes. Você gostaria de explorar algum ponto específico?"*

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

### 4.2 Por tipo de documento

#### PDFs com tabelas complexas

| Parâmetro | Valor recomendado |
|---|---|
| Tamanho alvo (prosa) | 400–500 tokens |
| Tamanho máximo (tabelas) | 800–1.000 tokens (não cortar tabelas) |
| Overlap (prosa) | 10% (~50 tokens) — repetição da última frase do chunk anterior |
| Overlap (tabelas) | 0% + repetição do cabeçalho em cada chunk de tabela partida |
| Critério de corte | **Estrutural** (limite de seção/subseção detectado por heading PDF) |
| Fallback | Semântico por parágrafo se headings não detectados |

**Regra especial**: tabelas nunca devem ser partidas dentro de uma linha. Se a tabela excede o tamanho máximo, partir entre linhas completas, repetindo os cabeçalhos no início de cada chunk continuado. Marcar com metadado `continuação: true` e `parte: 2/3`.

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
| Metadado obrigatório | `url_fonte`, `ultima_atualizacao`, `links_internos` (lista) |

O breadcrumb no início de cada chunk é obrigatório — ele fornece ao modelo o contexto hierárquico mesmo quando chunks vizinhos não são recuperados, e permite ao atendente localizar o documento original se precisar.

#### Planilhas Excel

| Parâmetro | Valor recomendado |
|---|---|
| Tamanho alvo | 300–600 tokens (variável por região lógica) |
| Overlap | Não aplicável (chunks por região de dados, não por tamanho) |
| Critério de corte | **Semântico por região lógica** (ex: tabela de uma combinação origem-tipo) |
| Metadado obrigatório | `arquivo_origem`, `aba`, `tipo: [tabela_dados | regra_calculo | descricao]` |

Chunks de planilha não seguem a lógica de tamanho dos outros tipos. A unidade de chunking é a **região lógica de dados**: uma tabela de frete por estado, uma lista de exceções, uma descrição de regra de cálculo. Cada região vira um chunk independente do seu tamanho, com a tolerância de não ultrapassar 1.000 tokens por região (regiões maiores devem ser subdivididas por critério de domínio).

### 4.3 Chunking hierárquico vs. flat — resumo da escolha

| Critério | Chunking Hierárquico | Chunking Flat |
|---|---|---|
| Preservação de estrutura | Alta | Baixa |
| Complexidade de implementação | Alta | Baixa |
| Adequação para documentos estruturados | Excelente | Ruim |
| Adequação para texto homogêneo (ex: narrativa contínua) | Boa | Boa |
| Risco de chunks vazios | Médio (seções podem ser muito curtas) | Baixo |
| Impacto em *lost in the middle* | Menor (chunks mais informativos precisam de menos volume) | Maior (mais chunks necessários para cobrir a mesma informação) |

**Para NovaTech**: hierárquico em todos os tipos exceto partes narrativas de PDFs sem estrutura clara, onde flat com overlap é aceitável como fallback.

---

## 5. Validação Crítica

Esta seção não resume as seções anteriores. Ela as contesta.

---

### 5.1 Estimativas excessivamente otimistas

**Estimativa de 500 palavras/página PDF**

Este valor é razoável para documentos bem formatados, mas documentos escaneados podem ter rendimento real de 250–350 palavras/página após OCR com qualidade média. Se 30–40% dos PDFs forem documentos escaneados (o briefing menciona "alguns" sem quantificar), a estimativa de tokens para PDFs pode estar superestimada em 15–25%. Isso não compromete a análise de orçamento de contexto (que já tem folga enorme), mas afeta o planejamento de cobertura do corpus.

**Volume de planilhas**

A estimativa de 240.000 tokens para planilhas foi calculada com estrutura conservadora (20×20 células, 60% preenchidas). Planilhas de frete real de empresas de logística com 15+ anos de operação frequentemente têm 500–2.000 linhas por aba, com 10+ abas. O volume real pode ser 5–10× maior que o estimado. Recomendo auditoria manual de uma amostra de 5 planilhas antes de comprometer com a estratégia de desnormalização.

**Qualidade da extração Confluence**

A estimativa de 800.000 tokens para a wiki assume extração limpa do HTML. Macros customizadas e conteúdo dinâmico podem fazer com que 20–30% das páginas resultem em conteúdo parcial ou corrompido na extração. O volume efetivo pode ser 560.000–640.000 tokens.

---

### 5.2 Contradições entre seções

**Chunks grandes para OCR (Seção 4) vs. posicionamento eficiente no contexto (Seção 3)**

A Seção 4 recomenda chunks de 700–750 tokens para documentos OCR (para diluir ruído). A Seção 3 recomenda 15 chunks de 500 tokens por query para controlar o orçamento. Se queries frequentes precisarem de múltiplos chunks de documentos escaneados, o orçamento prático por query sobe para 9.000–11.250 tokens — ainda confortável, mas o número máximo de chunks por query cai para 10–12 se se quiser manter dentro de 7.500 tokens para retrieved content.

**Resolução**: definir um orçamento de chunks separado por tipo: até 5 chunks de OCR (750 tokens) e até 10 chunks de documentos estruturados (500 tokens) por query, totalizando ~8.750 tokens para retrieved content — dentro do orçamento projetado.

**Desnormalização de planilhas (Seção 1.4) vs. volume do corpus (Seção 2)**

A Seção 1.4 recomenda desnormalizar tabelas de referência cruzada em pares explícitos. A Seção 2 estima 240.000 tokens para planilhas. Se tabelas de frete com 100 origens × 5 destinos × 10 faixas de peso forem desnormalizadas, cada planilha pode gerar 5.000 pares (100 × 5 × 10), e ao custo de ~10 tokens por par, uma única planilha contribui com 50.000 tokens. Com 10 planilhas desse perfil, o volume de planilhas sozinho chegaria a 500.000 tokens — mais que o dobro estimado. Não é um problema de orçamento de contexto, mas pode degradar a precisão da recuperação por excesso de candidatos similares.

---

### 5.3 O que ficou em aberto para o time de desenvolvimento

Os itens abaixo não foram resolvidos nesta análise e precisam de decisão técnica antes da implementação:

1. **Estratégia de atualização incremental**: documentos são atualizados mensalmente por 3 áreas sem processo unificado. O sistema precisa de um mecanismo para detectar alterações (hash de documento, webhook do SharePoint, data de modificação) e re-indexar apenas os documentos alterados. Re-indexação total mensal é tecnicamente viável mas custosa e introduz janelas de inconsistência.

2. **Gestão de conflitos entre documentos**: documentos de Operações e Compliance podem conter regras contraditórias para o mesmo cenário. O RAG vai recuperar ambos e o modelo pode gerar uma síntese inconsistente. É necessário definir uma hierarquia de autoridade por tipo de documento e implementá-la como metadado de peso na recuperação.

3. **Threshold de confiança para resposta**: quando o sistema não encontra evidência documental suficiente, deve responder "não encontrei esta informação" ou tentar uma resposta baseada em raciocínio? Esta decisão de produto tem implicações diretas na taxa de alucinação percebida.

4. **Ciclo de feedback dos atendentes**: sem um mecanismo de feedback (ex: "esta resposta foi útil?"), é impossível detectar falhas silenciosas onde o sistema retorna uma resposta plausível mas incorreta. Este loop é crítico para manutenção da qualidade ao longo do tempo.

5. **Autenticação e controle de acesso**: documentos de Compliance podem ter restrições de acesso. O pipeline RAG precisa respeitar ACLs do SharePoint e Confluence, não apenas indexar tudo globalmente.

---

### 5.4 Risco mais subestimado nesta análise

**O processo de atualização mensal sem governança unificada é o risco mais crítico e o menos endereçável por meios técnicos.**

Três áreas publicando documentos de forma independente significa:

- Versões contraditórias do mesmo procedimento podem coexistir no corpus (uma área atualiza, outra não)
- Documentos obsoletos não são removidos — o sistema indexa versões antigas e novas simultaneamente
- Não há indicador para o RAG distinguir "documento atualizado" de "documento substituído"

Nenhuma das soluções técnicas desta análise resolve esse problema. Chunking hierárquico não detecta contradição entre documentos. Re-ranking por relevância não prioriza versão mais recente por padrão. OCR de alta qualidade em um documento desatualizado produz informação errada com alta confiança.

**A recomendação é implementar, em paralelo ao desenvolvimento técnico, um processo mínimo de versionamento**: (a) convenção de nomenclatura que inclua data de versão no nome do arquivo, (b) campo de metadado `valido_ate` preenchido durante a publicação, e (c) filtro de expiração na recuperação. Sem isso, a qualidade do assistente vai degradar progressivamente a cada ciclo de atualização, e o time de desenvolvimento terá dificuldade em diagnosticar por que — porque as métricas de embedding e retrieval parecerão saudáveis.

---

*Documento gerado como artefato técnico de projeto. Revisão recomendada após auditoria de amostra do corpus real.*
