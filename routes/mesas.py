"""Tela de mesas, balcão e comanda.

- Mesas: grade com as NUM_MESAS mesas (livre, ocupada, conta pedida), atualizada
  sozinha por /mesas/estado (JSON) a cada INTERVALO_ATUALIZACAO_MESAS segundos.
- Balcão / Para Viagem: comandas pelo nome do cliente.
- Comanda: cardápio e itens. Lançar, "+" e "−" vão pelo JavaScript (JSON, sem
  recarregar a página); a comanda também se atualiza sozinha por /estado.
  As ações menos frequentes (observação, pessoas, conta pedida, transferir,
  juntar, cancelar) são formulários comuns que voltam para a comanda.
- "−" remove sem PIN dentro do prazo; depois disso a tela abre o cancelamento
  (motivo + autorização do gerente).
"""
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for

import config
from routes.conexao import obter_conexao
from routes.seguranca import autorizacao_do_formulario, login_obrigatorio
from services import comandas, produtos
from services.erros import (
    CaixaFechadoError,
    ComandaFechadaError,
    DadosInvalidosError,
    ErroDeNegocio,
    MesaOcupadaError,
    NaoEncontradoError,
    PrazoRemocaoExpiradoError,
)
from services.formatacao import formatar_moeda, plural

bp = Blueprint("mesas", __name__)

ATALHOS_OBSERVACAO = ["sem gelo", "com gelo e limão", "bem gelada", "bem passado", "sem cebola", "para viagem"]
ATALHOS_CANCELAMENTO = ["Cliente desistiu", "Lançado errado", "Produto em falta", "Demorou demais"]
ATALHOS_CANCELAR_COMANDA = ["Cliente foi embora", "Comanda aberta por engano", "Lançado na mesa errada"]
PESSOAS_RAPIDAS = range(1, 9)

NOMES_STATUS = {"livre": "Livre", "ocupada": "Ocupada", "conta_pedida": "Conta pedida"}


def _para_comanda(comanda_id, aba="comanda"):
    return redirect(url_for("mesas.comanda", comanda_id=comanda_id, aba=aba))


def _voltar_da_comanda(comanda):
    """Endereço do "Voltar" da comanda: mesas ou lista do balcão."""
    return url_for("mesas.balcao") if comanda.tipo == "balcao" else url_for("mesas.mesas")


def _mensagem_comanda_fechada(comanda):
    if comanda.status == "paga":
        return f"{comanda.identificacao}: a conta já foi paga."
    if comanda.status == "cancelada":
        return f"{comanda.identificacao}: a comanda foi cancelada."
    return "Esta comanda foi juntada a outra mesa."


def _destino_comanda_fechada(comanda):
    """Para onde ir quando a comanda foi fechada (talvez em outro aparelho)."""
    if comanda.status == "unida" and comanda.unida_a:
        return url_for("mesas.comanda", comanda_id=comanda.unida_a)
    return _voltar_da_comanda(comanda)


# ============================================================
# MESAS
# ============================================================
def _mesa_json(estado):
    if estado.status == "livre":
        endereco = url_for("mesas.abrir_mesa", numero=estado.numero)
    else:
        endereco = url_for("mesas.comanda", comanda_id=estado.comanda_id)
    juntas = estado.mesas_juntas if len(estado.mesas_juntas) > 1 else []
    return {
        "numero": estado.numero,
        "status": estado.status,
        "status_nome": NOMES_STATUS[estado.status],
        "pessoas": estado.pessoas,
        "pessoas_texto": plural(estado.pessoas, "pessoa", "pessoas") if estado.status != "livre" else "",
        "total": formatar_moeda(estado.total_centavos) if estado.status != "livre" else "",
        "juntas": " + ".join(str(m) for m in juntas),
        "endereco": endereco,
    }


def _estado_da_tela_de_mesas(conexao):
    return {
        "mesas": [_mesa_json(e) for e in comandas.estado_mesas(conexao)],
        "balcao_abertas": len(comandas.listar_abertas(conexao, tipo="balcao")),
    }


