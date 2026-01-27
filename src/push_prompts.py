"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
)
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).
    
    IMPORTANTE: Esta função apenas VALIDA, não altera o prompt_data.

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    # Campos obrigatórios
    required_fields = ["description", "system_prompt"]
    for field in required_fields:
        if field not in prompt_data:
            errors.append(f"Campo obrigatório faltando: {field}")

    # Validação de system_prompt (apenas leitura, sem alterar)
    system_prompt = prompt_data.get("system_prompt", "")
    if isinstance(system_prompt, str):
        system_prompt = system_prompt.strip()
    if not system_prompt:
        errors.append("system_prompt está vazio ou não definido")

    # Validação de user_prompt (opcional, mas recomendado) - apenas leitura
    user_prompt = prompt_data.get("user_prompt", "")
    if isinstance(user_prompt, str):
        user_prompt = user_prompt.strip()
    if not user_prompt and not system_prompt:
        errors.append("É necessário ter system_prompt ou user_prompt")

    # Verifica se há TODOs no prompt (apenas leitura)
    if isinstance(system_prompt, str) and ("TODO" in system_prompt.upper() or "[TODO]" in system_prompt):
        errors.append("system_prompt ainda contém TODOs - complete o prompt antes de fazer push")

    return (len(errors) == 0, errors)


def _build_chat_prompt_template(prompt_data: dict) -> ChatPromptTemplate:
    """
    Constrói um ChatPromptTemplate a partir dos dados do prompt.
    
    IMPORTANTE: Esta função apenas LÊ do prompt_data, não altera nada.
    Os valores são copiados para criar o template.

    Args:
        prompt_data: Dados do prompt com system_prompt e user_prompt

    Returns:
        ChatPromptTemplate configurado
    """
    # Lê os valores originais (sem alterar o prompt_data)
    system_prompt_text = prompt_data.get("system_prompt", "")
    user_prompt_text = prompt_data.get("user_prompt", "")

    # Normaliza strings (apenas para construção do template, não altera o original)
    if isinstance(system_prompt_text, str):
        system_prompt_text = system_prompt_text.strip()
    if isinstance(user_prompt_text, str):
        user_prompt_text = user_prompt_text.strip()

    # Se não tiver user_prompt, usa um padrão mínimo
    if not user_prompt_text:
        user_prompt_text = "{bug_report}"

    # Cria os templates
    system_template = PromptTemplate.from_template(system_prompt_text)
    human_template = PromptTemplate.from_template(user_prompt_text)

    # Constrói o ChatPromptTemplate
    messages = [
        SystemMessagePromptTemplate(prompt=system_template),
        HumanMessagePromptTemplate(prompt=human_template),
    ]

    return ChatPromptTemplate.from_messages(messages)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt (ex: "bug_to_user_story_v2")
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        # Obtém o username do LangSmith Hub
        username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
        if not username:
            print("❌ USERNAME_LANGSMITH_HUB não configurado no .env")
            print("   Configure a variável USERNAME_LANGSMITH_HUB com seu username do LangSmith Hub")
            return False

        # Constrói o nome completo do repositório: username/prompt_name
        repo_full_name = f"{username}/{prompt_name}"

        # Constrói o ChatPromptTemplate
        prompt_template = _build_chat_prompt_template(prompt_data)

        # Extrai metadados
        description = prompt_data.get("description", f"Prompt otimizado: {prompt_name}")
        tags = prompt_data.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        # Adiciona tags padrão se não houver
        if "optimized" not in [t.lower() for t in tags]:
            tags.append("optimized")
        if "bug-to-user-story" not in [t.lower() for t in tags]:
            tags.append("bug-to-user-story")

        print(f"   📤 Fazendo push para: {repo_full_name}")
        print(f"   📝 Descrição: {description[:60]}...")
        print(f"   🏷️  Tags: {', '.join(tags[:5])}")

        # Faz push para o LangSmith Hub (público)
        commit_hash = hub.push(
            repo_full_name=repo_full_name,
            object=prompt_template,
            new_repo_is_public=True,
            new_repo_description=description,
            tags=tags,
        )

        print(f"   ✅ Push realizado com sucesso!")
        print(f"   🔗 Commit hash: {commit_hash}")
        print(f"   🌐 Acesse em: https://smith.langchain.com/prompts/{repo_full_name}")

        return True

    except Exception as e:
        print(f"   ❌ Erro ao fazer push: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description="Faz push de prompts otimizados para o LangSmith Hub"
    )
    parser.add_argument(
        "prompt_file",
        nargs="?",
        default="prompts/bug_to_user_story_v2.yml",
        help="Caminho do arquivo YAML do prompt (default: prompts/bug_to_user_story_v2.yml)",
    )
    args = parser.parse_args()

    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH HUB")

    # Valida variáveis de ambiente
    required_vars = ["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]
    if not check_env_vars(required_vars):
        return 1

    # Caminho do arquivo de prompt otimizado
    prompt_file = Path(args.prompt_file)

    if not prompt_file.exists():
        print(f"❌ Arquivo não encontrado: {prompt_file}")
        print("\nCertifique-se de que o arquivo existe antes de fazer push.")
        print("Você pode criar o arquivo editando prompts/bug_to_user_story_v1.yml")
        print("e salvando como prompts/bug_to_user_story_v2.yml")
        return 1

    # Carrega o arquivo YAML
    yaml_data = load_yaml(str(prompt_file))
    if not yaml_data:
        print(f"❌ Erro ao carregar arquivo: {prompt_file}")
        return 1

    # Extrai o primeiro prompt do YAML (formato: {nome: {dados}})
    prompt_entries = list(yaml_data.keys())
    if not prompt_entries:
        print(f"❌ Nenhum prompt encontrado no arquivo: {prompt_file}")
        return 1

    # Usa o primeiro prompt encontrado para os dados
    prompt_data = yaml_data[prompt_entries[0]]
    
    # Usa o nome do arquivo (sem extensão) como nome do prompt para o push
    # Isso garante que bug_to_user_story_v2.yml -> bug_to_user_story_v2
    prompt_name = prompt_file.stem  # Remove a extensão .yml

    print(f"📄 Prompt encontrado no arquivo: {prompt_entries[0]}")
    print(f"📁 Arquivo: {prompt_file}")
    print(f"🚀 Nome do prompt para push: {prompt_name}\n")

    # Valida o prompt
    print("🔍 Validando prompt...")
    is_valid, errors = validate_prompt(prompt_data)

    if not is_valid:
        print("❌ Validação falhou. Erros encontrados:")
        for error in errors:
            print(f"   - {error}")
        print("\nCorrija os erros antes de fazer push.")
        return 1

    print("✅ Validação passou!\n")

    # Faz push para o LangSmith
    success = push_prompt_to_langsmith(prompt_name, prompt_data)

    if success:
        print("\n" + "=" * 50)
        print("✅ PUSH CONCLUÍDO COM SUCESSO!")
        print("=" * 50)
        print("\nPróximos passos:")
        print("1. Verifique o prompt no dashboard do LangSmith")
        print("2. Execute a avaliação: python src/evaluate.py")
        return 0
    else:
        print("\n" + "=" * 50)
        print("❌ FALHA NO PUSH")
        print("=" * 50)
        return 1


if __name__ == "__main__":
    sys.exit(main())
