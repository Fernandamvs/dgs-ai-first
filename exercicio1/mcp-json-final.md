# .mcp/mcp.json final — NovaTech Assistant (least privilege)

Baseado no [mapeamento.md](mapeamento.md). Arquivo aplicado em `.mcp/mcp.json` no repo do projeto.

```json
{
  "mcpServers": {
    "filesystem-dev": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./src",
        "./specs",
        "./skills",
        "./.mcp"
      ],
      "_description": "Leitura e escrita apenas em src/, specs/, skills/ e .mcp/ — as únicas pastas de código, specs, skills e configuração MCP que o agente de desenvolvimento precisa modificar. Não inclui a raiz do projeto (.) nem infra/, docs/ ou data/, para que o poder de escrita não alcance documentação de negócio, corpus do RAG ou parâmetros de infraestrutura."
    },
    "filesystem-docs": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./docs/novatech"
      ],
      "_description": "Somente leitura de docs/novatech/ (POL-001, PROC-042 v1/v2, SLA-2024, FAQ). O server não tem modo read-only nativo, então write_file, edit_file, move_file e create_directory desta instância devem ser negados em permissions.deny no settings.json."
    },
    "filesystem-corpus": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./data/retrieval-corpus"
      ],
      "_description": "Somente leitura de data/retrieval-corpus/, para inspecionar os chunks indexados pelo pipeline RAG. O corpus é gerado pelo pipeline de ingestão, não pelo assistente, então write_file, edit_file, move_file e create_directory desta instância devem ser negados em permissions.deny."
    },
    "git": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."],
      "_description": "Consulta ao histórico do repositório (git_log, git_show, git_diff, git_status). O '.' identifica qual repositório consultar, não expõe a raiz como diretório de arquivos via filesystem. Tools de escrita (git_commit, git_add, git_reset, git_checkout, git_create_branch) devem ser negadas em permissions.deny, pois a necessidade é somente leitura de histórico."
    },
    "memory": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "MEMORY_FILE_PATH": "./.mcp/memory/novatech-graph.json"
      },
      "_description": "Memória persistente de decisões e linguagem ubíqua do projeto NovaTech, isolada em um arquivo de grafo dedicado a este repositório (não compartilhado com outros projetos)."
    }
  }
}
```

## Decisões de escopo

- **Raiz do projeto (`.`) nunca é `args` de nenhum `filesystem-*`.** Cada instância lista só as pastas que sua necessidade exige (`filesystem-dev` inclui `.mcp/` porque a própria configuração MCP é um artefato de desenvolvimento que o agente precisa poder editar).
- **`infra/` não aparece em nenhum `args`.** Nenhuma das 5 necessidades pede acesso a ele.
- **`_description` em cada server** documenta o motivo do escopo, para que uma futura revisão não amplie `args` sem justificativa.
- **`type: "stdio"`** em todos os servers, conforme solicitado — todos rodam como processo local via `npx`/`uvx`, sem exposição de rede.

## Limitação conhecida: `git` e `infra/`

`infra/*.bicep` e `infra/parameters/*.bicepparam` estão versionados no git. O `mcp-server-git` opera sobre o repositório inteiro (não tem escopo por pasta) — então tools como `git_show`/`git_diff` podem, tecnicamente, recuperar o conteúdo histórico de `infra/`, mesmo que nenhum `filesystem-*` aponte para lá.

Isso **não é uma permissão nova**: qualquer pessoa com `git clone` do repositório já tem esse mesmo acesso via `git show`/`git log` no terminal — o server MCP apenas expõe via tool o que já é acessível pelo git local. Duas mitigações possíveis, caso os `.bicepparam` contenham valores sensíveis reais (em vez de referências a Key Vault):

1. Tratar isso como um problema de **higiene do repositório** (segredos não deveriam estar versionados em texto plano, independentemente do MCP) — fora do escopo desta configuração.
2. Se for necessário isolar mesmo o histórico, o `git` server precisaria apontar para um mirror do repo com `infra/` removido do histórico (`git filter-repo`), o que é uma decisão maior e não foi pedida aqui.

## Próximo passo sugerido (fora deste arquivo)

O `settings.json` do Claude Code precisa das regras `permissions.deny` para as tools de escrita de `filesystem-docs`, `filesystem-corpus` e `git` (ex.: `mcp__filesystem-docs__write_file`, `mcp__git__git_commit`) — isso não é parte do `.mcp/mcp.json`, é configurado separadamente.
