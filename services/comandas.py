"""Comandas de mesa e de balcão.

Regras principais (ver CLAUDE.md):
- Tudo exige caixa aberto.
- Mesa ocupada = vínculo ativo em comanda_mesas (o banco impede duas comandas na mesma mesa).
- Cada lançamento é uma linha própria, com a hora, para a regra dos 2 minutos.
- Remover sem PIN só até config.PRAZO_REMOCAO_ITEM_MINUTOS após o lançamento;
  depois, só cancelamento com motivo e autorização de gerente.
- Nenhuma alteração pode deixar a conta menor que o valor já pago.
- Toda alteração roda numa transação e confere, dentro dela, se a comanda ainda
  está aberta (outro aparelho pode ter acabado de pagar, juntar ou cancelar).
"""
from datetime import datetime, timedelta

import config
from database import transacao
from models import (
    Comanda,
    ComandaPendente,
    Conta,
    EstadoMesa,
    ItemComanda,
    ResultadoLancamento,
    ResumoComanda,
    de_linha,
)
from models.comandas import STATUS_EDITAVEIS
from services import configuracoes
from services.caixa import exigir_caixa_aberto
from services.comum import (
    exigir_inteiro,
    exigir_texto,
    ler_data,
    registrar_auditoria,
    texto_data,
    texto_opcional,
)
from services.erros import (
    ComandaComPagamentosError,
    ComandaFechadaError,
    DadosInvalidosError,
    MesaOcupadaError,
    NaoEncontradoError,
    PrazoRemocaoExpiradoError,
    TotalAbaixoDoPagoError,
)
from services.usuarios import verificar_gerente

MAXIMO_PESSOAS = 99
MAXIMO_QUANTIDADE = 99
EDITAVEIS_SQL = "('aberta', 'conta_pedida')"


# ============================================================
# LEITURA
# ============================================================
def _mesas_da_comanda(conexao, linha):
    """Mesas atuais (comanda aberta) ou as que estavam ligadas no fechamento."""
    if linha["status"] in STATUS_EDITAVEIS:
        sql = "SELECT mesa FROM comanda_mesas WHERE comanda_id = ? AND liberada_em IS NULL"
        parametros = (linha["id"],)
    else:
        sql = "SELECT mesa FROM comanda_mesas WHERE comanda_id = ? AND liberada_em = ?"
        parametros = (linha["id"], linha["fechada_em"])
    return [l["mesa"] for l in conexao.execute(sql + " ORDER BY principal DESC, mesa", parametros)]


def _comanda(conexao, linha):
    return de_linha(Comanda, linha, taxa_servico_ativa=bool(linha["taxa_servico_ativa"]),
                    mesas=_mesas_da_comanda(conexao, linha))


def obter_comanda(conexao, comanda_id):
    linha = conexao.execute("SELECT * FROM comandas WHERE id = ?", (comanda_id,)).fetchone()
    if linha is None:
        raise NaoEncontradoError("Comanda não encontrada.")
    return _comanda(conexao, linha)


def _comanda_editavel(conexao, comanda_id):
    comanda = obter_comanda(conexao, comanda_id)
    if not comanda.editavel:
        raise ComandaFechadaError()
    return comanda


def comanda_da_mesa(conexao, mesa):
    """Comanda aberta ligada à mesa, ou None se a mesa estiver livre."""
    linha = conexao.execute(
        """SELECT c.* FROM comandas c JOIN comanda_mesas cm ON cm.comanda_id = c.id
           WHERE cm.mesa = ? AND cm.liberada_em IS NULL""",
        (mesa,),
    ).fetchone()
    return _comanda(conexao, linha) if linha else None


def total_pago(conexao, comanda_id):
    """Soma dos pagamentos não estornados."""
    return conexao.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM pagamentos WHERE comanda_id = ? AND estornado_em IS NULL",
        (comanda_id,),
    ).fetchone()[0]


def calcular_taxa(subtotal_centavos, ativa=True):
    """Taxa de serviço sobre o subtotal, arredondada ao centavo (meio centavo para cima)."""
    if not ativa:
        return 0
    return (subtotal_centavos * config.TAXA_SERVICO_PERCENTUAL + 50) // 100


