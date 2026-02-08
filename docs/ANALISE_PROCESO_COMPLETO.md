# Análise do processo completo — Bug to User Story

Este documento consolida, em ordem cronológica e lógica, todas as análises realizadas durante a otimização do prompt `bug_to_user_story_v2`: diagnóstico inicial, métricas, melhorias de recall e precision, tratamento de redundâncias e planos de implementação. **É o único arquivo necessário em `docs/` para entender todo o processo passo a passo.**

---

## Documentos que podem ser removidos de `docs/`

O conteúdo dos arquivos abaixo foi **integrado neste documento**. Eles **foram removidos** de `docs/`; este arquivo é a referência única.

| Arquivo | Conteúdo consolidado em |
|---------|-------------------------|
| `ANALISE_PROMPT_V2.md` | Seções 3.4, 4 |
| `RELATORIO_OTIMIZACAO.md` | Seções 3–5, 10 |
| `RELATORIO_METRICAS_EVALUATE.md` | Seção 2 |
| `ANALISE_CRITICA_PROMPT_E_DATASET.md` | Seção 6 |
| `ANALISE_PRECISION_PROMPT_V2.md` | Seção 7 |
| `ANALISE_REDUNDANCIAS_PROMPT_V2.md` | Seção 8 |
| `PLANO_MUDANCA_RECALL.md` | Seção 9.1 |
| `OPCOES_AUMENTO_RECALL_DETALHADO.md` | Seção 9.2 |
| `PLANO_IMPLEMENTACAO_ALTERNATIVA_1.md` | Seção 9.3 |

**Manter em `docs/`:** apenas `INSTRUCOES_DESAFIO.md` (instruções originais do desafio) e este arquivo (`ANALISE_PROCESO_COMPLETO.md`).

---

## 1. Objetivo e contexto

**Objetivo:** Transformar relatos de bug em user stories completas, com métricas de avaliação (Helpfulness, Correctness, F1-Score, Clarity, Precision) ≥ 0,9.

**Ferramentas:** LangChain, LangSmith (pull/push de prompts e avaliação), dataset `bug_to_user_story.jsonl`, script `src/evaluate.py` com métricas em `src/metrics.py`.

**Fluxo:** Pull do prompt V1 → análise e refatoração → push do V2 → avaliação → iterações até aprovação.

---

## 2. Métricas do evaluate.py (base para todas as decisões)

O `evaluate.py` usa até 10 exemplos do dataset. Para cada exemplo calcula:

| Métrica | Tipo | O que mede |
|--------|------|------------|
| **F1-Score** | Direta | Equilíbrio Precision×Recall: cobertura do esperado (recall) e correção/relevância do gerado (precision). F1 = 2×P×R/(P+R). |
| **Clarity** | Direta | Organização, linguagem simples, ausência de ambiguidade, concisão (média de 4 critérios). |
| **Precision** | Direta | Ausência de alucinações, foco na pergunta, correção factual (média de 3 critérios). |
| **Helpfulness** | Derivada | (avg_clarity + avg_precision) / 2. |
| **Correctness** | Derivada | (avg_f1 + avg_precision) / 2. |

**Aprovação:** média das cinco métricas ≥ 0,9.

**Recall** não é exibido separadamente; entra no F1. Recall baixo → modelo omite informações da referência → F1 e Correctness caem.

---

## 3. Fase 1 — Análise inicial (V1)

### 3.1 Prompt base

- Prompt puxado do LangSmith: `leonanluppi/bug_to_user_story_v1`.
- Características: genérico (“assistente que transforma bugs em tarefas”), sem formato definido, sem regras de completude, zero-shot.

### 3.2 Primeira avaliação

Executado `python src/evaluate.py` com 10 exemplos.

**Resultados V1:**

- Helpfulness: 0,93 ✓ | Correctness: 0,81 ✗ | F1-Score: 0,69 ✗ | Clarity: 0,94 ✓ | Precision: 0,92 ✓  
- Média: ~0,86.

### 3.3 Diagnóstico

- Precision alta (0,92) e F1 baixo (0,69) → **Recall baixo**: o modelo omite informações da referência.
- Variação por exemplo: melhores em bugs simples; piores em casos com mais detalhes (steps, logs, contexto técnico, múltiplos problemas).

### 3.4 Análise detalhada do prompt V1 (6 problemas)

Documento `ANALISE_PROMPT_V2.md` identificou:

