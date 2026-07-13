# Exercício 2.1 — MCP Servers no Projeto NovaTech
## Plano Explicativo + Prompts para o Chat da IDE

> **Papel:** Desenvolvedor  
> **Ferramentas:** Claude Code (chat na IDE) + GitHub Copilot  
> **Entregável:** Mapeamento, `.mcp/mcp.json`, evidência de execução, análise de riscos

---

## O que o exercício pede (resumo executivo)

O exercício tem **4 partes encadeadas**:

| Parte | O que fazer | Ferramenta |
|-------|-------------|------------|
| 1 | Mapear cada necessidade do projeto para um MCP server local e gratuito | Claude Code (chat) |
| 2 | Escrever o `.mcp/mcp.json` com least privilege justificado | Claude Code (chat) |
| 3 | Subir os servers e provar uso real com evidências | Terminal + Claude Code |
| 4 | Identificar 2+ riscos de segurança e propor mitigações | Claude Code (chat) |

---

## Conceitos essenciais antes de começar

**MCP (Model Context Protocol)** padroniza como LLMs se conectam a ferramentas externas. Um server MCP expõe:
- **Tools** → ações que o modelo pode executar (ex: ler arquivo, buscar, commitar)
- **Resources** → dados read-only que o modelo pode consultar
- **Prompts** → templates reutilizáveis

Os 4 servers que o exercício menciona (todos gratuitos, locais, sem API externa):

| Server | Pacote npm | O que faz |
|--------|-----------|-----------|
| `filesystem` | `@modelcontextprotocol/server-filesystem` | Lê e escreve arquivos em pastas configuradas |
| `git` | `@modelcontextprotocol/server-git` | Lê histórico, branches, diffs do repositório |
| `memory` | `@modelcontextprotocol/server-memory` | Grafo de conhecimento persistente (key-value em JSON) |
| `everything` | `@modelcontextprotocol/server-everything` | Server de demo com tools, resources e prompts de exemplo |

**Least privilege** = cada server recebe acesso apenas ao mínimo necessário para sua função. Fontes de negócio (docs, corpus) devem ser somente leitura.

---

## Estrutura esperada do repositório

```
novatech-assistant/
├── .mcp/
│   └── mcp.json          ← você vai criar este arquivo
├── docs/
│   └── novatech/         ← docs de negócio (read-only para o agente)
├── data/
│   └── retrieval-corpus/ ← chunks do RAG (read-only para o agente)
├── src/                  ← código-fonte (leitura + escrita)
├── specs/                ← specs SDD (leitura + escrita)
└── skills/               ← skills do projeto (leitura + escrita)
```

---

## Passo a passo de execução

### PASSO 1 — Preparar o repositório local (terminal)

Antes de usar qualquer prompt, execute no terminal dentro do repositório `novatech-assistant`:

```bash
# Criar as pastas necessárias
mkdir -p .mcp docs/novatech data/retrieval-corpus

# Copiar os documentos do Anexo A para docs/novatech/
# Arquivos esperados:
# - docs/novatech/POL-001-politica-devolucao.md
# - docs/novatech/PROC-042-v2-frete-especial-revisado.md
# - docs/novatech/SLA-2024-tabela-sla-clientes.md
# - docs/novatech/FAQ-atendimento.md

# Copiar o Anexo B para data/retrieval-corpus/
# - data/retrieval-corpus/chunks.md

# Confirmar que o git está inicializado
git log --oneline -5
```

---

### PASSO 2 — Mapeamento: necessidades → MCP servers

**Use este prompt no chat do Claude Code:**

---

**PROMPT 1 — Mapeamento de necessidades para MCP servers**

```
Estou configurando os MCP servers para o projeto NovaTech Assistant — 
um assistente RAG para atendentes, com pipeline de ingestão, API Azure Functions, 
bot no Teams e painel React.

As necessidades de acesso do projeto são:
1. Código, specs e skills do repositório (ler e escrever)
2. Documentação de negócio da NovaTech em docs/novatech/ (somente leitura)
3. Corpus de chunks para RAG em data/retrieval-corpus/ (somente leitura)
4. Histórico e branches do repositório git
5. Memória persistente de decisões arquiteturais e linguagem ubíqua do domínio

Os MCP servers disponíveis são locais e gratuitos:
- @modelcontextprotocol/server-filesystem
- @modelcontextprotocol/server-git  
- @modelcontextprotocol/server-memory
- @modelcontextprotocol/server-everything

Para cada necessidade, me diga:
- Qual server atende
- O que ele expõe (Tools, Resources, Prompts)
- Quem consome (desenvolvedor, agente de IA, QA)
- Qual escopo mínimo (least privilege)
- Por que esse escopo é o mínimo suficiente

Apresente como uma tabela e depois como texto narrativo por server.
```