def _conta(conexao, comanda):
    subtotal = conexao.execute(
        "SELECT COALESCE(SUM(preco_unitario_centavos * quantidade), 0) FROM itens_comanda WHERE comanda_id = ?",
        (comanda.id,),
    ).fetchone()[0]
    desconto = conexao.execute(
        "SELECT COALESCE(SUM(valor_centavos), 0) FROM descontos WHERE comanda_id = ?", (comanda.id,)
    ).fetchone()[0]
    return Conta(
        subtotal_centavos=subtotal,
        taxa_servico_centavos=calcular_taxa(subtotal, comanda.taxa_servico_ativa),
        couvert_centavos=comanda.couvert_unitario_centavos * comanda.pessoas,
        desconto_centavos=desconto,
        pago_centavos=total_pago(conexao, comanda.id),
        pessoas=comanda.pessoas,
    )


def calcular_conta(conexao, comanda_id):
    return _conta(conexao, obter_comanda(conexao, comanda_id))


def _exigir_conta_coberta(conexao, comanda_id):
    """Depois de uma alteração: a conta não pode ficar menor que o já pago."""
    if calcular_conta(conexao, comanda_id).saldo_centavos < 0:
        raise TotalAbaixoDoPagoError()


def listar_itens(conexao, comanda_id, incluir_zerados=False):
    filtro = "" if incluir_zerados else "AND i.quantidade > 0"
    linhas = conexao.execute(
        f"""SELECT i.*, u.nome AS lancado_por_nome FROM itens_comanda i
            JOIN usuarios u ON u.id = i.lancado_por
            WHERE i.comanda_id = ? {filtro} ORDER BY i.lancado_em, i.id""",
        (comanda_id,),
    ).fetchall()
    return [de_linha(ItemComanda, l) for l in linhas]


def _obter_item(conexao, item_id):
    linha = conexao.execute("SELECT * FROM itens_comanda WHERE id = ?", (item_id,)).fetchone()
    if linha is None:
        raise NaoEncontradoError("Item não encontrado.")
    return de_linha(ItemComanda, linha)


def removivel_ate(item):
    """Até quando o item pode ser removido sem PIN de gerente (datetime)."""
    return ler_data(item.lancado_em) + timedelta(minutes=config.PRAZO_REMOCAO_ITEM_MINUTOS)


def pode_remover_sem_pin(item, agora=None):
    return (agora or datetime.now()) <= removivel_ate(item)


def obter_resumo(conexao, comanda_id):
    comanda = obter_comanda(conexao, comanda_id)
    return ResumoComanda(comanda, _conta(conexao, comanda), listar_itens(conexao, comanda_id))


def listar_abertas(conexao, tipo=None):
    """Comandas abertas ou com conta pedida (sem os itens), mais antigas primeiro."""
    condicao, parametros = "", []
    if tipo is not None:
        condicao, parametros = "AND tipo = ?", [tipo]
    linhas = conexao.execute(
        f"SELECT * FROM comandas WHERE status IN {EDITAVEIS_SQL} {condicao} ORDER BY aberta_em, id",
        parametros,
    ).fetchall()
    resumos = []
    for linha in linhas:
        comanda = _comanda(conexao, linha)
        resumos.append(ResumoComanda(comanda, _conta(conexao, comanda)))
    return resumos


def listar_pendentes(conexao, caixa_id):
    """Comandas que impedem fechar o caixa (abertas ou com conta pedida)."""
    return [
        ComandaPendente(r.comanda.id, r.comanda.identificacao, r.comanda.status,
                        r.conta.total_centavos, r.conta.saldo_centavos)
        for r in listar_abertas(conexao) if r.comanda.caixa_id == caixa_id
    ]


def estado_mesas(conexao):
    """Situação de cada mesa (1 a NUM_MESAS) para a tela de mesas."""
    estados = {n: EstadoMesa(n, "livre") for n in range(1, config.NUM_MESAS + 1)}
    for resumo in listar_abertas(conexao, tipo="mesa"):
        comanda = resumo.comanda
        status = "conta_pedida" if comanda.status == "conta_pedida" else "ocupada"
        for mesa in comanda.mesas:
            if mesa in estados:
                estados[mesa] = EstadoMesa(mesa, status, comanda.id, comanda.pessoas,
                                           resumo.conta.total_centavos, list(comanda.mesas))
    return [estados[n] for n in sorted(estados)]


# ============================================================
# ABERTURA
# ============================================================
def _validar_mesa(mesa):
    return exigir_inteiro(mesa, "o número da mesa", minimo=1, maximo=config.NUM_MESAS)


def _validar_pessoas(pessoas):
    return exigir_inteiro(pessoas, "o número de pessoas", minimo=1, maximo=MAXIMO_PESSOAS)


