"""
rag_service.py - Lógica do RAG (Retrieval-Augmented Generation).

Usa a biblioteca openai (AzureOpenAI) para embeddings e chat,
agora com gpt-4o (modelo nativo OpenAI, estável e confiável).
"""

import os
import logging
from typing import Dict, List

from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential


# ===== Configurações (lidas de variáveis de ambiente) =====
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01")
EMBEDDING_DEPLOYMENT = os.environ["EMBEDDING_DEPLOYMENT"]
CHAT_DEPLOYMENT = os.environ["CHAT_DEPLOYMENT"]

AZURE_SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
AZURE_SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
AZURE_SEARCH_INDEX_NAME = os.environ["AZURE_SEARCH_INDEX_NAME"]


# Quantos chunks recuperar do índice (top-k)
TOP_K = 3


# ===== Clientes globais (reusam conexão entre requests) =====
_openai_client = None
_search_client = None


def get_openai_client() -> AzureOpenAI:
    """Cliente do Azure OpenAI (pra embeddings e chat)."""
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )
    return _openai_client


def get_search_client() -> SearchClient:
    """Cliente do Azure AI Search."""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX_NAME,
            credential=AzureKeyCredential(AZURE_SEARCH_API_KEY),
        )
    return _search_client


def gerar_embedding(texto: str) -> List[float]:
    """Gera o vetor de uma pergunta."""
    client = get_openai_client()
    response = client.embeddings.create(
        input=texto,
        model=EMBEDDING_DEPLOYMENT,
    )
    return response.data[0].embedding


def buscar_chunks_relevantes(pergunta: str, top_k: int = TOP_K) -> List[Dict]:
    """Faz busca vetorial e retorna os top-k chunks mais relevantes."""
    vetor = gerar_embedding(pergunta)
    search_client = get_search_client()

    vector_query = VectorizedQuery(
        vector=vetor,
        k_nearest_neighbors=top_k,
        fields="vetor",
    )

    resultados = search_client.search(
        search_text=None,
        vector_queries=[vector_query],
        select=["id", "texto", "fonte", "chunk_index"],
        top=top_k,
    )

    chunks = []
    for r in resultados:
        chunks.append({
            "chunk": r["texto"],
            "source": r["fonte"],
            "chunk_index": r["chunk_index"],
            "score": r.get("@search.score", 0),
        })
    return chunks


def montar_prompt(pergunta: str, chunks: List[Dict]) -> str:
    """Monta o prompt com contexto e instruções."""
    contexto = "\n\n---\n\n".join([
        f"[Fonte: {c['source']}]\n{c['chunk']}"
        for c in chunks
    ])

    prompt = f"""Você é um assistente especializado em bulas de medicamentos.
Responda à pergunta do usuário usando APENAS as informações dos trechos de bulas fornecidos abaixo.

REGRAS:
1. Se a resposta não estiver nos trechos, diga claramente que não foi encontrada nas bulas disponíveis.
2. Cite o nome do medicamento ao responder.
3. Use linguagem clara e acessível.
4. Não invente dosagens, efeitos colaterais ou interações que não estejam no contexto.
5. Sempre recomende consultar um profissional de saúde para decisões médicas.

CONTEXTO (trechos de bulas):
{contexto}

PERGUNTA DO USUÁRIO:
{pergunta}

RESPOSTA:"""
    return prompt


def gerar_resposta(pergunta: str) -> Dict:
    """
    Pipeline completo de RAG:
    1. Busca chunks relevantes
    2. Monta prompt com contexto
    3. Chama LLM (gpt-4o)
    4. Retorna resposta + fontes
    """
    logging.info(f"Pergunta recebida: {pergunta}")

    # 1. Busca contexto
    chunks = buscar_chunks_relevantes(pergunta)

    if not chunks:
        return {
            "answer": "Não encontrei informações nas bulas disponíveis para responder essa pergunta.",
            "sources": [],
        }

    # 2. Monta prompt
    prompt = montar_prompt(pergunta, chunks)

    # 3. Chama LLM (gpt-4o via AzureOpenAI)
    client = get_openai_client()
    response = client.chat.completions.create(
        model=CHAT_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Você é um assistente especializado em bulas de medicamentos brasileiras."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=600,
        temperature=0.3,
    )

    resposta_texto = response.choices[0].message.content
    logging.info(f"Resposta gerada com {len(resposta_texto)} caracteres")

    return {
        "answer": resposta_texto,
        "sources": chunks,
    }