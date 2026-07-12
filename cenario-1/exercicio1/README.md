# Exercício 1.1 — Análise de Viabilidade Técnica com Fundamentos de LLM e Engenharia de Contexto

## Objetivo

Avaliar a viabilidade técnica de um assistente RAG (Retrieval-Augmented Generation) para a NovaTech, empresa de logística com 1.200 funcionários. O foco é analisar os desafios de ingestão de documentação heterogênea, estimar o volume do corpus em tokens, calcular o orçamento de contexto por query e definir estratégia de chunking apropriada.

## Contexto do Problema

A equipe de atendimento da NovaTech (45 pessoas) gasta em média 12 minutos por chamado consultando documentação interna. A meta é reduzir esse tempo para menos de 2 minutos com um assistente de IA integrado ao Microsoft Teams e SharePoint.

**Fontes de documentação:**
- SharePoint: ~800 documentos PDF/Word com tabelas complexas, fluxogramas e documentos escaneados
- Confluence: ~400 páginas wiki com links internos e macros customizadas
- Pasta de rede: ~50 planilhas Excel com fórmulas interdependentes

## Metodologia Aplicada

O exercício usou uma abordagem de iteração com duas personas distintas no Claude:

**Turno 1 — Engenheiro Sênior de RAG:** gerou a análise técnica inicial com autocrítica embutida por seção. A instrução explícita de responder mentalmente "o que pode dar errado aqui?" antes de escrever cada seção forçou honestidade durante a escrita.

**Turno 2 — Revisor Técnico Sênior:** leu o documento com a restrição de "apenas identificar falhas, sem reescrever". Identificou 10 problemas, rankeou os 3 mais críticos e gerou a versão final com correções cirúrgicas.

## Principais Resultados

**Volume do corpus:** estimado entre 6,4M e 9,1M tokens brutos, dependendo da estrutura real das planilhas (cenário de desnormalização completa de tabelas de frete).

**Orçamento de contexto:** com janela de 128k tokens, uma query típica consome ~13.450 tokens (cenário misto com chunks estruturados e OCR), deixando ~89% da janela ociosa. O gargalo não é tamanho da janela, mas qualidade do retrieval.

**Estratégia de chunking:** hierárquica por tipo de documento — preservando estrutura semântica de headings em PDFs e Confluence, serialização linha-a-linha com cabeçalho repetido para tabelas, e desnormalização por região lógica para planilhas.

**Risco mais crítico identificado:** o processo de atualização mensal por 3 áreas independentes (Operações, Compliance, Comercial) sem governança unificada — risco organizacional invisível para métricas técnicas de retrieval.

## Problemas Corrigidos na Revisão (v1.0 → v1.1)

| Problema | Impacto | Correção aplicada |
|---|---|---|
| Orçamento calculado com chunks uniformes de 500 tokens, mas chunking recomendava 700–750 para OCR | Subestimava contexto consumido por query em 40–100% | Tabela de orçamento substituída por cenário misto |
| Modelo de embeddings ausente da análise | Decisão que afeta todo o sistema estava invisível | Seção 3.5 adicionada com critérios de seleção |
| Grafo de dependência Confluence tratado como detalhe | Subestimava esforço de implementação em 2–4× | Reposicionado como decisão arquitetural com alternativa MVP |
| Diacríticos PT-BR ausentes da tabela de erros OCR | Padrão mais frequente em português ignorado | Linha adicionada com impacto em palavras-chave |
| Volume de planilhas com apenas cenário base | Mascarava risco real de 5–10× o volume estimado | Tabela com range completo (240k–3M tokens) |

## Arquivos

| Arquivo | Descrição |
|---|---|
| `exercicio1-1.md` | Enunciado do exercício com contexto, inputs e critérios de avaliação |
| `analise-viabilidade-rag-novatech.md` | Análise técnica v1.0 (gerada no Turno 1) |
| `analise-viabilidade-rag-novatech-final.md` | Análise técnica v1.1 (revisada e corrigida no Turno 2) |
| `iteracao-exercicio-rag-novatech.md` | Registro completo da iteração: prompts enviados, passos executados, problemas identificados e delta entre versões |
