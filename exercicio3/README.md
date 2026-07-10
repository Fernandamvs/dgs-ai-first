# Exercício 1.3 — POC do Pipeline de RAG (NovaTech)

## Descrição

Este exercício é uma prova de conceito funcional de um pipeline de RAG (Retrieval-Augmented Generation) construída inteiramente com ferramentas gratuitas e open-source, sem depender de nenhum serviço pago. 
O objetivo foi validar, para o cenário da NovaTech, se é possível montar um fluxo de ingestão, busca semântica e montagem de prompt que responda perguntas de atendimento com base na documentação interna da empresa — antes de investir em licenças Azure (Azure AI Search, Azure OpenAI, etc.).

## Stack utilizada

- **Python** — linguagem usada em todos os scripts do pipeline.
- **ChromaDB** — banco de dados vetorial local (persistente em disco) usado para armazenar e consultar os embeddings dos chunks.
- **sentence-transformers** (modelo `all-MiniLM-L6-v2`) — geração dos embeddings usados na busca semântica.
- **GitHub Copilot** — geração do código dos scripts Python a partir de prompts descritivos.
- **Claude (via chat)** — geração das perguntas de teste e avaliação das respostas produzidas pelo pipeline.

## Arquivos do projeto

- **config.py** — arquivo de configuração central: caminho do ChromaDB, nome da coleção, modelo de embedding, caminho dos documentos-fonte, limite de tokens por chunk e lista dos documentos a serem ingeridos.
- **ingestao.py** — lê os documentos markdown da NovaTech, divide o conteúdo em chunks por seção (`##`/`###`) sem quebrar tabelas, gera os embeddings com `sentence-transformers` e persiste tudo no ChromaDB.
- **busca.py** — recebe uma pergunta, gera seu embedding, consulta o ChromaDB pelos chunks mais similares e devolve os resultados já normalizados (score, fonte, classificação, versão, confiabilidade etc.), incluindo interface de linha de comando.
- **montagem_prompt.py** — monta o prompt final enviado ao LLM em três partes (system prompt com as regras de resposta, contexto com os chunks recuperados e a pergunta do atendente).
- **executar_testes.py** — roda uma bateria de 5 perguntas de teste contra o pipeline completo (busca + montagem de prompt) e salva os resultados brutos em JSON.
- **requirements.txt** — lista as dependências Python do projeto (`chromadb`, `sentence-transformers`, `torch`).
- **resultados-testes.md** — resultados das 5 perguntas de teste, com os chunks recuperados e as respostas avaliadas.
- **analise-problemas.md** — análise dos problemas identificados durante os testes do pipeline.

## Estratégia de chunking

Foi utilizado chunking por seção markdown (`##` e `###`), com limite de 600 tokens por chunk. Essa escolha se justifica porque os documentos da NovaTech têm uma estrutura clara em seções numeradas e contêm tabelas importantes (como a de multiplicadores regionais de frete e a tabela de SLA por cliente) que não podem ser cortadas no meio. Um chunking por tamanho fixo quebraria essas tabelas em pedaços incompletos e perderia o contexto semântico de cada regra de negócio — por isso o `ingestao.py` preserva blocos de tabela
inteiros ao dividir uma seção em sub-chunks, mesmo que isso ultrapasse ligeiramente o limite de tokens.

## Evidência de uso do GitHub Copilot

Todos os scripts `.py` deste projeto foram gerados via GitHub Copilot, a partir de prompts descritivos em linguagem natural. Os prompts utilizados para cada arquivo foram:

- **ingestao.py**: "Crie um script Python que leia os documentos markdown da NovaTech, divida o conteúdo em chunks por seção (headings ## e ###), respeitando um limite máximo de 600 tokens por chunk e sem quebrar tabelas markdown no meio, gere os embeddings de cada chunk com sentence-transformers (modelo all-MiniLM-L6-v2) e persista tudo em uma coleção do ChromaDB, imprimindo um resumo da quantidade de chunks gerados por documento."
- **busca.py**: "Crie um script Python com uma função que receba uma pergunta, gere seu embedding com sentence-transformers e busque no ChromaDB os chunks mais similares, retornando para cada resultado o texto, a fonte, o título, a classificação do documento, se é confiável, a versão e o score de similaridade normalizado entre 0 e 1. Inclua também uma interface de linha de comando para testar buscas manualmente."
- **montagem_prompt.py**: "Crie um script Python com uma função que monte o prompt final para o LLM em três partes: um system prompt com instruções para responder somente com base nos chunks fornecidos, citar a fonte, alertar sobre conflitos entre versões diferentes do mesmo documento e sobre chunks de fontes não confiáveis; um bloco de contexto formatando cada chunk recuperado com sua fonte, seção e score; e a pergunta original do atendente."
- **executar_testes.py**: "Crie um script Python que execute uma lista fixa de 5 perguntas de teste contra o pipeline de busca e montagem de prompt, imprima no console os chunks recuperados e o prompt final de cada pergunta, trate o erro de ChromaDB não inicializado com uma mensagem clara pedindo para rodar a ingestão primeiro, e salve todos os resultados em um arquivo JSON."

## Como executar

Execute os comandos abaixo, na ordem, a partir da pasta `exercicio3`:

```
..\.venv\Scripts\python.exe ingestao.py
..\.venv\Scripts\python.exe executar_testes.py
```

O primeiro comando realiza a ingestão dos documentos e popula o ChromaDB. O segundo executa as 5 perguntas de teste contra o pipeline completo e salva os resultados brutos em `resultados-brutos.json`.

## Resultados

Os resultados detalhados dos 5 testes estão documentados em
[resultados-testes.md](resultados-testes.md), e os problemas identificados
durante a análise do pipeline estão descritos em
[analise-problemas.md](analise-problemas.md).
