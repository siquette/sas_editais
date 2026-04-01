# Gerador de Editais — Lei 14.133/2021

Converte texto livre em Termo de Referência e Aviso de Contratação Direta
padronizados, baseados nos modelos pré-aprovados pela PGU-USP (Portaria PG nº 12/24).

## Fluxo

```
Texto livre ou .docx  →  Gemini (extração)  →  Revisão  →  TR + Aviso (.docx)
```

## Instalação local

```bash
git clone <seu-repo>
cd edital_agent

pip install -r requirements.txt

cp .env.example .env
# Edite .env e preencha GEMINI_API_KEY e APP_PASSWORD

streamlit run app.py
```

## Deploy no Streamlit Cloud

1. Suba o repositório no GitHub (o `.env` está no `.gitignore` — nunca sobe)
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte o repositório
3. Em **Settings → Secrets**, adicione:

```toml
GEMINI_API_KEY = "sua_chave_gemini"
APP_PASSWORD   = "senha_para_os_usuarios"

INSTITUICAO_NOME  = "Nome da sua instituição"
INSTITUICAO_SIGLA = "SIGLA"
INSTITUICAO_CNPJ  = "00.000.000/0000-00"
INSTITUICAO_SETOR = "Secretaria / Depto."
INSTITUICAO_CIDADE = "São Paulo - SP"
INSTITUICAO_FORO  = "comarca de São Paulo"
```

4. Clique em **Deploy** — os templates são gerados automaticamente na primeira execução.

## Estrutura

```
edital_agent/
├── app.py                  # Interface Streamlit
├── config.py               # Configurações (lê .env ou st.secrets)
├── core/
│   ├── reader.py           # Lê texto livre ou .docx
│   ├── extractor.py        # Gemini → JSON de campos
│   ├── validator.py        # Pydantic + auto-fill
│   └── generator.py        # Renderiza TR + Aviso (.docx)
├── templates/
│   └── criar_templates.py  # Gera os templates na 1ª execução
├── requirements.txt
├── .env.example
└── .gitignore
```

## Limites legais (Decreto 12.343/2024)

| Modalidade | Limite |
|---|---|
| Dispensa — Inciso II (bens/serviços) | até R$ 62.725,59 |
| Dispensa — Inciso I (engenharia) | até R$ 125.451,15 |
| Pregão Eletrônico | até R$ 1.000.000,00 |
| Concorrência | acima de R$ 1.000.000,00 |

Atualize `LIMITE_DISPENSA_INC_I` e `LIMITE_DISPENSA_INC_II` nos Secrets
quando sair novo decreto.

## Observação de privacidade

O texto do briefing é enviado à API do Gemini (Google Cloud) para extração.
Para dados sigilosos, considere rodar localmente (`streamlit run app.py`).
