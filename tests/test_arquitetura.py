"""Regras de arquitetura do CLAUDE.md, conferidas no código-fonte."""
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _importacoes(arquivo):
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    nomes = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
    return nomes


def _arquivos_do_sistema():
    pastas = ["models", "services", "routes", "scripts"]
    arquivos = [RAIZ / nome for nome in ("app.py", "servidor.py", "config.py", "database.py", "janela_servidor.py")]
    for pasta in pastas:
        arquivos += sorted((RAIZ / pasta).glob("*.py"))
    return arquivos


def test_services_nao_importam_flask():
    for arquivo in (RAIZ / "services").glob("*.py"):
        assert not any(nome.split(".")[0] == "flask" for nome in _importacoes(arquivo)), arquivo.name


def test_rotas_nao_acessam_o_banco_direto():
    for arquivo in (RAIZ / "routes").glob("*.py"):
        if arquivo.name == "conexao.py":  # abre e fecha a conexão da requisição
            continue
        texto = arquivo.read_text(encoding="utf-8")
        assert ".execute(" not in texto and "sqlite3" not in texto, arquivo.name


def test_nada_importa_o_legado_tkinter():
    for arquivo in _arquivos_do_sistema():
        assert not any(nome.startswith("legado_tkinter") for nome in _importacoes(arquivo)), arquivo.name
