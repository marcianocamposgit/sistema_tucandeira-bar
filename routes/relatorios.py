"""Relatórios por período (dia, semana, mês ou intervalo) e CSV.

- Gerente logado abre direto; operador precisa da autorização de um gerente
  (vale por config.ACESSO_TELA_RELATORIOS_MINUTOS).
- Cada seção tem o botão "Baixar CSV" (separador ";", UTF-8 com BOM).
"""
import time
from functools import wraps

from flask import Blueprint, Response, flash, g, redirect, render_template, request, session, url_for

import config
from routes.conexao import obter_conexao
from routes.seguranca import autorizacao_do_formulario, login_obrigatorio
from services import relatorios
from services.erros import ErroDeNegocio

bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")

SITUACOES = {"negativo": "Estoque negativo", "zerado": "Sem estoque", "abaixo_minimo": "Abaixo do mínimo"}


def _pode_ver():
    return g.usuario.gerente or session.get("acesso_relatorios_ate", 0) > time.time()


def tela_de_gerente(rota):
    @wraps(rota)
    def protegida(*args, **kwargs):
        if not _pode_ver():
            return render_template("relatorios/acesso.html")
        return rota(*args, **kwargs)
    return protegida


@bp.route("/acesso", methods=["POST"])
@login_obrigatorio
def acesso():
    """Operador abre os relatórios com a autorização de um gerente."""
    try:
        autorizacao_do_formulario()
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return render_template("relatorios/acesso.html")
    session["acesso_relatorios_ate"] = time.time() + config.ACESSO_TELA_RELATORIOS_MINUTOS * 60
    return redirect(url_for("relatorios.tela"))


def _periodo_pedido():
    """Período da URL; se estiver errado, avisa e mostra o dia de operação atual."""
    dia_operacao = relatorios.dia_de_operacao(obter_conexao())
    try:
        return relatorios.periodo(request.args.get("periodo", "dia"), de=request.args.get("de"),
                                  ate=request.args.get("ate"), dia_operacao=dia_operacao)
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return relatorios.periodo("dia", dia_operacao=dia_operacao)


@bp.route("/")
@login_obrigatorio
@tela_de_gerente
def tela():
    conexao = obter_conexao()
    p = _periodo_pedido()
    # O CSV usa sempre as datas exatas da tela.
    args_csv = {"periodo": "intervalo", "de": p.inicio.isoformat(), "ate": p.fim.isoformat()}
    return render_template(
        "relatorios/relatorios.html",
        periodo=p,
        nome_periodo=relatorios.nome_periodo(p),
        resumo=relatorios.resumo_vendas(conexao, p),
        vendidos=relatorios.produtos_mais_vendidos(conexao, p),
        cancelamentos=relatorios.cancelamentos(conexao, p),
        descontos=relatorios.descontos(conexao, p),
        estoque=relatorios.estoque_em_alerta(conexao),
        fechamentos=relatorios.fechamentos_caixa(conexao, p),
        formas=config.FORMAS_PAGAMENTO,
        situacoes=SITUACOES,
        args_csv=args_csv,
    )


@bp.route("/csv/<relatorio>")
@login_obrigatorio
@tela_de_gerente
def baixar_csv(relatorio):
    if relatorio not in relatorios.RELATORIOS_CSV:
        flash("Relatório inválido.", "erro")
        return redirect(url_for("relatorios.tela"))
    p = _periodo_pedido()
    texto = relatorios.gerar_csv(relatorios.linhas_csv(obter_conexao(), relatorio, p))
    return Response(
        texto.encode("utf-8"),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{relatorios.nome_arquivo_csv(relatorio, p)}"'},
    )
