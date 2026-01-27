"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
import json
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def _local_prompt_name(prompt_identifier: str) -> str:
    """Converte 'owner/repo' -> 'repo' para nome local."""
    if "/" in prompt_identifier:
        return prompt_identifier.split("/")[-1]
    return prompt_identifier


def _extract_chat_prompt_parts(prompt_obj) -> tuple[str, str]:
    """
    Extrai (system_prompt, user_prompt) de um ChatPromptTemplate quando possível.

    Se não for possível, retorna strings vazias.
    """
    try:
        # Import local para não quebrar se versões mudarem
        from langchain_core.messages import SystemMessage, HumanMessage
        from langchain_core.prompts import ChatPromptTemplate

        if not isinstance(prompt_obj, ChatPromptTemplate):
            return ("", "")

        system_parts: list[str] = []
        user_parts: list[str] = []

        for msg in prompt_obj.messages:
            try:
                # Cada item pode ser (message_template, ) ou já uma mensagem.
                role = getattr(msg, "type", None) or getattr(msg, "__class__", type("X", (), {})).__name__

                template = ""
                if hasattr(msg, "prompt") and hasattr(msg.prompt, "template"):
                    template = msg.prompt.template
                elif hasattr(msg, "template"):
                    template = msg.template  # fallback
                elif hasattr(msg, "content"):
                    template = msg.content

                template = (template or "").strip()
                if not template:
                    continue

                if role in ("system", "SystemMessagePromptTemplate") or isinstance(msg, SystemMessage):
                    system_parts.append(template)
                elif role in ("human", "HumanMessagePromptTemplate") or isinstance(msg, HumanMessage):
                    user_parts.append(template)
                else:
                    # Outros papéis (ai/tool/placeholder) entram no user_prompt por compatibilidade
                    user_parts.append(template)
            except Exception:
                continue

        return ("\n\n".join(system_parts).strip(), "\n\n".join(user_parts).strip())
    except Exception:
        return ("", "")


def _build_yaml_entry(
    prompt_identifier: str,
    *,
    prompt_obj,
    prompt_commit_manifest: dict | None = None,
) -> dict:
    """
    Constrói o dicionário no formato YAML esperado pelo projeto.

    - Mantém campos principais: description, system_prompt, user_prompt
    - Inclui metadados mínimos
    - Inclui `langchain_manifest` para preservar o conteúdo completo quando necessário
    """
    system_prompt, user_prompt = _extract_chat_prompt_parts(prompt_obj)

    description = f"Prompt puxado do LangSmith Hub: {prompt_identifier}"

    entry: dict = {
        "description": description,
        "system_prompt": system_prompt or "",
        "user_prompt": user_prompt or "",
        "version": "pulled",
        "created_at": date.today().isoformat(),
        "tags": ["langsmith", "pull"],
    }

    # Preserva o conteúdo completo, caso extração não seja perfeita
    if prompt_commit_manifest is not None:
        entry["langchain_manifest"] = prompt_commit_manifest

    return entry


def pull_prompts_from_langsmith():
    required_vars = ["LANGSMITH_API_KEY"]
    if not check_env_vars(required_vars):
        return 1

    client = Client()

    # Prompts a puxar (pode expandir depois)
    prompts_to_pull = [
        "leonanluppi/bug_to_user_story_v1",
    ]

    prompts_dir = Path("prompts")
    prompts_dir.mkdir(parents=True, exist_ok=True)

    for prompt_identifier in prompts_to_pull:
        local_name = _local_prompt_name(prompt_identifier)
        output_path = prompts_dir / f"{local_name}.yml"

        print(f"🔽 Pull: {prompt_identifier}")

        # 1) Pull do prompt como objeto LangChain (pedido do enunciado)
        prompt_obj = client.pull_prompt(prompt_identifier)

        # 2) Pull do commit para capturar o manifest completo
        prompt_commit = client.pull_prompt_commit(prompt_identifier)
        manifest = prompt_commit.manifest if hasattr(prompt_commit, "manifest") else None

        entry = _build_yaml_entry(
            prompt_identifier,
            prompt_obj=prompt_obj,
            prompt_commit_manifest=manifest,
        )

        # Formato local: { <nome_do_prompt>: { ... } }
        payload = {local_name: entry}

        if save_yaml(payload, str(output_path)):
            print(f"   ✓ Salvo em: {output_path}")
        else:
            print(f"   ❌ Falha ao salvar em: {output_path}")
            return 1

    return 0


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH")

    # Validação extra: evita rodar sem .env/.env.example
    if not os.getenv("LANGSMITH_API_KEY"):
        print("❌ LANGSMITH_API_KEY não configurada no .env")
        print("Configure a chave e tente novamente.\n")
        return 1

    try:
        return pull_prompts_from_langsmith()
    except Exception as e:
        print(f"\n❌ Erro inesperado durante pull: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
