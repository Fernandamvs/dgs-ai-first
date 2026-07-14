# Resultados dos Testes — Assistente de Atendimento NovaTech

> Observação geral sobre os dados: em **todos** os chunks recuperados, os campos `fonte` e `versao` vieram vazios (exibidos como "Fonte: desconhecido — Sem título (versão N/A)") e a `classificacao` veio como `"informal"` em 100% dos casos. Isso indica uma falha no pipeline de indexação (metadados de origem não preenchidos), e é um fator relevante em todas as avaliações de "citou fonte" abaixo.

---

## Teste 1 — Qual o prazo para solicitar devolução de mercadoria?

### Chunks recuperados
| Chunk | Seção | Fonte | Versão | Classificação | Score |
|---|---|---|---|---|---|
| 1 | 3.3. Procedimento de devolução | desconhecido | N/A | informal | 1.00 |
| 2 | 3. Prazo de entrega para frete especial | desconhecido | N/A | informal | 0.07 |
| 3 | Item 3 — devolver carga perigosa | desconhecido | N/A | informal | 0.04 |
| 4 | 3.5. Custos de devolução | desconhecido | N/A | informal | 0.00 |

### Resposta do Claude
Segundo a documentação disponível (Fonte: desconhecida — metadados de origem não preenchidos), o processo de devolução funciona assim: o cliente abre um chamado no Portal do Cliente informando o CT-e, fotos da mercadoria e o motivo da devolução; o atendimento faz a triagem em até 4h úteis e, se aprovado, agenda a coleta reversa em até 2 dias úteis (seção "3.3. Procedimento de devolução").

Quanto ao prazo para **solicitar** a devolução: a seção "3.5. Custos de devolução" indica que solicitações feitas após **7 dias úteis** não são mais elegíveis para devolução padrão, devendo ser encaminhadas ao Comercial para negociação caso a caso. Portanto, o prazo para solicitar a devolução é de até **7 dias úteis**.

⚠️ Atenção: os trechos usados estão classificados como "informal" (fonte não validada oficialmente). Recomendo confirmar essa informação com a documentação oficial de política de devoluções antes de repassá-la como definitiva ao cliente.

### Avaliação
- Correta? **Sim** — o prazo de 7 dias úteis está explicitamente no chunk 4 (o de menor score, 0.00), e a resposta corretamente priorizou esse conteúdo por relevância semântica em vez de se guiar cegamente pelo score de similaridade.
- Citou fonte? **Parcial** — mencionou as seções de origem (3.3, 3.5), mas não pôde citar um doc_id formal porque o campo "fonte" veio vazio em todos os chunks; optou por declarar isso explicitamente em vez de inventar um código de documento.
- Respeitou guardrails? **Sim** — alertou explicitamente que a classificação é "informal" e recomendou validação antes de repassar a informação como definitiva.

### Veredito: PASSOU PARCIALMENTE

---

## Teste 2 — Posso devolver uma carga perigosa?

### Chunks recuperados
| Chunk | Seção | Fonte | Versão | Classificação | Score |
|---|---|---|---|---|---|
| 1 | Item 3 — devolver carga perigosa | desconhecido | N/A | informal | 1.00 |
| 2 | Item 38 — carga chegou danificada | desconhecido | N/A | informal | 0.36 |
| 3 | Item 32 — carga perigosa com frete expresso | desconhecido | N/A | informal | 0.07 |
| 4 | Item 22 — seguro de carga | desconhecido | N/A | informal | 0.00 |

### Resposta do Claude
De acordo com o único trecho diretamente relacionado a essa pergunta (Fonte: desconhecida — trecho classificado como nota interna informal, "Item 3"), oficialmente não é possível devolver carga perigosa pelo processo padrão de devolução. No entanto, o próprio trecho menciona que já houve casos em que o setor de Gestão de Riscos (ramal 4500) autorizou exceções. Recomendo orientar o cliente a acionar o ramal 4500 para avaliação do caso, informando que a situação exige tratamento especial, em vez de afirmar que é impossível.

⚠️ Atenção: essa é a única informação disponível sobre o tema e vem de uma fonte classificada como "informal" (parece ser um registro interno de dúvidas frequentes de atendimento, não um documento de política oficial). Recomendo validar com Gestão de Riscos ou com a documentação oficial de devolução de cargas perigosas antes de confirmar definitivamente ao cliente.