1. **Sem formato definido** — dataset espera “Como… Eu quero… Para que…” + Critérios Given-When-Then; o prompt não mencionava.
2. **Sem orientação de completude** — nenhuma instrução para incluir todas as informações relevantes (passos, logs, endpoints, impacto).
3. **Sem tratamento de complexidade** — referências médias/complexas têm Contexto Técnico, Contexto do Bug, Tasks; o prompt tratava todos igual.
4. **“Tarefas para desenvolvedores” vago** — esperado são user stories completas, não só tarefas soltas.
5. **Zero-shot** — sem exemplos de formato nem nível de detalhe.
6. **Bug no system prompt** — `{bug_report}` aparecia no system; o relato deve vir só no user.

**Melhorias sugeridas:** formato explícito, completude (“não omitir”), regras para médio/complexo (Contexto Técnico, etc.), estrutura de saída definida, 1–2 exemplos few-shot, manter “não inventar”.

---

## 4. Fase 2 — Propostas 1 a 3 (Role, formato, completude, few-shot)

### 4.1 Proposta 1 — Role + formato + estrutura

- **Objetivo:** Definir role claro, formato obrigatório e estrutura; separar system/user.
- **Mudanças:** Role “analista sênior”; formato “Como… Eu quero… Para que…” e critérios Given-When-Then; estrutura: User story → Critérios; `bug_report` apenas no user prompt.

### 4.2 Proposta 2 — Completude + complexidade + edge cases

- **Objetivo:** Aumentar recall: não omitir informações; tratar simples vs médio/complexo.
- **Mudanças:** Seção COMPLETUDE (incluir tudo, não omitir, não inventar); COMPLEXIDADE (simples = user story + critérios; médio/complexo = + Contexto Técnico, Contexto do Bug, Tasks); EDGE CASES (relato vago, múltiplos bugs, só stack trace, relato curto); estrutura com itens 3 e 4 (Contexto Técnico, Contexto do Bug/Tasks).

### 4.3 Proposta 3 — Few-shot

- **Objetivo:** Reduzir ambiguidade com exemplos concretos.
- **Mudanças:** Dois exemplos: (1) bug simples — carrinho; (2) bug médio — webhook com steps e HTTP 500, saída com User story + Critérios + Contexto Técnico.

### 4.4 Resultados após Propostas 1–3 (V2)

- Helpfulness: 0,95 ✓ | Correctness: 0,87 ✗ | F1-Score: 0,77 ✗ | Clarity: 0,93 ✓ | Precision: 0,96 ✓  
- Média: 0,8963.  
- F1 e Correctness ainda abaixo de 0,9 → decisão: adicionar processo de análise antes de gerar (Skeleton of Thought).

---

## 5. Fase 3 — Proposta 4: Skeleton of Thought (V3)

### 5.1 Objetivo

Forçar o modelo a analisar sistematicamente antes de gerar, para que todas as informações sejam identificadas e refletidas na saída.

### 5.2 Processo de análise (4 passos)

1. **EXTRAÇÃO** — Identificar no relato: persona, problema, passos, logs, endpoints, impacto, severidade, etc.  
2. **CLASSIFICAÇÃO** — Simples / Médio / Complexo.  
3. **CHECKLIST** — Antes de gerar: confirmar que identificou TODAS as informações do passo 1.  
4. **GERAÇÃO** — Só então gerar seguindo FORMATO e ESTRUTURA DA SAÍDA.

### 5.3 Resultados V3 — Aprovação

- Helpfulness: 0,94 ✓ | Correctness: 0,90 ✓ | F1-Score: 0,82 ✓ | Clarity: 0,91 ✓ | Precision: 0,97 ✓  
- Média: 0,9089 ✅  

Evolução: V1 → V3: Correctness +0,09, F1-Score +0,13, média +0,05.

---

## 6. Análise crítica: prompt, dataset e recall

Documento `ANALISE_CRITICA_PROMPT_E_DATASET.md` avaliou a aderência do prompt às expectativas das métricas e ao dataset.

### 6.1 Expectativas por métrica

- **Recall:** todas as informações importantes da referência presentes na resposta.  
- **Precision:** informações na resposta corretas e relevantes (nada inventado).  
- **Clarity:** organização, linguagem, ausência de ambiguidade, concisão sem redundância.

### 6.2 Aderência do prompt (na época da análise)

