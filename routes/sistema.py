"""Tela "Sobre": versão, endereços para os tablets, pasta de dados e backup.

- Qualquer usuário logado vê a tela.
- "Fazer backup agora" é só para o gerente logado.
"""
from flask import Blueprint, current_app, flash, g, redirect, render_template, url_for

import config
from routes.seguranca import login_obrigatorio
from services import backup
from services.formatacao import plural
from services.rede import enderecos_para_tablets

bp = Blueprint("sistema", __name__)

NOMES_AMBIENTE = {"producao": "Produção (bar)", "desenvolvimento": "Desenvolvimento"}


def _pasta_backups():
    return current_app.config["PASTA_DADOS"] / config.NOME_PASTA_BACKUPS


@bp.route("/sobre")
@login_obrigatorio
def sobre():
    ultimo = backup.ultimo_backup(_pasta_backups())
    return render_template(
        "sobre.html",
        versao=config.VERSAO,
        enderecos=enderecos_para_tablets(config.PORTA),
        porta=config.PORTA,
        pasta_dados=current_app.config["PASTA_DADOS"],
        ambiente=NOMES_AMBIENTE.get(current_app.config["AMBIENTE"], current_app.config["AMBIENTE"]),
        ultimo_backup=ultimo[0].strftime("%d/%m/%Y %H:%M") if ultimo else None,
        backups_texto=plural(len(backup.listar_backups(_pasta_backups())), "backup guardado", "backups guardados"),
        backups_mantidos=config.BACKUPS_MANTIDOS,
    )


@bp.route("/backup", methods=["POST"])
@login_obrigatorio
def fazer_backup():
    if not g.usuario.gerente:
        flash("Só o gerente pode fazer o backup pela tela.", "erro")
        return redirect(url_for("sistema.sobre"))
    feito = backup.fazer_backup(current_app.config["CAMINHO_BANCO"], _pasta_backups(),
                                manter=config.BACKUPS_MANTIDOS)
    current_app.logger.info("Backup feito pela tela por %s: %s", g.usuario.nome, feito)
    flash(f"Backup feito: {feito.name}", "sucesso")
    return redirect(url_for("sistema.sobre"))
