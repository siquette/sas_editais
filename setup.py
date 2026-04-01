"""
setup.py — Configuração do ambiente para o Gerador de Editais

Uso:
    python setup.py

O script faz tudo automaticamente:
  1. Verifica a versão do Python (mínimo 3.10)
  2. Cria o ambiente virtual em .venv
  3. Instala todas as dependências
  4. Cria o .env a partir do .env.example
  5. Verifica a estrutura de pastas
  6. Mostra as instruções para rodar o app

Compatível com Linux, macOS e Windows.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

# ── Cores para o terminal (funciona em todos os SOs modernos) ─────────────

VERDE  = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL   = "\033[94m"
RESET  = "\033[0m"
NEGRITO = "\033[1m"

def ok(msg):    print(f"  {VERDE}✓{RESET} {msg}")
def info(msg):  print(f"  {AZUL}→{RESET} {msg}")
def aviso(msg): print(f"  {AMARELO}⚠{RESET}  {msg}")
def erro(msg):  print(f"  {VERMELHO}✗{RESET} {msg}")
def titulo(msg): print(f"\n{NEGRITO}{msg}{RESET}")


# ── Diretório raiz do projeto ─────────────────────────────────────────────

ROOT = Path(__file__).parent.resolve()
VENV = ROOT / ".venv"


# ══════════════════════════════════════════════════════════════════════════
# PASSO 1 — Verificar Python
# ══════════════════════════════════════════════════════════════════════════

def verificar_python():
    titulo("Passo 1 — Verificando Python")
    versao = sys.version_info
    info(f"Python encontrado: {versao.major}.{versao.minor}.{versao.micro}")

    if versao < (3, 10):
        erro(f"Python 3.10+ é necessário. Versão atual: {versao.major}.{versao.minor}")
        erro("Instale Python 3.10 ou superior em: https://python.org/downloads")
        sys.exit(1)

    ok(f"Python {versao.major}.{versao.minor} — compatível")


# ══════════════════════════════════════════════════════════════════════════
# PASSO 2 — Criar ambiente virtual
# ══════════════════════════════════════════════════════════════════════════

def criar_venv():
    titulo("Passo 2 — Ambiente virtual")

    if VENV.exists():
        aviso(".venv já existe — pulando criação")
        ok("Usando ambiente virtual existente")
        return

    info("Criando .venv...")
    resultado = subprocess.run(
        [sys.executable, "-m", "venv", str(VENV)],
        capture_output=True, text=True
    )
    if resultado.returncode != 0:
        erro("Falha ao criar o ambiente virtual:")
        print(resultado.stderr)
        sys.exit(1)

    ok(".venv criado com sucesso")


# ══════════════════════════════════════════════════════════════════════════
# PASSO 3 — Instalar dependências
# ══════════════════════════════════════════════════════════════════════════

def python_venv() -> str:
    """Retorna o caminho do Python dentro do .venv."""
    if sys.platform == "win32":
        return str(VENV / "Scripts" / "python.exe")
    return str(VENV / "bin" / "python")


def pip_venv() -> str:
    """Retorna o caminho do pip dentro do .venv."""
    if sys.platform == "win32":
        return str(VENV / "Scripts" / "pip.exe")
    return str(VENV / "bin" / "pip")


def instalar_dependencias():
    titulo("Passo 3 — Instalando dependências")

    req = ROOT / "requirements.txt"
    if not req.exists():
        erro("requirements.txt não encontrado.")
        sys.exit(1)

    info("Atualizando pip...")
    subprocess.run(
        [python_venv(), "-m", "pip", "install", "--upgrade", "pip"],
        capture_output=True
    )

    info("Instalando pacotes (pode levar alguns minutos)...")
    resultado = subprocess.run(
        [pip_venv(), "install", "-r", str(req)],
        capture_output=True, text=True
    )

    if resultado.returncode != 0:
        erro("Falha ao instalar dependências:")
        print(resultado.stderr[-2000:])  # últimas 2000 chars do erro
        sys.exit(1)

    # Lista os pacotes instalados para confirmar
    pacotes_req = [
        line.split("==")[0].split(">=")[0].strip()
        for line in req.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    for pacote in pacotes_req:
        ok(pacote)


# ══════════════════════════════════════════════════════════════════════════
# PASSO 4 — Configurar .env
# ══════════════════════════════════════════════════════════════════════════

def configurar_env():
    titulo("Passo 4 — Arquivo de configuração (.env)")

    env_file    = ROOT / ".env"
    env_example = ROOT / ".env.example"

    if not env_example.exists():
        aviso(".env.example não encontrado — pulando")
        return

    if env_file.exists():
        aviso(".env já existe — não será sobrescrito")
        ok("Arquivo .env mantido")
        return

    shutil.copy(env_example, env_file)
    ok(".env criado a partir do .env.example")
    aviso("IMPORTANTE: Abra o .env e preencha os valores obrigatórios:")
    print()
    print(f"    {AMARELO}GEMINI_API_KEY{RESET} = sua chave da API do Google Gemini")
    print(f"    {AMARELO}APP_PASSWORD{RESET}   = senha para acessar o app")
    print(f"    {AMARELO}INSTITUICAO_NOME{RESET} = nome da sua instituição")
    print()
    print(f"  Obtenha a chave Gemini em: {AZUL}https://aistudio.google.com/apikey{RESET}")


# ══════════════════════════════════════════════════════════════════════════
# PASSO 5 — Verificar estrutura de pastas
# ══════════════════════════════════════════════════════════════════════════

def verificar_estrutura():
    titulo("Passo 5 — Verificando estrutura do projeto")

    arquivos_obrigatorios = [
        "app.py",
        "config.py",
        "requirements.txt",
        "core/__init__.py",
        "core/reader.py",
        "core/extractor.py",
        "core/validator.py",
        "core/generator.py",
        "templates/__init__.py",
        "templates/criar_templates.py",
    ]

    tudo_ok = True
    for arquivo in arquivos_obrigatorios:
        caminho = ROOT / arquivo
        if caminho.exists():
            ok(arquivo)
        else:
            erro(f"Não encontrado: {arquivo}")
            tudo_ok = False

    if not tudo_ok:
        erro("Estrutura incompleta. Verifique se todos os arquivos foram baixados.")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════
# PASSO 6 — Gerar templates
# ══════════════════════════════════════════════════════════════════════════

def gerar_templates():
    titulo("Passo 6 — Gerando templates de edital")

    script_templates = ROOT / "templates" / "criar_templates.py"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    resultado = subprocess.run(
        [python_venv(), str(script_templates)],
        capture_output=True, text=True,
        cwd=str(ROOT), env=env
    )

    if resultado.returncode != 0:
        aviso("Não foi possível gerar os templates agora:")
        print(f"    {resultado.stderr[:500]}")
        aviso("Os templates serão gerados automaticamente na primeira execução do app.")
    else:
        for linha in resultado.stdout.strip().splitlines():
            if linha.strip():
                ok(linha.strip().lstrip("✓").strip())


# ══════════════════════════════════════════════════════════════════════════
# RESUMO FINAL
# ══════════════════════════════════════════════════════════════════════════

def instrucoes_finais():
    titulo("✅  Setup concluído!")
    print()

    # Comando para ativar o venv
    if sys.platform == "win32":
        ativar = r".venv\Scripts\activate"
    else:
        ativar = "source .venv/bin/activate"

    print(f"{NEGRITO}Para rodar o app:{RESET}")
    print()
    print(f"  1. Ative o ambiente virtual:")
    print(f"     {VERDE}{ativar}{RESET}")
    print()
    print(f"  2. Configure o .env com sua chave de API:")
    print(f"     {VERDE}nano .env{RESET}   (Linux/Mac)")
    print(f"     {VERDE}notepad .env{RESET}  (Windows)")
    print()
    print(f"  3. Inicie o app:")
    print(f"     {VERDE}streamlit run app.py{RESET}")
    print()
    print(f"{NEGRITO}Para o Streamlit Cloud:{RESET}")
    print(f"  Configure as variáveis do .env em Settings → Secrets no painel.")
    print(f"  Documentação: {AZUL}https://docs.streamlit.io/deploy/streamlit-community-cloud{RESET}")
    print()


# ══════════════════════════════════════════════════════════════════════════
# EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{NEGRITO}{'═' * 50}")
    print("  Gerador de Editais — Setup do Ambiente")
    print(f"{'═' * 50}{RESET}")

    verificar_python()
    criar_venv()
    instalar_dependencias()
    configurar_env()
    verificar_estrutura()
    gerar_templates()
    instrucoes_finais()
