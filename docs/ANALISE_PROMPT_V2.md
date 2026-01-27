# Análise do resultado e do prompt `bug_to_user_story_v2`

## 1. Resultados da avaliação

| Métrica | Valor | Status | Interpretação |
|--------|-------|--------|----------------|
| **Helpfulness** | 0.93 | ✓ | Boa utilidade e clareza geral |
| **Correctness** | 0.81 | ✗ | Abaixo do limite 0.9 — alinhamento com referência insuficiente |
| **F1-Score** | 0.69 | ✗ | Principal gargalo — muitas informações da referência omitidas |
| **Clarity** | 0.94 | ✓ | Respostas organizadas e legíveis |
| **Precision** | 0.92 | ✓ | Poucas alucinações; modelo não inventa em excesso |

### Como as métricas são calculadas (evaluate.py)

- **Correctness** = `(F1-Score + Precision) / 2` → hoje 0.81.
- **F1-Score** = `2 × (Precision × Recall) / (Precision + Recall)` (métrica customizada em `metrics.py`).
- **Precision** (custom): corretude, foco e ausência de alucinações.
- **Recall** (implícito no F1): quanto da resposta esperada (referência) está presente na resposta gerada.

### Diagnóstico

- **Precision 0.92** alto → o modelo tende a **não inventar** informação.
- **F1 0.69** baixo com Precision alta → **Recall é o gargalo**: o modelo **omite** informação importante que está na referência.

Ou seja: as respostas são relativamente corretas e claras, mas **incompletas** em relação ao ground truth. Isso puxa o F1 para baixo e, por consequência, o **Correctness**.

### Variação por exemplo (terminal)

```
[5/10] F1: 0.17  ← Safari/imagens (simples) — grande divergência
[10/10] F1: 0.40 ← Android/notificações (médio) — omissão de contexto técnico
[4/10] F1: 0.56, [8/10] F1: 0.67  ← casos médios
[1,2,3,6,7,9] F1: 0.74–0.94      ← melhores
```

Conclusão: o prompt funciona melhor em bugs **simples** e pior quando há **mais detalhes** (steps, logs, impacto, contexto técnico, múltiplos problemas). A referência exige **preservar e estruturar** tudo isso; o modelo atual simplifica demais.

---

## 2. Análise do prompt atual (`bug_to_user_story_v2`)

### Conteúdo atual (system)

```
Você é um assistente que ajuda a transformar relatos de bugs de usuários em tarefas para desenvolvedores.

Analise o relato de bug abaixo e crie uma user story a partir dele.

Relato de Bug:
---
{bug_report}
---
User Story gerada:
```

### Problemas identificados

1. **Sem definição de formato**
   - O dataset espera user stories no padrão: **“Como um [persona], eu quero [ação], para que [benefício]”** + **Critérios de Aceitação** (Given-When-Then).
   - O prompt não menciona isso. O modelo escolhe formato livre, gerando respostas **estruturalmente incorretas** em relação à referência → prejudica Correctness e F1.

2. **Sem orientação de completude**
   - Não há instrução para **incluir todas as informações relevantes** do bug (passos, logs, ambiente, endpoints, impacto, severidade).
   - O modelo tende a resumir e **omitir** trechos que a referência inclui → **Recall baixo** → F1 baixo.

3. **Sem tratamento de complexidade**
   - O dataset tem bugs **simples**, **médios** e **complexos**. As referências para médios/complexos incluem:
     - **Contexto Técnico** (endpoints, logs, stack traces)
     - **Critérios técnicos** ou **Tasks técnicas**
     - Seções como “Contexto do Bug”, “Impacto”, etc.
   - O prompt trata todos igual → em bugs complexos o modelo não produz essas seções → nova fonte de omissão e **Recall** baixo.

4. **“Tarefas para desenvolvedores” é vago**
   - O esperado são **user stories completas** (descrição + critérios de aceitação + contexto quando fizer sentido), não apenas “tarefas” soltas. A vagueza pode levar a saídas mais superficiais.

5. **Sem exemplos (zero-shot)**
   - Nada ilustra o formato nem o nível de detalhe esperado. Aumenta variabilidade e desalinhamento com as referências.

6. **User message redundante**
   - O `bug_report` aparece no system (entre `---`) e de novo no user. Não é necessariamente ruim, mas o prompt não deixa explícito que a **entrada principal** é o relato e que a saída deve **cobri-lo por completo**.

