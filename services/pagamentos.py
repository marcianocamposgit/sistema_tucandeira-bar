"""Pagamentos, descontos, estornos e fechamento da venda.

Regras (ver CLAUDE.md):
- O cliente paga o preço de tabela: total = soma dos itens − descontos.
- Pagamento parcial: cada pagamento abate o saldo e registra quem recebeu.
- Nenhum pagamento passa do saldo. Em dinheiro, o valor recebido pode ser
  maior que o valor pago e a diferença vira troco.
- Quando o saldo chega a zero, na mesma transação: cria a venda com os itens,
  baixa o estoque, marca a comanda como paga e libera as mesas.
- Estorno: só com a comanda ainda não paga, com motivo e PIN de gerente. O
  pagamento não é apagado; deixa de contar no já pago e na conferência do caixa.
- Desconto: opcional, só em R$ e só se o gerente tiver ligado "permitir desconto";
  exige motivo e PIN de gerente; não pode passar da conta nem deixá-la abaixo do já pago.
"""
from collections import OrderedDict

import config
from database import transacao
from models import Desconto, ItemVenda, Pagamento, ResultadoPagamento, Venda, de_linha
from services import comandas, configuracoes, produtos
from services.caixa import exigir_caixa_aberto
from services.comum import exigir_centavos, exigir_texto, registrar_auditoria, texto_data
from services.erros import (
    ComandaFechadaError,
    DadosInvalidosError,
    DescontoNaoPermitidoError,
    NaoEncontradoError,
    TotalAbaixoDoPagoError,
)
from services.formatacao import formatar_moeda
from services.usuarios import verificar_gerente

FORMAS = tuple(config.FORMAS_PAGAMENTO)


# ============================================================
# CONSULTAS
# ============================================================
def listar_pagamentos(conexao, comanda_id, incluir_estornados=True):
    filtro = "" if incluir_estornados else "AND p.estornado_em IS NULL"
    linhas = conexao.execute(
        f"""SELECT p.*, u.nome AS recebido_por_nome FROM pagamentos p
            JOIN usuarios u ON u.id = p.recebido_por
            WHERE p.comanda_id = ? {filtro} ORDER BY p.criado_em, p.id""",
        (comanda_id,),
    ).fetchall()
    return [de_linha(Pagamento, l) for l in linhas]


def _obter_pagamento(conexao, pagamento_id):
    linha = conexao.execute("SELECT * FROM pagamentos WHERE id = ?", (pagamento_id,)).fetchone()
    if linha is None:
        raise NaoEncontradoError("Pagamento não encontrado.")
    return de_linha(Pagamento, linha)


def listar_descontos(conexao, comanda_id):
    linhas = conexao.execute("SELECT * FROM descontos WHERE comanda_id = ? ORDER BY criado_em, id",
                             (comanda_id,)).fetchall()
    return [de_linha(Desconto, l) for l in linhas]


def obter_venda(conexao, comanda_id):
    """Venda da comanda (com os itens), ou None se ainda não foi paga."""
    linha = conexao.execute("SELECT * FROM vendas WHERE comanda_id = ?", (comanda_id,)).fetchone()
    if linha is None:
        return None
    itens = conexao.execute("SELECT * FROM itens_venda WHERE venda_id = ? ORDER BY id", (linha["id"],)).fetchall()
    return de_linha(Venda, linha, itens=[de_linha(ItemVenda, i) for i in itens])


def calcular_troco(valor_centavos, recebido_centavos):
    """Troco em dinheiro. Recebido menor que o valor é erro."""
    exigir_centavos(valor_centavos, "o valor")
    exigir_centavos(recebido_centavos, "o valor recebido")
    if recebido_centavos < valor_centavos:
        raise DadosInvalidosError(
            f"O valor recebido ({formatar_moeda(recebido_centavos)}) é menor que o valor a pagar "
            f"({formatar_moeda(valor_centavos)}).")
    return recebido_centavos - valor_centavos