---

### PASSO 3 — Gerar o .mcp/mcp.json com least privilege

**PROMPT 2 — Geração do .mcp/mcp.json**

```
Com base no mapeamento de necessidades do projeto NovaTech Assistant, 
gere o arquivo .mcp/mcp.json completo com os seguintes servers:

1. filesystem-dev — leitura e escrita para o código do projeto
   - Pastas: ./src, ./specs, ./skills, ./.mcp
   - Justificativa: apenas código e artefatos que o dev precisa criar/editar

2. filesystem-docs — somente leitura para documentação de negócio
   - Pasta: ./docs/novatech
   - Justificativa: documentação de negócio não deve ser alterada por agentes

3. filesystem-corpus — somente leitura para o corpus de RAG
   - Pasta: ./data/retrieval-corpus
   - Justificativa: chunks são gerados pelo pipeline, não pelo agente de dev

4. git — acesso ao histórico do repositório
   - Repositório: diretório atual (.)
   - Escopo: leitura de log, branches, diffs

5. memory — memória persistente de decisões e linguagem ubíqua

Requisitos:
- Use formato padrão MCP com "type": "stdio" e "command": "npx"
- A raiz do projeto (.) NÃO deve estar exposta no filesystem — apenas subpastas específicas
- Inclua um campo "description" em cada server explicando o escopo e o motivo
- Least privilege: nenhum server deve ter mais acesso que o mínimo necessário

Gere o JSON completo pronto para salvar em .mcp/mcp.json
```

---

### PASSO 4 — Revisar least privilege

**PROMPT 3 — Revisão de segurança do mcp.json**

```
Revise o .mcp/mcp.json que acabamos de criar para o projeto NovaTech. 
Verifique especificamente:

1. Algum server tem acesso a pastas que contêm .env, segredos ou tokens?
   - A raiz do projeto (.) está exposta ao filesystem?
   - As pastas node_modules, .git ou infra/ estão acessíveis?

2. Algum server de leitura tem permissão de escrita inadvertida?

3. O server git tem escopo restrito ao repositório correto?

4. O server memory armazena dados sensíveis que não deveriam persistir?

Para cada problema encontrado, mostre a correção concreta no JSON.
Apresente o JSON revisado e final.
```

---

### PASSO 5 — Instalar e verificar os servers (terminal)

```bash
# Verificar node e npx disponíveis
node --version && npx --version

# Testar cada server individualmente (ctrl+c para sair após confirmar que sobe)
npx -y @modelcontextprotocol/server-filesystem ./src ./specs ./skills
npx -y @modelcontextprotocol/server-git .
npx -y @modelcontextprotocol/server-memory

# Com Claude Code CLI: verificar servers registrados
claude mcp list

# Se o mcp.json estiver em .mcp/mcp.json, o Claude Code lê automaticamente
# Reinicie o Claude Code após salvar o arquivo
```

---

### PASSO 6 — Evidências de uso real

Com os servers ativos no Claude Code, execute estes 3 prompts e capture os resultados:

---

**PROMPT 4 — Evidência A: Leitura de documento de negócio via MCP**

```
Use o MCP server filesystem-docs para listar e ler os documentos disponíveis 
em docs/novatech/.

Após listar, leia o conteúdo completo da política de devolução (POL-001) e responda:
- Qual o prazo para solicitar devolução?
- Quais categorias de carga não são elegíveis pelo processo padrão?
- Qual o procedimento passo a passo para abrir um chamado?
- Quais são os custos em cada cenário de devolução?

Responda usando APENAS o conteúdo lido via MCP — não use conhecimento prévio.
Cite o nome do arquivo e a seção de onde veio cada informação.
```

> **Capture como evidência:** print do chat mostrando o agente listando arquivos e citando seções exatas do documento.

---

**PROMPT 5 — Evidência B: Recuperação de chunk do corpus RAG via MCP**

```
Use o MCP server filesystem-corpus para buscar em data/retrieval-corpus/ 
os chunks mais relevantes para esta pergunta de um atendente NovaTech:

"Qual o valor do frete especial para uma carga de 2.000 kg com destino ao Nordeste?"

Leia os chunks disponíveis e identifique:
1. Quais chunks são relevantes para essa pergunta? (cite os IDs: PROC-042-A, PROC-042v2-B etc.)
2. Qual a fórmula de cálculo e os multiplicadores corretos?
3. Existe mais de uma versão do procedimento? Qual deve ser usada e por quê?
4. Qual seria o cálculo para: valor base R$1.000, carga de 2.000kg, destino Nordeste?

Use apenas o conteúdo dos chunks lidos via MCP. Cite o ID de cada chunk usado.
```

