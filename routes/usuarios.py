"""Tela de usuários: listar, cadastrar, editar, trocar PIN, desativar e reativar.

- Gerente logado vê a tela direto; operador precisa da autorização de um
  gerente para abrir (vale por config.ACESSO_TELA_USUARIOS_MINUTOS).
- Cada alteração pede a autorização do gerente na hora (mesmo com gerente logado).
"""
import time
from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

import config
from models.usuarios import PERFIS
from routes.conexao import obter_conexao
from routes.seguranca import autorizacao_do_formulario, login_obrigatorio
from services import usuarios
from services.erros import ErroDeNegocio, NaoEncontradoError

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


def _pode_ver_tela():
    if g.usuario.gerente:
        return True
    return session.get("acesso_usuarios_ate", 0) > time.time()


def tela_de_gerente(rota):
    @wraps(rota)
    def protegida(*args, **kwargs):
        if not _pode_ver_tela():
            return render_template("usuarios/acesso.html")
        return rota(*args, **kwargs)
    return protegida


@bp.route("/acesso", methods=["POST"])
@login_obrigatorio
def acesso():
    """Operador abre a tela de usuários com a autorização de um gerente."""
    try:
        autorizacao_do_formulario()
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return render_template("usuarios/acesso.html")
    session["acesso_usuarios_ate"] = time.time() + config.ACESSO_TELA_USUARIOS_MINUTOS * 60
    return redirect(url_for("usuarios.lista"))


@bp.route("/")
@login_obrigatorio
@tela_de_gerente
def lista():
    return render_template("usuarios/lista.html", lista=usuarios.listar_todos(obter_conexao()))


def _obter_ou_voltar(usuario_id):
    try:
        return usuarios.obter(obter_conexao(), usuario_id)
    except NaoEncontradoError as erro:
        flash(str(erro), "erro")
        return None


@bp.route("/novo", methods=["GET", "POST"])
@login_obrigatorio
@tela_de_gerente
def novo():
    dados = {"nome": "", "perfil": "operador"}
    if request.method == "POST":
        dados = {"nome": request.form.get("nome", ""), "perfil": request.form.get("perfil", "")}
        pin = request.form.get("pin", "")
        if pin != request.form.get("pin_confirmacao", ""):
            flash("Os dois PINs não são iguais. Digite de novo.", "erro")
        else:
            try:
                autorizacao = autorizacao_do_formulario()
                criado = usuarios.cadastrar(obter_conexao(), dados["nome"], pin, dados["perfil"],
                                            g.usuario.id, autorizacao)
            except ErroDeNegocio as erro:
                flash(str(erro), "erro")
            else:
                flash(f"{criado.nome} cadastrado como {criado.perfil_nome}.", "sucesso")
                return redirect(url_for("usuarios.lista"))
    return render_template("usuarios/form.html", dados=dados, perfis=PERFIS, editando=None)


@bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
@tela_de_gerente
def editar(usuario_id):
    alvo = _obter_ou_voltar(usuario_id)
    if alvo is None:
        return redirect(url_for("usuarios.lista"))
    dados = {"nome": alvo.nome, "perfil": alvo.perfil}
    if request.method == "POST":
        dados = {"nome": request.form.get("nome", ""), "perfil": request.form.get("perfil", "")}
        try:
            autorizacao = autorizacao_do_formulario()
            usuarios.editar(obter_conexao(), usuario_id, dados["nome"], dados["perfil"], g.usuario.id, autorizacao)
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash("Usuário alterado.", "sucesso")
            return redirect(url_for("usuarios.lista"))
    return render_template("usuarios/form.html", dados=dados, perfis=PERFIS, editando=alvo)


@bp.route("/<int:usuario_id>/pin", methods=["GET", "POST"])
@login_obrigatorio
@tela_de_gerente
def trocar_pin(usuario_id):
    alvo = _obter_ou_voltar(usuario_id)
    if alvo is None:
        return redirect(url_for("usuarios.lista"))
    if request.method == "POST":
        pin = request.form.get("pin", "")
        if pin != request.form.get("pin_confirmacao", ""):
            flash("Os dois PINs não são iguais. Digite de novo.", "erro")
        else:
            try:
                autorizacao = autorizacao_do_formulario()
                usuarios.trocar_pin(obter_conexao(), usuario_id, pin, g.usuario.id, autorizacao=autorizacao)
            except ErroDeNegocio as erro:
                flash(str(erro), "erro")
            else:
                flash(f"PIN de {alvo.nome} alterado.", "sucesso")
                return redirect(url_for("usuarios.lista"))
    return render_template("usuarios/pin.html", alvo=alvo)


@bp.route("/<int:usuario_id>/<acao>", methods=["POST"])
@login_obrigatorio
@tela_de_gerente
def ativar_desativar(usuario_id, acao):
    if acao not in ("desativar", "reativar"):
        return redirect(url_for("usuarios.lista"))
    funcao = usuarios.desativar if acao == "desativar" else usuarios.reativar
    try:
        autorizacao = autorizacao_do_formulario()
        alvo = funcao(obter_conexao(), usuario_id, g.usuario.id, autorizacao)
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
    else:
        flash(f"{alvo.nome} {'desativado' if acao == 'desativar' else 'reativado'}.", "sucesso")
    return redirect(url_for("usuarios.lista"))
