# 🩺 RAG Bulas — Sistema de Consulta de Bulas de Medicamentos

> Trabalho final da disciplina **Cloud & Cognitive Environments** do MBA em Data Science e IA da FIAP.
>
> **Alunos:** Anderson — RM 362612 - Daniel - RM - 364495 - João Alves  - RM - 363514 - Ricardo  - RM - 363450
> **Professor:** Fabio Bazacas Zetola

---

## 📋 Visão Geral

### O problema

Bulas de medicamentos são documentos longos, técnicos e padronizados. Quando um usuário tem uma dúvida específica (ex: "posso tomar dipirona se estou amamentando?"), buscar a resposta na bula completa é demorado e nem sempre intuitivo.

### A solução

Uma aplicação **RAG (Retrieval-Augmented Generation)** que:
1. Indexa bulas em PDF como vetores em um banco vetorial
2. Recebe perguntas em linguagem natural via API HTTP
3. Recupera os trechos mais relevantes via busca semântica
4. Gera respostas contextualizadas com um LLM, **citando a fonte**

### Características

- ✅ Respostas baseadas **apenas no conteúdo das bulas** (não inventa)
- ✅ Cita o medicamento e o trecho exato que embasou a resposta
- ✅ Admite quando a informação não está disponível
- ✅ Sempre recomenda consultar profissional de saúde

### Link do vídeo demonstrativo

🎥 https://youtu.be/OVv6nefb_l0

---

## 🏗️ Arquitetura

┌─────────────┐  POST /api/query  ┌──────────────────────────┐
│   Cliente   │ ─────────────────▶│   Azure Function          │
│  (Postman)  │                   │   (Python 3.11)           │
└─────────────┘ ◀───────────────── │                          │
                  JSON response    └──────┬───────────────────┘
                                          │
                        ┌─────────────────┼─────────────────┐
                        ▼                 ▼                 ▼
                ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
                │ Azure        │  │ Azure AI     │  │ Azure Storage  │
                │ OpenAI       │  │ Search       │  │ (PDFs)         │
                │ Foundry      │  │ (Vector DB)  │  │                │
                └──────────────┘  └──────────────┘  └────────────────┘


### Fluxo de uma consulta

1. **Cliente** envia `POST /api/query` com `{"question": "..."}`
2. **Function** gera embedding da pergunta via Azure OpenAI (`text-embedding-3-small`)
3. **AI Search** retorna os top-3 chunks mais relevantes (busca vetorial HNSW)
4. **Function** monta prompt com instruções + contexto + pergunta
5. **GPT-4o** gera a resposta baseada no contexto
6. **API** retorna `{"answer": "...", "sources": [...]}`

### Stack tecnológica

| Camada | Tecnologia |
|---|---|
| **Modelo de embeddings** | Azure OpenAI `text-embedding-3-small` (1536 dimensões) |
| **Modelo de geração** | Azure OpenAI `gpt-4o` (Global Standard) |
| **Banco vetorial** | Azure AI Search (algoritmo HNSW) |
| **Storage** | Azure Storage Blob |
| **API** | Azure Functions Python 3.11 (Flex Consumption) |
| **Chunking** | LangChain `RecursiveCharacterTextSplitter` |
| **Linguagem** | Python 3.13 (local) / 3.11 (nuvem) |

---

## 📁 Estrutura do projeto

rag-bulas-fiap/
├── documentos/
│   └── bulas/                  # 10 PDFs de bulas da Anvisa
├── src/
│   ├── api/                    # Azure Function
│   │   ├── function_app.py     # Endpoints HTTP (/query, /health)
│   │   ├── rag_service.py      # Lógica do RAG
│   │   ├── host.json
│   │   ├── local.settings.json # (ignorado pelo Git — segredos)
│   │   └── requirements.txt
│   ├── ingestao/               # Pipeline de ingestão
│   │   ├── chunker.py          # Leitura de PDFs + chunking
│   │   ├── criar_indice.py     # Cria índice no AI Search
│   │   ├── indexar.py          # Pipeline completo
│   │   └── testar_busca.py     # Validação da busca
│   └── utils/
│       └── config.py           # Configurações centralizadas
├── .env                        # (ignorado — segredos)
├── .gitignore
├── README.md
├── requirements.txt            # Dependências locais
├── test_conexao.py             # Teste de conexão com Azure
└── perguntas_demo.md           # Perguntas usadas no vídeo

