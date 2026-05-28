# Perguntas para demonstração / vídeo

## ✅ Testadas e funcionando

### 1. Dipirona + amamentação
```json
{"question":"Posso tomar dipirona se estou amamentando?"}
```

### 2. Dose máxima paracetamol
```json
{"question":"Qual a dose máxima diária de paracetamol para adultos?"}
```

### 3. Amoxicilina pediátrica (demonstra honestidade do modelo)
```json
{"question":"Como tomar amoxicilina para criança com infecção de garganta?"}
```

## 🆕 Sugestões para mais testes

### 4. Efeitos colaterais diabetes
```json
{"question":"Quais são os efeitos colaterais da metformina?"}
```

### 5. Antialérgico e sono
```json
{"question":"Loratadina dá sono?"}
```

### 6. Anti-inflamatório e estômago
```json
{"question":"Ibuprofeno pode causar problemas no estômago?"}
```

### 7. Interação medicamentosa
```json
{"question":"Posso tomar omeprazol todos os dias?"}
```

### 8. Pressão alta
```json
{"question":"Quais cuidados ao tomar losartana?"}
```

### 9. Anti-inflamatório forte
```json
{"question":"Quando usar nimesulida e por quanto tempo?"}
```

### 10. Fora do escopo (controle)
```json
{"question":"Qual a melhor receita de bolo de chocolate?"}
```

## 📋 Comando completo (PowerShell)

```powershell
$body = '{"question":"SUA_PERGUNTA_AQUI"}'
Invoke-RestMethod -Uri "http://localhost:7071/api/query" -Method POST -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json; charset=utf-8"
```