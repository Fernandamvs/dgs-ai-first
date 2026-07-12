# Exercício 1.2 — Prototipação de Prompt com Engenharia de Contexto

## Objetivo

Prototipar e iterar o system prompt de um assistente RAG de atendimento para a NovaTech, com foco em engenharia de contexto: definição de guardrails, estrutura estática vs. dinâmica do prompt, e validação com cenários reais.

## Contexto do Problema

Continuação do exercício 1.1. Com a viabilidade técnica do assistente estabelecida, o foco passa para a camada de prompt: como estruturar as instruções para que o assistente use apenas documentação recuperada, cite fontes, respeite exceções e saiba quando escalar.

**Guardrails definidos pelo Product Specialist:**
1. Sempre citar a fonte do documento
2. Nunca inventar prazos ou valores fora da documentação
3. Quando não encontrar resposta, dizer explicitamente e sugerir escalação para supervisor
4. Responder em português formal mas acessível

**Chunks simulados usados nos testes:**
- **Chunk A** (POL-001, seção 3.2): política de devolução — 7 dias úteis, exceto cargas perigosas (ANTT classes 1–6)
- **Chunk B** (SLA-2024): SLAs por tier — Gold 24h, Silver 48h, Standard 72h
- **Chunk C** (PROC-042-v2, seção 2): frete especial para cargas acima de 500kg com multiplicadores regionais

## Metodologia Aplicada

O Claude foi usado como ambiente de teste direto: o system prompt foi colado como instrução inicial, os chunks como contexto dinâmico, e as perguntas enviadas como se fossem de um atendente real.

**Estrutura de contexto:**

| Parte | Tipo | Tokens estimados |
|---|---|---|
| Identidade, objetivo, regras, prioridade de fontes | Estático | ~400–500 tokens |
| Chunks recuperados (3 × ~80 tokens) | Dinâmico | ~240 tokens por query |
| Histórico de conversa | Dinâmico | Variável |
| Query do atendente | Dinâmico | ~20–50 tokens |

## Cenários Testados e Resultados

### Pergunta 1 — "Qual o prazo de devolução para carga perigosa?"

**v1:** Respondeu que não há prazo alternativo disponível e recomendou escalar. Correto, mas não deixou explícito que a carga perigosa está *excluída* da regra geral.

**v2:** Reformulou para deixar claro que cargas perigosas **não são elegíveis** para o processo padrão, eliminando ambiguidade. A v2 adicionou regra específica no prompt para tratar esse caso diretamente.

### Pergunta 2 — "Meu cliente é Gold, qual o SLA de resolução?"

**v1 e v2:** Ambas corretas — SLA de resolução de até 24h, resposta inicial em até 2h, com fonte citada (Tabela SLA-2024).

### Pergunta 3 — "Quanto custa o frete para 600kg para Manaus?"

**v1 e v2:** Ambas corretas — aplicou multiplicador da Região Norte (×1,8), informou que o valor base não consta nos chunks e recomendou consultar área responsável para o valor final.

## Melhorias de v1 para v2

| Elemento | v1 | v2 |
|---|---|---|
| Verificação pré-resposta | 4 perguntas genéricas | 5 perguntas, incluindo cobertura parcial do escopo |
| Prioridade entre versões de documento | Genérica | Exemplo específico para PROC-042 v1 vs v2 |
| Tratamento de casos específicos | Ausente | Seção dedicada com 4 casos explícitos (carga perigosa, tier inexistente, frete abaixo de 500kg, cálculo incompleto) |
| Regra 8 (cobertura parcial) | Ausente | Adicionada — instrui o assistente a sinalizar o que não foi coberto pelos chunks |

## Arquivos

| Arquivo | Descrição |
|---|---|
| `exercicio1-2.md` | Enunciado do exercício com contexto, inputs, tarefas e critérios de avaliação |
| `novatech-atendimento.md` | System prompt v1 com mapeamento de contexto e interações das 3 perguntas |
| `novatech-atendimentoV2.md` | System prompt v2 (iterado após análise crítica) com as mesmas 3 interações |