> **Capture como evidência:** print mostrando o agente acessando o corpus e identificando os chunks PROC-042v2 (versão mais recente) vs PROC-042 (versão antiga).

---

**PROMPT 6 — Evidência C: Leitura do histórico git via MCP**

```
Use o MCP server git para ler o histórico do repositório novatech-assistant.

Me mostre:
1. Os últimos 10 commits com hash curto, autor, data e mensagem
2. As branches existentes no repositório
3. Os arquivos alterados no commit mais recente (diff stat)
4. Alguma branch com nome sugestivo de feature ou fix?

Use apenas o que o MCP server git retornar. 
Não execute comandos git diretos — use apenas as tools do MCP server.
```

> **Capture como evidência:** print mostrando commits reais retornados pelo MCP git server.

---

### PASSO 7 — Análise de riscos de segurança

**PROMPT 7 — Análise de riscos do setup MCP local**

```
Analise os riscos de segurança do setup de MCP servers que configuramos 
para o projeto NovaTech (filesystem-dev, filesystem-docs, filesystem-corpus, git, memory).

Para cada risco, use esta estrutura:
**Risco:** [nome]
**Vetor:** como seria explorado neste contexto local
**Impacto:** o que poderia acontecer
**Mitigação:** ação concreta para reduzir o risco (com exemplo no mcp.json se aplicável)

Analise ao menos estes riscos:

1. Exposição de segredos por escopo amplo de filesystem
   - Um filesystem server com acesso a pastas erradas pode expor .env, 
     infra/parameters/*.bicepparam (com connection strings) ou .git/config
   - Como evitar concretamente?

2. Escrita não supervisionada em arquivos de produção
   - O agente pode alterar src/ sem revisão humana, introduzindo bugs ou backdoors
   - Que controles de processo e configuração reduzem esse risco?

3. Vazamento de dados de negócio via memory server
   - O memory server persiste tudo que o agente "aprende" — incluindo dados de clientes
     mencionados em conversas de desenvolvimento
   - Como escopar e controlar o que é persistido?

4. Prompt injection via documentos do corpus
   - Um documento malicioso em docs/novatech/ poderia conter instruções para o agente
   - Como o filesystem read-only mitiga (ou não mitiga) este risco?

Para cada mitigação, seja específico: mostre a linha do mcp.json a alterar 
ou o processo de workflow a adotar.
```

---

## Estrutura do entregável final

Ao concluir o exercício, você deve ter:

```
novatech-assistant/
├── .mcp/
│   └── mcp.json                        ✅ Config com 5 servers, least privilege
├── docs/
│   └── novatech/                       ✅ Docs lidos via MCP (evidência A)
└── data/
    └── retrieval-corpus/               ✅ Chunks recuperados (evidência B)
```

**Documentos a entregar:**
1. Mapeamento (tabela: necessidade → server → escopo → justificativa)
2. `.mcp/mcp.json` final com escopo mínimo justificado
3. Evidências de execução (prints dos Prompts 4, 5 e 6)
4. Análise de riscos com mitigações (output do Prompt 7)

---

## Checklist de avaliação

- [ ] Apenas servers locais e gratuitos (sem serviços pagos/externos)
- [ ] `docs/novatech/` configurado em server read-only
- [ ] `data/retrieval-corpus/` configurado em server read-only
- [ ] A raiz do projeto `.` NÃO está exposta no filesystem server
- [ ] Evidência A: agente citou seções reais do documento lido via MCP
- [ ] Evidência B: agente identificou PROC-042v2 como versão correta (não a antiga)
- [ ] Evidência C: agente retornou commits reais via MCP git
- [ ] Mínimo 2 riscos específicos identificados com mitigação acionável

---

## Sequência de uso dos prompts

```
Terminal → PASSO 1 (preparar repo)
Chat    → PROMPT 1 (mapeamento)
Chat    → PROMPT 2 (gerar mcp.json)
Chat    → PROMPT 3 (revisar least privilege)
Terminal → PASSO 5 (instalar e verificar servers)
Chat    → PROMPT 4 (evidência A — doc)
Chat    → PROMPT 5 (evidência B — chunk RAG)
Chat    → PROMPT 6 (evidência C — git)
Chat    → PROMPT 7 (análise de riscos)
```

---

## Referências

- MCP Reference Servers: https://github.com/modelcontextprotocol/servers
- Filesystem server: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
- Git server: https://github.com/modelcontextprotocol/servers/tree/main/src/git
- Memory server: https://github.com/modelcontextprotocol/servers/tree/main/src/memory
- Claude Code + MCP: https://docs.anthropic.com/claude-code/mcp
