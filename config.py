"""
config.py — fonte única de configuração.

Funciona em dois ambientes:
  - Local: lê do arquivo .env via python-dotenv
  - Streamlit Cloud: lê de st.secrets (Settings → Secrets no painel)

Nenhum outro módulo deve chamar os.getenv() diretamente.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _cfg(key: str, default: str = "") -> str:
    """Lê de st.secrets (Streamlit Cloud) ou .env (local)."""
    try:
        import streamlit as st
        return str(st.secrets.get(key, os.getenv(key, default)))
    except Exception:
        return os.getenv(key, default)


class Settings:

    # ── API ───────────────────────────────────────────────────────────────
    @property
    def GEMINI_API_KEY(self) -> str:
        return _cfg("GEMINI_API_KEY")

    @property
    def APP_PASSWORD(self) -> str:
        return _cfg("APP_PASSWORD")

    # ── Modelo ────────────────────────────────────────────────────────────
    @property
    def GEMINI_MODEL(self) -> str:
        return _cfg("GEMINI_MODEL", "gemini-2.0-flash")

    GEMINI_TEMPERATURE: float = 0.0
    GEMINI_MAX_TOKENS: int    = 2048

    # ── Instituição ───────────────────────────────────────────────────────
    @property
    def INSTITUICAO_NOME(self) -> str:
        return _cfg("INSTITUICAO_NOME", "NOME DA INSTITUIÇÃO")

    @property
    def INSTITUICAO_SIGLA(self) -> str:
        return _cfg("INSTITUICAO_SIGLA", "SIGLA")

    @property
    def INSTITUICAO_CNPJ(self) -> str:
        return _cfg("INSTITUICAO_CNPJ", "00.000.000/0000-00")

    @property
    def INSTITUICAO_SETOR(self) -> str:
        return _cfg("INSTITUICAO_SETOR", "PRÓ-REITORIA DE ADMINISTRAÇÃO")

    @property
    def INSTITUICAO_CIDADE(self) -> str:
        return _cfg("INSTITUICAO_CIDADE", "Cidade - UF")

    @property
    def INSTITUICAO_FORO(self) -> str:
        return _cfg("INSTITUICAO_FORO", "comarca sede da Instituição")

    # ── Limites legais — Decreto 12.343/2024 ──────────────────────────────
    @property
    def LIMITE_DISPENSA_INC_I(self) -> float:
        return float(_cfg("LIMITE_DISPENSA_INC_I", "125451.15"))

    @property
    def LIMITE_DISPENSA_INC_II(self) -> float:
        return float(_cfg("LIMITE_DISPENSA_INC_II", "62725.59"))

    @property
    def LIMITE_HABILITACAO_SIMPLES(self) -> float:
        return round(self.LIMITE_DISPENSA_INC_II / 4, 2)

    @property
    def LIMITE_PREGAO(self) -> float:
        return float(_cfg("LIMITE_PREGAO", "1000000.00"))

    # Fundamentos legais
    FUNDAMENTO_DISPENSA_I:    str = "Art. 75, inciso I, da Lei nº 14.133/2021"
    FUNDAMENTO_DISPENSA_II:   str = "Art. 75, inciso II, da Lei nº 14.133/2021"
    FUNDAMENTO_PREGAO:        str = "Art. 82 da Lei nº 14.133/2021"
    FUNDAMENTO_CONCORRENCIA:  str = "Art. 29 da Lei nº 14.133/2021"

    # ── Caminhos ──────────────────────────────────────────────────────────
    BASE_DIR:       Path = Path(__file__).parent
    TEMPLATE_DIR:   Path = Path(__file__).parent / "templates"
    TEMPLATE_TR:    Path = Path(__file__).parent / "templates" / "tr_fornecimento.docx"
    TEMPLATE_AVISO: Path = Path(__file__).parent / "templates" / "aviso_contratacao.docx"

    # ── Defaults ──────────────────────────────────────────────────────────
    PAGAMENTO_PADRAO: str = (
        "30 (trinta) dias corridos após entrega e aceite definitivo, "
        "mediante apresentação de Nota Fiscal"
    )

    def validar(self) -> list[str]:
        erros = []
        if not self.GEMINI_API_KEY:
            erros.append("GEMINI_API_KEY não configurada.")
        if not self.APP_PASSWORD:
            erros.append("APP_PASSWORD não configurada.")
        return erros


settings = Settings()
