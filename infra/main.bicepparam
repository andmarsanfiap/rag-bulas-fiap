// ============================================================
// main.bicepparam
// Valores dos parâmetros para o deploy da infraestrutura
// ============================================================

using './main.bicep'

// Sufixo único nos nomes (3-10 chars, números/letras minúsculas)
param suffix = '777'

// Região principal (Foundry, Storage, Function App)
param location = 'eastus2'

// Região do AI Search (pode ser diferente — East US tem tier Free)
param searchLocation = 'eastus'

// SKU do AI Search (free pra projeto acadêmico, basic+ pra produção real)
param searchSku = 'free'