def _inserir_comanda(conexao, tipo, nome_cliente, pessoas, caixa, taxa, usuario_id, agora):
    couvert = configuracoes.couvert_para_data(conexao, ler_data(caixa.aberto_em).date())
    return conexao.execute(
        """INSERT INTO comandas (tipo, nome_cliente, pessoas, caixa_id, taxa_servico_ativa,
                                 couvert_unitario_centavos, aberta_em, aberta_por)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (tipo, nome_cliente, pessoas, caixa.id, 1 if taxa else 0, couvert, texto_data(agora), usuario_id),
    ).lastrowid


def abrir_mesa(conexao, mesa, usuario_id, pessoas=1, agora=None):
    """Abre a comanda de uma mesa livre. Taxa de serviço ativada por padrão."""
    _validar_mesa(mesa)
    _validar_pessoas(pessoas)
    with transacao(conexao):
        caixa = exigir_caixa_aberto(conexao)
        if comanda_da_mesa(conexao, mesa):
            raise MesaOcupadaError(mesa)
        comanda_id = _inserir_comanda(conexao, "mesa", None, pessoas, caixa, True, usuario_id, agora)
        conexao.execute(
            "INSERT INTO comanda_mesas (comanda_id, mesa, principal, vinculada_em) VALUES (?, ?, 1, ?)",
            (comanda_id, mesa, texto_data(agora)),
        )
    return obter_comanda(conexao, comanda_id)


def abrir_balcao(conexao, nome_cliente, usuario_id, pessoas=1, agora=None):
    """Abre uma comanda de balcão / para viagem, identificada pelo nome do cliente."""
    nome_cliente = exigir_texto(nome_cliente, "o nome do cliente", maximo=40)
    _validar_pessoas(pessoas)
    with transacao(conexao):
        caixa = exigir_caixa_aberto(conexao)
        repetida = conexao.execute(
            f"""SELECT 1 FROM comandas WHERE tipo = 'balcao' AND status IN {EDITAVEIS_SQL}
                AND nome_cliente = ? COLLATE NOCASE""",
            (nome_cliente,),
        ).fetchone()
        if repetida:
            raise DadosInvalidosError(
                f"Já existe uma comanda de balcão aberta para {nome_cliente}. Use outro nome.")
        comanda_id = _inserir_comanda(conexao, "balcao", nome_cliente, pessoas, caixa, False, usuario_id, agora)
    return obter_comanda(conexao, comanda_id)


# ============================================================
# ITENS
# ============================================================
def lancar_item(conexao, comanda_id, produto_id, usuario_id, quantidade=1, observacao=None, agora=None):
    """Lança um produto na comanda. Sem estoque: lança e devolve um aviso."""
    exigir_inteiro(quantidade, "a quantidade", minimo=1, maximo=MAXIMO_QUANTIDADE)
    observacao = texto_opcional(observacao, maximo=100)
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        _comanda_editavel(conexao, comanda_id)
        produto = conexao.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        if produto is None:
            raise NaoEncontradoError("Produto não encontrado.")
        if not produto["ativo"]:
            raise DadosInvalidosError(f"{produto['nome']} está desativado no cardápio.")
        item_id = conexao.execute(
            """INSERT INTO itens_comanda (comanda_id, produto_id, nome_produto, preco_unitario_centavos,
                                          quantidade, observacao, lancado_por, lancado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (comanda_id, produto_id, produto["nome"], produto["preco_centavos"], quantidade,
             observacao, usuario_id, texto_data(agora)),
        ).lastrowid
        # O estoque só baixa no pagamento; aqui o aviso considera o que já está nas comandas abertas.
        nas_comandas = conexao.execute(
            f"""SELECT COALESCE(SUM(i.quantidade), 0) FROM itens_comanda i
                JOIN comandas c ON c.id = i.comanda_id
                WHERE i.produto_id = ? AND c.status IN {EDITAVEIS_SQL}""",
            (produto_id,),
        ).fetchone()[0]
    aviso = None
    if produto["estoque"] - nas_comandas < 0:
        aviso = (f"Atenção: {produto['nome']} está sem estoque suficiente "
                 f"(estoque: {produto['estoque']}). O pedido foi aceito.")
    return ResultadoLancamento(_obter_item(conexao, item_id), aviso)


def _diminuir_item(conexao, item, quantidade, tipo, usuario_id, motivo, autorizado_por, agora):
    if quantidade > item.quantidade:
        raise DadosInvalidosError(f"O item tem só {item.quantidade} unidade(s).")
    conexao.execute("UPDATE itens_comanda SET quantidade = quantidade - ? WHERE id = ?",
                    (quantidade, item.id))
    conexao.execute(
        """INSERT INTO item_ajustes (item_id, tipo, quantidade, motivo, usuario_id, autorizado_por, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (item.id, tipo, quantidade, motivo, usuario_id, autorizado_por, texto_data(agora)),
    )


def remover_item(conexao, item_id, usuario_id, quantidade=1, agora=None):
    """Remove sem PIN, só dentro do prazo após o lançamento."""
    exigir_inteiro(quantidade, "a quantidade", minimo=1)
    momento = agora or datetime.now()
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        item = _obter_item(conexao, item_id)
        _comanda_editavel(conexao, item.comanda_id)
        if not pode_remover_sem_pin(item, momento):
            raise PrazoRemocaoExpiradoError(config.PRAZO_REMOCAO_ITEM_MINUTOS)
        _diminuir_item(conexao, item, quantidade, "remocao", usuario_id, None, None, momento)
        _exigir_conta_coberta(conexao, item.comanda_id)
    return _obter_item(conexao, item_id)


def cancelar_item(conexao, item_id, motivo, usuario_id, autorizacao, quantidade=1, agora=None):
    """Cancela item já lançado (fora do prazo): motivo + autorização de gerente, registrado."""
    exigir_inteiro(quantidade, "a quantidade", minimo=1)
    motivo = exigir_texto(motivo, "o motivo do cancelamento", maximo=200)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        exigir_caixa_aberto(conexao)
        item = _obter_item(conexao, item_id)
        _comanda_editavel(conexao, item.comanda_id)
        _diminuir_item(conexao, item, quantidade, "cancelamento", usuario_id, motivo, gerente.id, agora)
        _exigir_conta_coberta(conexao, item.comanda_id)
    return _obter_item(conexao, item_id)


def alterar_observacao(conexao, item_id, observacao, usuario_id, agora=None):
    observacao = texto_opcional(observacao, maximo=100)
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        item = _obter_item(conexao, item_id)
        _comanda_editavel(conexao, item.comanda_id)
        conexao.execute("UPDATE itens_comanda SET observacao = ? WHERE id = ?", (observacao, item_id))
        registrar_auditoria(conexao, "observacao_alterada", usuario_id,
                            {"item_id": item_id, "antes": item.observacao, "depois": observacao}, agora=agora)
    return _obter_item(conexao, item_id)


# ============================================================
# COMANDA
# ============================================================
def alterar_pessoas(conexao, comanda_id, pessoas, usuario_id, agora=None):
    _validar_pessoas(pessoas)
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        comanda = _comanda_editavel(conexao, comanda_id)
        conexao.execute("UPDATE comandas SET pessoas = ? WHERE id = ?", (pessoas, comanda_id))
        _exigir_conta_coberta(conexao, comanda_id)  # o couvert é por pessoa
        registrar_auditoria(conexao, "pessoas_alteradas", usuario_id,
                            {"comanda_id": comanda_id, "antes": comanda.pessoas, "depois": pessoas},
                            agora=agora)
    return obter_comanda(conexao, comanda_id)


def marcar_conta_pedida(conexao, comanda_id, usuario_id, pedida=True, agora=None):
    """Marca (ou desmarca) que o cliente pediu a conta."""
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        _comanda_editavel(conexao, comanda_id)
        status = "conta_pedida" if pedida else "aberta"
        conexao.execute("UPDATE comandas SET status = ? WHERE id = ?", (status, comanda_id))
        registrar_auditoria(conexao, "conta_pedida" if pedida else "conta_reaberta", usuario_id,
                            {"comanda_id": comanda_id}, agora=agora)
    return obter_comanda(conexao, comanda_id)


def _comanda_da_mesa_obrigatoria(conexao, mesa):
    comanda = comanda_da_mesa(conexao, mesa)
    if comanda is None:
        raise NaoEncontradoError(f"A mesa {mesa} está livre.")
    return comanda


def transferir_mesa(conexao, mesa_origem, mesa_destino, usuario_id, agora=None):
    """Passa a comanda da mesa de origem para uma mesa livre."""
    _validar_mesa(mesa_origem)
    _validar_mesa(mesa_destino)
    if mesa_origem == mesa_destino:
        raise DadosInvalidosError("Escolha uma mesa diferente.")
    momento = texto_data(agora)
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        comanda = _comanda_da_mesa_obrigatoria(conexao, mesa_origem)
        if comanda_da_mesa(conexao, mesa_destino):
            raise MesaOcupadaError(mesa_destino)
        vinculo = conexao.execute(
            "SELECT id, principal FROM comanda_mesas WHERE mesa = ? AND liberada_em IS NULL", (mesa_origem,)
        ).fetchone()
        conexao.execute("UPDATE comanda_mesas SET liberada_em = ? WHERE id = ?", (momento, vinculo["id"]))
        conexao.execute(
            "INSERT INTO comanda_mesas (comanda_id, mesa, principal, vinculada_em) VALUES (?, ?, ?, ?)",
            (comanda.id, mesa_destino, vinculo["principal"], momento),
        )
        registrar_auditoria(conexao, "mesa_transferida", usuario_id,
                            {"comanda_id": comanda.id, "de": mesa_origem, "para": mesa_destino}, agora=agora)
    return obter_comanda(conexao, comanda.id)


def juntar_mesas(conexao, mesa_principal, mesa_adicional, usuario_id, agora=None):
    """Junta a mesa adicional à comanda da mesa principal.

    Se a mesa adicional estiver ocupada, a comanda dela é unida à principal:
    itens, descontos, pagamentos e pessoas passam para a comanda principal, e a
    outra fica com status 'unida'. As mesas ficam vinculadas até o pagamento.
    """
    _validar_mesa(mesa_principal)
    _validar_mesa(mesa_adicional)
    if mesa_principal == mesa_adicional:
        raise DadosInvalidosError("Escolha uma mesa diferente.")
    momento = texto_data(agora)
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        principal = _comanda_da_mesa_obrigatoria(conexao, mesa_principal)
        outra = comanda_da_mesa(conexao, mesa_adicional)
        if outra is None:
            mesas_novas = [mesa_adicional]
            detalhes = {"comanda_id": principal.id, "mesa": mesa_adicional}
        else:
            if outra.id == principal.id:
                raise DadosInvalidosError("Estas mesas já estão juntas.")
            mesas_novas = outra.mesas
            for tabela in ("itens_comanda", "descontos", "pagamentos"):
                conexao.execute(f"UPDATE {tabela} SET comanda_id = ? WHERE comanda_id = ?",
                                (principal.id, outra.id))
            conexao.execute("UPDATE comanda_mesas SET liberada_em = ? WHERE comanda_id = ? AND liberada_em IS NULL",
                            (momento, outra.id))
            conexao.execute("UPDATE comandas SET pessoas = pessoas + ? WHERE id = ?",
                            (outra.pessoas, principal.id))
            conexao.execute(
                """UPDATE comandas SET status = 'unida', unida_a = ?, fechada_em = ?, fechada_por = ?
                   WHERE id = ?""",
                (principal.id, momento, usuario_id, outra.id),
            )
            detalhes = {"comanda_id": principal.id, "comanda_unida": outra.id, "mesas": mesas_novas}
        for mesa in mesas_novas:
            conexao.execute(
                "INSERT INTO comanda_mesas (comanda_id, mesa, principal, vinculada_em) VALUES (?, ?, 0, ?)",
                (principal.id, mesa, momento),
            )
        registrar_auditoria(conexao, "mesas_juntadas", usuario_id, detalhes, agora=agora)
    return obter_comanda(conexao, principal.id)


def cancelar_comanda(conexao, comanda_id, usuario_id, motivo=None, autorizacao=None, agora=None):
    """Cancela a comanda e libera as mesas.

    Sem itens: o operador cancela sozinho. Com itens: motivo + gerente, e cada
    item fica registrado como cancelado. Com pagamentos: recusado.
    """
    momento = texto_data(agora)
    with transacao(conexao):
        exigir_caixa_aberto(conexao)
        _comanda_editavel(conexao, comanda_id)
        if total_pago(conexao, comanda_id) > 0:
            raise ComandaComPagamentosError()
        itens = listar_itens(conexao, comanda_id)
        gerente_id = None
        if itens:
            motivo = exigir_texto(motivo, "o motivo do cancelamento", maximo=200)
            gerente_id = verificar_gerente(conexao, autorizacao).id
            for item in itens:
                _diminuir_item(conexao, item, item.quantidade, "cancelamento", usuario_id, motivo,
                               gerente_id, agora)
        else:
            motivo = texto_opcional(motivo, maximo=200)
        conexao.execute("UPDATE comanda_mesas SET liberada_em = ? WHERE comanda_id = ? AND liberada_em IS NULL",
                        (momento, comanda_id))
        conexao.execute(
            """UPDATE comandas SET status = 'cancelada', fechada_em = ?, fechada_por = ?,
                   motivo_cancelamento = ?, cancelamento_autorizado_por = ?
               WHERE id = ?""",
            (momento, usuario_id, motivo, gerente_id, comanda_id),
        )
    return obter_comanda(conexao, comanda_id)
