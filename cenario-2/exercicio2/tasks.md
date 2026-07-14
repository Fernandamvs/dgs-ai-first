# Tasks — Query Endpoint

> Gerado a partir de `plan.md` (query-endpoint). Segue a estrutura de diretórios do Anexo C
> (`src/functions/query/`, `src/services/`, `src/shared/`). Convenções: TypeScript + Azure
> Functions v4, Zod para validação, retry com backoff exponencial nas chamadas Azure, logging
> estruturado com pino.

---

### TASK-001 — Tipos de domínio compartilhados

**Descrição:** Criar `src/shared/types.ts` com os tipos TypeScript do domínio do query endpoint:
`QueryRequest` (input do POST), `ConversationTurn`, `Chunk` (com `id`, `content`, `sourceDocument`,
`score`, `vigencia: "vigente" | "obsoleto"`), `QueryResponse` (output com `answer` e
`sourceDocuments: string[]`).

**Critérios de aceite:**

- O arquivo exporta os 4 tipos/interfaces acima; `tsc --noEmit` passa sem erros.
- `Chunk.vigencia` é um union type literal (`"vigente" | "obsoleto"`), não `string`.
- `QueryRequest` inclui `question: string` e `conversationHistory?: ConversationTurn[]`.
- Nenhum tipo usa `any`.

**Dependências:** Nenhuma.

**Estimativa:** P

---

### TASK-002 — Configuração de ambiente (`config.ts`)

**Descrição:** Criar `src/shared/config.ts` que lê e valida as variáveis de ambiente necessárias:
`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`,
`AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`,
`AZURE_SEARCH_INDEX_NAME`. Usar Zod para validar o `process.env` na inicialização.

**Critérios de aceite:**

- Com todas as variáveis definidas, `getConfig()` retorna um objeto tipado com as 7 chaves.
- Se `AZURE_OPENAI_API_KEY` estiver ausente, `getConfig()` lança erro na primeira chamada
  (fail-fast), com mensagem contendo o nome da variável faltante — não retorna `undefined`
  silenciosamente.
- `getConfig()` é memoizado (chamadas subsequentes não relêem `process.env`).
- Teste unitário cobre: todas vars presentes (sucesso) e uma var ausente (lança erro).

**Dependências:** Nenhuma.

**Estimativa:** P

---

### TASK-003 — Logger estruturado (`logger.ts`)

**Descrição:** Criar `src/shared/logger.ts` com uma instância pino configurada para logging JSON,
incluindo campos padrão (`service: "query-endpoint"`, `env`) e um helper `childLogger(requestId)`
que anexa `requestId` a todas as entradas subsequentes.

**Critérios de aceite:**

- `logger.info({ requestId: "abc" }, "mensagem")` produz uma linha JSON com `requestId: "abc"`,
  `msg: "mensagem"`, `level` e `time`.
- `childLogger("req-123").info("teste")` inclui `requestId: "req-123"` sem precisar repassá-lo
  manualmente na chamada.
- Em `NODE_ENV=test`, o nível de log é `silent` (não polui output de testes).

**Dependências:** Nenhuma.

**Estimativa:** P

---

### TASK-004 — Hierarquia de erros customizados (`errors.ts`)

**Descrição:** Criar `src/shared/errors.ts` com classes de erro: `ValidationError` (400),
`ExternalServiceError` (502, recebe o nome do serviço externo: `"azure-openai"` ou
`"azure-search"`), `RetryExhaustedError` (503, estende `ExternalServiceError`). Cada classe expõe
`statusCode` e `toJSON()` retornando `{ error: string, message: string }`.

**Critérios de aceite:**

- `new ValidationError("question é obrigatório").statusCode === 400`.
- `new ExternalServiceError("azure-search", "timeout").statusCode === 502`.
- `new RetryExhaustedError("azure-openai", 3).statusCode === 503` e a mensagem menciona o número
  de tentativas (`3`).
- Todas as classes estendem `Error` nativo (`instanceof Error` é `true`) e preservam `stack`.