@bp.route("/mesas")
@login_obrigatorio
def mesas():
    conexao = obter_conexao()
    return render_template("mesas/mesas.html", estado=_estado_da_tela_de_mesas(conexao),
                           intervalo=config.INTERVALO_ATUALIZACAO_MESAS)


@bp.route("/mesas/estado")
@login_obrigatorio
def estado_mesas():
    return jsonify(_estado_da_tela_de_mesas(obter_conexao()))


@bp.route("/mesas/<int:numero>/abrir", methods=["GET", "POST"])
@login_obrigatorio
def abrir_mesa(numero):
    conexao = obter_conexao()
    ocupada = comandas.comanda_da_mesa(conexao, numero) if 1 <= numero <= config.NUM_MESAS else None
    if ocupada:
        return _para_comanda(ocupada.id, aba="cardapio")  # outro aparelho abriu agora há pouco
    pessoas = ""
    if request.method == "POST":
        pessoas = request.form.get("pessoas", "").strip()
        try:
            aberta = comandas.abrir_mesa(conexao, numero, g.usuario.id,
                                         pessoas=request.form.get("pessoas", type=int))
        except MesaOcupadaError:
            ocupada = comandas.comanda_da_mesa(conexao, numero)
            if ocupada:
                return _para_comanda(ocupada.id, aba="cardapio")
            raise
        except CaixaFechadoError:
            raise
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            return _para_comanda(aberta.id, aba="cardapio")
    return render_template("mesas/abrir_mesa.html", numero=numero, pessoas=pessoas,
                           pessoas_rapidas=PESSOAS_RAPIDAS)


# ============================================================
# BALCÃO / PARA VIAGEM
# ============================================================
@bp.route("/balcao", methods=["GET", "POST"])
@login_obrigatorio
def balcao():
    conexao = obter_conexao()
    nome = ""
    if request.method == "POST":
        nome = request.form.get("nome_cliente", "")
        try:
            aberta = comandas.abrir_balcao(conexao, nome, g.usuario.id)
        except CaixaFechadoError:
            raise
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            return _para_comanda(aberta.id, aba="cardapio")
    return render_template("mesas/balcao.html", abertas=comandas.listar_abertas(conexao, tipo="balcao"),
                           nome=nome)


# ============================================================
# COMANDA
# ============================================================
def _estado_comanda(conexao, comanda_id):
    """O que a tela da comanda precisa para se redesenhar (JSON)."""
    resumo = comandas.obter_resumo(conexao, comanda_id)
    comanda, conta = resumo.comanda, resumo.conta
    if not comanda.editavel:
        return {"fechada": True, "erro": _mensagem_comanda_fechada(comanda),
                "ir_para": _destino_comanda_fechada(comanda)}
    grupos = comandas.agrupar_itens(resumo.itens)
    return {
        "fechada": False,
        "identificacao": comanda.identificacao,
        "status": comanda.status,
        "pessoas": comanda.pessoas,
        "pessoas_texto": plural(comanda.pessoas, "pessoa", "pessoas"),
        "quantidade_itens": resumo.quantidade_itens,
        "itens_texto": plural(resumo.quantidade_itens, "item", "itens"),
        "tem_itens": bool(grupos),
        "total": formatar_moeda(conta.total_centavos),
        "pago": formatar_moeda(conta.pago_centavos) if conta.pago_centavos else "",
        "saldo": formatar_moeda(conta.saldo_centavos),
        "itens_html": render_template("mesas/_itens.html", grupos=grupos),
    }


def _obter_comanda_ou_voltar(conexao, comanda_id):
    """A comanda aberta, ou (None, redirecionamento) se não existe ou já fechou."""
    try:
        comanda = comandas.obter_comanda(conexao, comanda_id)
    except NaoEncontradoError as erro:
        flash(str(erro), "erro")
        return None, redirect(url_for("mesas.mesas"))
    if not comanda.editavel:
        flash(_mensagem_comanda_fechada(comanda), "aviso")
        return None, redirect(_destino_comanda_fechada(comanda))
    return comanda, None


