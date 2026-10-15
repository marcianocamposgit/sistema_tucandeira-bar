"""Tela de caixa: abertura, suprimento, sangria e fechamento com conferência.

- Qualquer usuário abre o caixa e lança suprimento.
- Sangria e fechamento pedem a autorização do gerente na hora.
- Fechamento em dois passos: digitar o valor contado de cada forma, ver a
  conferência (esperado x contado x diferença) e confirmar com o PIN do gerente.
- O cabeçalho de todas as telas mostra se o caixa está aberto ou fechado, e
  qualquer rota que esbarrar em CaixaFechadoError mostra o aviso com o botão
  para abrir o caixa.
"""
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

import config
from models import ResultadoFechamento
from routes.conexao import obter_conexao
from routes.seguranca import autorizacao_do_formulario, login_obrigatorio
from services import caixa, usuarios
from services.erros import (
    CaixaFechadoError,
    CaixaJaAbertoError,
    ComandasAbertasError,
    ErroDeNegocio,
    NaoEncontradoError,
)
from services.formatacao import formatar_moeda, ler_moeda, valor_para_campo

bp = Blueprint("caixa", __name__, url_prefix="/caixa")

FORMAS = config.FORMAS_PAGAMENTO

ATALHOS_MOTIVO = {
    "suprimento": ["Reforço de troco", "Troco do dono"],
    "sangria": ["Depósito no banco", "Pagamento de fornecedor", "Compra de gelo", "Retirada do dono"],
}


def _nome_usuario(usuario_id):
    if usuario_id is None:
        return ""
    try:
        return usuarios.obter(obter_conexao(), usuario_id).nome
    except NaoEncontradoError:
        return "?"


# ============================================================
# CABEÇALHO E AVISO DE CAIXA FECHADO (valem para todas as telas)
# ============================================================
@bp.app_context_processor
def variaveis_do_caixa():
    def caixa_atual():
        return caixa.caixa_aberto(obter_conexao())
    return {"caixa_atual": caixa_atual}


@bp.app_errorhandler(CaixaFechadoError)
def caixa_fechado(erro):
    if request.is_json or request.accept_mimetypes.best == "application/json":
        return jsonify(erro=str(erro), caixa_fechado=True), 409
    return render_template("caixa/fechado.html", mensagem=str(erro)), 409


# ============================================================
# PAINEL
# ============================================================
@bp.route("/")
@login_obrigatorio
def painel():
    conexao = obter_conexao()
    atual = caixa.caixa_aberto(conexao)
    if atual is None:
        return render_template("caixa/abrir.html", fundo="", ultimo=caixa.ultimo_fechado(conexao))
    return render_template(
        "caixa/painel.html",
        caixa=atual,
        aberto_por=_nome_usuario(atual.aberto_por),
        esperado=caixa.calcular_esperado(conexao, atual.id),
        movimentos=caixa.listar_movimentos(conexao, atual.id),
        formas=FORMAS,
        a_receber=caixa.comandas_pendentes(conexao, atual.id),
    )


@bp.route("/abrir", methods=["POST"])
@login_obrigatorio
def abrir():
    fundo = request.form.get("fundo", "")
    conexao = obter_conexao()
    try:
        aberto = caixa.abrir(conexao, ler_moeda(fundo, "o fundo de troco"), g.usuario.id)
    except CaixaJaAbertoError as erro:
        flash(str(erro), "aviso")  # outro aparelho abriu agora há pouco
        return redirect(url_for("caixa.painel"))
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return render_template("caixa/abrir.html", fundo=fundo, ultimo=caixa.ultimo_fechado(conexao))
    flash(f"Caixa aberto com fundo de troco de {formatar_moeda(aberto.valor_inicial_centavos)}.", "sucesso")
    return redirect(url_for("caixa.painel"))


# ============================================================
# SUPRIMENTO E SANGRIA
# ============================================================
MENSAGEM_REGISTRADO = {"suprimento": "Suprimento de {} registrado.", "sangria": "Sangria de {} registrada."}


