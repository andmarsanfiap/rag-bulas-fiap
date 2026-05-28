"""
indexar.py - Pipeline completo de indexação.

Processa todos os PDFs, gera embeddings via Azure OpenAI Foundry
e envia tudo pro Azure AI Search.

Este é o script principal de ingestão.
"""

import sys
from pathlib import Path
from typing import List, Dict
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openai import AzureOpenAI
from azure.search.documents import SearchClient
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
from src.ingestao.chunker import processar_todos_pdfs


# Quantos chunks processar por vez ao gerar embeddings
# (batches melhoram performance e respeitam limites de rate)
BATCH_SIZE_EMBEDDING = 16

# Quantos documentos enviar por vez pro AI Search
BATCH_SIZE_UPLOAD = 50


def criar_cliente_openai():
    """Cliente do Azure OpenAI / Foundry."""
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )


def criar_cliente_search():
    """Cliente do Azure AI Search."""
    return SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY),
    )


def gerar_embeddings_em_lote(
    client: AzureOpenAI, textos: List[str]
) -> List[List[float]]:
    """
    Gera embeddings pra uma lista de textos em uma única chamada.
    Muito mais eficiente que chamar um por um.
    """
    response = client.embeddings.create(
        input=textos,
        model=EMBEDDING_DEPLOYMENT,
    )
    return [item.embedding for item in response.data]


def gerar_embeddings_para_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    Adiciona o campo 'vetor' em cada chunk usando o embedding gerado.
    Processa em batches pra otimizar.
    """
    client = criar_cliente_openai()
    total = len(chunks)
    print(f"\n🧮 Gerando embeddings para {total} chunks...")

    for i in range(0, total, BATCH_SIZE_EMBEDDING):
        batch = chunks[i : i + BATCH_SIZE_EMBEDDING]
        textos = [c["texto"] for c in batch]

        try:
            vetores = gerar_embeddings_em_lote(client, textos)
            for chunk, vetor in zip(batch, vetores):
                chunk["vetor"] = vetor

            print(f"   ✅ Batch {i // BATCH_SIZE_EMBEDDING + 1}: chunks {i+1}-{min(i+BATCH_SIZE_EMBEDDING, total)}")
        except Exception as e:
            print(f"   ❌ Erro no batch {i // BATCH_SIZE_EMBEDDING + 1}: {e}")
            raise

        # Delay leve pra respeitar rate limits
        time.sleep(0.5)

    print(f"✅ Embeddings gerados para {total} chunks")
    return chunks


def enviar_para_search(chunks: List[Dict]):
    """
    Envia os chunks (com vetores) pro Azure AI Search em batches.
    """
    client = criar_cliente_search()
    total = len(chunks)
    print(f"\n📤 Enviando {total} chunks pro AI Search...")

    # Prepara os documentos no formato esperado pelo índice
    documentos = []
    for c in chunks:
        documentos.append({
            "id": c["id"],
            "texto": c["texto"],
            "fonte": c["fonte"],
            "chunk_index": c["chunk_index"],
            "total_chunks_no_doc": c["total_chunks_no_doc"],
            "vetor": c["vetor"],
        })

    sucesso = 0
    falha = 0

    for i in range(0, total, BATCH_SIZE_UPLOAD):
        batch = documentos[i : i + BATCH_SIZE_UPLOAD]
        try:
            resultado = client.upload_documents(documents=batch)
            sucesso += sum(1 for r in resultado if r.succeeded)
            falha += sum(1 for r in resultado if not r.succeeded)
            print(f"   ✅ Batch enviado: {i+1}-{min(i+BATCH_SIZE_UPLOAD, total)}")
        except Exception as e:
            print(f"   ❌ Erro no batch: {e}")
            falha += len(batch)

    print(f"\n✅ Upload concluído: {sucesso} sucesso, {falha} falhas")


def main():
    """Pipeline completo."""
    print("=" * 60)
    print("🚀 PIPELINE DE INDEXAÇÃO - RAG Bulas")
    print("=" * 60)

    # 1. Processa todos os PDFs e gera chunks
    chunks = processar_todos_pdfs()

    if not chunks:
        print("❌ Nenhum chunk gerado. Verifique os PDFs.")
        return

    # 2. Gera embeddings pra cada chunk
    chunks = gerar_embeddings_para_chunks(chunks)

    # 3. Envia tudo pro AI Search
    enviar_para_search(chunks)

    print("\n" + "=" * 60)
    print("🎉 INDEXAÇÃO CONCLUÍDA!")
    print(f"   {len(chunks)} chunks indexados no '{AZURE_SEARCH_INDEX_NAME}'")
    print("=" * 60)


if __name__ == "__main__":
    main()