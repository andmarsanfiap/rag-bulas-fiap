"""
testar_busca.py - Testa se a busca vetorial está funcionando.

Faz perguntas de exemplo em linguagem natural e retorna
os chunks mais relevantes do índice.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

from src.utils.config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    EMBEDDING_DEPLOYMENT,
    AZURE_SEARCH_ENDPOINT,
    AZURE_SEARCH_API_KEY,
    AZURE_SEARCH_INDEX_NAME,
)


def gerar_embedding_pergunta(pergunta: str) -> list:
    """Gera embedding pra uma pergunta."""
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    response = client.embeddings.create(
        input=pergunta,
        model=EMBEDDING_DEPLOYMENT,
    )
    return response.data[0].embedding


def buscar(pergunta: str, top_k: int = 3):
    """
    Busca os top-k chunks mais relevantes pra uma pergunta.
    """
    print(f"\n{'='*60}")
    print(f"❓ PERGUNTA: {pergunta}")
    print(f"{'='*60}")

    # 1. Gera embedding da pergunta
    vetor_pergunta = gerar_embedding_pergunta(pergunta)

    # 2. Busca vetorial no AI Search
    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY),
    )

    vector_query = VectorizedQuery(
        vector=vetor_pergunta,
        k_nearest_neighbors=top_k,
        fields="vetor",
    )

    resultados = search_client.search(
        search_text=None,  # busca puramente vetorial
        vector_queries=[vector_query],
        select=["id", "texto", "fonte", "chunk_index"],
        top=top_k,
    )

    # 3. Mostra resultados
    for i, r in enumerate(resultados, start=1):
        score = r.get("@search.score", 0)
        print(f"\n📄 Resultado {i} (score: {score:.4f})")
        print(f"   Fonte: {r['fonte']} (chunk {r['chunk_index']})")
        texto_preview = r["texto"][:300].replace("\n", " ")
        print(f"   Trecho: {texto_preview}...")


if __name__ == "__main__":
    # Perguntas de teste cobrindo diferentes bulas
    perguntas_teste = [
        "Posso tomar dipirona se estou amamentando?",
        "Qual a dose máxima de paracetamol por dia?",
        "Como tomar amoxicilina para infecção de garganta?",
        "Quais são os efeitos colaterais da metformina?",
        "Loratadina dá sono?",
    ]

    for pergunta in perguntas_teste:
        buscar(pergunta, top_k=2)

    print(f"\n{'='*60}")
    print("🎉 TESTE DE BUSCA VETORIAL CONCLUÍDO!")
    print(f"{'='*60}")