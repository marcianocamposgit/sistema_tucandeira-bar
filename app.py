"""Aplicação Flask do Tucandeira Rock Bar.

Desenvolvimento:  python app.py      (servidor do Flask, com recarga automática)
No bar:           python servidor.py (waitress, acessível pela rede local)
"""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, render_template

import config
from database import ambiente_do_banco, conectar, migrar
from routes import auth, caixa, conexao, mesas, pagamentos, principal, seguranca, usuarios
from services.backup import fazer_backup
from services.formatacao import formatar_data_hora, formatar_moeda, plural


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


def carregar_secret_key(pasta_dados):
    """Chave que assina o cookie de sessão: gerada na primeira vez e guardada na pasta de dados."""
    arquivo = Path(pasta_dados) / config.NOME_ARQUIVO_SECRET_KEY
    if arquivo.exists():
        chave = arquivo.read_text(encoding="ascii").strip()
        if chave:
            return chave
    chave = secrets.token_hex(32)
    arquivo.write_text(chave, encoding="ascii")
    return chave


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
        SECRET_KEY=carregar_secret_key(pasta_dados),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=config.TEMPO_SESSAO_MINUTOS),
    )
    if configuracoes_extras:
        app.config.update(configuracoes_extras)

    app.add_template_filter(formatar_moeda, "moeda")
    app.add_template_filter(formatar_data_hora, "data_hora")
    app.add_template_filter(plural, "plural")
    app.jinja_env.globals.update(VERSAO=config.VERSAO)

    conexao.registrar(app)
    seguranca.registrar(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(principal.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(caixa.bp)
    app.register_blueprint(mesas.bp)
    app.register_blueprint(pagamentos.bp)

    @app.url_defaults
    def versao_dos_arquivos_estaticos(endpoint, valores):
        """Acrescenta ?v=<data do arquivo> aos endereços de static/ (CSS, JS, imagens).

        Depois de uma atualização do sistema, o tablet e o PC baixam o arquivo novo
        em vez de usar o antigo guardado no cache do navegador.
        Atenção (Etapa 9): o service worker precisa de endereço fixo, sem ?v=.
        """
        if endpoint == "static" and "filename" in valores and "v" not in valores:
            try:
                valores["v"] = int((Path(app.static_folder) / valores["filename"]).stat().st_mtime)
            except OSError:
                pass

    @app.errorhandler(400)
    def requisicao_invalida(erro):
        return render_template("erro.html", titulo="Não foi possível concluir",
                               mensagem=getattr(erro, "description", None)), 400

    @app.errorhandler(404)
    def nao_encontrado(_erro):
        return render_template("erro.html", titulo="Página não encontrada",
                               mensagem="O endereço digitado não existe."), 404

    @app.errorhandler(500)
    def erro_interno(_erro):
        return render_template("erro.html", titulo="Algo deu errado",
                               mensagem="Ocorreu um erro inesperado. Tente de novo."), 500

    return app


if __name__ == "__main__":
    # Com a recarga automática, o Flask roda este arquivo em dois processos.
    # O backup é feito só no primeiro (o que não tem WERKZEUG_RUN_MAIN).
    processo_recarregado = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    app = create_app(backup=not processo_recarregado)
    app.run(host="127.0.0.1", port=config.PORTA, debug=True)
