# Relatório Final — Pull, Otimização e Avaliação de Prompts (Bug to User Story)

Relatório de entrega do desafio de **pull, otimização e avaliação de prompts** com LangChain e LangSmith. O objetivo foi transformar relatos de bug em user stories completas, atingindo métricas ≥ 0,9 em todas as avaliações.

**Instruções originais do desafio:** [docs/INSTRUCOES_DESAFIO.md](docs/INSTRUCOES_DESAFIO.md)  
**Análise detalhada do processo (passo a passo):** [docs/ANALISE_PROCESO_COMPLETO.md](docs/ANALISE_PROCESO_COMPLETO.md)

---

## 1. Processo e decisões (resumo passo a passo)

| Fase | O que foi feito | Decisão principal |
|------|-----------------|-------------------|
| **1. Pull** | Pull do prompt `leonanluppi/bug_to_user_story_v1` via `src/pull_prompts.py`; salvamento em `prompts/`. | Usar LangSmith como fonte do prompt inicial; manter V1 local para comparação. |
| **2. Avaliação V1** | Execução de `src/evaluate.py` com 10 exemplos do dataset. | Resultados: F1 0,69 e Correctness 0,81 abaixo de 0,9; Precision 0,92 alta → **diagnóstico: Recall baixo** (modelo omitia informações da referência). |
| **3. Análise** | Análise do prompt V1 e do dataset (`ANALISE_PROMPT_V2.md`). | Identificados 6 problemas: sem formato definido, sem completude, sem tratamento de complexidade, prompt vago, zero-shot, bug no system prompt. |
| **4. Propostas 1–3** | Role + formato + estrutura; completude + complexidade + edge cases; few-shot (2 exemplos). | Separação system/user; formato “Como… Eu quero… Para que…” + Given-When-Then; lista de seções; 2 exemplos (simples e médio). |
| **5. Avaliação V2** | Nova avaliação após Propostas 1–3. | Média 0,90 mas F1 0,77 e Correctness 0,87 ainda abaixo de 0,9 → **decisão: forçar análise sistemática antes de gerar** (Skeleton of Thought). |
| **6. Proposta 4** | Pipeline em 4 passos: EXTRAÇÃO → CLASSIFICAÇÃO → CHECKLIST → GERAÇÃO. | Modelo deve identificar todas as informações do relato e só então gerar; checklist “identificou tudo?” antes da geração. |
| **7. Avaliação V3** | Avaliação após Skeleton of Thought. | **Aprovação:** média 0,9089; todas as métricas ≥ 0,9 ou muito próximas. |
| **8. Iterações posteriores** | Análise crítica, ajustes de Precision, desredundância, opções de recall, exemplos adicionais e edge cases. | Alinhamento às referências do dataset; regras RECALL/PRECISION explícitas; 8 exemplos (simples a complexo); edge cases (performance, estoque, Safari/Chrome, complexo 4+ problemas); proteção “não inventar” e “só o que o relato mencionar”. |

---

## 2. Técnicas Aplicadas (Fase 2)

As técnicas abaixo foram aplicadas no prompt otimizado (`prompts/bug_to_user_story_v2.yml`), com justificativa de cada escolha.

### 2.1 Role Prompting (persona e objetivo)

**O que foi feito:** Definição clara de papel: “Você é um analista que transforma relatos de bug em user stories completas para desenvolvimento” e objetivo (equilíbrio recall/precision, termos do relato, saída clara).

**Justificativa:** O V1 usava “assistente que transforma bugs em tarefas”, o que era vago e não alinhado ao formato user story. Um “analista” com objetivo explícito reduz ambiguidade e alinha o modelo ao output esperado (user story + critérios + contexto quando aplicável).

---

### 2.2 Regras explícitas (RECALL e PRECISION)

**O que foi feito:** Duas regras obrigatórias: (1) **RECALL** — cada fato explícito ou diretamente implícito do relato deve aparecer na saída; não inferir fatos que não estejam escritos; (2) **PRECISION** — usar apenas informações do relato; não inventar; citar literalmente endpoints, códigos HTTP, valores, severidade; critérios Given-When-Then derivados do relato.

**Justificativa:** O avaliador (F1, Correctness, Precision) mede cobertura do esperado (recall) e correção do gerado (precision). Deixar essas duas regras explícitas direciona o modelo a “incluir tudo que está no relato” e “não acrescentar o que não está”, evitando tanto omissão (recall baixo) quanto alucinação (precision baixa).

---

### 2.3 Chain of Thought / Skeleton of Thought (pipeline)

**O que foi feito:** Pipeline em 6 passos antes de gerar: (a) Extrair do relato apenas o que o relato mencionar; (b) Classificar complexidade (Simples | Médio | Complexo); (c) Mapear cada item para uma seção da saída; (d) Verificar inclusão e, em múltiplos problemas, blocos A./B./C./D.; (d.1) Verificação por tipo (PERFORMANCE, FLUXO/REGRA, COMPLEXO); (e) Gerar na ordem das seções; (f) Checklist final (tudo incluído? nada inventado? termos exatos?).