---

## 🚀 Como executar localmente

### Pré-requisitos

- Python 3.11 ou superior
- Azure CLI (`az`)
- Azure Functions Core Tools v4
- Conta Azure com:
  - Azure OpenAI / Foundry (com modelos `text-embedding-3-small` e `gpt-4o`)
  - Azure AI Search (tier Free ou superior)
  - Storage Account

### 1. Clonar o repositório

```bash
git clone https://github.com/andmarsanfiap/rag-bulas-fiap.git
cd rag-bulas-fiap
```

### 2. Criar e ativar ambiente virtual

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz com suas credenciais:

```env
AZURE_OPENAI_ENDPOINT=https://SEU-FOUNDRY.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=sua_chave_aqui
AZURE_OPENAI_API_VERSION=2024-02-01
EMBEDDING_DEPLOYMENT=text-embedding-3-small
CHAT_DEPLOYMENT=gpt-4o

AZURE_SEARCH_ENDPOINT=https://SEU-SEARCH.search.windows.net
AZURE_SEARCH_API_KEY=sua_admin_key_aqui
AZURE_SEARCH_INDEX_NAME=bulas-medicamentos

AZURE_STORAGE_CONNECTION_STRING=sua_connection_string_aqui
AZURE_STORAGE_CONTAINER=bulas-pdf
```

### 5. Testar conexão com Azure

```bash
python test_conexao.py
```

Deve retornar ✅ em todos os 5 testes.

### 6. Indexar as bulas

```bash
# Cria o índice no AI Search
python src/ingestao/criar_indice.py

# Processa PDFs, gera embeddings e indexa
python src/ingestao/indexar.py

# Testa a busca vetorial
python src/ingestao/testar_busca.py
```

### 7. Rodar a API localmente

Copie o arquivo `.env` para `src/api/local.settings.json` no formato:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_OPENAI_ENDPOINT": "...",
    ...
  }
}
```

Inicie a Function:

```bash
cd src/api
func start
```

A API estará disponível em:
- `GET  http://localhost:7071/api/health`
- `POST http://localhost:7071/api/query`

---

## ☁️ Como fazer o deploy

### 1. Criar Function App no Azure

Via portal Azure ou CLI:

```bash
az functionapp create \
  --resource-group rg-rag-bulas \
  --consumption-plan-location eastus2 \
  --runtime python \
  --runtime-version 3.11 \
  --name func-ragbulas-XXX \
  --storage-account stragbulasXXX \
  --os-type linux
```

### 2. Configurar variáveis de ambiente na nuvem

Pelo portal Azure ou CLI:

```bash
az functionapp config appsettings set \
  --name func-ragbulas-XXX \
  --resource-group rg-rag-bulas \
  --settings \
    "AZURE_OPENAI_ENDPOINT=..." \
    "AZURE_OPENAI_API_KEY=..." \
    "AZURE_OPENAI_API_VERSION=2024-02-01" \
    "EMBEDDING_DEPLOYMENT=text-embedding-3-small" \
    "CHAT_DEPLOYMENT=gpt-4o" \
    "AZURE_SEARCH_ENDPOINT=..." \
    "AZURE_SEARCH_API_KEY=..." \
    "AZURE_SEARCH_INDEX_NAME=bulas-medicamentos"
```

### 3. Fazer o deploy

```bash
cd src/api
func azure functionapp publish func-ragbulas-XXX
```

---

## 📝 Exemplos de uso

### Exemplo 1 — Dipirona e amamentação