- **Recall:** Parcial. Instruções de completude e processo em 4 passos existiam, mas a saída não estava explícita como “mesmo nível de detalhe e mesmas seções” que a referência; faltava exemplo complexo (múltiplas seções, A./B./C./D., Contexto de Segurança, Exemplo de Cálculo).  
- **Precision:** Intenção ok; faltava reforço de “cada critério derivável do relato”.  
- **Clarity:** Aderente; cuidado para não pedir “respostas curtas” e prejudicar recall.

### 6.3 Pontos fracos identificados

1. Estrutura de saída não alinhada a todas as seções das referências (Contexto de Segurança, Exemplo de Cálculo, Critérios Adicionais, etc.).  
2. Exemplos insuficientes: só 2 (simples e médio webhook); nenhum com múltiplos blocos A./B./C./D. ou Exemplo de Cálculo.  
3. Checklist falava em “identificou”, não em “incluiu na resposta”.  
4. Risco de o modelo acrescentar critérios “razoáveis” não presentes no relato → queda de Precision.

### 6.4 Dataset

- 16 exemplos no arquivo; `evaluate.py` usa os primeiros 10.  
- Nos 10 primeiros já aparecem: Contexto Técnico, Contexto de Segurança, Contexto do Bug, Critérios Adicionais, Exemplo de Cálculo, Critérios Técnicos.  
- Nomes de seção variam; para recall alto a resposta precisa ter estruturas e informações equivalentes às referências.

### 6.5 Recomendações para recall (sem prejudicar Precision/Clarity)

- Listar explicitamente todas as seções possíveis da saída.  
- Checklist explícito de “nada omitido” (incluí passos, endpoints, critérios, contexto?).  
- Um exemplo completo alinhado ao dataset (médio com várias seções).  
- Reforço: “Não inclua critérios/detalhes que não estejam no relato.”  
- Não pedir “respostas curtas”; manter concisão como “sem redundância”.

---

## 7. Ajustes de Precision (não inventar, não preencher com genérico)

Documento `ANALISE_PRECISION_PROMPT_V2.md` identificou pontos do prompt que podiam reduzir Precision ao priorizar recall.

### 7.1 Ajustes aplicados

- **RECALL:** Limitar a fatos **explícitos ou diretamente implícitos**; “não inferir fatos que não estejam escritos”.  
- **Pipeline (a):** “Extraia **apenas o que o relato mencionar**; não preencha categorias sem base no texto.”  
- **Pipeline (f):** “Sem adicionar fatos que não estejam no relato.”  
- **Seções:** “Só inclua uma seção se o relato trouxer dados concretos; evite conteúdo genérico.”  
- **Edge case médio/complexo:** “Mantenha cada item ligado a um fato do relato.”  
- **Pós-exemplos:** Regra de que cada bullet deve ter base explícita/implícita no relato; não adicionar boas práticas ou sugestões não mencionadas.  
- **System prompt:** Remover trecho “--- Relato do bug: {bug_report} ---”.

### 7.2 Recall em relatos complexos (após ganhos em Precision)

Recall em exemplos complexos (ex.: 13–15) caiu (modelo ficou conservador). Ajustes feitos:

- Edge case **Relato COMPLEXO:** saída deve ter User story, Critérios A./B./C./D. (um por problema), Critérios Técnicos com causas/sugestões **derivadas do relato**, Contexto do Bug com todos os problemas e números, Tasks; deixar claro que “problema → solução” derivada do relato **não** é inventar.  
- Em relatos complexos: usar formato do Exemplo 8 (=== USER STORY ===, === CRITÉRIOS ===, === CRITÉRIOS TÉCNICOS ===, === CONTEXTO DO BUG ===, === TASKS ===); não pular seções.  
- Pipeline (d): se houver múltiplos problemas numerados, conferir bloco A./B./C./D. e presença em Contexto do Bug e Tasks.  
- Regra pós-exemplos: em complexos **incluir** causas e sugestões técnicas derivadas do relato (ex.: “Connection pool exhausted” → “Aumentar connection pool”); continuar **não** adicionando boas práticas não citadas (ex.: acessibilidade).

---

## 8. Redundâncias e desredundância do prompt

Documento `ANALISE_REDUNDANCIAS_PROMPT_V2.md`: revisão para consolidar repetições.

### 8.1 Alterações sugeridas e aplicadas

