"""
function_app.py - Entry point da Azure Function.

Define o endpoint HTTP POST /api/query que recebe perguntas
e retorna respostas geradas pelo RAG.
"""

import json
import logging

import azure.functions as func

from rag_service import gerar_resposta


# Cria a "app" da Azure Function
# AuthLevel.FUNCTION significa que vai precisar de uma chave pra chamar
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="query", methods=["POST"])
def query(req: func.HttpRequest) -> func.HttpResponse:
    """
    Endpoint POST /api/query
    
    Body esperado:
        {"question": "sua pergunta aqui"}
    
    Retorna:
        {
            "answer": "resposta gerada...",
            "sources": [
                {"chunk": "...", "source": "dipirona.pdf", "score": 0.85},
                ...
            ]
        }
    """
    logging.info("Endpoint /api/query foi chamado")

    # ===== 1. Parsear o body JSON =====
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({
                "error": "Body inválido. Envie um JSON com o campo 'question'.",
            }),
            status_code=400,
            mimetype="application/json",
        )

    # ===== 2. Validar campo 'question' =====
    pergunta = body.get("question", "").strip()
    if not pergunta:
        return func.HttpResponse(
            json.dumps({
                "error": "Campo 'question' é obrigatório e não pode estar vazio.",
            }),
            status_code=400,
            mimetype="application/json",
        )

    # ===== 3. Chamar o RAG =====
    try:
        resultado = gerar_resposta(pergunta)
    except Exception as e:
        logging.error(f"Erro ao processar pergunta: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": "Erro interno ao processar a pergunta.",
                "detail": str(e),
            }),
            status_code=500,
            mimetype="application/json",
        )

    # ===== 4. Retornar resposta =====
    return func.HttpResponse(
        json.dumps(resultado, ensure_ascii=False, indent=2),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """
    Endpoint de health check: GET /api/health
    Útil pra verificar se a API está no ar (sem gastar chamada do LLM).
    """
    return func.HttpResponse(
        json.dumps({"status": "ok", "service": "rag-bulas-api"}),
        status_code=200,
        mimetype="application/json",
    )