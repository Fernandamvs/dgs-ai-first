# Evidência — Cálculo de Frete Especial (Corpus RAG)

**Pergunta do atendente:** "Qual o valor do frete especial para uma carga de 2.000 kg com destino ao Nordeste?"

**Fonte:** `data/retrieval-corpus/chunks-novatech.md`

> **Nota sobre acesso:** a instrução original pedia o uso do servidor MCP `filesystem-corpus`
> para esta leitura. Nesta sessão, nenhuma ferramenta desse servidor estava conectada/carregada
> (verificado por busca nas tools disponíveis — `mcp__filesystem-corpus__read_file` e variantes
> não retornaram resultado), então a leitura foi feita diretamente do arquivo no disco, com
> autorização do usuário. O conteúdo lido é o mesmo que o servidor MCP exporia (mesmo arquivo,
> mesmo diretório `data/retrieval-corpus/`, somente leitura).

---

## 1. Chunks relevantes

Para uma carga de 2.000 kg com destino ao Nordeste, os chunks recuperáveis por similaridade semântica são os da PROC-042 (Frete Especial), em suas duas versões, mais o FAQ que alerta sobre a duplicidade:

- **PROC-042-A** — Fórmula do frete especial (versão original): `Valor base × Multiplicador regional × Fator de peso`, com fator de peso 1.2 para 1.001–3.000 kg.
- **PROC-042-B** — Multiplicadores regionais (v1): Nordeste = 1.4.
- **PROC-042v2-A** — Fórmula atualizada (revisão nov/2023), com fator de peso **1.15** para 1.001–3.000 kg.
- **PROC-042v2-B** — Multiplicadores regionais atualizados: Nordeste = **1.5**.
- **PROC-042v2-E** — Disposições transitórias: define qual versão usar conforme a data de abertura do chamado.
- **FAQ-08** — Alerta de que existem duas versões da PROC-042 e orienta usar a mais recente (v2) na dúvida.

Chunks de menor relevância que podem aparecer no retrieval, mas não devem ser usados para o cálculo: PROC-042-C / PROC-042v2-C (prazo de entrega, não valor) e PROC-042v2-D (desconto de volume, só se aplicável ao cliente).

## 2. Existe mais de uma versão — qual usar e por quê

Sim. Há **PROC-042 (v1, original)** e **PROC-042-v2 (revisão de novembro/2023)**, com multiplicadores e fatores de peso diferentes — e isso é uma armadilha proposital do corpus (ver seção "Armadilhas" do Anexo B: contradição PROC-042 vs v2).

Regra de decisão, conforme **PROC-042v2-E**:
- Chamados **abertos antes de 01/12/2023** e ainda em processamento → usar multiplicadores da **v1**.
- Chamados **novos a partir de 01/12/2023** → usar a **v2**.

Como a data atual é 2026-07-13 (muito depois de 01/12/2023) e não há indicação de que este seja um chamado antigo em processamento, **a versão correta é a v2**. Isso também é consistente com a orientação informal do **FAQ-08** ("na dúvida, use a mais recente v2"), mas o FAQ não é a fonte oficial — a decisão formal vem da disposição transitória PROC-042v2-E. O FAQ-08 ainda serve de alerta útil: se o cliente reclamar do valor, pode ser que seu contrato específico ainda esteja atrelado à tabela antiga — nesse caso, verificar com o comercial antes de fechar o valor.

## 3. Multiplicador e fator de peso corretos (v2, Nordeste, 2.000 kg)

- Multiplicador regional Nordeste (v2): **1.5** (PROC-042v2-B)
- Fator de peso para 2.000 kg, faixa 1.001–3.000 kg (v2): **1.15** (PROC-042v2-A)

(Para referência, na v1 seriam: multiplicador Nordeste 1.4 e fator de peso 1.2 — **não usar**, pois é a versão superada.)

## 4. Cálculo com valor base R$ 1.000,00

```
Valor do frete = Valor base × Multiplicador regional × Fator de peso
Valor do frete = R$ 1.000,00 × 1.5 × 1.15
Valor do frete = R$ 1.725,00
```

**Resposta: R$ 1.725,00**, usando a PROC-042-v2.

- Se, por exceção documentada (chamado antigo em processamento, PROC-042v2-E), fosse necessário aplicar a v1: R$ 1.000,00 × 1.4 × 1.2 = **R$ 1.680,00**. Este valor não deve ser usado como padrão — só citado se houver indicação explícita de que o chamado se qualifica para a regra de transição.
- Não foi aplicado o desconto de volume do **PROC-042v2-D** (5% a partir de 8 fretes especiais/mês, 10% acima de 15/mês) porque a pergunta não informa o volume mensal do cliente. Se essa informação existir, o multiplicador regional deve ser reduzido antes do cálculo.
