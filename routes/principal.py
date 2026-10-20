"""Página inicial (menu) e arquivos do PWA servidos na raiz do site."""
from flask import Blueprint, current_app, render_template, send_from_directory

import config
from routes.seguranca import login_obrigatorio

bp = Blueprint("principal", __name__)


@bp.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(current_app.static_folder, "manifest.webmanifest",
                               mimetype="application/manifest+json", max_age=0)


@bp.route("/sw.js")
def service_worker():
    """Na raiz (e não em /static/) para o service worker valer para o site inteiro.
    Endereço fixo, sem ?v=, e sem cache: o navegador sempre confere se mudou."""
    resposta = send_from_directory(current_app.static_folder, "sw.js", mimetype="text/javascript", max_age=0)
    resposta.headers["Cache-Control"] = "no-cache"
    return resposta


@bp.route("/")
@login_obrigatorio
def inicio():
    return render_template("inicio.html", versao=config.VERSAO)