---

## 3. O que melhorar para Correctness e F1-Score

Objetivo: **aumentar Recall** (incluir tudo que a referência inclui) e **alinhar estrutura e conteúdo** (Correctness).

### 3.1 Formato explícito

- Exigir **user story** no padrão: “Como um [persona], eu quero [ação], para que [benefício].”
- Exigir seção **“Critérios de Aceitação”** em formato **Given-When-Then** (ou equivalente), com critérios **testáveis e específicos**.

### 3.2 Completude e Recall

- Instruir: **“Inclua todas as informações relevantes do relato: passos para reproduzir, logs, ambiente, endpoints, impacto, severidade. Não omita detalhes importantes.”**
- Reforçar que a user story deve **cobrir integralmente** o problema descrito.

### 3.3 Complexidade (médio/complexo)

- Se o bug tiver **steps, logs, múltiplos problemas ou impacto descrito**: incluir seção **“Contexto Técnico”** (e, quando fizer sentido, **“Contexto do Bug”** ou **“Tasks técnicas”**).
- Deixar claro que bugs **simples** podem ter apenas user story + critérios; **médios/complexos** devem ganhar essas seções adicionais.

### 3.4 Estrutura da saída

- Definir ordem sugerida:
  1. User story (Como... Eu quero... Para que...).
  2. Critérios de Aceitação.
  3. (Se aplicável) Contexto Técnico / Contexto do Bug.
  4. (Se aplicável) Tasks técnicas ou critérios técnicos.

### 3.5 Few-shot (opcional mas recomendado)

- Incluir **1 exemplo simples** e **1 médio** (bug → user story completa) para fixar formato, nível de detalhe e uso de contexto técnico.

### 3.6 Anti-alucinação (manter Precision)

- Manter orientação implícita: **não inventar** dados que não estão no relato. Isso já funciona (Precision 0.92); as mudanças devem **preservar** isso enquanto aumentam Recall.

---

## 4. Resumo das melhorias sugeridas

| Melhoria | Objetivo | Impacto esperado |
|----------|----------|-------------------|
| Formato explícito (Como... Eu quero... Para que... + Critérios Given-When-Then) | Alinhar estrutura à referência | ↑ Correctness, ↑ F1 |
| Instrução de completude (“não omitir”) | Aumentar Recall | ↑ F1 (principalmente) |
| Regras para bugs médios/complexos (Contexto Técnico, etc.) | Cobrir referências complexas | ↑ F1 em exemplos 4, 5, 8, 10 |
| Estrutura de saída definida | Consistência e comparação com referência | ↑ Correctness |
| 1–2 exemplos few-shot | Reduzir ambiguidade | ↑ Correctness, ↑ F1 |

Prioridade imediata: **formato explícito** + **completude** + **tratamento de complexidade**. Few-shot pode ser adicionado em uma segunda iteração.

---

## 5. Melhorias implementadas em `bug_to_user_story_v2.yml`

As alterações acima foram aplicadas ao prompt em `prompts/bug_to_user_story_v2.yml`:

- **Formato explícito**: regras 1 e 2 (user story + critérios Given-When-Then).
- **Completude**: regra 3 (incluir tudo, não omitir, não inventar).
- **Complexidade**: regra 4 (simples vs. médio/complexo, contexto técnico e tasks).
- **Estrutura da saída**: ordem fixa (user story → critérios → contexto/tasks).

**Próximos passos:**

1. Fazer push do prompt atualizado: `python src/push_prompts.py`
2. Rodar a avaliação: `python src/evaluate.py`
3. Conferir se **Correctness** e **F1-Score** subiram (meta: ≥ 0,9). Se não, considerar adicionar 1–2 exemplos few-shot.

---

## 6. Referências no dataset

- **Simples**: user story + critérios de aceitação (3–5 itens).
- **Médio**: idem + **Contexto Técnico** (endpoint, logs, sugestões).
- **Complexo**: user story + critérios + **Contexto Técnico** + **Contexto do Bug** + **Tasks técnicas** e, em alguns casos, **Critérios técnicos** ou **Critérios adicionais**.

O prompt precisa **orientar** o modelo a produzir esse tipo de saída quando o relato tiver a complexidade correspondente.