**Dependências:** Nenhuma.

**Estimativa:** P

---

### TASK-005 — Utilitário de retry com backoff exponencial

**Descrição:** Criar `src/shared/retry.ts` exportando `withRetry<T>(fn: () => Promise<T>, options: { retries: number, baseDelayMs: number, serviceName: string }): Promise<T>`. Reexecuta `fn` em
caso de falha com delay `baseDelayMs * 2^tentativa`, e lança `RetryExhaustedError` (TASK-004) após
esgotar as tentativas.

**Critérios de aceite:**

- Com `retries: 3`, se `fn` falha 2 vezes e sucede na 3ª chamada, `withRetry` retorna o valor de
  sucesso e `fn` foi chamado exatamente 3 vezes.
- Com `retries: 2`, se `fn` sempre falha, `withRetry` lança `RetryExhaustedError` após exatamente
  2 chamadas (não 3).
- Os delays entre tentativas seguem a progressão `baseDelayMs, baseDelayMs*2, baseDelayMs*4, ...`
  (verificável via fake timers no teste, sem esperar tempo real).
- Erros do tipo `ValidationError` (não recuperáveis) não são reexecutados — `fn` é chamado uma
  única vez e o erro original é relançado.

**Dependências:** TASK-004.

**Estimativa:** P

---

### TASK-006 — Setup do endpoint + validação de input

**Descrição:** Criar `src/functions/query/validator.ts` com o schema Zod de `POST /api/query`
(`question: string().min(1).max(2000)`, `conversationHistory` opcional, máx. 3 turnos, cada turno
com `role: "user" | "assistant"` e `content: string`) e `src/functions/query/handler.ts` com o
HTTP trigger (Azure Functions v4) que: valida o body com o schema, e em caso de erro retorna
`400` com `{ error: "validation_error", details: [...] }`; em caso de sucesso, por enquanto
retorna `501 Not Implemented` (a orquestração real vem em TASK-013).

**Critérios de aceite:**

- `POST /api/query` com body `{ "question": "Qual o prazo de devolução?" }` retorna `501` (stub)
  — confirma que passou pela validação.
- `POST /api/query` com body `{}` (sem `question`) retorna `400` com
  `{ "error": "validation_error", "details": [{ "path": ["question"], ... }] }`.
- `POST /api/query` com `question` de 2001 caracteres retorna `400`.
- `POST /api/query` com `conversationHistory` de 4 turnos retorna `400`.
- `POST /api/query` com `Content-Type` ausente ou body não-JSON retorna `400` (não `500`).
- Teste unitário do validator cobre os 5 casos acima diretamente (sem subir o Functions host).

**Dependências:** TASK-001, TASK-004.

**Estimativa:** M

---

### TASK-007 — Serviço de embeddings (Azure OpenAI)

**Descrição:** Criar `src/services/embedder.ts` com `embedQuestion(question: string): Promise<number[]>`, que chama o endpoint de embeddings do Azure OpenAI (deployment de
`config.ts`) usando `withRetry` (TASK-005) com `retries: 3`.

**Critérios de aceite:**

- Com a chamada HTTP mockada (nock/msw) retornando um vetor de 1536 posições, `embedQuestion("Qual o prazo de devolução?")` resolve para um `number[]` de tamanho 1536.
- Se a API mockada retornar `429` duas vezes e `200` na terceira, `embedQuestion` ainda resolve
  com sucesso (valida uso do retry).
- Se a API mockada retornar `500` em todas as tentativas, `embedQuestion` rejeita com
  `RetryExhaustedError` cujo `serviceName === "azure-openai"`.
- Se `question` for string vazia, a função lança `ValidationError` antes de fazer a chamada HTTP
  (nenhuma chamada de rede é feita — verificável pelo mock não ter sido invocado).

**Dependências:** TASK-002, TASK-004, TASK-005.

**Estimativa:** M

---

### TASK-008 — Serviço de busca vetorial (Azure AI Search)

