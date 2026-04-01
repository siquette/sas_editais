"""
core/generator.py
Gera o pacote de Contratação Direta por Dispensa:
  - TR de Fornecimento (.docx)
  - Aviso de Contratação Direta (.docx)

Retorna os bytes de cada arquivo para download direto no Streamlit.
"""

import time
import tempfile
from datetime import date
from pathlib import Path
from docxtpl import DocxTemplate

from config import settings
from core.validator import CamposEdital


def _numero_processo() -> str:
    seq = int(time.time()) % 9999 + 1
    return f"{date.today().year}/{seq:04d}"


def _contexto(campos: CamposEdital, numero_processo: str) -> dict:
    ctx = campos.model_dump()
    ctx["numero_processo"]   = numero_processo
    ctx["ano_atual"]         = str(date.today().year)
    ctx["instituicao_nome"]  = settings.INSTITUICAO_NOME
    ctx["instituicao_sigla"] = settings.INSTITUICAO_SIGLA
    ctx["instituicao_cnpj"]  = settings.INSTITUICAO_CNPJ
    ctx["instituicao_setor"] = settings.INSTITUICAO_SETOR
    ctx["instituicao_cidade"] = settings.INSTITUICAO_CIDADE
    ctx["limite_habilitacao"] = (
        f"R$ {settings.LIMITE_HABILITACAO_SIMPLES:,.2f}"
        .replace(",", "X").replace(".", ",").replace("X", ".")
    )
    ctx["contato_responsavel"] = (
        campos.agente_contratacao or campos.unidade_solicitante
    )
    # Flags para blocos condicionais no template
    ctx["tem_catmat"]          = bool(campos.codigo_catmat)
    ctx["tem_valor_unitario"]  = bool(campos.valor_unitario_estimado)
    ctx["tem_vigencia"]        = bool(campos.prazo_vigencia_meses)
    ctx["tem_fiscal"]          = bool(campos.fiscal_contrato)
    ctx["tem_dotacao"]         = bool(campos.dotacao_orcamentaria)
    ctx["tem_garantia"]        = bool(campos.garantia_produto)
    ctx["tem_sustentabilidade"] = bool(campos.sustentabilidade)
    ctx["tem_observacoes"]     = bool(campos.observacoes)
    return ctx


def _renderizar_bytes(template_path: Path, contexto: dict) -> bytes:
    """Renderiza o template e retorna os bytes do arquivo gerado."""
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template não encontrado: {template_path}\n"
            "Execute: python templates/criar_templates.py"
        )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        tpl = DocxTemplate(template_path)
        tpl.render(contexto)
        tpl.save(tmp_path)
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def gerar_pacote(
    campos: CamposEdital,
    numero_processo: str | None = None,
) -> dict[str, bytes]:
    """
    Gera o pacote completo e retorna os bytes de cada arquivo.

    Retorna:
        {
          "tr":    bytes do TR de Fornecimento,
          "aviso": bytes do Aviso de Contratação Direta,
          "numero_processo": str,
        }
    """
    if not numero_processo:
        numero_processo = _numero_processo()

    ctx = _contexto(campos, numero_processo)

    return {
        "tr":    _renderizar_bytes(settings.TEMPLATE_TR,    ctx),
        "aviso": _renderizar_bytes(settings.TEMPLATE_AVISO, ctx),
        "numero_processo": numero_processo,
    }
