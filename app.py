"""Aplicação Flask do Tucandeira Rock Bar.

Desenvolvimento:  python app.py      (servidor do Flask, com recarga automática)
No bar:           python servidor.py (waitress, acessível pela rede local)
"""
import os
from pathlib import Path

from flask import Flask

import config
from database import ambiente_do_banco, conectar, migrar
from routes import conexao, principal
from services.backup import fazer_backup
from services.formatacao import formatar_moeda


def ambiente_para(pasta_dados):
    """'desenvolvimento' só rodando pelo código-fonte com a pasta data/ do projeto."""
    if not config.EXECUTAVEL and Path(pasta_dados).resolve() == config.PASTA_DADOS_DESENVOLVIMENTO.resolve():
        return "desenvolvimento"
    return "producao"


def preparar_dados(pasta_dados, ambiente=None, backup=True):
    """Prepara a pasta de dados ao iniciar o servidor.

    1. Cria a pasta, se não existir.
    2. Faz backup do banco existente (antes de qualquer migração).
    3. Cria ou migra o banco até a versão atual.
    Devolve (caminho_banco, caminho_backup ou None, ambiente do banco).
    """
    pasta_dados = Path(pasta_dados)
    pasta_dados.mkdir(parents=True, exist_ok=True)
    caminho_banco = pasta_dados / config.NOME_BANCO

    caminho_backup = None
    if backup:
        caminho_backup = fazer_backup(
            caminho_banco, pasta_dados / config.NOME_PASTA_BACKUPS, manter=config.BACKUPS_MANTIDOS
        )

    conexao_banco = conectar(caminho_banco)
    try:
        migrar(conexao_banco, ambiente or ambiente_para(pasta_dados))
        ambiente_atual = ambiente_do_banco(conexao_banco)
    finally:
        conexao_banco.close()
    return caminho_banco, caminho_backup, ambiente_atual


def create_app(pasta_dados=None, ambiente=None, backup=False, configuracoes_extras=None):
    """Cria o app. `backup=True` só ao iniciar o servidor de verdade."""
    pasta_dados = Path(pasta_dados or config.PASTA_DADOS)
    caminho_banco, _, ambiente_atual = preparar_dados(pasta_dados, ambiente, backup)

    app = Flask(
        __name__,
        template_folder=str(config.PASTA_TEMPLATES),
        static_folder=str(config.PASTA_STATIC),
    )
    app.config.update(
        PASTA_DADOS=pasta_dados,
        CAMINHO_BANCO=caminho_banco,
        AMBIENTE=ambiente_atual,
    )
    if configuracoes_extras:
        app.config.update(configuracoes_extras)

    app.add_template_filter(formatar_moeda, "moeda")
    app.jinja_env.globals.update(VERSAO=config.VERSAO)

    conexao.registrar(app)
    app.register_blueprint(principal.bp)
    return app


if __name__ == "__main__":
    # Com a recarga automática, o Flask roda este arquivo em dois processos.
    # O backup é feito só no primeiro (o que não tem WERKZEUG_RUN_MAIN).
    processo_recarregado = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    app = create_app(backup=not processo_recarregado)
    app.run(host="127.0.0.1", port=config.PORTA, debug=True)
