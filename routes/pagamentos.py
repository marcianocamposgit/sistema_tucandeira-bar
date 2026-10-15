"""Tela de pagamento (fechar conta) e configuração do desconto.

- Mostra itens, descontos, total, já pago, saldo e o valor por pessoa.
- Recebe pagamentos parciais em Dinheiro, Débito, Crédito ou PIX. Em dinheiro,
  o valor recebido pode ser maior e a diferença vira troco (calculado no service).
- Cada formulário de pagamento leva uma chave própria: se o mesmo envio chegar
  duas vezes (toque duplo, F5), o service não cobra de novo.
- Estorno, desconto e remoção de desconto pedem motivo e a autorização do gerente.
- Ao quitar, a mesma tela mostra a venda concluída e os avisos de estoque. Quem
  abrir a comanda depois (outro aparelho) vê que a conta já foi paga.
- Configurações (só gerente): ligar/desligar o desconto, com autorização na hora.
"""
import secrets

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

import config
from routes.conexao import obter_conexao
from routes.seguranca import autorizacao_do_formulario, login_obrigatorio
from services import comandas, configuracoes, pagamentos, usuarios
from services.erros import (
    CaixaFechadoError,
    ComandaFechadaError,
    DadosInvalidosError,
    ErroDeNegocio,
    NaoEncontradoError,
)
from services.formatacao import formatar_moeda, formatar_valor_campo, ler_moeda, plural, valor_para_campo

bp = Blueprint("pagamentos", __name__)

FORMAS = config.FORMAS_PAGAMENTO
CEDULAS = [10, 20, 50, 100]
ATALHOS_ESTORNO = ["Forma de pagamento errada", "Valor errado", "Lançado na comanda errada"]
ATALHOS_DESCONTO = ["Cortesia da casa", "Cliente fiel", "Produto com defeito", "Demora no atendimento"]


def _para_tela(comanda_id):
    return redirect(url_for("pagamentos.tela", comanda_id=comanda_id))


def _nome_usuario(conexao, usuario_id):
    try:
        return usuarios.obter(conexao, usuario_id).nome
    except NaoEncontradoError:
        return "?"


# ============================================================
# TELA
# ============================================================
@bp.route("/comandas/<int:comanda_id>/pagamento", methods=["GET"])
@login_obrigatorio
def tela(comanda_id):
    conexao = obter_conexao()
    try:
        comanda = comandas.obter_comanda(conexao, comanda_id)
    except NaoEncontradoError as erro:
        flash(str(erro), "erro")
        return redirect(url_for("mesas.mesas"))
    if comanda.status == "paga":
        return _tela_paga(conexao, comanda)
    if comanda.status == "unida" and comanda.unida_a:
        flash("Esta comanda foi juntada a outra mesa.", "aviso")
        return _para_tela(comanda.unida_a)
    if not comanda.editavel:
        flash(f"{comanda.identificacao}: a comanda foi cancelada.", "aviso")
        return redirect(url_for("mesas.mesas"))
    return _tela_aberta(conexao, comanda)


def _tela_aberta(conexao, comanda, dados=None):
    resumo = comandas.obter_resumo(conexao, comanda.id)
    conta = resumo.conta
    dados = dados or {"forma": "", "valor": "", "recebido": ""}
    descontos = pagamentos.listar_descontos(conexao, comanda.id)
    return render_template(
        "pagamentos/pagamento.html",
        comanda=comanda,
        conta=conta,
        grupos=comandas.agrupar_itens(resumo.itens),
        descontos=descontos,
        pagamentos=pagamentos.listar_pagamentos(conexao, comanda.id),
        formas=FORMAS,
        dados=dados,
        chave=secrets.token_hex(12),
        pessoas_texto=plural(conta.pessoas, "pessoa", "pessoas"),
        saldo_campo=formatar_valor_campo(conta.saldo_centavos),
        # "Por pessoa" só ajuda se for menor que o saldo (senão é o saldo inteiro).
        por_pessoa_campo=(formatar_valor_campo(conta.por_pessoa_centavos)
                          if conta.pessoas > 1 and conta.por_pessoa_centavos < conta.saldo_centavos else ""),
        cedulas=CEDULAS,
        desconto_permitido=configuracoes.desconto_permitido(conexao),
        atalhos_estorno=ATALHOS_ESTORNO,
        atalhos_desconto=ATALHOS_DESCONTO,
        intervalo=config.INTERVALO_ATUALIZACAO_MESAS,
    )


