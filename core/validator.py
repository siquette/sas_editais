"""
core/validator.py
Valida e normaliza os campos extraídos pelo Gemini.
Campos alinhados com o TR de Fornecimento (Contratação Direta, art. 75, II).
"""

import re
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CamposEdital(BaseModel):

    # ── Obrigatórios ───────────────────────────────────────────────────────
    objeto: str = Field(..., min_length=10,
        description="Descrição do bem ou serviço")
    unidade_solicitante: str = Field(..., min_length=3,
        description="Setor solicitante")
    quantidade: str = Field(...,
        description="Quantidade do item")
    valor_total_estimado: str = Field(...,
        description="Valor total estimado (ex: R$ 40.000,00)")
    prazo_entrega_dias: str = Field(...,
        description="Prazo de entrega em dias")
    justificativa_necessidade: str = Field(..., min_length=20,
        description="Justificativa da necessidade")

    # ── Opcionais ──────────────────────────────────────────────────────────
    codigo_catmat: Optional[str]            = None
    agente_contratacao: Optional[str]       = None
    fiscal_contrato: Optional[str]          = None
    unidade_medida: str                     = "unidade"
    valor_unitario_estimado: Optional[str]  = None
    justificativa_quantidade: Optional[str] = None
    especificacoes_tecnicas: list[str]      = Field(default_factory=list)
    criterio_aceitacao: Optional[str]       = None
    prazo_vigencia_meses: Optional[str]     = None
    local_entrega: Optional[str]            = None
    condicoes_entrega: Optional[str]        = None
    condicoes_pagamento: Optional[str]      = None
    dotacao_orcamentaria: Optional[str]     = None
    numero_sei: Optional[str]              = None
    garantia_produto: Optional[str]        = None
    assistencia_tecnica: Optional[str]     = None
    sustentabilidade: Optional[str]        = None
    observacoes: Optional[str]             = None

    # ── Calculados automaticamente ─────────────────────────────────────────
    modalidade_licitacao: Optional[str]    = None
    inciso_legal: Optional[str]            = None
    fundamento_legal: Optional[str]        = None
    especificacoes_lista: Optional[str]    = None
    data_geracao: str = Field(
        default_factory=lambda: date.today().strftime("%d/%m/%Y"))

    # ── Validators ────────────────────────────────────────────────────────

    @field_validator("valor_total_estimado")
    @classmethod
    def valor_positivo(cls, v: str) -> str:
        nums = re.findall(r"[\d.,]+", v)
        if not nums:
            raise ValueError(f"Valor não reconhecido: '{v}'. Use R$ 40.000,00")
        val = float(nums[0].replace(".", "").replace(",", "."))
        if val <= 0:
            raise ValueError("Valor deve ser maior que zero.")
        return v.strip()

    @field_validator("prazo_entrega_dias")
    @classmethod
    def prazo_tem_numero(cls, v: str) -> str:
        if not re.search(r"\d", v):
            raise ValueError(
                f"Prazo deve conter número: '{v}'. Ex: '30 dias corridos'")
        return v.strip()

    @field_validator("especificacoes_tecnicas", mode="before")
    @classmethod
    def normaliza_specs(cls, v) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in re.split(r"[;\n]", v) if s.strip()]
        return [str(s) for s in v if s]

    @field_validator("unidade_medida", mode="before")
    @classmethod
    def unidade_padrao(cls, v) -> str:
        return v or "unidade"

    # ── Model validators ──────────────────────────────────────────────────

    @model_validator(mode="after")
    def inferir_dados_legais(self) -> "CamposEdital":
        from core.extractor import inferir_modalidade
        info = inferir_modalidade(self.valor_total_estimado)
        self.modalidade_licitacao = info["modalidade"]
        self.inciso_legal         = info["inciso"]
        self.fundamento_legal     = info["fundamento"]
        return self

    @model_validator(mode="after")
    def preenche_pagamento(self) -> "CamposEdital":
        if not self.condicoes_pagamento:
            from config import settings
            self.condicoes_pagamento = settings.PAGAMENTO_PADRAO
        return self

    @model_validator(mode="after")
    def formata_especificacoes(self) -> "CamposEdital":
        if self.especificacoes_tecnicas:
            self.especificacoes_lista = "\n".join(
                f"• {s}" for s in self.especificacoes_tecnicas)
        else:
            self.especificacoes_lista = (
                "Conforme especificações constantes neste Termo de Referência.")
        return self


# ── Resultado ─────────────────────────────────────────────────────────────

class ResultadoValidacao:
    def __init__(self, campos: CamposEdital | None, erros: list[dict]):
        self.campos = campos
        self.erros  = erros
        self.valido = len(erros) == 0

    @property
    def campos_faltando(self) -> list[str]:
        return [e["campo"] for e in self.erros if e["tipo"] == "ausente"]


def validar_campos(dados: dict) -> ResultadoValidacao:
    """Valida o dicionário extraído pelo Gemini."""
    from pydantic import ValidationError

    OBRIGATORIOS = [
        "objeto", "unidade_solicitante", "quantidade",
        "valor_total_estimado", "prazo_entrega_dias", "justificativa_necessidade",
    ]

    erros: list[dict] = []
    for campo in OBRIGATORIOS:
        if not dados.get(campo):
            erros.append({
                "campo": campo,
                "tipo": "ausente",
                "mensagem": f"'{campo}' não encontrado no texto.",
            })

    if erros:
        return ResultadoValidacao(None, erros)

    try:
        campos = CamposEdital(**dados)
        return ResultadoValidacao(campos, [])
    except ValidationError as e:
        for err in e.errors():
            campo = " → ".join(str(loc) for loc in err["loc"])
            erros.append({"campo": campo, "tipo": "invalido",
                          "mensagem": err["msg"]})
        return ResultadoValidacao(None, erros)