# ============================================================
# FECHAMENTO DA VENDA
# ============================================================
def _fechar_venda(conexao, comanda_id, usuario_id, agora):
    """Cria a venda, baixa o estoque, marca a comanda como paga e libera as mesas.

    Chamar dentro da transação, quando o saldo acabou de chegar a zero.
    Devolve (venda, avisos de estoque).
    """
    comanda = comandas.obter_comanda(conexao, comanda_id)
    conta = comandas.calcular_conta(conexao, comanda_id)
    momento = texto_data(agora)
    caixa = exigir_caixa_aberto(conexao)
    venda_id = conexao.execute(
        """INSERT INTO vendas (comanda_id, caixa_id, pessoas, subtotal_centavos, desconto_centavos,
                               total_centavos, fechada_por, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (comanda_id, caixa.id, comanda.pessoas, conta.subtotal_centavos, conta.desconto_centavos,
         conta.total_centavos, usuario_id, momento),
    ).lastrowid

    # Agrupa os lançamentos iguais (mesmo produto e preço) numa linha da venda.
    agrupados = OrderedDict()
    for item in comandas.listar_itens(conexao, comanda_id):
        chave = (item.produto_id, item.nome_produto, item.preco_unitario_centavos)
        agrupados[chave] = agrupados.get(chave, 0) + item.quantidade
    por_produto = OrderedDict()
    for (produto_id, nome, preco), quantidade in agrupados.items():
        conexao.execute(
            """INSERT INTO itens_venda (venda_id, produto_id, nome_produto, preco_unitario_centavos,
                                        quantidade, subtotal_centavos)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (venda_id, produto_id, nome, preco, quantidade, preco * quantidade),
        )
        por_produto[produto_id] = por_produto.get(produto_id, 0) + quantidade

    avisos = []
    for produto_id, quantidade in por_produto.items():
        produto = produtos.baixar_por_venda(conexao, produto_id, quantidade, agora=agora)
        if produto.situacao_estoque == "negativo":
            avisos.append(f"{produto.nome}: estoque negativo ({produto.estoque}).")
        elif produto.situacao_estoque == "zerado":
            avisos.append(f"{produto.nome}: estoque zerado.")
        elif produto.situacao_estoque == "abaixo_minimo":
            avisos.append(f"{produto.nome}: estoque baixo ({produto.estoque}, mínimo {produto.estoque_minimo}).")

    conexao.execute("UPDATE comandas SET status = 'paga', fechada_em = ?, fechada_por = ? WHERE id = ?",
                    (momento, usuario_id, comanda_id))
    conexao.execute("UPDATE comanda_mesas SET liberada_em = ? WHERE comanda_id = ? AND liberada_em IS NULL",
                    (momento, comanda_id))
    return obter_venda(conexao, comanda_id), avisos


def _resultado(conexao, comanda_id, pagamento=None, venda=None, avisos=None):
    return ResultadoPagamento(comandas.calcular_conta(conexao, comanda_id), pagamento, venda, avisos or [])