@bp.route("/<any(suprimento, sangria):tipo>", methods=["GET", "POST"])
@login_obrigatorio
def movimento(tipo):
    """Suprimento: um passo. Sangria: confere valor e motivo e só então pede o PIN do gerente."""
    conexao = obter_conexao()
    atual = caixa.exigir_caixa_aberto(conexao)
    dados = {"valor": "", "motivo": ""}
    acao = request.form.get("acao", "")
    if request.method == "POST" and acao != "corrigir":
        # O valor volta formatado ("500" → "500,00") se a tela for mostrada de novo.
        dados = {"valor": valor_para_campo(request.form.get("valor", "")), "motivo": request.form.get("motivo", "")}
        valor = None
        try:
            valor = ler_moeda(dados["valor"], "o valor")
            if tipo == "suprimento":
                caixa.registrar_suprimento(conexao, valor, dados["motivo"], g.usuario.id)
            elif acao == "confirmar":
                autorizacao = autorizacao_do_formulario()
                caixa.registrar_sangria(conexao, valor, dados["motivo"], g.usuario.id, autorizacao)
            else:
                # Passo 1: valor e motivo conferidos antes de chamar o gerente.
                caixa.validar_sangria(conexao, valor, dados["motivo"])
                return render_template("caixa/sangria_confirmar.html", dados=dados, valor=valor)
        except CaixaFechadoError:
            raise
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
            if acao == "confirmar" and valor is not None:
                # PIN errado ou o caixa mudou: continua na confirmação, com "Corrigir".
                return render_template("caixa/sangria_confirmar.html", dados=dados, valor=valor)
        else:
            flash(MENSAGEM_REGISTRADO[tipo].format(formatar_moeda(valor)), "sucesso")
            return redirect(url_for("caixa.painel"))
    elif acao == "corrigir":
        dados = {"valor": valor_para_campo(request.form.get("valor", "")), "motivo": request.form.get("motivo", "")}
    return render_template(
        "caixa/movimento.html",
        tipo=tipo,
        dados=dados,
        atalhos=ATALHOS_MOTIVO[tipo],
        dinheiro_em_caixa=caixa.calcular_esperado(conexao, atual.id)["dinheiro"],
    )


# ============================================================
# FECHAMENTO
# ============================================================
def _contado_do_formulario():
    """Lê o valor contado de cada forma. Devolve (textos digitados, centavos)."""
    textos = {forma: request.form.get(f"contado_{forma}", "") for forma in FORMAS}
    centavos = {forma: ler_moeda(textos[forma], f"o valor contado em {nome}")
                for forma, nome in FORMAS.items()}
    return textos, centavos


def _tela_contagem(atual, textos, pendentes=None):
    if pendentes is None:
        pendentes = caixa.comandas_pendentes(obter_conexao(), atual.id)
    return render_template("caixa/fechar.html", caixa=atual, formas=FORMAS, textos=textos,
                           pendentes=pendentes)


@bp.route("/fechar", methods=["GET", "POST"])
@login_obrigatorio
def fechar():
    conexao = obter_conexao()
    atual = caixa.exigir_caixa_aberto(conexao)
    if request.method == "GET" or request.form.get("acao") == "corrigir":
        textos = {forma: request.form.get(f"contado_{forma}", "") for forma in FORMAS}
        return _tela_contagem(atual, textos)

    try:
        textos, contado = _contado_do_formulario()
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return _tela_contagem(atual, {forma: request.form.get(f"contado_{forma}", "") for forma in FORMAS})

    observacao = request.form.get("observacao", "")
    if request.form.get("acao") == "confirmar":
        try:
            autorizacao = autorizacao_do_formulario()
            caixa.fechar(conexao, contado, g.usuario.id, autorizacao, observacao=observacao)
        except ComandasAbertasError as erro:
            flash(str(erro), "erro")
            return _tela_contagem(atual, textos, erro.comandas)
        except CaixaFechadoError:
            raise
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash("Caixa fechado.", "sucesso")
            return redirect(url_for("caixa.resumo", caixa_id=atual.id))

    # Passo 2: mostra a conferência para o gerente confirmar.
    return render_template(
        "caixa/conferencia.html",
        caixa=atual,
        formas=FORMAS,
        textos=textos,
        previa=ResultadoFechamento(atual, caixa.conferencia(conexao, contado)),
        pendentes=caixa.comandas_pendentes(conexao, atual.id),
        observacao=observacao,
    )


@bp.route("/<int:caixa_id>")
@login_obrigatorio
def resumo(caixa_id):
    conexao = obter_conexao()
    try:
        resultado = caixa.resumo_fechamento(conexao, caixa_id)
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return redirect(url_for("caixa.painel"))
    return render_template(
        "caixa/resumo.html",
        resultado=resultado,
        aberto_por=_nome_usuario(resultado.caixa.aberto_por),
        fechado_por=_nome_usuario(resultado.caixa.fechado_por),
        movimentos=caixa.listar_movimentos(conexao, caixa_id),
        formas=FORMAS,
    )