**Request:**
```bash
POST /api/query?code=SUA_CHAVE
Content-Type: application/json

{
  "question": "Posso tomar dipirona se estou amamentando?"
}
```

**Response:**
```json
{
  "answer": "De acordo com a bula da dipirona, a amamentação deve ser evitada durante e por até 48 horas após o uso do medicamento, pois a dipirona é eliminada no leite materno. O uso da dipirona no período de lactação depende da avaliação e acompanhamento de um médico ou cirurgião-dentista. Recomenda-se consultar um profissional de saúde para orientação adequada.",
  "sources": [
    {
      "chunk": "...A amamentação deve ser evitada durante e por até 48 horas após o uso de dipirona. A dipirona é eliminada no leite materno...",
      "source": "dipirona.pdf",
      "chunk_index": 9,
      "score": 0.77
    }
  ]
}
```

### Exemplo 2 — Efeitos colaterais

**Request:**
```json
{"question": "Quais são os efeitos colaterais da metformina?"}
```

A API retorna os efeitos colaterais citados na bula (náusea, diarreia, etc.), citando `metformina.pdf` como fonte.

### Exemplo 3 — Pergunta fora do escopo (controle)

**Request:**
```json
{"question": "Qual a melhor receita de bolo de chocolate?"}
```

A API responde corretamente que **a informação não foi encontrada nas bulas disponíveis** — comportamento esperado de um RAG bem implementado, que não "inventa" respostas fora do contexto.

---

## 🧠 Decisões técnicas

### Por que chunking recursivo (1500 chars, 200 overlap)?

Bulas têm estrutura hierárquica clara (seções → parágrafos → frases). O `RecursiveCharacterTextSplitter` tenta dividir nessa ordem natural:
1. Parágrafo (`\n\n`)
2. Linha (`\n`)
3. Frase (`. `)
4. Palavra (` `)

Isso **preserva contexto semântico** dos chunks, melhor que chunking fixo por número de caracteres.

- **`chunk_size=1500`** equivale a ~300 palavras (~1 parágrafo grande). Tamanho que **caiba bem no contexto do LLM** sem ser fragmentado demais.
- **`chunk_overlap=200`** evita perda de contexto na borda entre chunks consecutivos (uma informação importante na fronteira aparece em ambos).

### Por que Azure AI Search como banco vetorial?

- Recomendado pelo professor na disciplina
- Tier **Free** disponível (suficiente pro projeto)
- Suporta busca vetorial nativa com algoritmo **HNSW** (Hierarchical Navigable Small World) — rápido e preciso pra busca aproximada de vizinhos
- Integra nativamente com Azure OpenAI
- Permite combinar busca vetorial + filtros estruturados (futuro)

### Por que `text-embedding-3-small`?

- 1536 dimensões — bom equilíbrio entre qualidade e custo
- Versão `small` é ~3x mais barata que `large`
- Suficiente pra domínio restrito (bulas)

### Por que `gpt-4o`?

- Foi o modelo com **maior cota disponível** na conta Azure for Students
- Qualidade superior pra tarefas de raciocínio sobre contexto
- Suporta português nativamente
- Compatível com a biblioteca `openai` (sem precisar trocar SDK)

### Por que Azure Functions (Flex Consumption)?

- Padrão da disciplina
- Pay-as-you-go (paga só quando alguém chama)
- Suporta Python 3.11+
- Deploy simples via `func azure functionapp publish`
- Logging integrado com Application Insights

### Por que `top_k=3`?

- 3 chunks dão **contexto suficiente** pra maioria das perguntas
- Mantém o prompt curto (custo menor, resposta mais rápida)
- Foi suficiente nos testes pra cobrir cenários comparativos

### Por que `temperature=0.3`?

- Para RAG, queremos respostas **factuais e consistentes**, não criativas
- Temperaturas baixas (0.1-0.4) reduzem alucinação
- A criatividade do modelo deve estar **limitada ao reformular o contexto**, não inventar fatos

---

## 📊 Métricas do projeto

