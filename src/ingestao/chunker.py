"""
chunker.py - Pipeline de ingestão e chunking de PDFs.

Lê PDFs da pasta documentos/bulas/, extrai texto,
divide em chunks com estratégia recursiva e retorna
uma lista pronta pra ser indexada.
"""

import sys
from pathlib import Path
from typing import List, Dict
import hashlib
import re

# Adiciona a raiz do projeto no path pra importar utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.utils.config import BULAS_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def limpar_texto(texto: str) -> str:
    """
    Limpa texto extraído de PDF.
    - Remove espaços e quebras de linha excessivos
    - Remove caracteres de controle
    """
    # Substitui múltiplos espaços/quebras por um único espaço
    texto = re.sub(r"\s+", " ", texto)
    # Remove espaços no começo/fim
    return texto.strip()


def extrair_texto_pdf(caminho_pdf: Path) -> str:
    """
    Lê um PDF e retorna todo o texto concatenado.
    """
    leitor = PdfReader(str(caminho_pdf))
    paginas = []
    for pagina in leitor.pages:
        texto = pagina.extract_text() or ""
        paginas.append(texto)
    texto_completo = "\n".join(paginas)
    return limpar_texto(texto_completo)


def gerar_id_chunk(texto: str, nome_arquivo: str, indice: int) -> str:
    """
    Gera um ID único pra cada chunk (hash do conteúdo + posição).
    Necessário pro Azure AI Search exigir IDs únicos.
    """
    base = f"{nome_arquivo}_{indice}_{texto[:50]}"
    return hashlib.md5(base.encode()).hexdigest()


def dividir_em_chunks(texto: str, nome_arquivo: str) -> List[Dict]:
    """
    Divide texto em chunks usando estratégia recursiva.
    
    Estratégia: tenta quebrar nos separadores na ordem:
    1. Parágrafo (\n\n)
    2. Linha (\n)
    3. Frase (. )
    4. Palavra ( )
    5. Caractere (último recurso)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    pedacos = splitter.split_text(texto)

    chunks = []
    for i, pedaco in enumerate(pedacos):
        chunks.append({
            "id": gerar_id_chunk(pedaco, nome_arquivo, i),
            "texto": pedaco,
            "fonte": nome_arquivo,
            "chunk_index": i,
            "total_chunks_no_doc": len(pedacos),
        })

    return chunks


def processar_todos_pdfs() -> List[Dict]:
    """
    Lê todos os PDFs da pasta de bulas e retorna todos os chunks.
    """
    if not BULAS_DIR.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {BULAS_DIR}")

    pdfs = list(BULAS_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"Nenhum PDF encontrado em {BULAS_DIR}")

    print(f"📂 Encontrados {len(pdfs)} PDFs para processar")

    todos_chunks = []
    for pdf in pdfs:
        print(f"\n📄 Processando: {pdf.name}")
        try:
            texto = extrair_texto_pdf(pdf)
            print(f"   Caracteres extraídos: {len(texto)}")

            chunks = dividir_em_chunks(texto, pdf.name)
            print(f"   Chunks gerados: {len(chunks)}")

            todos_chunks.extend(chunks)
        except Exception as e:
            print(f"   ❌ Erro ao processar: {e}")

    print(f"\n✅ Total de chunks gerados: {len(todos_chunks)}")
    return todos_chunks


if __name__ == "__main__":
    # Quando rodar direto, processa tudo e mostra um resumo
    chunks = processar_todos_pdfs()

    print("\n" + "=" * 60)
    print("📊 RESUMO DOS CHUNKS")
    print("=" * 60)

    # Conta chunks por documento
    por_doc = {}
    for c in chunks:
        por_doc[c["fonte"]] = por_doc.get(c["fonte"], 0) + 1

    for doc, qtd in sorted(por_doc.items()):
        print(f"   {doc}: {qtd} chunks")

    # Mostra exemplo do primeiro chunk
    if chunks:
        print("\n📝 EXEMPLO (primeiro chunk):")
        print(f"   ID: {chunks[0]['id']}")
        print(f"   Fonte: {chunks[0]['fonte']}")
        print(f"   Texto (200 chars): {chunks[0]['texto'][:200]}...")