"""
app.py — Gerador de Editais (Contratação Direta por Dispensa, Lei 14.133/2021)

Fluxo:
  1. Autenticação por senha
  2. Input: texto livre OU upload de .docx
  3. Extração de campos via Gemini
  4. Revisão e edição dos campos
  5. Preview do edital
  6. Download: TR + Aviso de Contratação (.docx)
"""

import zipfile
import io
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

# ── Configuração da página ────────────────────────────────────────────────

st.set_page_config(
    page_title="Gerador de Editais",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .stTextArea textarea { font-size: 0.95rem; }
  .stAlert p { font-size: 0.9rem; margin: 0; }
  [data-testid="stMetricValue"] { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# AUTENTICAÇÃO
# ══════════════════════════════════════════════════════════════════════════

def checar_senha():
    """Bloqueia o app se a senha estiver errada."""
    from config import settings

    if st.session_state.get("autenticado"):
        return

    st.title("📄 Gerador de Editais")
    st.caption("Lei 14.133/2021 · Contratação Direta por Dispensa")
    st.divider()

    if not settings.APP_PASSWORD:
        # Sem senha configurada: avisa e deixa entrar (útil em dev)
        st.warning(
            "APP_PASSWORD não configurada. "
            "Configure nos Secrets para proteger o acesso.",
            icon="⚠️"
        )
        st.session_state.autenticado = True
        st.rerun()
        return

    col, _ = st.columns([1, 2])
    with col:
        senha = st.text_input("Senha de acesso", type="password",
                              placeholder="Digite a senha")
        if st.button("Entrar", type="primary", use_container_width=True):
            if senha == settings.APP_PASSWORD:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Senha incorreta.", icon="🔒")

    st.stop()


checar_senha()


# ══════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO DOS TEMPLATES
# ══════════════════════════════════════════════════════════════════════════

@st.cache_resource
def inicializar_templates():
    """Garante que os templates existam. Roda uma vez por instância."""
    from templates.criar_templates import garantir_templates
    garantir_templates()
    return True

inicializar_templates()


# ══════════════════════════════════════════════════════════════════════════
# ESTADO DA SESSÃO
# ══════════════════════════════════════════════════════════════════════════

_DEFAULTS = {
    "etapa":           "input",    # input | revisao | download
    "campos_brutos":   {},
    "texto_entrada":   "",
    "num_processo":    "",
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def reset():
    for k in _DEFAULTS:
        st.session_state[k] = _DEFAULTS[k]
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# CABEÇALHO E PROGRESSO
# ══════════════════════════════════════════════════════════════════════════

col_h, col_sair = st.columns([5, 1])
with col_h:
    st.title("📄 Gerador de Editais")
    st.caption("Lei 14.133/2021 · Contratação Direta por Dispensa de Valor")
with col_sair:
    st.write("")
    if st.button("↺ Reiniciar", use_container_width=True):
        reset()

etapas = ["📝 Texto", "✏️ Revisão", "⬇️ Download"]
idx    = ["input", "revisao", "download"].index(st.session_state.etapa)
colunas = st.columns(3)
for i, (col, label) in enumerate(zip(colunas, etapas)):
    with col:
        if i < idx:
            st.markdown(
                f'<p style="color:var(--success);font-weight:500">{label} ✓</p>',
                unsafe_allow_html=True)
        elif i == idx:
            st.markdown(
                f'<p style="color:#1a56db;font-weight:600">{label}</p>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<p style="color:#aaa">{label}</p>',
                unsafe_allow_html=True)

st.divider()


# ══════════════════════════════════════════════════════════════════════════
# ETAPA 1 — INPUT
# ══════════════════════════════════════════════════════════════════════════

if st.session_state.etapa == "input":

    st.subheader("Descreva a compra")
    st.write(
        "Escreva em linguagem livre o que precisa ser comprado. "
        "Não precisa seguir nenhum formato — a IA extrai as informações automaticamente."
    )

    aba_texto, aba_docx = st.tabs(["✍️ Digitar texto", "📎 Enviar arquivo Word"])

    texto_input = ""
    docx_input  = None

    with aba_texto:
        texto_input = st.text_area(
            "Descreva a compra aqui",
            height=260,
            placeholder=(
                "Exemplo:\n\n"
                "Precisamos adquirir 20 computadores desktop e 10 tablets para o "
                "laboratório de informática. Os computadores precisam ter processador "
                "i5, 16GB de RAM e SSD de 512GB. Os tablets devem ser de 10 polegadas "
                "com caneta stylus. Valor estimado de R$ 180.000,00. "
                "Prazo de entrega: 45 dias. Suporte técnico por 2 anos incluso. "
                "Solicitação do Departamento de TI."
            ),
            label_visibility="collapsed",
        )

    with aba_docx:
        arquivo = st.file_uploader(
            "Arquivo .docx com as informações da compra",
            type=["docx"],
            label_visibility="collapsed",
        )
        if arquivo:
            st.success(f"Arquivo carregado: **{arquivo.name}** "
                       f"({arquivo.size / 1024:.1f} KB)", icon="📄")
            docx_input = arquivo

    st.divider()

    # Validação de configurações antes de chamar a API
    from config import settings
    erros_cfg = settings.validar()
    erros_cfg = [e for e in erros_cfg if "APP_PASSWORD" not in e]  # não bloqueia por senha
    if erros_cfg:
        for e in erros_cfg:
            st.error(e, icon="⚙️")
        st.stop()

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        extrair = st.button("🔍 Extrair com IA", type="primary",
                            use_container_width=True,
                            disabled=(not texto_input and not docx_input))

    if extrair:
        from core.reader    import ler_texto, ler_docx
        from core.extractor import extrair_campos

        with st.spinner("Lendo o briefing..."):
            if docx_input:
                texto = ler_docx(docx_input)
            else:
                texto = ler_texto(texto_input)

        if len(texto.strip()) < 30:
            st.error("Texto muito curto. Descreva a compra com mais detalhes.", icon="⚠️")
            st.stop()

        st.session_state.texto_entrada = texto

        with st.spinner("Extraindo informações com o Gemini..."):
            try:
                campos = extrair_campos(texto)
                st.session_state.campos_brutos = campos
                st.session_state.etapa = "revisao"
                st.rerun()
            except Exception as e:
                st.error(f"Falha na extração: {e}", icon="🚨")

    with st.expander("💡 Dicas para melhores resultados"):
        st.markdown("""
        Quanto mais informações você incluir, mais completo será o edital gerado.
        O sistema consegue extrair automaticamente:

        | Campo | Exemplo no texto |
        |---|---|
        | Objeto | "adquirir 20 notebooks Dell" |
        | Valor estimado | "R$ 80.000,00" ou "oitenta mil reais" |
        | Prazo de entrega | "30 dias", "45 dias corridos" |
        | Justificativa | "para uso no laboratório X" |
        | Especificações | "processador i5, 16GB RAM, SSD 512GB" |
        | Unidade solicitante | "Departamento de TI", "Secretaria" |

        Se algum campo ficar vazio, você poderá preencher na próxima etapa.
        """)


# ══════════════════════════════════════════════════════════════════════════
# ETAPA 2 — REVISÃO
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.etapa == "revisao":

    from core.extractor import inferir_modalidade

    st.subheader("Revise os campos extraídos")
    st.info(
        "Verifique os campos abaixo. A IA pode ter errado ou deixado campos em branco — "
        "corrija antes de gerar o edital. Campos marcados com **\\*** são obrigatórios.",
        icon="✏️"
    )

    cb = st.session_state.campos_brutos

    # ── Processo e Data ──────────────────────────────────────────────────
    col_proc, col_data = st.columns(2)
    with col_proc:
        num_proc = st.text_input(
            "Número do processo *",
            value=st.session_state.num_processo or
                  f"{date.today().year}/{int(__import__('time').time()) % 9999 + 1:04d}",
            help="Número do processo SEI ou administrativo.",
        )
        st.session_state.num_processo = num_proc
    with col_data:
        st.text_input("Data", value=date.today().strftime("%d/%m/%Y"),
                      disabled=True)

    st.divider()

    # ── Identificação ────────────────────────────────────────────────────
    col_e, col_d = st.columns(2)

    with col_e:
        st.markdown("**Identificação**")
        objeto = st.text_area("Objeto *",
            value=cb.get("objeto") or "",
            height=90,
            help="Descrição completa do bem ou serviço.")
        unidade = st.text_input("Unidade solicitante *",
            value=cb.get("unidade_solicitante") or "")
        agente = st.text_input("Agente de contratação",
            value=cb.get("agente_contratacao") or "")
        fiscal = st.text_input("Fiscal do contrato",
            value=cb.get("fiscal_contrato") or "")

    with col_d:
        st.markdown("**Quantitativo e Valor**")
        col_qt, col_un = st.columns([1, 1])
        with col_qt:
            quantidade = st.text_input("Quantidade *",
                value=cb.get("quantidade") or "")
        with col_un:
            unidade_medida = st.text_input("Unidade de medida",
                value=cb.get("unidade_medida") or "unidade")

        valor_unit = st.text_input("Valor unitário estimado",
            value=cb.get("valor_unitario_estimado") or "",
            help="Ex: R$ 4.000,00")
        valor_total = st.text_input("Valor total estimado *",
            value=cb.get("valor_total_estimado") or "",
            help="Ex: R$ 80.000,00")

        # Sugestão de modalidade em tempo real
        if valor_total:
            info = inferir_modalidade(valor_total)
            if info["modalidade"] != "A definir":
                cor = "#2d6a4f" if "Dispensa" in info["modalidade"] else "#856404"
                st.markdown(
                    f'<p style="color:{cor};font-size:0.85rem;margin-top:4px">'
                    f'💡 {info["modalidade"]} — {info["fundamento"]}</p>',
                    unsafe_allow_html=True
                )

    st.divider()

    # ── Justificativa ────────────────────────────────────────────────────
    st.markdown("**Justificativa**")
    col_j1, col_j2 = st.columns(2)
    with col_j1:
        justificativa = st.text_area("Justificativa da necessidade *",
            value=cb.get("justificativa_necessidade") or "",
            height=110)
    with col_j2:
        just_qtd = st.text_area("Justificativa da quantidade",
            value=cb.get("justificativa_quantidade") or "",
            height=110,
            help="Opcional. Ex: '1 por aluno de IC'")

    st.divider()

    # ── Especificações Técnicas ──────────────────────────────────────────
    st.markdown("**Especificações técnicas** (uma por linha)")
    specs_raw = cb.get("especificacoes_tecnicas") or []
    specs_txt = "\n".join(specs_raw) if isinstance(specs_raw, list) else (specs_raw or "")
    specs_input = st.text_area(
        "Especificações",
        value=specs_txt,
        height=120,
        label_visibility="collapsed",
        placeholder="Intel Core i5 12ª geração\nRAM 16GB DDR4\nSSD 512GB NVMe",
    )

    st.divider()

    # ── Entrega e Pagamento ──────────────────────────────────────────────
    st.markdown("**Entrega e Pagamento**")
    col_e2, col_e3, col_e4 = st.columns(3)
    with col_e2:
        prazo = st.text_input("Prazo de entrega (dias) *",
            value=cb.get("prazo_entrega_dias") or "",
            help="Ex: 30")
    with col_e3:
        vigencia = st.text_input("Vigência do contrato (meses)",
            value=cb.get("prazo_vigencia_meses") or "",
            help="Opcional. Ex: 24")
    with col_e4:
        pagamento = st.text_input("Condições de pagamento",
            value=cb.get("condicoes_pagamento") or
                  "30 dias corridos após entrega e aceite, mediante Nota Fiscal")

    col_loc, col_dot = st.columns(2)
    with col_loc:
        local = st.text_input("Local de entrega",
            value=cb.get("local_entrega") or "")
    with col_dot:
        dotacao = st.text_input("Dotação orçamentária",
            value=cb.get("dotacao_orcamentaria") or "")

    st.divider()

    # ── Campos adicionais ────────────────────────────────────────────────
    with st.expander("Campos adicionais (garantia, sustentabilidade, observações)"):
        col_g, col_s = st.columns(2)
        with col_g:
            garantia = st.text_input("Garantia do produto",
                value=cb.get("garantia_produto") or "")
        with col_s:
            catmat = st.text_input("Código CATMAT/CATSER",
                value=cb.get("codigo_catmat") or "")
        sustent = st.text_area("Requisitos de sustentabilidade",
            value=cb.get("sustentabilidade") or "", height=80)
        obs = st.text_area("Observações adicionais",
            value=cb.get("observacoes") or "", height=80)

    st.divider()

    # ── Botões ───────────────────────────────────────────────────────────
    col_v, col_g, _ = st.columns([1, 1, 3])
    with col_v:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.etapa = "input"
            st.rerun()
    with col_g:
        gerar_btn = st.button("📄 Gerar edital", type="primary",
                              use_container_width=True)

    if gerar_btn:
        from core.validator import validar_campos
        from core.generator import gerar_pacote

        campos_revisados = {
            "objeto":                   objeto,
            "unidade_solicitante":      unidade,
            "agente_contratacao":       agente or None,
            "fiscal_contrato":          fiscal or None,
            "quantidade":               quantidade,
            "unidade_medida":           unidade_medida or "unidade",
            "valor_unitario_estimado":  valor_unit or None,
            "valor_total_estimado":     valor_total,
            "prazo_entrega_dias":       prazo,
            "prazo_vigencia_meses":     vigencia or None,
            "justificativa_necessidade": justificativa,
            "justificativa_quantidade":  just_qtd or None,
            "especificacoes_tecnicas":  [s.strip() for s in specs_input.splitlines() if s.strip()],
            "local_entrega":            local or None,
            "condicoes_pagamento":      pagamento or None,
            "dotacao_orcamentaria":     dotacao or None,
            "garantia_produto":         garantia or None,
            "codigo_catmat":            catmat or None,
            "sustentabilidade":         sustent or None,
            "observacoes":              obs or None,
            "numero_sei":               num_proc or None,
        }

        validacao = validar_campos(campos_revisados)

        if not validacao.valido:
            for err in validacao.erros:
                st.error(f"**{err['campo']}**: {err['mensagem']}", icon="⚠️")
        else:
            with st.spinner("Gerando TR e Aviso de Contratação..."):
                try:
                    pacote = gerar_pacote(
                        validacao.campos,
                        numero_processo=num_proc,
                    )
                    st.session_state["pacote"]         = pacote
                    st.session_state["campos_finais"]  = validacao.campos.model_dump()
                    st.session_state.etapa = "download"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao gerar edital: {e}", icon="🚨")


# ══════════════════════════════════════════════════════════════════════════
# ETAPA 3 — DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════

elif st.session_state.etapa == "download":

    pacote = st.session_state.get("pacote", {})
    cf     = st.session_state.get("campos_finais", {})
    num    = pacote.get("numero_processo", "")

    st.success("Edital gerado com sucesso!", icon="✅")

    # ── Resumo ───────────────────────────────────────────────────────────
    st.subheader("Resumo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Processo",    num)
    col2.metric("Modalidade",  cf.get("modalidade_licitacao", "—").split(" (")[0])
    col3.metric("Valor total", cf.get("valor_total_estimado", "—"))

    col4, col5, col6 = st.columns(3)
    col4.metric("Quantidade",  f"{cf.get('quantidade','—')} {cf.get('unidade_medida','')}")
    col5.metric("Prazo",       f"{cf.get('prazo_entrega_dias','—')} dias")
    col6.metric("Fundamento",  cf.get("fundamento_legal", "—"))

    st.divider()

    # ── Preview do edital ─────────────────────────────────────────────────
    st.subheader("Preview")

    with st.container(border=True):
        from config import settings as cfg
        st.markdown(f"**{cfg.INSTITUICAO_NOME.upper()}**")
        st.markdown(f"**{cfg.INSTITUICAO_SETOR.upper()}**")
        st.markdown("---")
        st.markdown("### TERMO DE REFERÊNCIA")
        st.markdown(
            f"**Processo:** {num} &nbsp;&nbsp; "
            f"**Data:** {cf.get('data_geracao','—')} &nbsp;&nbsp; "
            f"**Fundamento:** {cf.get('fundamento_legal','—')}"
        )
        st.markdown("---")

        st.markdown(f"**1. OBJETO**")
        st.markdown(f"{cf.get('objeto','—')}")
        st.markdown(f"Quantidade: **{cf.get('quantidade','—')} {cf.get('unidade_medida','')}**")

        st.markdown(f"**2. JUSTIFICATIVA**")
        st.markdown(cf.get("justificativa_necessidade", "—"))

        if cf.get("especificacoes_tecnicas"):
            st.markdown("**3. ESPECIFICAÇÕES TÉCNICAS**")
            for spec in cf["especificacoes_tecnicas"]:
                st.markdown(f"• {spec}")

        st.markdown("**VALOR ESTIMADO**")
        if cf.get("valor_unitario_estimado"):
            st.markdown(f"Unitário: {cf['valor_unitario_estimado']}")
        st.markdown(f"**Total: {cf.get('valor_total_estimado','—')}**")

        st.markdown(f"**PRAZO DE ENTREGA:** {cf.get('prazo_entrega_dias','—')} dias corridos")
        if cf.get("local_entrega"):
            st.markdown(f"**LOCAL:** {cf['local_entrega']}")
        st.markdown(f"**PAGAMENTO:** {cf.get('condicoes_pagamento','—')}")

    st.divider()

    # ── Downloads ─────────────────────────────────────────────────────────
    st.subheader("Baixar documentos")

    slug = num.replace("/", "-")

    # Zip com os dois arquivos
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"TR_Fornecimento_{slug}.docx",   pacote["tr"])
        zf.writestr(f"Aviso_Contratacao_{slug}.docx", pacote["aviso"])
    zip_buf.seek(0)

    col_zip, col_tr, col_av, _ = st.columns([1.2, 1, 1, 1.5])

    with col_zip:
        st.download_button(
            label="⬇️ Baixar tudo (.zip)",
            data=zip_buf.getvalue(),
            file_name=f"edital_{slug}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

    with col_tr:
        st.download_button(
            label="📄 TR Fornecimento",
            data=pacote["tr"],
            file_name=f"TR_Fornecimento_{slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    with col_av:
        st.download_button(
            label="📋 Aviso Contratação",
            data=pacote["aviso"],
            file_name=f"Aviso_Contratacao_{slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    st.divider()

    col_novo, _ = st.columns([1, 4])
    with col_novo:
        if st.button("📝 Novo edital", use_container_width=True):
            reset()

    # Campos completos (expansível para debug)
    with st.expander("Ver todos os campos utilizados"):
        st.json(cf)