**Descrição:** Criar `src/services/search.ts` com `searchChunks(embedding: number[]): Promise<Chunk[]>`, que consulta o índice do Azure AI Search (top-5 por similaridade vetorial) e
mapeia o resultado para `Chunk[]` (TASK-001), incluindo o metadado `vigencia` do índice.

**Critérios de aceite:**

- Com a API do Azure AI Search mockada retornando 5 documentos, `searchChunks` retorna exatamente
  5 `Chunk[]`, cada um com `id`, `content`, `sourceDocument`, `score` e `vigencia` preenchidos.
- Se a API mockada retornar apenas 2 documentos (índice pequeno), `searchChunks` retorna 2 chunks
  sem erro (não força um mínimo de 5).
- Usa `withRetry` (TASK-005): em caso de timeout simulado seguido de sucesso, retorna os chunks
  normalmente; em caso de falha persistente, rejeita com `RetryExhaustedError` cujo
  `serviceName === "azure-search"`.
- Caso de teste com dados realistas: consulta simulando "Qual o multiplicador de frete especial
  para a região Sul?" retorna chunks de `PROC-042` e `PROC-042-v2` com `vigencia` distintas
  (`"obsoleto"` para v1, `"vigente"` para v2).

**Dependências:** TASK-001, TASK-002, TASK-004, TASK-005.

**Estimativa:** M

---

### TASK-009 — Prompt builder com context budget

**Descrição:** Criar `src/services/prompt-builder.ts` com `buildPrompt(question: string, chunks: Chunk[], history: ConversationTurn[]): { systemPrompt: string, userPrompt: string }`. Carrega o
system prompt de `/prompts/system-prompt.md`, monta o contexto com os chunks (ordenados por
`score` desc), respeitando o budget (~4K tokens para system, ~8K para chunks) e instrui o modelo a
priorizar chunks com `vigencia: "vigente"` quando houver conflito. Função pura, sem chamadas de
rede.

**Critérios de aceite:**

- Com 5 chunks cujo total estimado de tokens é menor que 8K, `buildPrompt` inclui todos os 5 no
  `userPrompt`.
- Com chunks cujo total excede 8K tokens, `buildPrompt` descarta os de menor `score` até caber no
  budget, e loga (via logger, TASK-003) quantos chunks foram descartados.
- Quando dois chunks têm o mesmo `sourceDocument` raiz mas `vigencia` diferente (ex.: um chunk de
  `PROC-042` obsoleto e um de `PROC-042-v2` vigente), o `userPrompt` gerado contém instrução
  explícita para o modelo priorizar o chunk vigente (string verificável no output, ex.:
  `"vigente"` ou `"desconsidere versões obsoletas"`).
- `history` com 3 turnos é incluído no `userPrompt`; um 4º turno (se passado, apesar da validação
  de TASK-006 já limitar a 3) é truncado — a função não assume que o input já foi sanitizado.
- Teste unitário usa os chunks de exemplo do Anexo B (POL-001, PROC-042, PROC-042-v2) como
  fixture em `tests/fixtures/chunks.ts`.

**Dependências:** TASK-001, TASK-003.

**Estimativa:** M

---

### TASK-010 — Serviço de completion (GPT-4o)

**Descrição:** Criar `src/services/completion.ts` com `generateAnswer(systemPrompt: string, userPrompt: string): Promise<{ text: string, usage: { promptTokens: number, completionTokens: number } }>`, chamando o Azure OpenAI chat completions (deployment GPT-4o) com `withRetry`
(TASK-005).

**Critérios de aceite:**

- Com a API mockada retornando `{ choices: [{ message: { content: "Resposta simulada" } }], usage: {...} }`, `generateAnswer` resolve `text === "Resposta simulada"` e `usage` preenchido.
- Se a API mockada retornar `429` (rate limit) 2 vezes e `200` na 3ª, `generateAnswer` ainda
  resolve com sucesso.
- Se a API mockada retornar erro persistente, rejeita com `RetryExhaustedError` cujo
  `serviceName === "azure-openai"`.
