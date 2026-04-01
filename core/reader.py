"""
core/reader.py
Normaliza a entrada do usuário para texto puro.

Aceita dois tipos de input:
  - Texto livre digitado diretamente na interface
  - Arquivo .docx enviado via upload

A saída é sempre uma string de texto limpa,
pronta para ser enviada ao Gemini.
"""

from pathlib import Path
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def _iter_blocos(doc):
    """Itera parágrafos e tabelas na ordem real do documento."""
    from docx.oxml.ns import qn
    for child in doc.element.body:
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def ler_docx(arquivo) -> str:
    """
    Lê um arquivo .docx e retorna texto limpo.
    Aceita Path ou objeto de arquivo (BytesIO do Streamlit).
    """
    doc = Document(arquivo)
    blocos: list[str] = []

    for bloco in _iter_blocos(doc):
        if isinstance(bloco, Paragraph):
            texto = bloco.text.strip()
            if texto:
                blocos.append(texto)

        elif isinstance(bloco, Table):
            linhas = []
            for linha in bloco.rows:
                celulas = [c.text.strip() for c in linha.cells if c.text.strip()]
                if celulas:
                    linhas.append(" | ".join(celulas))
            if linhas:
                blocos.append("[TABELA]\n" + "\n".join(linhas) + "\n[/TABELA]")

    return "\n".join(blocos)


def ler_texto(texto: str) -> str:
    """
    Normaliza texto livre digitado pelo usuário.
    Remove linhas em branco excessivas.
    """
    linhas = [l.strip() for l in texto.splitlines()]
    # Remove sequências de mais de uma linha em branco
    resultado = []
    em_branco = 0
    for linha in linhas:
        if not linha:
            em_branco += 1
            if em_branco <= 1:
                resultado.append("")
        else:
            em_branco = 0
            resultado.append(linha)
    return "\n".join(resultado).strip()