**Justificativa:** O recall baixo no V1/V2 vinha em parte do modelo “resumir” sem passar por uma etapa de extração e verificação. Um processo explícito (Skeleton of Thought) força o modelo a identificar primeiro o que está no relato e só depois gerar, reduzindo omissões. A verificação por tipo (performance, estoque, complexo) cobre os padrões do dataset e das referências.

---

### 2.4 Estrutura da saída (seções possíveis)

**O que foi feito:** Lista fixa de seções na ordem: User story, Critérios de Aceitação, Contexto Técnico, Contexto do Bug, Contexto de Segurança, Exemplo de Cálculo, Critérios Adicionais, Critérios Técnicos/Tasks. Regra: só incluir seção se o relato trouxer dados concretos; em relatos complexos usar formato Exemplo 8 (=== USER STORY ===, === CRITÉRIOS ===, etc.).

**Justificativa:** As referências do dataset usam essas seções (Contexto de Segurança, Exemplo de Cálculo, Critérios Adicionais, etc.). Sem lista explícita, o modelo tendia a produzir menos seções e o avaliador considerava “informações importantes omitidas” (recall baixo). Alinhar a estrutura da saída à das referências reduz omissão de blocos inteiros.

---

### 2.5 Few-shot Learning (8 exemplos)

**O que foi feito:** Oito exemplos entrada/saída no system prompt: 1–2 simples (carrinho, email), 3–4 médios (dashboard, webhook), 5–7 com segurança, cálculo, z-index/modal, e **Exemplo 8** complexo (checkout com múltiplos problemas A./B./C./D., Critérios Técnicos, Contexto do Bug, Tasks).

**Justificativa:** Zero-shot no V1 gerava formato e nível de detalhe inconsistentes. Few-shot fixa o formato esperado (Como… Eu quero… Para que…, Given-When-Then, seções nomeadas) e mostra casos médios e complexos alinhados ao dataset. O Exemplo 8 cobre relatos com 4+ problemas e impacto, que são os que mais penalizavam recall quando faltavam blocos A./B./C./D. e Tasks.

---

### 2.6 Tratamento de edge cases

**O que foi feito:** Regras explícitas para: relato vago ou curto; “em X não funciona, em Y funciona” (ex.: Safari vs Chrome); performance (relatório/query lento, ANR, lista grande); estoque/carrinho (validação, último item, Critérios de Prevenção); z-index/modal/menu lateral; múltiplos bugs; só técnico (stack trace); relato médio/complexo; **relato COMPLEXO** (4+ problemas, todos os números, SLA Atual vs Esperado, Tasks por fase).

**Justificativa:** O dataset e as referências contêm esses padrões. Sem regras específicas, o modelo tratava tudo de forma genérica e omitia seções ou números que o avaliador esperava. Os edge cases garantem que performance, estoque, multi-ambiente e relatos complexos tenham saída alinhada às referências (Contexto Técnico com “Problema identificado/Performance atual/esperada”, Critérios de Prevenção, blocos A./B./C./D., etc.).

---

### 2.7 Separação System vs User Prompt

**O que foi feito:** O relato de bug vai **apenas** no user message (`user_prompt: '{bug_report}'`); no system prompt ficam apenas instruções, regras, pipeline, estrutura e exemplos (sem `{bug_report}`).

**Justificativa:** Evita confusão e duplicação; deixa claro que a “entrada” é só o relato e que todas as regras são fixas. Também corrige o bug do V1 em que `{bug_report}` aparecia no system e podia ser interpretado literalmente.

---

### 2.8 Proteção de Precision (não inventar)

**O que foi feito:** Frases explícitas: extrair “apenas o que o relato mencionar”; “não preencha categorias sem base no texto”; “cada bullet deve ter base no relato”; “não adicione boas práticas que o relato não citou”; em complexos, “causas e sugestões técnicas **derivadas** do relato” (ex.: Connection pool exhausted → Aumentar connection pool) são permitidas; “sem adicionar fatos que não estejam no relato”.

**Justificativa:** Ao reforçar recall (incluir tudo), havia risco de o modelo “completar” com critérios ou sugestões que não estavam na referência e perder Precision. As regras acima limitam a fatos explícitos ou diretamente implícitos e a problema→solução derivada do relato, sem abrir espaço para boas práticas genéricas não pedidas.

---

## 3. Resultados Finais

### Link do LangSmith

