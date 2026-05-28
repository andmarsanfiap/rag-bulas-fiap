"""
criar_indice.py - Cria o índice vetorial no Azure AI Search.

Define a estrutura (schema) do índice:
- Quais campos cada documento vai ter
- Qual campo é vetorial (pra busca semântica)
- Qual algoritmo de busca usar (HNSW)

Rode esse script UMA VEZ pra criar o índice.
Se já existir, ele deleta e recria.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.core.credentials import AzureKeyCredential

from src.utils.config import (
    AZURE_SEARCH_ENDPOINT,
    AZURE_SEARCH_API_KEY,
    AZURE_SEARCH_INDEX_NAME,
)


# Dimensão do vetor do text-embedding-3-small (fixo do modelo)
EMBEDDING_DIMENSION = 1536


def criar_indice():
    """Cria (ou recria) o índice vetorial no Azure AI Search."""
    
    # Cliente que gerencia índices
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY),
    )

    # ===== Se o índice já existe, deleta antes de recriar =====
    indices_existentes = list(index_client.list_index_names())
    if AZURE_SEARCH_INDEX_NAME in indices_existentes:
        print(f"⚠️  Índice '{AZURE_SEARCH_INDEX_NAME}' já existe. Deletando...")
        index_client.delete_index(AZURE_SEARCH_INDEX_NAME)
        print(f"   ✅ Índice deletado")

    # ===== Define os campos do índice =====
    campos = [
        # ID único de cada chunk (chave primária)
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        # Texto do chunk (pesquisável por busca textual também)
        SearchableField(
            name="texto",
            type=SearchFieldDataType.String,
            analyzer_name="pt-br.microsoft",  # Analisador em português
        ),
        # Nome do arquivo de origem (filtrável)
        SimpleField(
            name="fonte",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        # Índice do chunk dentro do documento (pra ordenação)
        SimpleField(
            name="chunk_index",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        # Total de chunks no documento (contexto)
        SimpleField(
            name="total_chunks_no_doc",
            type=SearchFieldDataType.Int32,
            filterable=True,
        ),
        # Campo VETORIAL - aqui está a mágica do RAG
        SearchField(
            name="vetor",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSION,
            vector_search_profile_name="perfil-hnsw",
        ),
    ]

    # ===== Configuração da busca vetorial =====
    # HNSW = Hierarchical Navigable Small World
    # É o algoritmo padrão e mais eficiente pra busca aproximada de vizinhos
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="config-hnsw",
            ),
        ],
        profiles=[
            VectorSearchProfile(
                name="perfil-hnsw",
                algorithm_configuration_name="config-hnsw",
            ),
        ],
    )

    # ===== Monta e cria o índice =====
    indice = SearchIndex(
        name=AZURE_SEARCH_INDEX_NAME,
        fields=campos,
        vector_search=vector_search,
    )

    print(f"\n🔨 Criando índice '{AZURE_SEARCH_INDEX_NAME}'...")
    resultado = index_client.create_index(indice)
    print(f"✅ Índice criado com sucesso!")
    print(f"   Nome: {resultado.name}")
    print(f"   Total de campos: {len(resultado.fields)}")
    print(f"   Campo vetorial: 'vetor' com {EMBEDDING_DIMENSION} dimensões")


if __name__ == "__main__":
    criar_indice()