- Timeout de rede configurável via `config.ts`; teste simula requisição que excede o timeout e
  confirma que é tratada como falha (elegível a retry), não como travamento indefinido.

**Dependências:** TASK-002, TASK-004, TASK-005.

**Estimativa:** M

---

### TASK-011 — Harness de validação determinística de resposta

**Descrição:** Criar `src/services/response-validator.ts` com `validateAnswer(answer: string, chunks: Chunk[]): { valid: boolean, warnings: string[] }`. Aplica checagens determinísticas
antes de devolver a resposta ao atendente: (a) a resposta não pode citar um documento fonte que
não está entre os `chunks` recuperados; (b) se a resposta se baseia unicamente em chunk(s) com
`vigencia: "obsoleto"`, adiciona warning.

**Critérios de aceite:**

- `validateAnswer("O prazo é de 7 dias, conforme POL-001.", chunks)` onde `chunks` inclui um
  chunk de `sourceDocument: "POL-001"` retorna `{ valid: true, warnings: [] }`.
- `validateAnswer("Conforme o documento XYZ-999...", chunks)` onde nenhum chunk tem
  `sourceDocument: "XYZ-999"` retorna `valid: false` e um warning mencionando `"XYZ-999"`.
- `validateAnswer(respostaBaseadaSoEmChunkObsoleto, chunksComApenasObsoletos)` retorna
  `valid: true` (a resposta ainda é enviada) mas `warnings` contém um aviso de uso de fonte
  obsoleta.
- Função pura, sem chamadas de rede ou I/O — testável 100% com fixtures de `tests/fixtures/`.

**Dependências:** TASK-001.

**Estimativa:** M

---

### TASK-012 — Response builder

**Descrição:** Criar `src/functions/query/response-builder.ts` com `buildResponse(answer: string, chunks: Chunk[], validation: ReturnType<typeof validateAnswer>): QueryResponse`, montando o
payload final `{ answer, sourceDocuments, warnings? }` validado contra um schema Zod de output
antes de retornar.

**Critérios de aceite:**

- Com `answer = "O prazo é de 7 dias."` e `chunks` contendo `sourceDocument: "POL-001"` (único),
  `buildResponse` retorna `{ answer: "O prazo é de 7 dias.", sourceDocuments: ["POL-001"] }` sem
  a chave `warnings` quando não há avisos.
- `sourceDocuments` não contém duplicatas mesmo se múltiplos chunks vierem do mesmo documento.
- Se `validation.warnings` não for vazio, o output inclui `warnings: string[]` com o mesmo
  conteúdo.
- Se o schema Zod de output falhar (ex.: `answer` vazio), a função lança erro em vez de retornar
  payload inválido — coberto por teste unitário.

**Dependências:** TASK-001, TASK-011.

**Estimativa:** P

---

### TASK-013 — Orquestração do handler (pipeline completo)

**Descrição:** Atualizar `src/functions/query/handler.ts` (stub de TASK-006) para orquestrar o
pipeline completo: validar input → `embedQuestion` (TASK-007) → `searchChunks` (TASK-008) →
`buildPrompt` (TASK-009) → `generateAnswer` (TASK-010) → `validateAnswer` (TASK-011) →
`buildResponse` (TASK-012) → `200 OK`. Mapeia `ExternalServiceError`/`RetryExhaustedError` para
`502`/`503` e qualquer erro não tratado para `500` genérico (sem vazar stack trace no body).

**Critérios de aceite:**

- `POST /api/query` com `{ "question": "Qual o prazo de devolução?" }` (dependências externas
  mockadas com sucesso) retorna `200` com `{ answer: string, sourceDocuments: string[] }`.
- Se `searchChunks` rejeitar com `RetryExhaustedError`, o endpoint retorna `503` com
  `{ error: "azure-search", message: "..." }` — não `500`.
- Se `generateAnswer` rejeitar com erro desconhecido (ex.: `TypeError` interno), o endpoint
  retorna `500` com `{ error: "internal_error" }` — o body não contém o stack trace.
- Latência total do pipeline (mockado) é registrada em log (ver TASK-014) antes da resposta ser
  enviada.
