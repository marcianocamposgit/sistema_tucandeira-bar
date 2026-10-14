"""Página inicial."""
from flask import Blueprint, render_template

import config

bp = Blueprint("principal", __name__)


@bp.route("/")
def inicio():
    return render_template("inicio.html", versao=config.VERSAO)
