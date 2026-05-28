"""
config.py - Configurações centralizadas do projeto.

Lê variáveis de ambiente do arquivo .env e expõe constantes
que os outros scripts vão usar.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega o arquivo .env da raiz do projeto
# Path(__file__) = caminho deste arquivo (config.py)
# .parent.parent.parent = sobe 3 níveis (utils → src → raiz)
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

# ===== Azure OpenAI / Foundry =====
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT")
CHAT_DEPLOYMENT = os.getenv("CHAT_DEPLOYMENT")

# ===== Azure AI Search =====
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

# ===== Azure Storage =====
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")

# ===== Caminhos do projeto =====
BULAS_DIR = ROOT_DIR / "documentos" / "bulas"

# ===== Configurações de chunking =====
# Tamanho do chunk em caracteres (não palavras)
# 1500 chars ≈ 300 palavras ≈ 1 parágrafo grande
CHUNK_SIZE = 1500

# Sobreposição entre chunks consecutivos (em caracteres)
# Ajuda a manter contexto na borda dos chunks
CHUNK_OVERLAP = 200


def validar_config():
    """Verifica se todas as variáveis essenciais foram carregadas."""
    obrigatorias = {
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
        "EMBEDDING_DEPLOYMENT": EMBEDDING_DEPLOYMENT,
        "CHAT_DEPLOYMENT": CHAT_DEPLOYMENT,
        "AZURE_SEARCH_ENDPOINT": AZURE_SEARCH_ENDPOINT,
        "AZURE_SEARCH_API_KEY": AZURE_SEARCH_API_KEY,
    }

    faltando = [nome for nome, valor in obrigatorias.items() if not valor]
    if faltando:
        raise ValueError(
            f"Variáveis de ambiente faltando no .env: {', '.join(faltando)}"
        )
    print("✅ Configurações carregadas com sucesso!")


if __name__ == "__main__":
    # Se rodar este arquivo direto, faz a validação
    validar_config()
    print(f"   ROOT_DIR: {ROOT_DIR}")
    print(f"   BULAS_DIR: {BULAS_DIR}")
    print(f"   Embedding deployment: {EMBEDDING_DEPLOYMENT}")
    print(f"   Chat deployment: {CHAT_DEPLOYMENT}")
    print(f"   Search index: {AZURE_SEARCH_INDEX_NAME}")