- Teste de integração (msw) cobre o caminho feliz completo e os 2 cenários de erro acima.

**Dependências:** TASK-006, TASK-007, TASK-008, TASK-009, TASK-010, TASK-011, TASK-012.

**Estimativa:** G

---

### TASK-014 — Logging estruturado do pipeline

**Descrição:** Instrumentar o `handler.ts` (TASK-013) com logs estruturados via `childLogger`
(TASK-003): início da requisição (`requestId`, tamanho da pergunta), fim de cada etapa do
pipeline (embed, search, completion) com latência em ms, e log final com status HTTP e latência
total.

**Critérios de aceite:**

- Uma requisição bem-sucedida gera ao menos 4 linhas de log JSON, todas com o mesmo `requestId`:
  início, fim do embed (`durationMs`), fim do search (`durationMs`, `chunksFound`), fim
  (`statusCode: 200`, `totalDurationMs`).
- Nenhuma linha de log contém a `question` completa do atendente em texto puro — apenas seu
  tamanho (`questionLength`) — para evitar logar dados potencialmente sensíveis de clientes.
- Em caso de erro em qualquer etapa, o log final registra `statusCode` de erro e o nome do
  serviço que falhou (`failedService`).

**Dependências:** TASK-003, TASK-013.

**Estimativa:** P

---

### TASK-015 — Testes de integração do endpoint completo

**Descrição:** Criar `tests/integration/query.test.ts` cobrindo o endpoint `/api/query`
ponta-a-ponta com Azure OpenAI e Azure AI Search mockados via `msw`, usando os fixtures de
`tests/fixtures/chunks.ts` (chunks do Anexo B) e `tests/fixtures/queries.ts`.

**Critérios de aceite:**

- Caso "caminho feliz": pergunta "Qual o prazo de devolução de mercadorias?" com chunks mockados
  de `POL-001` retorna `200` e `sourceDocuments` contém `"POL-001"`.
- Caso "documentos contraditórios": pergunta sobre multiplicador de frete especial retorna `200`
  com `sourceDocuments` incluindo `"PROC-042-v2"` (vigente) — teste falha explicitamente se a
  resposta citar apenas `"PROC-042"` (v1, obsoleto) como única fonte.
- Caso "falha externa": Azure AI Search mockado para retornar erro 3 vezes seguidas resulta em
  `503` do endpoint.
- Caso "validação": body sem `question` retorna `400` sem nenhuma chamada às APIs mockadas
  (asserção de que os mocks de `msw` não foram acionados).
- Suite roda via `vitest run tests/integration/query.test.ts` sem dependência de rede real ou
  credenciais Azure reais.

**Dependências:** TASK-013.

**Estimativa:** G

---

## Resumo de dependências

```
TASK-001 (types)         ─┬─> TASK-006, TASK-008, TASK-009, TASK-011, TASK-012
TASK-002 (config)        ─┬─> TASK-006, TASK-007, TASK-008, TASK-010
TASK-003 (logger)        ─┬─> TASK-009, TASK-014
TASK-004 (errors)        ─┬─> TASK-005, TASK-006, TASK-007, TASK-008, TASK-010
TASK-005 (retry)         ─┬─> TASK-007, TASK-008, TASK-010
TASK-006 (setup+validator) ─> TASK-013
TASK-007 (embedder)        ─> TASK-013
TASK-008 (search)          ─> TASK-013
TASK-009 (prompt-builder)  ─> TASK-013
TASK-010 (completion)      ─> TASK-013
TASK-011 (response-validator) ─> TASK-012, TASK-013
TASK-012 (response-builder)   ─> TASK-013
TASK-013 (orquestração)    ─> TASK-014, TASK-015
```

**Ordem sugerida de implementação:** TASK-001 → TASK-004 → TASK-002/003/005 (paralelo) →
TASK-006 (primeira task a implementar com Copilot) → TASK-007/008/009/010/011 (paralelo entre
devs) → TASK-012 → TASK-013 → TASK-014 → TASK-015.
