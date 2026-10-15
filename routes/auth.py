"""Primeiro acesso, login (nome + PIN) e troca de usuário."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from routes.conexao import obter_conexao
from routes.seguranca import (
    chaves_tentativa,
    entrar,
    login_obrigatorio,
    mensagem_bloqueio,
    sair,
    tentativas,
)
from services import usuarios
from services.erros import ErroDeNegocio, PinInvalidoError

bp = Blueprint("auth", __name__)


def _inteiro(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    conexao = obter_conexao()
    if not usuarios.existe_usuario(conexao):
        return redirect(url_for("auth.primeiro_acesso"))

    selecionado = None
    if request.method == "POST":
        usuario_id = _inteiro(request.form.get("usuario_id"))
        pin = request.form.get("pin", "")
        selecionado = usuario_id
        chaves = chaves_tentativa(usuario_id)
        segundos = tentativas.segundos_bloqueado(chaves)
        if segundos:
            flash(mensagem_bloqueio(segundos), "erro")
        else:
            try:
                usuario = usuarios.autenticar(conexao, usuario_id, pin)
            except PinInvalidoError as erro:
                tentativas.registrar_erro(chaves)
                flash(str(erro), "erro")
            else:
                tentativas.registrar_acerto(chaves)
                entrar(usuario)
                return redirect(url_for("principal.inicio"))

    return render_template("auth/login.html", usuarios_ativos=usuarios.listar_ativos(conexao),
                           selecionado=selecionado)


@bp.route("/primeiro-acesso", methods=["GET", "POST"])
def primeiro_acesso():
    """Só existe enquanto não há nenhum usuário: cria o gerente inicial."""
    conexao = obter_conexao()
    if usuarios.existe_usuario(conexao):
        return redirect(url_for("auth.login"))
    nome = ""
    if request.method == "POST":
        nome = request.form.get("nome", "")
        pin = request.form.get("pin", "")
        if pin != request.form.get("pin_confirmacao", ""):
            flash("Os dois PINs não são iguais. Digite de novo.", "erro")
        else:
            try:
                gerente = usuarios.criar_gerente_inicial(conexao, nome, pin)
            except ErroDeNegocio as erro:
                flash(str(erro), "erro")
            else:
                entrar(gerente)
                flash(f"Bem-vindo, {gerente.nome}! Você é o gerente do sistema.", "sucesso")
                return redirect(url_for("principal.inicio"))
    return render_template("auth/primeiro_acesso.html", nome=nome)


@bp.route("/sair", methods=["POST"])
def logout():
    sair()
    return redirect(url_for("auth.login"))


@bp.route("/meu-pin", methods=["GET", "POST"])
@login_obrigatorio
def meu_pin():
    if request.method == "POST":
        novo = request.form.get("pin", "")
        if novo != request.form.get("pin_confirmacao", ""):
            flash("Os dois PINs novos não são iguais. Digite de novo.", "erro")
        else:
            chaves = chaves_tentativa(g.usuario.id)
            segundos = tentativas.segundos_bloqueado(chaves)
            if segundos:
                flash(mensagem_bloqueio(segundos), "erro")
                return render_template("auth/meu_pin.html")
            try:
                usuarios.trocar_pin(obter_conexao(), g.usuario.id, novo, g.usuario.id,
                                    pin_atual=request.form.get("pin_atual", ""))
            except PinInvalidoError as erro:
                tentativas.registrar_erro(chaves)
                flash(str(erro), "erro")
            except ErroDeNegocio as erro:
                flash(str(erro), "erro")
            else:
                flash("PIN alterado.", "sucesso")
                return redirect(url_for("principal.inicio"))
    return render_template("auth/meu_pin.html")