### Avaliação
- Correta? **Parcial** — reflete fielmente o único chunk relevante, mas a "documentação" de origem é, ela mesma, uma nota informal (não uma política formal), então não há garantia de que reflete a política oficial vigente da NovaTech.
- Citou fonte? **Não** — não há doc_id nem nome de documento nos metadados; a resposta apenas descreveu o trecho como "nota interna informal, Item 3", sem um identificador formal de documento.
- Respeitou guardrails? **Sim** — alertou claramente que a fonte é informal/não validada e evitou uma negativa categórica, seguindo a orientação do próprio trecho ("não diga que é impossível — diga que precisa de tratamento especial").

### Veredito: PASSOU PARCIALMENTE

---

## Teste 3 — Qual o SLA do cliente Gold para incidentes críticos?

### Chunks recuperados
| Chunk | Seção | Fonte | Versão | Classificação | Score |
|---|---|---|---|---|---|
| 1 | Item 41 — SLA de resposta vs. resolução | desconhecido | N/A | informal | 1.00 |
| 2 | 3. Definição de incidente crítico | desconhecido | N/A | informal | 0.89 |
| 3 | 5. Medição e reportes | desconhecido | N/A | informal | 0.73 |
| 4 | Item 15 — tier "Platinum" não existe | desconhecido | N/A | informal | 0.00 |

### Resposta do Claude
Os trechos disponíveis (fonte: desconhecida) indicam o seguinte sobre SLA do plano Gold:
- SLA **padrão** (não crítico): resposta em até 2h e resolução em até 24h (seção "Item 41").
- Um incidente é considerado **crítico** quando, por exemplo, envolve carga acima de R$100.000 sem rastreamento há mais de 6h, carga perigosa com irregularidade documental, mais de 5 chamados repetidos em 24h, ou risco à segurança de pessoas (seção "3. Definição de incidente crítico").
- Para incidentes críticos de clientes Gold, o relógio de SLA **não pausa** fora do horário comercial, diferente dos chamados gerais (seção "5. Medição e reportes").
- O próprio trecho "Item 41" afirma que, para incidentes críticos, os prazos são **menores** do que os padrões (2h/24h) e remete a uma "tabela SLA-2024" — porém essa tabela com os valores exatos não está entre os trechos recuperados.

**Não encontrei o valor exato do SLA de incidente crítico para o cliente Gold** na documentação disponível — recomendo consultar diretamente a tabela SLA-2024 mencionada nos trechos.

⚠️ Atenção: os trechos usados estão classificados como "informal" (fonte não validada oficialmente).

### Avaliação
- Correta? **Parcial** — corretamente evitou inventar um número específico de SLA crítico que não estava nos chunks, mas apenas contextualizou com o que estava disponível (definição, regra do relógio, SLA padrão).
- Citou fonte? **Parcial** — mencionou a "tabela SLA-2024" (citada dentro do próprio texto do chunk) e as seções de origem, mas não havia doc_id formal nos metadados.
- Respeitou guardrails? **Sim** — reconheceu o gap de cobertura (valor exato do SLA crítico) em vez de inventar um número, e alertou sobre a classificação informal.

### Veredito: PASSOU PARCIALMENTE

---

## Teste 4 — Qual o multiplicador de frete especial para o Nordeste?

### Chunks recuperados
| Chunk | Seção | Fonte | Versão | Classificação | Score |
|---|---|---|---|---|---|
| 1 | 2.1. Multiplicadores regionais (atualizados nov/2023) | desconhecido | N/A | informal | 1.00 |
| 2 | 2.1. Multiplicadores regionais (sem data) | desconhecido | N/A | informal | 0.91 |
| 3 | Item 8 — como funciona o frete especial (nota sobre PROC-042 v1/v2) | desconhecido | N/A | informal | 0.01 |
| 4 | Item 41 — SLA resposta vs. resolução | desconhecido | N/A | informal | 0.00 |

### Resposta do Claude
⚠️ Atenção: os trechos recuperados contêm **duas versões conflitantes** da tabela de multiplicadores regionais (seção "2.1. Multiplicadores regionais"), aparentemente da PROC-042:
- Versão mais recente (atualizada em novembro/2023): Nordeste = **1.5**
- Versão mais antiga (sem data): Nordeste = **1.4**

Um terceiro trecho (Item 8) confirma que existem duas versões da PROC-042 e orienta usar a mais recente, que tem multiplicadores mais altos — portanto a versão de novembro/2023 (Nordeste = 1.5) é a que deve ser usada como referência atual.

**Resposta: o multiplicador de frete especial para o Nordeste é 1.5**, segundo a versão mais recente da tabela.

Importante: se o cliente contestar o valor, verifique se o contrato dele foi firmado antes da atualização de novembro/2023, pois pode ainda estar na tabela antiga (multiplicador 1.4), conforme apontado no mesmo trecho.

