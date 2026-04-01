"""
core/extractor.py
Envia o texto do briefing ao Gemini e retorna os campos do TR como JSON.

Responsabilidade do LLM: interpretar linguagem natural e extrair dados.
Responsabilidade do template: todo o texto jurídico fixo.
"""

import json
import re
from typing import Any

from google import genai
from google.genai import types

from config import settings

PROMPT_SISTEMA = """
Você é especialista em licitações públicas brasileiras (Lei 14.133/2021).

Sua tarefa: extrair campos estruturados de um texto de briefing de compra.
Retorne SOMENTE JSON válido. Sem markdown, sem explicações, sem texto extra.
Se um campo não estiver no texto, use null.

{
  "objeto": "descrição completa e precisa do bem ou serviço",
  "codigo_catmat": "código CATMAT/CATSER se mencionado",

  "unidade_solicitante": "setor ou departamento solicitante",
  "agente_contratacao": "nome do servidor responsável, se mencionado",
  "fiscal_contrato": "nome do fiscal, se mencionado",

  "quantidade": "número como string, ex: '20'",
  "unidade_medida": "unidade, litro, metro, caixa etc.",

  "valor_unitario_estimado": "valor unitário em reais, ex: 'R$ 3.500,00'",
  "valor_total_estimado": "valor total em reais, ex: 'R$ 70.000,00'",

  "justificativa_necessidade": "por que essa compra é necessária",
  "justificativa_quantidade": "por que essa quantidade",

  "especificacoes_tecnicas": ["array", "de", "especificações", "mínimas"],
  "criterio_aceitacao": "como verificar se o bem atende as specs",

  "prazo_entrega_dias": "número de dias como string, ex: '30'",
  "prazo_vigencia_meses": "vigência do contrato em meses, se aplicável",
  "local_entrega": "endereço ou sala de entrega",
  "condicoes_entrega": "condições de embalagem, transporte etc.",

  "condicoes_pagamento": "prazo e forma de pagamento",
  "dotacao_orcamentaria": "dotação ou fonte de recursos",
  "numero_sei": "número do processo SEI se já existir",

  "garantia_produto": "prazo de garantia do bem",
  "assistencia_tecnica": "condições de assistência técnica",
  "sustentabilidade": "requisitos ambientais/sustentabilidade",
  "observacoes": "outras informações relevantes"
}
"""


def _cliente() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise EnvironmentError(
            "GEMINI_API_KEY não configurada. "
            "Adicione ao .env (local) ou Secrets (Streamlit Cloud)."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def extrair_campos(texto: str) -> dict[str, Any]:
    """
    Extrai campos estruturados do texto via Gemini.
    Retorna dicionário com os campos do TR.
    """
    if not texto or not texto.strip():
        raise ValueError("Texto vazio — nada para extrair.")

    client = _cliente()
    prompt = f"{PROMPT_SISTEMA}\n\nTexto do briefing:\n\n{texto}"

    try:
        resposta = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                max_output_tokens=settings.GEMINI_MAX_TOKENS,
            ),
        )
    except Exception as e:
        raise RuntimeError(f"Falha na chamada ao Gemini: {e}") from e

    texto_resposta = resposta.text.strip()
    if texto_resposta.startswith("```"):
        linhas = texto_resposta.split("\n")
        texto_resposta = "\n".join(linhas[1:-1])

    try:
        return json.loads(texto_resposta)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Gemini retornou resposta inválida:\n{texto_resposta}"
        ) from e


def inferir_modalidade(valor_str: str | None) -> dict:
    """
    Determina modalidade, inciso e fundamento legal pelo valor estimado.
    Retorna dict com: modalidade, inciso, fundamento, valor_numerico.
    """
    vazio = {
        "modalidade": "A definir",
        "inciso": None,
        "fundamento": "Valor não informado",
        "valor_numerico": 0.0,
    }

    if not valor_str:
        return vazio

    nums = re.findall(r"[\d.,]+", valor_str)
    if not nums:
        return vazio

    try:
        valor = float(nums[0].replace(".", "").replace(",", "."))
    except ValueError:
        return vazio

    if valor <= 0:
        return vazio

    resultado = {"valor_numerico": valor}

    if valor <= settings.LIMITE_DISPENSA_INC_II:
        resultado.update({
            "modalidade": "Dispensa de Licitação",
            "inciso": "II",
            "fundamento": settings.FUNDAMENTO_DISPENSA_II,
        })
    elif valor <= settings.LIMITE_DISPENSA_INC_I:
        resultado.update({
            "modalidade": "Dispensa de Licitação",
            "inciso": "I",
            "fundamento": settings.FUNDAMENTO_DISPENSA_I,
        })
    elif valor <= settings.LIMITE_PREGAO:
        resultado.update({
            "modalidade": "Pregão Eletrônico",
            "inciso": None,
            "fundamento": settings.FUNDAMENTO_PREGAO,
        })
    else:
        resultado.update({
            "modalidade": "Concorrência",
            "inciso": None,
            "fundamento": settings.FUNDAMENTO_CONCORRENCIA,
        })

    return resultado
