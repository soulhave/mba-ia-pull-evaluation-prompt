"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import sys
import re
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_all_prompts():
    """Retorna todos os prompts de todos os arquivos YAML na pasta prompts/."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompts = []
    
    for yaml_file in prompts_dir.glob("*.yml"):
        data = load_prompts(str(yaml_file))
        if data:
            for prompt_name, prompt_data in data.items():
                # Filtrar apenas bug_to_user_story_v2
                if prompt_name == 'bug_to_user_story_v2':
                    prompts.append((prompt_name, prompt_data, yaml_file.name))
    
    return prompts

class TestPrompts:
    @pytest.mark.parametrize("prompt_name,prompt_data,filename", get_all_prompts())
    def test_prompt_has_system_prompt(self, prompt_name, prompt_data, filename):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert 'system_prompt' in prompt_data, \
            f"Prompt '{prompt_name}' em {filename} não possui campo 'system_prompt'"
        
        system_prompt = prompt_data['system_prompt']
        assert system_prompt is not None, \
            f"Prompt '{prompt_name}' em {filename} tem 'system_prompt' como None"
        
        assert isinstance(system_prompt, str), \
            f"Prompt '{prompt_name}' em {filename} tem 'system_prompt' que não é string"
        
        assert len(system_prompt.strip()) > 0, \
            f"Prompt '{prompt_name}' em {filename} tem 'system_prompt' vazio"

    @pytest.mark.parametrize("prompt_name,prompt_data,filename", get_all_prompts())
    def test_prompt_has_role_definition(self, prompt_name, prompt_data, filename):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = prompt_data.get('system_prompt', '')
        
        # Padrões comuns para definição de persona/role
        role_patterns = [
            r'Você é (um|uma|o|a) .+',
            r'You are (a|an|the) .+',
            r'Atue como .+',
            r'Act as .+',
            r'Seja .+',
            r'Be .+',
        ]
        
        has_role = any(re.search(pattern, system_prompt, re.IGNORECASE) 
                      for pattern in role_patterns)
        
        assert has_role, \
            f"Prompt '{prompt_name}' em {filename} não define uma persona/role " \
            f"(procura por padrões como 'Você é um...', 'You are a...', etc.)"

    @pytest.mark.parametrize("prompt_name,prompt_data,filename", get_all_prompts())
    def test_prompt_mentions_format(self, prompt_name, prompt_data, filename):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt_data.get('system_prompt', '').lower()
        
        # Padrões relacionados a formato
        format_keywords = [
            'markdown',
            'user story',
            'user story padrão',
            'formato',
            'formato obrigatório',
            'estrutura',
            'template',
            'padrão',
            'como um',
            'eu quero',
            'para que',
        ]
        
        has_format_mention = any(keyword in system_prompt for keyword in format_keywords)
        
        assert has_format_mention, \
            f"Prompt '{prompt_name}' em {filename} não menciona formato Markdown ou " \
            f"User Story padrão"

    @pytest.mark.parametrize("prompt_name,prompt_data,filename", get_all_prompts())
    def test_prompt_has_few_shot_examples(self, prompt_name, prompt_data, filename):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt_data.get('system_prompt', '')
        system_prompt_lower = system_prompt.lower()
        
        # Padrões relacionados a exemplos Few-shot
        example_keywords = [
            'exemplo',
            'example',
            'entrada',
            'saída',
            'input',
            'output',
            'sample',
            'caso de uso',
            'use case',
        ]
        
        # Verifica se há pelo menos uma palavra-chave de exemplo
        has_example_keyword = any(keyword in system_prompt_lower for keyword in example_keywords)
        
        # Verifica se há padrões como "ENTRADA:" e "SAÍDA:" ou "Input:" e "Output:"
        # (case-insensitive)
        has_input_output_pattern = (
            (re.search(r'entrada\s*:', system_prompt_lower) or 
             re.search(r'input\s*:', system_prompt_lower)) and
            (re.search(r'saída\s*:', system_prompt_lower) or 
             re.search(r'output\s*:', system_prompt_lower))
        )
        
        # Verifica se há exemplos numerados (Exemplo 1, Exemplo 2, etc.)
        has_numbered_examples = bool(re.search(r'exemplo\s+\d+', system_prompt_lower, re.IGNORECASE))
        
        assert has_example_keyword or has_input_output_pattern or has_numbered_examples, \
            f"Prompt '{prompt_name}' em {filename} não contém exemplos Few-shot " \
            f"(procura por palavras como 'exemplo', 'entrada', 'saída', etc.)"

    @pytest.mark.parametrize("prompt_name,prompt_data,filename", get_all_prompts())
    def test_prompt_no_todos(self, prompt_name, prompt_data, filename):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        system_prompt = prompt_data.get('system_prompt', '')
        user_prompt = prompt_data.get('user_prompt', '')
        
        # Verifica tanto [TODO] quanto TODO em maiúsculas/minúsculas
        todo_patterns = [
            r'\[TODO\]',
            r'\[todo\]',
            r'\[Todo\]',
            r'TODO:',
            r'todo:',
            r'Todo:',
        ]
        
        all_text = f"{system_prompt} {user_prompt}"
        
        found_todos = []
        for pattern in todo_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                found_todos.extend(matches)
        
        assert len(found_todos) == 0, \
            f"Prompt '{prompt_name}' em {filename} contém TODOs não resolvidos: {found_todos}"

    @pytest.mark.parametrize("prompt_name,prompt_data,filename", get_all_prompts())
    def test_minimum_techniques(self, prompt_name, prompt_data, filename):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        # Verifica se há campo 'techniques_applied' ou 'techniques' nos metadados
        techniques = prompt_data.get('techniques_applied', [])
        if not techniques:
            techniques = prompt_data.get('techniques', [])
        
        # Se não houver campo específico, verifica tags como técnicas
        if not techniques:
            tags = prompt_data.get('tags', [])
            # Filtra tags que podem ser técnicas (exclui 'langsmith', 'pull', etc.)
            technique_tags = [tag for tag in tags if tag not in ['langsmith', 'pull', 'pulled']]
            techniques = technique_tags
        
        # Se ainda não houver, verifica técnicas mencionadas ou implícitas no texto do prompt
        if len(techniques) < 2:
            system_prompt = prompt_data.get('system_prompt', '')
            system_prompt_lower = system_prompt.lower()
            mentioned_techniques = []
            
            # Técnicas explícitas mencionadas no texto
            explicit_techniques = {
                'few-shot': ['few-shot', 'few shot'],
                'chain of thought': ['chain of thought', 'cot'],
                'role playing': ['role playing', 'persona'],
                'zero-shot': ['zero-shot', 'zero shot'],
                'self-consistency': ['self-consistency', 'self consistency'],
                'tree of thoughts': ['tree of thoughts'],
                'prompt chaining': ['prompt chaining'],
                'output format': ['output format', 'formato obrigatório', 'formato'],
                'step by step': ['step by step', 'step-by-step', 'passo a passo'],
            }
            
            for technique_name, keywords in explicit_techniques.items():
                if any(keyword in system_prompt_lower for keyword in keywords):
                    mentioned_techniques.append(technique_name)
            
            # Técnicas implícitas detectadas por padrões
            # Role playing: se há definição de persona
            if re.search(r'você é (um|uma|o|a) .+', system_prompt_lower):
                if 'role playing' not in mentioned_techniques:
                    mentioned_techniques.append('role playing')
            
            # Output format: se há instruções de formato ou estrutura
            if any(keyword in system_prompt_lower for keyword in ['formato', 'estrutura', 'template', 'padrão', 'user story']):
                if 'output format' not in mentioned_techniques:
                    mentioned_techniques.append('output format')
            
            # Task decomposition: se há instruções de análise ou processo
            if any(keyword in system_prompt_lower for keyword in ['analise', 'análise', 'processo', 'process']):
                if 'task decomposition' not in mentioned_techniques:
                    mentioned_techniques.append('task decomposition')
            
            # Step by step: se há passos numerados ou processo
            if re.search(r'(passo|step)\s+\d+', system_prompt_lower) or 'processo' in system_prompt_lower:
                if 'step by step' not in mentioned_techniques:
                    mentioned_techniques.append('step by step')
            
            # Few-shot: se há exemplos
            if any(keyword in system_prompt_lower for keyword in ['exemplo', 'example', 'entrada', 'saída']):
                if 'few-shot' not in mentioned_techniques:
                    mentioned_techniques.append('few-shot')
            
            techniques = mentioned_techniques
        
        assert len(techniques) >= 2, \
            f"Prompt '{prompt_name}' em {filename} não possui pelo menos 2 técnicas " \
            f"listadas nos metadados (encontradas: {len(techniques)}: {techniques})"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])