- **10 bulas** indexadas (categorias: analgésicos, antibióticos, anti-inflamatórios, crônicos, antialérgicos)
- **~100 chunks** gerados
- **1536 dimensões** por embedding
- **Top-3** chunks retornados por consulta
- **~5-15s** de latência média por consulta (em produção)

---

## ⚠️ Limitações conhecidas

- **Cold start:** primeira chamada após inatividade pode demorar 30-60s
- **Domínio restrito:** funciona apenas pras 10 bulas indexadas. Pra ampliar, basta adicionar mais PDFs em `documentos/bulas/` e rodar `indexar.py` novamente
- **Sem cache:** cada pergunta gera nova chamada ao LLM (custo)
- **Não substitui orientação médica:** o sistema sempre recomenda consulta a profissional

---

## 📚 Referências

- [Trabalho da disciplina](./TRABALHO_FINAL_3.pdf)
- [Azure AI Search — Vector Search](https://learn.microsoft.com/azure/search/vector-search-overview)
- [Azure OpenAI — Embeddings](https://learn.microsoft.com/azure/ai-services/openai/concepts/understand-embeddings)
- [LangChain Text Splitters](https://python.langchain.com/docs/concepts/text_splitters/)
- [Bulário Eletrônico Anvisa](https://consultas.anvisa.gov.br/#/bulario/)

---

---

## 🏗️ Infrastructure as Code (IaC)

Toda a infraestrutura Azure deste projeto pode ser provisionada automaticamente usando **Bicep**, a linguagem oficial da Microsoft para IaC.

### 📁 Estrutura

infra/
├── main.bicep        # Template principal — descreve todos os recursos
└── main.bicepparam   # Valores dos parâmetros (sufixo, região, sku)

### 🛠️ O que é provisionado automaticamente

| Recurso | Tipo |
|---|---|
| Azure AI Foundry | `Microsoft.CognitiveServices/accounts` |
| Azure AI Search (tier Free) | `Microsoft.Search/searchServices` |
| Storage Account | `Microsoft.Storage/storageAccounts` |
| Container Blob `bulas-pdf` | `Microsoft.Storage/.../containers` |
| Function App (Flex Consumption) | `Microsoft.Web/sites` |
| App Settings (8 variáveis) | conectadas automaticamente ao Foundry e Search |

⚠️ **Nota:** O deploy dos modelos (`text-embedding-3-small` e `gpt-4o`) ainda precisa ser feito manualmente no portal Foundry, pois depende de cota disponível na assinatura.

### ▶️ Como usar

#### 1. Validar o template (não faz deploy)

```bash
az bicep build --file infra/main.bicep
```

Compila o Bicep em ARM JSON e valida a sintaxe.

#### 2. Provisionar a infraestrutura

```bash
# Criar resource group
az group create --name rg-rag-bulas-iac --location eastus2

# Fazer deploy do template
az deployment group create \
  --resource-group rg-rag-bulas-iac \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam
```

⏱️ Provisionamento completo: ~5-10 minutos.

#### 3. Personalizar parâmetros

Edite `infra/main.bicepparam` para mudar:
- **`suffix`** — sufixo único nos nomes dos recursos
- **`location`** — região principal
- **`searchLocation`** — região do AI Search
- **`searchSku`** — `free`, `basic`, ou `standard`

### 💡 Benefícios da abordagem IaC

- ✅ **Reproduzível:** mesma infra em segundos, sem cliques manuais
- ✅ **Versionável:** mudanças de infra ficam no Git, com histórico
- ✅ **Documentação viva:** o `main.bicep` é a fonte da verdade sobre a arquitetura
- ✅ **Multi-ambiente:** dá pra ter `dev.bicepparam`, `staging.bicepparam`, `prod.bicepparam`
- ✅ **App Settings auto-conectadas:** as variáveis de ambiente do Function App são populadas automaticamente com endpoints e chaves dos outros recursos

### 🧹 Limpeza

Pra remover toda a infraestrutura provisionada:

```bash
az group delete --name rg-rag-bulas-iac --yes
```