[**Dashboard LangSmith — Projeto de Avaliação**](https://smith.langchain.com/o/eb1222af-1ce7-4844-8121-e8fb24c8e915/projects/p/c98ffa42-1bde-4ae8-8235-db921629e781?timeModel=%7B%22duration%22%3A%227d%22%7D&tab=0)

O link acima contém: dataset de avaliação, execuções dos prompts v1 e v2, métricas e tracing de exemplos.

### Screenshots das avaliações (notas mínimas 0,9 atingidas)

**V2 com Gemini (gemini-2.5-flash) — APROVADO ✓**

![Avaliação V2 com Gemini](screenshots/eval-gemini.png)

**V2 com GPT (gpt-4o-mini / gpt-4o) — APROVADO ✓**

![Avaliação V2 com GPT](screenshots/eval-gpt.png)

### Tabela comparativa: prompts ruins (v1) vs prompts otimizados (v2)

| Métrica       | V1 (GPT) | V1 (Gemini) | V2 (GPT) | V2 (Gemini) | Meta |
|---------------|----------|-------------|----------|-------------|------|
| Helpfulness   | 0,88 ✗   | 0,93 ✓      | 0,94 ✓   | 0,97 ✓      | ≥ 0,9 |
| Correctness   | 0,79 ✗   | 0,83 ✗      | 0,92 ✓   | 0,94 ✓      | ≥ 0,9 |
| F1-Score      | 0,72 ✗   | 0,74 ✗      | 0,90 ✓   | 0,91 ✓      | ≥ 0,9 |
| Clarity       | 0,90 ✗   | 0,95 ✓      | 0,94 ✓   | 0,97 ✓      | ≥ 0,9 |
| Precision     | 0,86 ✗   | 0,92 ✓      | 0,94 ✓   | 0,97 ✓      | ≥ 0,9 |
| **Média**     | **0,8261** | **0,8750** | **0,9304** | **0,9530** | ≥ 0,9 |
| **Status**    | REPROVADO | REPROVADO   | APROVADO ✓ | APROVADO ✓ | — |

---

## 4. Como executar

### 4.1 Pré-requisitos

- **Python:** 3.9+
- **Ambiente:** Recomendado usar ambiente virtual (`venv`).
- **Variáveis de ambiente:** Copiar `.env.example` para `.env` e preencher:
  - **LangSmith:** `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `USERNAME_LANGSMITH_HUB` (para push).
  - **LLM:** `LLM_PROVIDER` (ex.: `openai` ou `google`), `LLM_MODEL`, `EVAL_MODEL`.
  - **OpenAI (se usar):** `OPENAI_API_KEY`.
  - **Google (se usar):** `GOOGLE_API_KEY`.
- **Dataset:** Arquivo `datasets/bug_to_user_story.jsonl` presente (já fornecido no repositório).
- **Dependências:** `pip install -r requirements.txt`.

### 4.2 Comandos (ordem sugerida)

```bash
# 1. Ambiente virtual (recomendado)
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Dependências
pip install -r requirements.txt

# 3. Configurar .env (copiar de .env.example e preencher chaves)

# 4. Pull do prompt inicial do LangSmith (salva em prompts/)
python src/pull_prompts.py

# 5. Push do prompt otimizado (bug_to_user_story_v2) para o LangSmith Hub
python src/push_prompts.py

# 6. Avaliação: carrega dataset, puxa prompt do Hub, roda 10 exemplos, calcula métricas
python src/evaluate.py

# 7. Testes de validação do prompt (pytest)
pytest tests/test_prompts.py
```

### 4.3 Pré-requisitos para o teste de avaliação

- `.env` com `LANGSMITH_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `EVAL_MODEL` e a API key do provider (OpenAI ou Google).
- Prompt `bug_to_user_story_v2` publicado no LangSmith Hub (via `push_prompts.py`) para o `evaluate.py` puxar do Hub.
- Arquivo `datasets/bug_to_user_story.jsonl` no caminho esperado pelo script (o `evaluate.py` usa os primeiros 10 exemplos).

---

## 5. Entregáveis e referências

| Entregável | Descrição |
|------------|-----------|
| **Código** | `src/pull_prompts.py`, `src/push_prompts.py`, `src/evaluate.py`, `src/metrics.py`, `src/dataset.py`, `src/utils.py` |
| **Prompt otimizado** | `prompts/bug_to_user_story_v2.yml` |
| **Testes** | `tests/test_prompts.py` (pytest) |
| **Instruções do desafio** | [docs/INSTRUCOES_DESAFIO.md](docs/INSTRUCOES_DESAFIO.md) |
| **Análise completa do processo** | [docs/ANALISE_PROCESO_COMPLETO.md](docs/ANALISE_PROCESO_COMPLETO.md) |
| **Evidências LangSmith** | [Dashboard LangSmith](https://smith.langchain.com/o/eb1222af-1ce7-4844-8121-e8fb24c8e915/projects/p/c98ffa42-1bde-4ae8-8235-db921629e781?timeModel=%7B%22duration%22%3A%227d%22%7D&tab=0) |

O documento [docs/ANALISE_PROCESO_COMPLETO.md](docs/ANALISE_PROCESO_COMPLETO.md) consolida, passo a passo, todas as análises (métricas, diagnóstico, recall, precision, redundâncias, planos de implementação e evolução do prompt) e referencia os demais relatórios em `docs/`.
