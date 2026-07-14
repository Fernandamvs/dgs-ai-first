# Revisão Técnica — TASK-006 (Setup do endpoint + validação de input)

**Projeto:** NovaTech Assistant
**Escopo revisado:** `src/functions/query/validator.ts`, `src/functions/query/handler.ts`
**Referência:** `tasks.md` (TASK-006), `plan.md`

---

## Resumo do que foi implementado

O Copilot criou `validator.ts` (schema Zod para `QueryRequest`, incluindo `conversationHistory` limitado a 3 turnos) e `handler.ts` (HTTP trigger Azure Functions v4 que valida Content-Type, faz parse do JSON, valida contra o schema Zod e retorna `501` em caso de sucesso ou `400` em caso de erro de validação). O escopo está bem contido — não há chamadas a serviços Azure nem lógica de orquestração antecipada de tasks futuras.

---

## Achados

### 1. [BLOCKER] Nenhum teste unitário foi criado — critério de aceite explícito da TASK-006 não foi cumprido

- **Arquivo:** N/A (ausente)
- **Motivo:** `tasks.md:134` exige explicitamente "Teste unitário do validator cobre os 5 casos acima diretamente (sem subir o Functions host)". Não existe nenhum arquivo `*.test.ts` no projeto. Isso não é uma preferência de estilo — é um critério de aceite mensurável da task que não foi atendido.
- **Ajuste recomendado:** bloquear o PR até existir uma suíte cobrindo: sucesso (`question` válida → passa validação), `question` ausente, `question` de 2001 caracteres, `conversationHistory` com 4 turnos, e Content-Type ausente/body não-JSON.

### 2. [SHOULD-FIX] `validateQueryRequest` é dead code

- **Arquivo:** `validator.ts:29-39`
- **Motivo:** confirmado via busca no repositório que essa função só é referenciada dentro do próprio arquivo onde é definida. O `handler.ts` faz a validação chamando `queryRequestSchema.safeParse(...)` diretamente (`handler.ts:44`), ignorando o helper. Código morto num PR gera ruído e sugere que o autor não decidiu qual é o padrão de validação do projeto (schema direto vs. helper que já lança `ValidationError`).
- **Ajuste recomendado:** escolher um padrão único. Se o padrão do projeto for "handler trata o `safeParse` e formata a resposta", remover `validateQueryRequest` do arquivo (ou de fato usá-lo no handler, o que simplificaria o `try/catch` de `ValidationError`). Não deixar as duas abordagens coexistindo.

### 3. [SHOULD-FIX] Formato do erro 400 não é consistente entre o path do Zod e o path de `ValidationError`

- **Arquivo:** `handler.ts:58-66` vs `handler.ts:46-48`
- **Motivo:** o envelope externo (`{ error: "validation_error", details: [...] }`) é igual nos dois casos, mas o conteúdo de `details[]` diverge semanticamente:
  - Path do Zod: `code` vem do vocabulário de issue codes do Zod (`too_small`, `invalid_type`, etc.) e `path` aponta para o campo real (ex.: `["question"]`).
  - Path de `ValidationError` (Content-Type inválido / JSON malformado): `code` é sempre a string fixa `"invalid_request"` (que não existe no vocabulário Zod) e `path` é sempre `[]`.

  Um cliente que faz `switch` em `details[].code` esperando códigos Zod vai quebrar silenciosamente para erros de Content-Type/parse. Os critérios de aceite da task (linha 130) só especificam o formato para o caso Zod — mas a inconsistência entre os dois caminhos vai gerar confusão em consumidores da API.
- **Ajuste recomendado:** documentar explicitamente (ou padronizar) que `code: "invalid_request"` é reservado para falhas de parsing/Content-Type, distinto dos códigos Zod — por exemplo, prefixando ou usando um campo separado tipo `stage: "parse" | "schema"`.

### 4. [SHOULD-FIX] `authLevel: "anonymous"` sem contexto de que há um gateway/APIM na frente

- **Arquivo:** `handler.ts:74`
- **Motivo:** este endpoint expõe uma funcionalidade de Q&A sobre documentos internos da empresa (conforme `plan.md`). `authLevel: "anonymous"` significa que, sem uma camada de auth na frente (API Management, Front Door com auth, etc.), qualquer requisição na internet acessa o endpoint sem chave nem token. Nem `plan.md` nem `tasks.md` mencionam a estratégia de autenticação, o que é uma lacuna de especificação, não necessariamente um erro do Copilot — mas antes de aprovar é preciso confirmar se há um gateway de auth documentado em outro lugar do projeto.
- **Ajuste recomendado:** se não houver gateway externo com auth, mudar para `authLevel: "function"` (ou `"anonymous"` intencionalmente documentado com um comentário/ADR explicando a decisão). Isso é bloqueante antes de TASK-013 (quando o endpoint passa a de fato consumir Azure OpenAI/Search com custo real por requisição).

### 5. [NITPICK] Nenhum log é emitido no handler, nem mesmo no caminho de erro

- **Arquivo:** `handler.ts` (ausência de import de logger)
- **Motivo:** correto que TASK-006 não depende de TASK-003 (logger) no grafo de dependências, e a instrumentação completa é escopo formal de TASK-014. Não há `console.log` nem qualquer log não estruturado — isso está certo. Mas como `logger.ts` (TASK-003) ainda nem existe no repo, vale um comentário no PR reforçando que TASK-014 precisa necessariamente vir antes de considerar o endpoint "pronto para produção", para não passar despercebido no board.
- **Ajuste recomendado:** nenhuma ação nesta PR — apenas comentário/lembrete, não bloqueia merge.

---

## O que está correto e pode ficar como está

- **Escopo:** a implementação não extrapola a TASK-006 — não há nenhuma chamada a `embedQuestion`, `searchChunks` ou lógica de orquestração que pertence a TASK-007+. O `501` stub está exatamente como especificado.
- **Sem logging não-estruturado:** nenhum `console.log`/`console.error` no código — quando o logging for adicionado (TASK-014), será via pino desde o início.
- **Tratamento de Content-Type/JSON malformado:** `parseRequestBody` trata corretamente os casos de Content-Type ausente e body não-JSON, retornando `400` em vez de deixar a exceção estourar como `500` — atende ao critério de aceite da linha 133 do `tasks.md`.
- **Schema Zod:** `question.min(1).max(2000)` e `conversationHistory.max(3)` batem exatamente com o especificado em `tasks.md:118-120`.
- **Hierarquia de erros (`errors.ts`):** `ValidationError`/`ExternalServiceError`/`RetryExhaustedError` estão corretas, com `statusCode`, `toJSON()` e preservação de `instanceof Error` — embora isso seja escopo de TASK-004, não há regressão introduzida aqui.