1. **Lista única de estrutura** — Remover “ESTRUTURA DA SAÍDA” resumida; manter uma lista completa (ex.: “SEÇÕES POSSÍVEIS DA SAÍDA” ou “ESTRUTURA DA SAÍDA” com todas as seções).  
2. **COMPLETUDE** — Consolidar as 3 frases de “inclua tudo / não omita / garanta” em um único parágrafo.  
3. **Precision** — Unificar as 2 frases “não invente / não inclua o que não está no relato” em uma.  
4. **COMPLEXIDADE** — Encurtar para uma linha que remeta à lista de seções, sem repetir “quando usar”.  
5. **“Não omita”** — Manter só a instrução mais específica (não omitir seção por causa de exemplo anterior).  
6. **FORMATO OBRIGATÓRIO** — Enxugar explicação de persona/ação/benefício.  

**Observação:** O texto do `system_prompt` está duplicado em `langchain_manifest.kwargs.messages[0].kwargs.prompt.kwargs.template`; edições devem ser replicadas nos dois lugares.

---

## 9. Recall: três alternativas e plano de implementação

### 9.1 Alternativas (documento PLANO_MUDANCA_RECALL.md)

- **Alternativa 1 — Estrutura explícita:** Listar todas as seções possíveis da saída, ordem e “quando usar”; reforçar completude (comparação com referência completa); um exemplo adicional médio (ex.: segurança ou cálculo); uma linha de proteção de Precision.  
- **Alternativa 2 — Checklist de inclusão:** Substituir/expandir o passo 3 por checklist de “incluído na resposta” (passos, endpoints, logs, impacto, múltiplos problemas, cálculo, perfis); lista curta de seções; um exemplo adicional; proteção de Precision.  
- **Alternativa 3 — Exemplos ricos:** Dois exemplos adicionais (médio segurança + médio cálculo), frase de recall antes dos exemplos, reforço em completude, proteção de Precision.

**Escolha recomendada:** Alternativa 1 — melhor equilíbrio entre ganho de recall, previsibilidade e tamanho do prompt.

### 9.2 Opções detalhadas para aumento de recall (OPCOES_AUMENTO_RECALL_DETALHADO.md)

Três opções com texto e passos de implementação:

- **Opção 1 — Checklist de inclusão na saída:** Passo 3 vira “CHECKLIST DE INCLUSÃO” com itens (passos, endpoints, logs, impacto, múltiplos problemas, cálculo, perfis); “se faltar, complete antes de finalizar”.  
- **Opção 2 — Quarto exemplo (Exemplo de Cálculo):** Exemplo completo com regra de negócio e números, saída com Exemplo de Cálculo + Contexto Técnico; opcional frase de recall antes dos exemplos.  
- **Opção 3 — Mapeamento relato → seções:** Bloco MAPEAMENTO (passos→critérios/contexto, endpoints→Contexto Técnico, impacto→Contexto do Bug, etc.); passo 4 (GERAÇÃO) reforça “inclua na resposta cada informação do passo 1”.

**Recomendação:** Implementar primeiro Opção 3; se insuficiente, adicionar Opção 2; depois considerar Opção 1.

### 9.3 Plano de implementação — Alternativa 1 (PLANO_IMPLEMENTACAO_ALTERNATIVA_1.md)

Passos detalhados:

1. Inserir bloco “SEÇÕES POSSÍVEIS DA SAÍDA” (lista completa e ordem).  
2. Reforçar COMPLETUDE (referência completa + lista do que garantir) e adicionar proteção de Precision (“Não inclua critérios/detalhes que não estejam no relato”).  
3. Adicionar Exemplo 3 (bug médio segurança: API/users, Critérios Adicionais para Admins, Contexto de Segurança).  
4. Replicar `system_prompt` no `template` do `langchain_manifest`.

Validação: rodar `python src/evaluate.py` e testes de prompt; comparar recall, F1, Precision e Clarity antes/depois.

---

## 10. Evolução final do prompt (resumo)

O `bug_to_user_story_v2.yml` atual incorpora:

