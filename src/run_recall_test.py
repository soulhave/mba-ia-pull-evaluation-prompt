"""
Teste de recall: roda o prompt local (YAML) contra o dataset JSONL e mede Recall, F1 e Precision.

Uso (na raiz do projeto, com venv ativado e dependências instaladas):
  python src/run_recall_test.py

Configure o .env: LLM_PROVIDER=openai ou google; OPENAI_API_KEY ou GOOGLE_API_KEY.
Não depende do LangSmith: carrega o prompt de prompts/bug_to_user_story_v2.yml
e o dataset de datasets/bug_to_user_story.jsonl.
"""

import argparse
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# garantir que src está no path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

from utils import load_yaml, check_env_vars, get_llm
from metrics import evaluate_f1_score
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
)


def load_dataset_from_jsonl(jsonl_path: str) -> List[Dict[str, Any]]:
    examples = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def build_prompt_from_yaml(prompt_data: dict) -> ChatPromptTemplate:
    system_prompt_text = (prompt_data.get("system_prompt") or "").strip()
    user_prompt_text = (prompt_data.get("user_prompt") or "").strip() or "{bug_report}"
    system_template = PromptTemplate.from_template(system_prompt_text)
    human_template = PromptTemplate.from_template(user_prompt_text)
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate(prompt=system_template),
        HumanMessagePromptTemplate(prompt=human_template),
    ])


def main():
    parser = argparse.ArgumentParser(description="Teste de recall: prompt local vs dataset JSONL")
    parser.add_argument("--limit", "-n", type=int, default=0, help="Máximo de exemplos a rodar (0 = todos)")
    args = parser.parse_args()

    print("=" * 60)
    print("TESTE DE RECALL – Prompt local vs dataset JSONL")
    print("=" * 60)

    # Config
    prompt_path = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v2.yml"
    jsonl_path = Path(__file__).resolve().parent.parent / "datasets" / "bug_to_user_story.jsonl"

    if not prompt_path.exists():
        print(f"❌ Prompt não encontrado: {prompt_path}")
        return 1
    if not jsonl_path.exists():
        print(f"❌ Dataset não encontrado: {jsonl_path}")
        return 1

    # LLM (mesmo que evaluate)
    provider = os.getenv("LLM_PROVIDER", "openai")
    required = ["LLM_PROVIDER"]
    if provider == "openai":
        required.append("OPENAI_API_KEY")
    elif provider in ("google", "gemini"):
        required.append("GOOGLE_API_KEY")
    if not check_env_vars(required):
        return 1

    llm = get_llm(temperature=0)
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    print(f"✓ LLM: {provider} / {model}")

    # Carregar prompt do YAML
    data = load_yaml(str(prompt_path))
    if not data or "bug_to_user_story_v2" not in data:
        print("❌ YAML inválido ou chave bug_to_user_story_v2 não encontrada")
        return 1
    prompt_template = build_prompt_from_yaml(data["bug_to_user_story_v2"])
    print(f"\n✓ Prompt carregado: {prompt_path.name}")

    # Carregar dataset
    examples = load_dataset_from_jsonl(str(jsonl_path))
    if args.limit and args.limit > 0:
        examples = examples[: args.limit]
        print(f"✓ Dataset (primeiros {len(examples)}): {jsonl_path.name}\n")
    else:
        print(f"✓ Dataset carregado: {len(examples)} exemplos de {jsonl_path.name}\n")

    chain = prompt_template | llm

    recalls: List[float] = []
    f1_scores: List[float] = []
    precision_scores: List[float] = []

    for i, ex in enumerate(examples, 1):
        inputs = ex.get("inputs", {})
        outputs = ex.get("outputs", {})
        bug_report = inputs.get("bug_report", "")
        reference = outputs.get("reference", "")
        metadata = ex.get("metadata", {})
        complexity = metadata.get("complexity", "?")

        if not bug_report or not reference:
            print(f"   [{i}] Ignorado (entrada/saída vazia)")
            continue

        print(f"   [{i}/{len(examples)}] Rodando (complexity={complexity})...", end=" ", flush=True)
        try:
            response = chain.invoke({"bug_report": bug_report})
            answer = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            print(f"Erro: {e}")
            continue

        if not answer:
            print("Resposta vazia")
            continue

        result = evaluate_f1_score(bug_report, answer, reference)
        rec = result["recall"]
        f1 = result["score"]
        prec = result["precision"]
        recalls.append(rec)
        f1_scores.append(f1)
        precision_scores.append(prec)
        print(f"Recall: {rec:.2f}  F1: {f1:.2f}  Precision: {prec:.2f}")

    if not recalls:
        print("\n❌ Nenhum exemplo avaliado com sucesso.")
        return 1

    avg_recall = sum(recalls) / len(recalls)
    avg_f1 = sum(f1_scores) / len(f1_scores)
    avg_precision = sum(precision_scores) / len(precision_scores)

    print("\n" + "-" * 60)
    print("RESUMO – Recall (e métricas relacionadas)")
    print("-" * 60)
    print(f"  Recall médio:    {avg_recall:.4f}")
    print(f"  F1 médio:        {avg_f1:.4f}")
    print(f"  Precision média: {avg_precision:.4f}")
    print(f"  Exemplos:        {len(recalls)}/{len(examples)}")
    avg_three = (avg_recall + avg_f1 + avg_precision) / 3
    # F1 já equilibra recall e precision; usar F1 como critério principal
    f1_ok = avg_f1 >= 0.9
    avg_ok = avg_three >= 0.9
    print(f"  Média (R+F1+P)/3: {avg_three:.4f}  {'✓ Meta ≥0.9' if avg_ok else '✗ Meta ≥0.9'}")
    print(f"  F1 médio (equilibrado): {avg_f1:.4f}  {'✓ F1 ≥0.9' if f1_ok else '✗ F1 ≥0.9'}")
    print("-" * 60)
    print(f"\n  Recall está {'bom' if avg_recall >= 0.85 else 'abaixo do desejado (alvo comum ≥ 0.85)'}.\n")

    # Aprova se F1 ≥ 0.9 (equilibrado) OU média das 3 ≥ 0.9
    return 0 if (f1_ok or avg_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
