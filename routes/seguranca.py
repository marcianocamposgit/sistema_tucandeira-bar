"""Sessão, expiração por inatividade, CSRF e autorização de gerente nas rotas."""
import hmac
import secrets
import time
from functools import wraps

from flask import abort, flash, g, jsonify, redirect, request, session, url_for

import config
from models import AutorizacaoGerente
from routes.conexao import obter_conexao
from services import usuarios
from services.erros import NaoEncontradoError, PermissaoNegadaError
from services.formatacao import plural
from services.tentativas import ControleTentativas

tentativas = ControleTentativas(config.TENTATIVAS_PIN, config.BLOQUEIO_PIN_SEGUNDOS)

# Requisições de atualização automática (ex.: tela de mesas) não renovam a sessão.
CABECALHO_AUTOMATICO = "X-Atualizacao-Automatica"


# ============================================================
# SESSÃO
# ============================================================
def entrar(usuario):
    session.clear()
    session.permanent = True
    session["usuario_id"] = usuario.id
    session["ultimo_acesso"] = time.time()
    session["csrf"] = secrets.token_hex(16)


def sair():
    session.clear()


def _carregar_usuario():
    """Coloca o usuário logado em g.usuario (ou None), aplicando a expiração."""
    g.usuario = None
    usuario_id = session.get("usuario_id")
    if usuario_id is None:
        return
    agora = time.time()
    if agora - session.get("ultimo_acesso", 0) > config.TEMPO_SESSAO_MINUTOS * 60:
        sair()
        g.sessao_expirada = True
        return
    try:
        usuario = usuarios.obter(obter_conexao(), usuario_id)
    except NaoEncontradoError:
        usuario = None
    if usuario is None or not usuario.ativo:
        sair()
        return
    g.usuario = usuario
    if not request.headers.get(CABECALHO_AUTOMATICO):
        session["ultimo_acesso"] = agora


def requisicao_do_javascript():
    """Pedido feito pelo JavaScript da tela (XMLHttpRequest), que espera JSON."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def login_obrigatorio(rota):
    @wraps(rota)
    def protegida(*args, **kwargs):
        if g.get("usuario") is None:
            if g.get("sessao_expirada"):
                flash("Sua sessão expirou por inatividade. Entre de novo.", "aviso")
            if requisicao_do_javascript():
                # O JavaScript recarrega a página, que mostra o login.
                return jsonify(erro="Sua sessão expirou. Entre de novo.", sessao_expirada=True), 401
            return redirect(url_for("auth.login"))
        return rota(*args, **kwargs)
    return protegida


# ============================================================
# CSRF
# ============================================================
def token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def _conferir_csrf():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    enviado = request.form.get("csrf") or request.headers.get("X-CSRF-Token") or ""
    esperado = session.get("csrf") or ""
    if not esperado or not hmac.compare_digest(enviado, esperado):
        abort(400, "Formulário expirado. Volte e tente de novo.")


# ============================================================
# TENTATIVAS DE PIN
# ============================================================
def chaves_tentativa(usuario_id):
    return [("usuario", usuario_id), ("aparelho", request.remote_addr or "?")]


def mensagem_bloqueio(segundos):
    return f"Muitas tentativas erradas. Aguarde {plural(segundos, "segundo", "segundos")} e tente de novo."


# ============================================================
# AUTORIZAÇÃO DE GERENTE (formulários com data-exige-gerente)
# ============================================================
def autorizacao_do_formulario():
    """Lê gerente_id + pin_gerente do formulário e confere (com limite de tentativas).

    Devolve a AutorizacaoGerente já conferida, para passar ao service.
    Lança PermissaoNegadaError (mensagem pronta) se faltar, estiver bloqueada ou errada.
    """
    try:
        gerente_id = int(request.form.get("gerente_id", ""))
    except ValueError:
        raise PermissaoNegadaError() from None
    pin = request.form.get("pin_gerente", "")
    chaves = chaves_tentativa(gerente_id)
    segundos = tentativas.segundos_bloqueado(chaves)
    if segundos:
        raise PermissaoNegadaError(mensagem_bloqueio(segundos))
    autorizacao = AutorizacaoGerente(gerente_id, pin)
    try:
        usuarios.verificar_gerente(obter_conexao(), autorizacao)
    except PermissaoNegadaError:
        tentativas.registrar_erro(chaves)
        raise
    tentativas.registrar_acerto(chaves)
    return autorizacao


# ============================================================
# REGISTRO NO APP
# ============================================================
def registrar(app):
    @app.before_request
    def antes_de_cada_requisicao():
        if request.endpoint == "static":
            return
        _carregar_usuario()
        _conferir_csrf()

    @app.context_processor
    def variaveis_dos_templates():
        def gerentes_para_autorizacao():
            return usuarios.listar_gerentes(obter_conexao())
        return {
            "usuario": g.get("usuario"),
            "csrf_token": token_csrf,
            "gerentes_para_autorizacao": gerentes_para_autorizacao,
            "TEMPO_SESSAO_MINUTOS": config.TEMPO_SESSAO_MINUTOS,
        }
