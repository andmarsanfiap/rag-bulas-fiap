// ============================================================
// main.bicep
// Infrastructure as Code para o projeto RAG Bulas FIAP
// 
// Cria toda a infraestrutura Azure necessária:
// - Azure AI Foundry (Cognitive Services account)
// - Azure AI Search
// - Storage Account
// - Function App (Flex Consumption)
// ============================================================

// ============================================================
// PARÂMETROS
// ============================================================
// Sufixo único pra evitar conflito de nomes globais (3-10 chars)
@description('Sufixo único para nomes de recursos (ex: 777, abc, etc)')
@minLength(3)
@maxLength(10)
param suffix string = '777'

// Região onde os recursos serão criados
@description('Região do Azure para deploy')
param location string = 'eastus2'

// Região do AI Search (pode ser diferente da Foundry)
@description('Região para o Azure AI Search')
param searchLocation string = 'eastus'

// Tier do AI Search (free para projeto acadêmico)
@description('SKU do Azure AI Search (free para projeto acadêmico)')
@allowed(['free', 'basic', 'standard'])
param searchSku string = 'free'

// ============================================================
// VARIÁVEIS
// ============================================================
var foundryName = 'foundry-ragbulas-${suffix}'
var searchName = 'srch-ragbulas-${suffix}'
var storageName = 'stragbulas${suffix}'
var functionAppName = 'func-ragbulas-${suffix}'
var hostingPlanName = 'plan-ragbulas-${suffix}'

// ============================================================
// 1. AZURE AI FOUNDRY (Cognitive Services account)
// ============================================================
// Recurso que abriga os modelos de IA (embeddings + chat)
// Os modelos (text-embedding-3-small, gpt-4o) precisam ser
// implantados manualmente no portal Foundry depois.
resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: foundryName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: foundryName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// ============================================================
// 2. AZURE AI SEARCH
// ============================================================
// Banco vetorial onde ficam os chunks indexados
resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: searchName
  location: searchLocation
  sku: {
    name: searchSku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
  }
}

// ============================================================
// 3. STORAGE ACCOUNT
// ============================================================
// Necessário pro Azure Functions Flex Consumption (runtime)
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
  }
}

// Container blob pros PDFs (opcional, não usado no fluxo atual mas
// reservado pra evoluções futuras)
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource bulasContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'bulas-pdf'
  properties: {
    publicAccess: 'None'
  }
}

// ============================================================
// 4. FUNCTION APP (Flex Consumption + Python 3.11)
// ============================================================
// Plano de hospedagem Flex Consumption
resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: hostingPlanName
  location: location
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true // Linux
  }
}

// Function App em si
resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}deploymentpackage'
          authentication: {
            type: 'StorageAccountConnectionString'
            storageAccountConnectionStringName: 'DEPLOYMENT_STORAGE_CONNECTION_STRING'
          }
        }
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 100
        instanceMemoryMB: 2048
      }
    }
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'DEPLOYMENT_STORAGE_CONNECTION_STRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: foundry.properties.endpoint
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: foundry.listKeys().key1
        }
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: '2024-02-01'
        }
        {
          name: 'EMBEDDING_DEPLOYMENT'
          value: 'text-embedding-3-small'
        }
        {
          name: 'CHAT_DEPLOYMENT'
          value: 'gpt-4o'
        }
        {
          name: 'AZURE_SEARCH_ENDPOINT'
          value: 'https://${searchService.name}.search.windows.net'
        }
        {
          name: 'AZURE_SEARCH_API_KEY'
          value: searchService.listAdminKeys().primaryKey
        }
        {
          name: 'AZURE_SEARCH_INDEX_NAME'
          value: 'bulas-medicamentos'
        }
      ]
    }
    httpsOnly: true
  }
}

// ============================================================
// OUTPUTS
// ============================================================
// Valores retornados depois do deploy (úteis pro README)
output foundryEndpoint string = foundry.properties.endpoint
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output storageAccountName string = storage.name
output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'