def _tela_paga(conexao, comanda):
    venda = pagamentos.obter_venda(conexao, comanda.id)
    return render_template(
        "pagamentos/venda.html",
        comanda=comanda,
        venda=venda,
        pagamentos=pagamentos.listar_pagamentos(conexao, comanda.id, incluir_estornados=False),
        fechada_por=_nome_usuario(conexao, venda.fechada_por) if venda else "",
        pessoas_texto=plural(venda.pessoas, "pessoa", "pessoas") if venda else "",
        voltar=url_for("mesas.balcao") if comanda.tipo == "balcao" else url_for("mesas.mesas"),
    )


def _comanda_fechada(comanda_id, erro):
    """Outro aparelho pagou, cancelou ou juntou a comanda: a tela mostra o que aconteceu."""
    try:
        status = comandas.obter_comanda(obter_conexao(), comanda_id).status
    except NaoEncontradoError:
        status = None
    if status == "paga":
        flash("Esta conta já foi paga (provavelmente em outro aparelho). Nada foi cobrado agora.", "erro")
    else:
        flash(str(erro), "erro")
    return _para_tela(comanda_id)


# ============================================================
# RECEBER
# ============================================================
def _centavos_opcional(texto, campo):
    return ler_moeda(texto, campo) if (texto or "").strip() else None


@bp.route("/comandas/<int:comanda_id>/pagamento", methods=["POST"])
@login_obrigatorio
def receber(comanda_id):
    conexao = obter_conexao()
    forma = request.form.get("forma", "")
    dados = {"forma": forma, "valor": valor_para_campo(request.form.get("valor", "")),
             "recebido": valor_para_campo(request.form.get("recebido", ""))}
    try:
        if forma not in FORMAS:
            raise DadosInvalidosError("Escolha a forma de pagamento: Dinheiro, Débito, Crédito ou PIX.")
        valor = ler_moeda(request.form.get("valor", ""), "o valor a pagar")
        recebido = _centavos_opcional(request.form.get("recebido", ""), "o valor recebido") \
            if forma == "dinheiro" else None
        resultado = pagamentos.registrar_pagamento(conexao, comanda_id, forma, valor, g.usuario.id,
                                                   recebido_centavos=recebido, chave=request.form.get("chave"))
    except CaixaFechadoError:
        raise
    except ComandaFechadaError as erro:
        return _comanda_fechada(comanda_id, erro)
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        try:
            comanda = comandas.obter_comanda(conexao, comanda_id)
        except NaoEncontradoError:
            return redirect(url_for("mesas.mesas"))
        if not comanda.editavel:
            return _para_tela(comanda_id)
        return _tela_aberta(conexao, comanda, dados)

    if resultado.repetido:
        flash("Este pagamento já tinha sido lançado (toque repetido): nada foi cobrado de novo.", "aviso")
        return _para_tela(comanda_id)
    pagamento = resultado.pagamento
    if pagamento.troco_centavos:
        flash(f"Troco: {formatar_moeda(pagamento.troco_centavos)}", "troco")
    if resultado.quitada:
        flash(f"Venda concluída: {pagamento.forma_nome} {formatar_moeda(pagamento.valor_centavos)} "
              "quitou a conta.", "sucesso")
        for aviso in resultado.avisos_estoque:
            flash(f"Estoque: {aviso}", "aviso")
    else:
        flash(f"{pagamento.forma_nome} {formatar_moeda(pagamento.valor_centavos)} recebido. "
              f"Falta pagar {formatar_moeda(resultado.conta.saldo_centavos)}.", "sucesso")
    return _para_tela(comanda_id)


