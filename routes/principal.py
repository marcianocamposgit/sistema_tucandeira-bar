"""Página inicial (menu)."""
from flask import Blueprint, render_template

import config
from routes.seguranca import login_obrigatorio

bp = Blueprint("principal", __name__)


@bp.route("/")
@login_obrigatorio
def inicio():
    return render_template("inicio.html", versao=config.VERSAO)
