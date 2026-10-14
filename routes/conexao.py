"""Uma conexão com o banco por requisição, guardada no `g` do Flask."""
from flask import current_app, g

from database import conectar


def obter_conexao():
    """Conexão da requisição atual (aberta na primeira chamada)."""
    if "conexao" not in g:
        g.conexao = conectar(current_app.config["CAMINHO_BANCO"])
    return g.conexao


def fechar_conexao(_erro=None):
    conexao = g.pop("conexao", None)
    if conexao is not None:
        conexao.close()


def registrar(app):
    app.teardown_appcontext(fechar_conexao)