⚠️ Todos os trechos usados aqui estão classificados como "informal" (fonte não validada oficialmente) — recomendo confirmar com a versão oficial vigente da PROC-042 antes de informar o valor definitivo ao cliente.

### Avaliação
- Correta? **Sim** — identificou corretamente a versão mais recente (1.5) usando a pista do terceiro chunk ("multiplicadores mais altos = mais recente"), sem se deixar enganar pelo score de similaridade (a versão antiga tinha score 0.91, próximo do 1.00 da nova).
- Citou fonte? **Parcial** — referenciou a seção "2.1. Multiplicadores regionais" e o documento "PROC-042" (mencionado dentro do texto do Item 8, não nos metadados), mas não há doc_id formal nos metadados (campo fonte vazio).
- Respeitou guardrails? **Sim** — alertou explicitamente sobre o conflito de versões e indicou qual era a mais recente, exatamente como pedido nas instruções do system prompt.

### Veredito: PASSOU

---

## Teste 5 — Qual o frete para uma carga de 300kg para São Paulo?

### Chunks recuperados
| Chunk | Seção | Fonte | Versão | Classificação | Score |
|---|---|---|---|---|---|
| 1 | Item 22 — seguro de carga | desconhecido | N/A | informal | 1.00 |
| 2 | 4. Condições especiais (versão A) | desconhecido | N/A | informal | 0.72 |
| 3 | 4. Condições especiais (versão B, com nota de revisão da PROC-043) | desconhecido | N/A | informal | 0.51 |
| 4 | 1. Objetivo | desconhecido | N/A | informal | 0.00 |

### Resposta do Claude
**Não encontrei essa informação na documentação disponível.**

Contexto: os trechos recuperados tratam do procedimento de "frete especial", que a própria documentação define como aplicável apenas a **cargas acima de 500kg** (seção "1. Objetivo"). Como a pergunta é sobre uma carga de 300kg, ela está fora do escopo desses trechos, e não há, entre os chunks fornecidos, uma tabela ou fórmula de frete padrão para cargas abaixo de 500kg. Recomendo consultar a tabela de frete padrão (não incluída nestes trechos) ou confirmar com o time de Comercial.

Observação adicional: notei também que dois trechos da seção "4. Condições especiais" apresentam conteúdo diferente entre si (um menciona desconto a partir de 10 fretes/mês negociado com o Comercial; outro traz uma escala de desconto de 5%/10% a partir de 8/15 fretes/mês, além de uma nota de que a PROC-043 está em revisão pelo Compliance) — isso sugere que também há versões conflitantes desse documento. Como não é diretamente relevante à pergunta sobre 300kg, isso não afeta a resposta final, mas registro o alerta.

⚠️ Todos os trechos usados são classificados como "informal" (fonte não validada).

### Avaliação
- Correta? **Sim** — reconheceu corretamente que a pergunta está fora do escopo da documentação de frete especial (que só cobre cargas acima de 500kg) e não inventou um valor de frete, respondendo com o fallback exigido pelo gap de cobertura.
- Citou fonte? **Parcial** — referenciou as seções (1. Objetivo, 4. Condições especiais) e o código "PROC-043" mencionado no texto, mas sem doc_id formal, já que o campo "fonte" veio vazio nos metadados.
- Respeitou guardrails? **Sim** — usou corretamente a regra de gap de cobertura (frase de fallback) em vez de estimar um valor, e ainda identificou proativamente um conflito de versão secundário na seção 4, alertando sobre isso.

### Veredito: PASSOU

---

## Resumo

| Teste | Pergunta | Veredito |
|---|---|---|
| 1 | Prazo para devolução de mercadoria | PASSOU PARCIALMENTE |
| 2 | Devolução de carga perigosa | PASSOU PARCIALMENTE |
| 3 | SLA Gold para incidentes críticos | PASSOU PARCIALMENTE |
| 4 | Multiplicador de frete — Nordeste | PASSOU |
| 5 | Frete para carga de 300kg (SP) | PASSOU |

**Padrão identificado:** em todos os 5 testes, o campo `fonte` dos chunks veio vazio ("desconhecido") e a `classificacao` veio sempre "informal" — uma falha no pipeline de indexação/metadados que impede a citação de doc_id formal exigida pelo system prompt, rebaixando a nota de "citou fonte" mesmo quando o raciocínio da resposta estava correto. Os testes 4 e 5 validam com sucesso os dois guardrails mais críticos do prompt: detecção de conflito de versão entre chunks do mesmo documento (PROC-042) e reconhecimento de gap de cobertura (frete para carga abaixo do limite de 500kg) sem alucinar um valor.