@bp.route("/comandas/<int:comanda_id>")
@login_obrigatorio
def comanda(comanda_id):
    conexao = obter_conexao()
    atual, voltar = _obter_comanda_ou_voltar(conexao, comanda_id)
    if atual is None:
        return voltar
    resumo = comandas.obter_resumo(conexao, comanda_id)
    estado = _estado_comanda(conexao, comanda_id)
    todas = comandas.estado_mesas(conexao)
    mesas_livres = [e.numero for e in todas if e.status == "livre"]
    outras_mesas = [e for e in todas if e.numero not in atual.mesas]
    return render_template(
        "mesas/comanda.html",
        comanda=atual,
        conta=resumo.conta,
        estado=estado,
        cardapio=produtos.cardapio(conexao),
        mesas_livres=mesas_livres,
        outras_mesas=outras_mesas,
        aba=request.args.get("aba", "cardapio"),
        voltar=_voltar_da_comanda(atual),
        intervalo=config.INTERVALO_ATUALIZACAO_MESAS,
        pessoas_rapidas=PESSOAS_RAPIDAS,
        atalhos_observacao=ATALHOS_OBSERVACAO,
        atalhos_cancelamento=ATALHOS_CANCELAMENTO,
        atalhos_cancelar_comanda=ATALHOS_CANCELAR_COMANDA,
        prazo_remocao=plural(config.PRAZO_REMOCAO_ITEM_MINUTOS, "minuto", "minutos"),
    )


@bp.route("/comandas/<int:comanda_id>/estado")
@login_obrigatorio
def estado_comanda(comanda_id):
    try:
        return jsonify(_estado_comanda(obter_conexao(), comanda_id))
    except NaoEncontradoError as erro:
        return jsonify(erro=str(erro), fechada=True, ir_para=url_for("mesas.mesas")), 404


def _resposta_json(conexao, comanda_id, aviso=None):
    resposta = _estado_comanda(conexao, comanda_id)
    resposta["aviso"] = aviso
    return jsonify(resposta)


def _erro_json(conexao, comanda_id, erro):
    """Erro de uma ação feita pelo JavaScript: mensagem pronta + estado atual da comanda."""
    if isinstance(erro, CaixaFechadoError):
        raise erro  # o tratamento do caixa fechado responde em JSON
    try:
        resposta = _estado_comanda(conexao, comanda_id)
    except NaoEncontradoError:
        resposta = {"fechada": True, "ir_para": url_for("mesas.mesas")}
    if resposta["fechada"]:
        resposta.setdefault("erro", str(erro))  # "a conta já foi paga", "foi cancelada"...
    else:
        resposta["erro"] = str(erro)
    return jsonify(resposta), 409


@bp.route("/comandas/<int:comanda_id>/lancar", methods=["POST"])
@login_obrigatorio
def lancar(comanda_id):
    conexao = obter_conexao()
    try:
        resultado = comandas.lancar_item(conexao, comanda_id, request.form.get("produto_id", type=int),
                                         g.usuario.id, chave=request.form.get("chave"))
    except ErroDeNegocio as erro:
        return _erro_json(conexao, comanda_id, erro)
    return _resposta_json(conexao, comanda_id, resultado.aviso_estoque)


@bp.route("/comandas/<int:comanda_id>/itens/<int:item_id>/mais", methods=["POST"])
@login_obrigatorio
def mais(comanda_id, item_id):
    conexao = obter_conexao()
    try:
        resultado = comandas.repetir_item(conexao, item_id, g.usuario.id, chave=request.form.get("chave"))
    except ErroDeNegocio as erro:
        return _erro_json(conexao, comanda_id, erro)
    return _resposta_json(conexao, comanda_id, resultado.aviso_estoque)


@bp.route("/comandas/<int:comanda_id>/itens/<int:item_id>/menos", methods=["POST"])
@login_obrigatorio
def menos(comanda_id, item_id):
    conexao = obter_conexao()
    try:
        comandas.remover_item(conexao, item_id, g.usuario.id)
    except PrazoRemocaoExpiradoError as erro:
        # Passou do prazo: a tela abre o cancelamento (motivo + gerente).
        resposta = _estado_comanda(conexao, comanda_id)
        resposta.update(precisa_cancelar=True, item_id=item_id, aviso=str(erro))
        return jsonify(resposta)
    except ErroDeNegocio as erro:
        return _erro_json(conexao, comanda_id, erro)
    return _resposta_json(conexao, comanda_id)