# ============================================================
# PAGAMENTO
# ============================================================
def registrar_pagamento(conexao, comanda_id, forma, valor_centavos, usuario_id,
                        recebido_centavos=None, agora=None):
    """Lança um pagamento (total ou parcial) na comanda.

    `valor_centavos` é o quanto abate do saldo. Em dinheiro, `recebido_centavos`
    é o que o cliente entregou (padrão: o próprio valor); a diferença é o troco.
    Se o saldo chegar a zero, a venda é fechada na mesma transação.
    """
    if forma not in FORMAS:
        raise DadosInvalidosError("Forma de pagamento inválida.")
    exigir_centavos(valor_centavos, "o valor", permitir_zero=False)
    if forma == "dinheiro":
        recebido = valor_centavos if recebido_centavos is None else recebido_centavos
        troco = calcular_troco(valor_centavos, recebido)
    else:
        if recebido_centavos not in (None, valor_centavos):
            raise DadosInvalidosError("Troco só existe em pagamento em dinheiro.")
        recebido, troco = None, 0

    with transacao(conexao):
        caixa = exigir_caixa_aberto(conexao)
        comanda = comandas.obter_comanda(conexao, comanda_id)
        if not comanda.editavel:
            raise ComandaFechadaError()
        saldo = comandas.calcular_conta(conexao, comanda_id).saldo_centavos
        if saldo <= 0:
            raise DadosInvalidosError("Esta comanda não tem saldo a pagar.")
        if valor_centavos > saldo:
            raise DadosInvalidosError(
                f"O valor ({formatar_moeda(valor_centavos)}) passa do saldo da conta ({formatar_moeda(saldo)}).")
        pagamento_id = conexao.execute(
            """INSERT INTO pagamentos (comanda_id, caixa_id, forma, valor_centavos, recebido_centavos,
                                       troco_centavos, recebido_por, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (comanda_id, caixa.id, forma, valor_centavos, recebido, troco, usuario_id, texto_data(agora)),
        ).lastrowid
        venda, avisos = None, []
        if valor_centavos == saldo:
            venda, avisos = _fechar_venda(conexao, comanda_id, usuario_id, agora)
    return _resultado(conexao, comanda_id, _obter_pagamento(conexao, pagamento_id), venda, avisos)


def estornar_pagamento(conexao, pagamento_id, motivo, usuario_id, autorizacao, agora=None):
    """Estorna um pagamento lançado errado (comanda ainda não paga). Motivo + gerente."""
    motivo = exigir_texto(motivo, "o motivo do estorno", maximo=200)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        exigir_caixa_aberto(conexao)
        pagamento = _obter_pagamento(conexao, pagamento_id)
        if pagamento.estornado:
            raise DadosInvalidosError("Este pagamento já foi estornado.")
        if not comandas.obter_comanda(conexao, pagamento.comanda_id).editavel:
            raise ComandaFechadaError("A comanda já foi fechada: não é possível estornar.")
        conexao.execute(
            """UPDATE pagamentos SET estornado_em = ?, estornado_por = ?, estorno_autorizado_por = ?,
                                     motivo_estorno = ?
               WHERE id = ?""",
            (texto_data(agora), usuario_id, gerente.id, motivo, pagamento_id),
        )
    return _resultado(conexao, pagamento.comanda_id, _obter_pagamento(conexao, pagamento_id))


# ============================================================
# DESCONTO
# ============================================================
def aplicar_desconto(conexao, comanda_id, valor_centavos, motivo, usuario_id, autorizacao, agora=None):
    """Desconto em R$ na comanda. Só se o desconto estiver permitido; motivo + gerente.

    Se o desconto quitar a conta (ex.: cortesia, ou o resto já pago), a venda é
    fechada na mesma transação.
    """
    exigir_centavos(valor_centavos, "o desconto", permitir_zero=False)
    motivo = exigir_texto(motivo, "o motivo do desconto", maximo=200)

    with transacao(conexao):
        if not configuracoes.desconto_permitido(conexao):
            raise DescontoNaoPermitidoError()
        gerente = verificar_gerente(conexao, autorizacao)
        exigir_caixa_aberto(conexao)
        comanda = comandas.obter_comanda(conexao, comanda_id)
        if not comanda.editavel:
            raise ComandaFechadaError()
        conta = comandas.calcular_conta(conexao, comanda_id)
        if conta.subtotal_centavos == 0:
            raise DadosInvalidosError("A comanda não tem itens.")
        if valor_centavos > conta.total_centavos:
            raise DadosInvalidosError(
                f"O desconto ({formatar_moeda(valor_centavos)}) passa do total da conta "
                f"({formatar_moeda(conta.total_centavos)}).")
        if valor_centavos > conta.saldo_centavos:
            raise TotalAbaixoDoPagoError()
        conexao.execute(
            """INSERT INTO descontos (comanda_id, valor_centavos, motivo, usuario_id, autorizado_por, criado_em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (comanda_id, valor_centavos, motivo, usuario_id, gerente.id, texto_data(agora)),
        )
        venda, avisos = None, []
        if valor_centavos == conta.saldo_centavos:
            venda, avisos = _fechar_venda(conexao, comanda_id, usuario_id, agora)
    return _resultado(conexao, comanda_id, venda=venda, avisos=avisos)


def remover_desconto(conexao, desconto_id, usuario_id, autorizacao, agora=None):
    """Desfaz um desconto aplicado por engano (comanda ainda aberta). Exige gerente.

    Funciona mesmo com o desconto desligado, para corrigir um desconto antigo.
    """
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        exigir_caixa_aberto(conexao)
        linha = conexao.execute("SELECT * FROM descontos WHERE id = ?", (desconto_id,)).fetchone()
        if linha is None:
            raise NaoEncontradoError("Desconto não encontrado.")
        desconto = de_linha(Desconto, linha)
        if not comandas.obter_comanda(conexao, desconto.comanda_id).editavel:
            raise ComandaFechadaError()
        conexao.execute("DELETE FROM descontos WHERE id = ?", (desconto_id,))
        registrar_auditoria(conexao, "desconto_removido", usuario_id,
                            {"comanda_id": desconto.comanda_id, "valor_centavos": desconto.valor_centavos,
                             "motivo": desconto.motivo, "aplicado_por": desconto.usuario_id,
                             "autorizado_por_original": desconto.autorizado_por},
                            autorizado_por=gerente.id, agora=agora)
    return _resultado(conexao, desconto.comanda_id)
