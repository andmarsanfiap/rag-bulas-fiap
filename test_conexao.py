"""
Script de teste de conexão com todos os serviços Azure.
Roda esse arquivo pra confirmar que tudo está configurado certo.
"""

import os
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

print("=" * 60)
print("🔍 TESTE DE CONEXÃO - RAG Bulas FIAP")
print("=" * 60)


# ===== Teste 1: Verificar se .env carregou =====
print("\n[1/5] Verificando arquivo .env...")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
if endpoint:
    print(f"   ✅ .env carregado. Endpoint: {endpoint[:50]}...")
else:
    print("   ❌ .env NÃO carregou. Verifica se o arquivo existe.")
    exit(1)


# ===== Teste 2: Conexão com Foundry (Embedding) =====
print("\n[2/5] Testando Foundry - Embedding...")
try:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

    response = client.embeddings.create(
        input="dipirona é analgésico",
        model=os.getenv("EMBEDDING_DEPLOYMENT"),
    )
    vetor = response.data[0].embedding
    print(f"   ✅ Embedding gerado! Tamanho do vetor: {len(vetor)}")
except Exception as e:
    print(f"   ❌ ERRO: {e}")


# ===== Teste 3: Conexão com Foundry (Chat) =====
print("\n[3/5] Testando Foundry - Chat (Phi-4)...")
try:
    response = client.chat.completions.create(
        model=os.getenv("CHAT_DEPLOYMENT"),
        messages=[
            {"role": "user", "content": "Responda em 5 palavras: o que é dipirona?"}
        ],
        max_tokens=50,
    )
    resposta = response.choices[0].message.content
    print(f"   ✅ Modelo respondeu: {resposta}")
except Exception as e:
    print(f"   ❌ ERRO: {e}")


# ===== Teste 4: Conexão com AI Search =====
print("\n[4/5] Testando Azure AI Search...")
try:
    from azure.search.documents.indexes import SearchIndexClient
    from azure.core.credentials import AzureKeyCredential

    index_client = SearchIndexClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY")),
    )
    # Lista índices (deve estar vazio por enquanto, mas o request precisa funcionar)
    indices = list(index_client.list_index_names())
    print(f"   ✅ AI Search conectado! Índices existentes: {indices or '[nenhum ainda]'}")
except Exception as e:
    print(f"   ❌ ERRO: {e}")


# ===== Teste 5: Conexão com Storage =====
print("\n[5/5] Testando Azure Storage...")
try:
    from azure.storage.blob import BlobServiceClient

    blob_service = BlobServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )
    # Lista containers (deve estar vazio)
    containers = [c.name for c in blob_service.list_containers()]
    print(f"   ✅ Storage conectado! Containers existentes: {containers or '[nenhum ainda]'}")
except Exception as e:
    print(f"   ❌ ERRO: {e}")


print("\n" + "=" * 60)
print("🎉 Teste finalizado!")
print("=" * 60)