def _acao_de_formulario(comanda_id, funcao, sucesso):
    """Executa uma ação de formulário e volta para a comanda com a mensagem."""
    try:
        funcao()
    except CaixaFechadoError:
        raise
    except ComandaFechadaError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("mesas.mesas"))
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
    else:
        if sucesso:
            flash(sucesso, "sucesso")
    return _para_comanda(comanda_id)


@bp.route("/comandas/<int:comanda_id>/cancelar-item", methods=["POST"])
@login_obrigatorio
def cancelar_item(comanda_id):
    conexao = obter_conexao()

    def cancelar():
        autorizacao = autorizacao_do_formulario()
        comandas.cancelar_item(conexao, request.form.get("item_id", type=int), request.form.get("motivo", ""),
                               g.usuario.id, autorizacao)
    return _acao_de_formulario(comanda_id, cancelar, "Item cancelado.")


@bp.route("/comandas/<int:comanda_id>/observacao", methods=["POST"])
@login_obrigatorio
def observacao(comanda_id):
    conexao = obter_conexao()
    return _acao_de_formulario(
        comanda_id,
        lambda: comandas.alterar_observacao_grupo(conexao, request.form.get("item_id", type=int),
                                                  request.form.get("observacao", ""), g.usuario.id),
        "Observação salva.")


@bp.route("/comandas/<int:comanda_id>/pessoas", methods=["POST"])
@login_obrigatorio
def pessoas(comanda_id):
    conexao = obter_conexao()
    return _acao_de_formulario(
        comanda_id,
        lambda: comandas.alterar_pessoas(conexao, comanda_id, request.form.get("pessoas", type=int),
                                         g.usuario.id),
        "Número de pessoas alterado.")


@bp.route("/comandas/<int:comanda_id>/conta-pedida", methods=["POST"])
@login_obrigatorio
def conta_pedida(comanda_id):
    conexao = obter_conexao()
    pedida = request.form.get("pedida") == "1"
    return _acao_de_formulario(
        comanda_id,
        lambda: comandas.marcar_conta_pedida(conexao, comanda_id, g.usuario.id, pedida=pedida),
        "Conta pedida." if pedida else "A comanda voltou a ficar aberta.")


@bp.route("/comandas/<int:comanda_id>/transferir", methods=["POST"])
@login_obrigatorio
def transferir(comanda_id):
    conexao = obter_conexao()
    origem = request.form.get("origem", type=int)
    destino = request.form.get("destino", type=int)
    return _acao_de_formulario(
        comanda_id,
        lambda: comandas.transferir_mesa(conexao, origem, destino, g.usuario.id),
        f"Mesa {origem} transferida para a mesa {destino}.")


@bp.route("/comandas/<int:comanda_id>/juntar", methods=["POST"])
@login_obrigatorio
def juntar(comanda_id):
    conexao = obter_conexao()
    mesa = request.form.get("mesa", type=int)

    def juntar_mesa():
        atual = comandas.obter_comanda(conexao, comanda_id)
        if not atual.editavel:
            raise ComandaFechadaError()
        if not atual.mesas:
            raise DadosInvalidosError("Só comandas de mesa podem ser juntadas.")
        comandas.juntar_mesas(conexao, atual.mesas[0], mesa, g.usuario.id)
    return _acao_de_formulario(comanda_id, juntar_mesa, f"Mesa {mesa} juntada a esta comanda.")


@bp.route("/comandas/<int:comanda_id>/cancelar", methods=["POST"])
@login_obrigatorio
def cancelar_comanda(comanda_id):
    conexao = obter_conexao()
    try:
        atual = comandas.obter_comanda(conexao, comanda_id)
        autorizacao = autorizacao_do_formulario() if request.form.get("gerente_id") else None
        comandas.cancelar_comanda(conexao, comanda_id, g.usuario.id, motivo=request.form.get("motivo"),
                                  autorizacao=autorizacao)
    except CaixaFechadoError:
        raise
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return _para_comanda(comanda_id)
    flash(f"{atual.identificacao}: comanda cancelada.", "sucesso")
    return redirect(_voltar_da_comanda(atual))