# ============================================================
# ESTORNO E DESCONTO (motivo + autorização do gerente)
# ============================================================
def _acao_de_gerente(comanda_id, funcao, sucesso):
    try:
        resultado = funcao()
    except CaixaFechadoError:
        raise
    except ComandaFechadaError as erro:
        return _comanda_fechada(comanda_id, erro)
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return _para_tela(comanda_id)
    flash(sucesso(resultado), "sucesso")
    for aviso in getattr(resultado, "avisos_estoque", []):
        flash(f"Estoque: {aviso}", "aviso")
    return _para_tela(comanda_id)


@bp.route("/comandas/<int:comanda_id>/estorno", methods=["POST"])
@login_obrigatorio
def estornar(comanda_id):
    conexao = obter_conexao()

    def estornar_pagamento():
        pagamento_id = request.form.get("pagamento_id", type=int)
        if pagamento_id not in [p.id for p in pagamentos.listar_pagamentos(conexao, comanda_id)]:
            raise DadosInvalidosError("Pagamento não encontrado nesta comanda.")
        return pagamentos.estornar_pagamento(conexao, pagamento_id, request.form.get("motivo", ""),
                                             g.usuario.id, autorizacao_do_formulario())

    return _acao_de_gerente(
        comanda_id, estornar_pagamento,
        lambda r: f"Pagamento estornado. Falta pagar {formatar_moeda(r.conta.saldo_centavos)}.")


@bp.route("/comandas/<int:comanda_id>/desconto", methods=["POST"])
@login_obrigatorio
def desconto(comanda_id):
    conexao = obter_conexao()

    def aplicar():
        valor = ler_moeda(request.form.get("valor", ""), "o desconto")
        return pagamentos.aplicar_desconto(conexao, comanda_id, valor, request.form.get("motivo", ""),
                                           g.usuario.id, autorizacao_do_formulario())

    def mensagem(resultado):
        if resultado.quitada:
            return "Desconto aplicado: a conta ficou quitada e a venda foi concluída."
        return f"Desconto aplicado. Falta pagar {formatar_moeda(resultado.conta.saldo_centavos)}."

    return _acao_de_gerente(comanda_id, aplicar, mensagem)


@bp.route("/comandas/<int:comanda_id>/desconto/<int:desconto_id>/remover", methods=["POST"])
@login_obrigatorio
def remover_desconto(comanda_id, desconto_id):
    conexao = obter_conexao()

    def remover():
        if desconto_id not in [d.id for d in pagamentos.listar_descontos(conexao, comanda_id)]:
            raise DadosInvalidosError("Desconto não encontrado nesta comanda.")
        return pagamentos.remover_desconto(conexao, desconto_id, g.usuario.id, autorizacao_do_formulario())

    return _acao_de_gerente(
        comanda_id, remover,
        lambda r: f"Desconto removido. Falta pagar {formatar_moeda(r.conta.saldo_centavos)}.")


# ============================================================
# CONFIGURAÇÕES (só gerente)
# ============================================================
@bp.route("/configuracoes", methods=["GET", "POST"])
@login_obrigatorio
def configuracoes_bar():
    if not g.usuario.gerente:
        flash("As configurações são só para o gerente.", "erro")
        return redirect(url_for("principal.inicio"))
    conexao = obter_conexao()
    if request.method == "POST":
        ligar = request.form.get("permitir_desconto") == "1"
        try:
            configuracoes.definir_desconto_permitido(conexao, ligar, g.usuario.id, autorizacao_do_formulario())
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash("Desconto ligado: o botão aparece na tela de pagamento." if ligar
                  else "Desconto desligado: o botão não aparece mais na tela de pagamento.", "sucesso")
        return redirect(url_for("pagamentos.configuracoes_bar"))
    return render_template("pagamentos/configuracoes.html",
                           desconto_permitido=configuracoes.desconto_permitido(conexao))