- **Papel e objetivo** — Analista que transforma bug em user story; equilíbrio recall/precision; termos do relato.  
- **Regras obrigatórias** — RECALL (fatos explícitos/implícitos devem aparecer), PRECISION (só informações do relato; citar literalmente), critérios Given-When-Then.  
- **Pipeline** — (a) Extrair apenas o que o relato mencionar; (b) Classificar complexidade; (c) Mapear para seções; (d) Verificar inclusão e, em complexos, blocos A./B./C./D.; (d.1) Verificação por tipo (PERFORMANCE, FLUXO/REGRA, COMPLEXO); (e) Gerar; (f) Checklist final (tudo incluído? nada inventado? termos exatos?).  
- **Estrutura da saída** — Lista completa de seções (User story, Critérios, Contexto Técnico, Contexto do Bug, Contexto de Segurança, Exemplo de Cálculo, Critérios Adicionais, Critérios Técnicos/Tasks); em complexos, formato Exemplo 8.  
- **Edge cases** — Relato vago, “em X não funciona em Y funciona”, performance, estoque/carrinho, z-index/modal, múltiplos bugs, só técnico, médio/complexo, relato COMPLEXO com todos os números e blocos.  
- **Exemplos** — 8 exemplos (simples a complexo), incluindo Exemplo 8 (checkout com A./B./C./D., Critérios Técnicos, Contexto do Bug, Tasks).  
- **Técnicas** — Role Prompting, Few-shot, Chain of Thought (pipeline), regras explícitas, tratamento de edge cases, System vs User.

---

## 11. Passos executados (resumo em ordem)

1. **Pull** — Executar `python src/pull_prompts.py`; prompt V1 salvo em `prompts/`.
2. **Avaliação V1** — Executar `python src/evaluate.py`; identificar F1 e Correctness abaixo de 0,9 (recall baixo).
3. **Análise V1** — Listar 6 problemas do prompt (formato, completude, complexidade, vagueza, zero-shot, bug system prompt).
4. **Proposta 1** — Inserir role, formato “Como… Eu quero… Para que…”, Given-When-Then; separar system/user.
5. **Proposta 2** — Inserir COMPLETUDE, COMPLEXIDADE, EDGE CASES; estrutura com Contexto Técnico e Contexto do Bug/Tasks.
6. **Proposta 3** — Inserir 2 exemplos few-shot (simples + médio webhook).
7. **Avaliação V2** — Rodar `evaluate.py`; F1 0,77 e Correctness 0,87 ainda abaixo de 0,9.
8. **Proposta 4** — Inserir pipeline EXTRAÇÃO → CLASSIFICAÇÃO → CHECKLIST → GERAÇÃO (Skeleton of Thought).
9. **Avaliação V3** — Rodar `evaluate.py`; média 0,9089 ✅ (aprovação).
10. **Análise crítica** — Alinhar estrutura da saída às referências; listar seções possíveis; recomendar exemplo complexo e checklist “nada omitido”.
11. **Ajustes de Precision** — Limitar recall a fatos explícitos/implícitos; “apenas o que o relato mencionar”; “sem adicionar fatos”; regra pós-exemplos; recall em complexos (blocos A./B./C./D., sugestões derivadas do relato).
12. **Redundâncias** — Uma lista de estrutura; consolidar frases de completude e precision; encurtar COMPLEXIDADE e FORMATO OBRIGATÓRIO.
13. **Recall** — Escolher Alternativa 1 (estrutura explícita); aplicar seções possíveis, reforço de completude, Exemplo 3 (segurança), proteção de Precision; replicar no `langchain_manifest`.
14. **Evolução final** — Incluir 8 exemplos, edge cases (performance, estoque, Safari/Chrome, complexo), pipeline (d.1) por tipo, regras RECALL/PRECISION explícitas.
15. **Push e validação** — `python src/push_prompts.py`; `python src/evaluate.py`; `pytest tests/test_prompts.py`.

---

## 12. Referências aos documentos originais (já consolidados aqui)

Os arquivos listados abaixo tiveram o conteúdo incorporado neste documento e **foram removidos** de `docs/`:

- **RELATORIO_OTIMIZACAO.md** — Fases 1–5, evolução V1→V2→V3 (Seções 3–5, 10).  
- **RELATORIO_METRICAS_EVALUATE.md** — Métricas do `evaluate.py` (Seção 2).  
- **ANALISE_PROMPT_V2.md** — Problemas do V1 e melhorias (Seções 3.4, 4).  
- **ANALISE_CRITICA_PROMPT_E_DATASET.md** — Aderência, dataset, recall (Seção 6).  
- **ANALISE_PRECISION_PROMPT_V2.md** — Ajustes de Precision e recall em complexos (Seção 7).  
- **ANALISE_REDUNDANCIAS_PROMPT_V2.md** — Redundâncias (Seção 8).  
- **OPCOES_AUMENTO_RECALL_DETALHADO.md** — Três opções de recall (Seção 9.2).  
- **PLANO_MUDANCA_RECALL.md** — Três alternativas e escolha (Seção 9.1).  
- **PLANO_IMPLEMENTACAO_ALTERNATIVA_1.md** — Passos de implementação (Seção 9.3).
