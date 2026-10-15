import threading

import pytest

import config
from database import conectar, migrar
from models import AutorizacaoGerente
from services import caixa, comandas, configuracoes, pagamentos, produtos
from services.erros import (
    ComandaFechadaError,
    DadosInvalidosError,
    DescontoNaoPermitidoError,
    PermissaoNegadaError,
    TotalAbaixoDoPagoError,
)

BRAHMA, HEINEKEN, WHISKY, CALABRESA, PASTEL, MARLBORO = 1, 2, 3, 4, 5, 6


@pytest.fixture
def desconto_ligado(conexao, gerente, autorizacao):
    configuracoes.definir_desconto_permitido(conexao, True, gerente.id, autorizacao)


@pytest.fixture
def mesa(conexao, operador, caixa_aberto):
    """Mesa 1 com 3 pessoas: 4 Brahma (32,00) + 1 Calabresa (28,00) + 2 Pastel (14,00) = 74,00."""
    c = comandas.abrir_mesa(conexao, 1, operador.id, pessoas=3)
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id, quantidade=4)
    comandas.lancar_item(conexao, c.id, CALABRESA, operador.id)
    comandas.lancar_item(conexao, c.id, PASTEL, operador.id, quantidade=2)
    return c


def test_pagamento_total_fecha_a_venda(conexao, operador, mesa):
    resultado = pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 7400, operador.id)
    assert resultado.quitada and resultado.conta.saldo_centavos == 0
    venda = resultado.venda
    assert (venda.subtotal_centavos, venda.desconto_centavos, venda.total_centavos, venda.pessoas) == (7400, 0, 7400, 3)
    assert [(i.nome_produto, i.quantidade, i.subtotal_centavos) for i in venda.itens] == [
        ("Brahma Lata", 4, 3200), ("Porção Calabresa", 1, 2800), ("Pastel Carne", 2, 1400)]
    assert comandas.obter_comanda(conexao, mesa.id).status == "paga"
    assert comandas.comanda_da_mesa(conexao, 1) is None
    # O estoque só baixa agora, no fechamento.
    assert produtos.obter_produto(conexao, BRAHMA).estoque == 26
    assert produtos.obter_produto(conexao, CALABRESA).estoque == 7


def test_lancamentos_iguais_viram_uma_linha_na_venda(conexao, operador, caixa_aberto):
    c = comandas.abrir_balcao(conexao, "Ana", operador.id)
    for _ in range(3):
        comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)
    venda = pagamentos.registrar_pagamento(conexao, c.id, "debito", 2400, operador.id).venda
    assert [(i.nome_produto, i.quantidade) for i in venda.itens] == [("Brahma Lata", 3)]


def test_pagamento_parcial_com_quem_recebeu(conexao, gerente, operador, mesa):
    # Uma pessoa paga a parte dela e vai embora.
    r1 = pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 2500, operador.id)
    assert not r1.quitada
    assert (r1.conta.total_centavos, r1.conta.pago_centavos, r1.conta.saldo_centavos) == (7400, 2500, 4900)
    assert r1.pagamento.recebido_por == operador.id
    # Ainda dá para lançar mais um item: o saldo sobe.
    comandas.lancar_item(conexao, mesa.id, HEINEKEN, operador.id)
    assert comandas.calcular_conta(conexao, mesa.id).saldo_centavos == 6100
    pagamentos.registrar_pagamento(conexao, mesa.id, "debito", 3000, gerente.id)
    final = pagamentos.registrar_pagamento(conexao, mesa.id, "dinheiro", 3100, operador.id, recebido_centavos=5000)
    assert final.quitada and final.pagamento.troco_centavos == 1900
    lista = pagamentos.listar_pagamentos(conexao, mesa.id)
    assert [(p.forma, p.valor_centavos, p.recebido_por_nome) for p in lista] == [
        ("pix", 2500, "Operador"), ("debito", 3000, "Gerente"), ("dinheiro", 3100, "Operador")]


def test_valor_por_pessoa(conexao, operador, mesa):
    conta = comandas.calcular_conta(conexao, mesa.id)
    assert conta.por_pessoa_centavos == 2467  # 74,00 / 3 = 24,666... (arredonda para cima)


def test_nao_paga_mais_que_o_saldo(conexao, operador, mesa):
    with pytest.raises(DadosInvalidosError):
        pagamentos.registrar_pagamento(conexao, mesa.id, "credito", 7401, operador.id)
    with pytest.raises(DadosInvalidosError):
        pagamentos.registrar_pagamento(conexao, mesa.id, "dinheiro", 7500, operador.id, recebido_centavos=10000)
    assert pagamentos.listar_pagamentos(conexao, mesa.id) == []


def test_troco_so_em_dinheiro_e_recebido_suficiente(conexao, operador, mesa):
    with pytest.raises(DadosInvalidosError):
        pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 2000, operador.id, recebido_centavos=5000)
    with pytest.raises(DadosInvalidosError):
        pagamentos.registrar_pagamento(conexao, mesa.id, "dinheiro", 2000, operador.id, recebido_centavos=1000)
    r = pagamentos.registrar_pagamento(conexao, mesa.id, "dinheiro", 2000, operador.id)
    assert (r.pagamento.recebido_centavos, r.pagamento.troco_centavos) == (2000, 0)
    assert pagamentos.calcular_troco(7400, 10000) == 2600


@pytest.mark.parametrize("forma, valor", [("cheque", 100), ("pix", 0), ("pix", -5), ("pix", 10.5)])
def test_dados_invalidos(conexao, operador, mesa, forma, valor):
    with pytest.raises(DadosInvalidosError):
        pagamentos.registrar_pagamento(conexao, mesa.id, forma, valor, operador.id)


def test_comanda_vazia_nao_tem_o_que_pagar(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 2, operador.id)
    with pytest.raises(DadosInvalidosError):
        pagamentos.registrar_pagamento(conexao, c.id, "pix", 100, operador.id)


def test_comanda_paga_nao_recebe_mais_pagamento(conexao, operador, mesa):
    pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 7400, operador.id)
    with pytest.raises(ComandaFechadaError):
        pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 100, operador.id)
    with pytest.raises(ComandaFechadaError):
        comandas.lancar_item(conexao, mesa.id, BRAHMA, operador.id)


def test_estorno(conexao, gerente, operador, autorizacao, mesa):
    errado = pagamentos.registrar_pagamento(conexao, mesa.id, "credito", 5000, operador.id).pagamento
    with pytest.raises(PermissaoNegadaError):
        pagamentos.estornar_pagamento(conexao, errado.id, "Era débito", operador.id, None)
    with pytest.raises(DadosInvalidosError):
        pagamentos.estornar_pagamento(conexao, errado.id, " ", operador.id, autorizacao)
    r = pagamentos.estornar_pagamento(conexao, errado.id, "Era débito", operador.id, autorizacao)
    assert r.pagamento.estornado and r.pagamento.estorno_autorizado_por == gerente.id
    assert (r.conta.pago_centavos, r.conta.saldo_centavos) == (0, 7400)
    # Não é apagado: continua na lista, marcado como estornado.
    assert [p.estornado for p in pagamentos.listar_pagamentos(conexao, mesa.id)] == [True]
    assert pagamentos.listar_pagamentos(conexao, mesa.id, incluir_estornados=False) == []
    with pytest.raises(DadosInvalidosError):
        pagamentos.estornar_pagamento(conexao, errado.id, "De novo", operador.id, autorizacao)
    # Não conta na conferência do caixa.
    assert caixa.calcular_esperado(conexao, mesa.caixa_id)["credito"] == 0


def test_nao_estorna_comanda_ja_paga(conexao, operador, autorizacao, mesa):
    pagamento = pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 7400, operador.id).pagamento
    with pytest.raises(ComandaFechadaError):
        pagamentos.estornar_pagamento(conexao, pagamento.id, "Erro", operador.id, autorizacao)


def test_desconto_desligado_por_padrao(conexao, operador, autorizacao, mesa):
    assert not configuracoes.desconto_permitido(conexao)
    with pytest.raises(DescontoNaoPermitidoError):
        pagamentos.aplicar_desconto(conexao, mesa.id, 400, "Cliente frequente", operador.id, autorizacao)
    assert pagamentos.listar_descontos(conexao, mesa.id) == []


def test_so_gerente_liga_e_desliga_o_desconto(conexao, gerente, operador, autorizacao):
    with pytest.raises(PermissaoNegadaError):
        configuracoes.definir_desconto_permitido(conexao, True, operador.id, None)
    configuracoes.definir_desconto_permitido(conexao, True, operador.id, autorizacao)
    assert configuracoes.desconto_permitido(conexao)
    configuracoes.definir_desconto_permitido(conexao, False, operador.id, autorizacao)
    assert not configuracoes.desconto_permitido(conexao)
    registros = conexao.execute(
        "SELECT acao, usuario_id, autorizado_por FROM auditoria WHERE acao LIKE 'desconto_%' ORDER BY id").fetchall()
    assert [tuple(r) for r in registros] == [("desconto_ligado", operador.id, gerente.id),
                                             ("desconto_desligado", operador.id, gerente.id)]


def test_desconto_em_reais(conexao, gerente, operador, autorizacao, desconto_ligado, mesa):
    with pytest.raises(PermissaoNegadaError):
        pagamentos.aplicar_desconto(conexao, mesa.id, 400, "Cliente frequente", operador.id,
                                    AutorizacaoGerente(gerente.id, "0000"))
    with pytest.raises(DadosInvalidosError):
        pagamentos.aplicar_desconto(conexao, mesa.id, 400, "", operador.id, autorizacao)
    with pytest.raises(DadosInvalidosError):
        pagamentos.aplicar_desconto(conexao, mesa.id, 4.5, "Cliente frequente", operador.id, autorizacao)
    r = pagamentos.aplicar_desconto(conexao, mesa.id, 400, "Cliente frequente", operador.id, autorizacao)
    assert (r.conta.desconto_centavos, r.conta.total_centavos) == (400, 7000)
    descontos = pagamentos.listar_descontos(conexao, mesa.id)
    assert [(d.valor_centavos, d.motivo, d.usuario_id, d.autorizado_por) for d in descontos] == [
        (400, "Cliente frequente", operador.id, gerente.id)]
    venda = pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 7000, operador.id).venda
    assert (venda.subtotal_centavos, venda.desconto_centavos, venda.total_centavos) == (7400, 400, 7000)


def test_desconto_nao_passa_da_conta_nem_do_saldo(conexao, operador, autorizacao, desconto_ligado, mesa):
    with pytest.raises(DadosInvalidosError):
        pagamentos.aplicar_desconto(conexao, mesa.id, 7401, "Erro", operador.id, autorizacao)
    pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 7000, operador.id)
    with pytest.raises(TotalAbaixoDoPagoError):
        pagamentos.aplicar_desconto(conexao, mesa.id, 500, "Atraso", operador.id, autorizacao)


def test_desconto_que_quita_fecha_a_venda(conexao, operador, autorizacao, desconto_ligado, mesa):
    pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 7000, operador.id)
    r = pagamentos.aplicar_desconto(conexao, mesa.id, 400, "Arredondamento", operador.id, autorizacao)
    assert r.quitada and r.venda.total_centavos == 7000


def test_cortesia_total(conexao, operador, autorizacao, desconto_ligado, mesa):
    r = pagamentos.aplicar_desconto(conexao, mesa.id, 7400, "Cortesia da casa", operador.id, autorizacao)
    assert r.quitada and r.venda.total_centavos == 0
    assert produtos.obter_produto(conexao, BRAHMA).estoque == 26  # cortesia também baixa estoque


def test_remover_desconto_mesmo_com_desconto_desligado(conexao, gerente, operador, autorizacao,
                                                      desconto_ligado, mesa):
    pagamentos.aplicar_desconto(conexao, mesa.id, 1000, "Engano", operador.id, autorizacao)
    configuracoes.definir_desconto_permitido(conexao, False, gerente.id, autorizacao)
    desconto = pagamentos.listar_descontos(conexao, mesa.id)[0]
    with pytest.raises(PermissaoNegadaError):
        pagamentos.remover_desconto(conexao, desconto.id, operador.id, None)
    r = pagamentos.remover_desconto(conexao, desconto.id, operador.id, autorizacao)
    assert r.conta.total_centavos == 7400
    registro = conexao.execute("SELECT detalhes FROM auditoria WHERE acao = 'desconto_removido'").fetchone()
    assert '"motivo": "Engano"' in registro["detalhes"]


def test_remover_item_nao_deixa_desconto_maior_que_a_conta(conexao, operador, autorizacao, desconto_ligado,
                                                          caixa_aberto):
    c = comandas.abrir_balcao(conexao, "Ana", operador.id)
    item = comandas.lancar_item(conexao, c.id, WHISKY, operador.id).item
    comandas.lancar_item(conexao, c.id, PASTEL, operador.id)
    pagamentos.aplicar_desconto(conexao, c.id, 1000, "Promoção", operador.id, autorizacao)
    with pytest.raises(DadosInvalidosError):
        comandas.remover_item(conexao, item.id, operador.id)


def test_avisos_de_estoque_no_fechamento(conexao, operador, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    comandas.lancar_item(conexao, c.id, CALABRESA, operador.id, quantidade=9)  # estoque 8
    r = pagamentos.registrar_pagamento(conexao, c.id, "credito", 9 * 2800, operador.id)
    assert r.avisos_estoque == ["Porção Calabresa: estoque negativo (-1)."]
    assert produtos.obter_produto(conexao, CALABRESA).situacao_estoque == "negativo"


def test_itens_removidos_e_cancelados_nao_entram_na_venda(conexao, operador, autorizacao, caixa_aberto):
    c = comandas.abrir_mesa(conexao, 1, operador.id)
    removido = comandas.lancar_item(conexao, c.id, WHISKY, operador.id).item
    comandas.remover_item(conexao, removido.id, operador.id)
    cancelado = comandas.lancar_item(conexao, c.id, HEINEKEN, operador.id, quantidade=2).item
    comandas.cancelar_item(conexao, cancelado.id, "Cliente desistiu", operador.id, autorizacao)
    comandas.lancar_item(conexao, c.id, BRAHMA, operador.id)
    venda = pagamentos.registrar_pagamento(conexao, c.id, "pix", 800 + 1200, operador.id).venda
    assert [(i.nome_produto, i.quantidade) for i in venda.itens] == [("Heineken Long Neck", 1), ("Brahma Lata", 1)]
    assert produtos.obter_produto(conexao, WHISKY).estoque == 12


def test_mesas_juntas_sao_liberadas_no_pagamento(conexao, operador, caixa_aberto):
    a = comandas.abrir_mesa(conexao, 3, operador.id)
    b = comandas.abrir_mesa(conexao, 4, operador.id)
    comandas.lancar_item(conexao, a.id, BRAHMA, operador.id)
    comandas.lancar_item(conexao, b.id, BRAHMA, operador.id, quantidade=2)
    pagamentos.registrar_pagamento(conexao, b.id, "pix", 800, operador.id)  # alguém da mesa 4 já pagou uma parte
    comandas.juntar_mesas(conexao, 3, 4, operador.id)
    assert comandas.calcular_conta(conexao, a.id).saldo_centavos == 2400 - 800
    r = pagamentos.registrar_pagamento(conexao, a.id, "dinheiro", 1600, operador.id)
    assert r.quitada and r.venda.total_centavos == 2400
    assert comandas.comanda_da_mesa(conexao, 3) is None and comandas.comanda_da_mesa(conexao, 4) is None
    assert comandas.obter_comanda(conexao, a.id).mesas == [3, 4]  # histórico da comanda paga


def test_conferencia_do_caixa_com_pagamentos_reais(conexao, operador, autorizacao, mesa, caixa_aberto):
    pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 2000, operador.id)
    estorno = pagamentos.registrar_pagamento(conexao, mesa.id, "credito", 1000, operador.id).pagamento
    pagamentos.estornar_pagamento(conexao, estorno.id, "Cartão recusado", operador.id, autorizacao)
    pagamentos.registrar_pagamento(conexao, mesa.id, "debito", 1400, operador.id)
    pagamentos.registrar_pagamento(conexao, mesa.id, "dinheiro", 4000, operador.id, recebido_centavos=5000)
    esperado = caixa.calcular_esperado(conexao, caixa_aberto.id)
    # Dinheiro: fundo 100,00 + 40,00 (o troco de 10,00 não fica no caixa)
    assert esperado == {"dinheiro": 14000, "debito": 1400, "credito": 0, "pix": 2000}
    resultado = caixa.fechar(conexao, esperado, operador.id, autorizacao)
    assert resultado.diferenca_total_centavos == 0


def test_dois_aparelhos_pagando_o_saldo_ao_mesmo_tempo(tmp_path, monkeypatch):
    """Dois aparelhos tentam pagar o saldo inteiro da mesma comanda: só um pagamento vale."""
    from services import usuarios
    monkeypatch.setattr(config, "ITERACOES_PIN", 1000)
    caminho = tmp_path / "pagamento.db"
    con = conectar(caminho)
    migrar(con)
    garcom = usuarios.criar_gerente_inicial(con, "Garçom", "1234")
    caixa.abrir(con, 0, garcom.id)
    comanda_id = comandas.abrir_mesa(con, 1, garcom.id).id
    comandas.lancar_item(con, comanda_id, BRAHMA, garcom.id, quantidade=2)
    con.close()

    resultados = []
    barreira = threading.Barrier(2)

    def aparelho(forma):
        c = conectar(caminho)
        try:
            barreira.wait()
            pagamentos.registrar_pagamento(c, comanda_id, forma, 1600, garcom.id)
            resultados.append("pagou")
        except (ComandaFechadaError, DadosInvalidosError):
            resultados.append("recusado")
        finally:
            c.close()

    threads = [threading.Thread(target=aparelho, args=(f,)) for f in ("pix", "credito")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(resultados) == ["pagou", "recusado"]
    con = conectar(caminho)
    assert con.execute("SELECT COUNT(*) FROM pagamentos").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM vendas").fetchone()[0] == 1
    assert produtos.obter_produto(con, BRAHMA).estoque == 28
    con.close()


# ============================================================
# ENVIO REPETIDO (toque duplo, rede instável, F5)
# ============================================================
def test_envio_repetido_de_pagamento_parcial_nao_cobra_duas_vezes(conexao, operador, mesa):
    primeiro = pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 2500, operador.id, chave="envio-1")
    de_novo = pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 2500, operador.id, chave="envio-1")
    assert not primeiro.repetido and de_novo.repetido
    assert de_novo.pagamento.id == primeiro.pagamento.id
    assert de_novo.conta.pago_centavos == 2500 and de_novo.conta.saldo_centavos == 4900
    # Outro envio (outra chave) com o mesmo valor é outro pagamento de verdade.
    pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 2500, operador.id, chave="envio-2")
    assert comandas.calcular_conta(conexao, mesa.id).pago_centavos == 5000


def test_envio_repetido_depois_de_quitar_devolve_a_venda(conexao, operador, mesa):
    pago = pagamentos.registrar_pagamento(conexao, mesa.id, "dinheiro", 7400, operador.id,
                                          recebido_centavos=10000, chave="quitar")
    de_novo = pagamentos.registrar_pagamento(conexao, mesa.id, "dinheiro", 7400, operador.id,
                                             recebido_centavos=10000, chave="quitar")
    assert pago.quitada and de_novo.quitada and de_novo.repetido
    assert de_novo.venda.id == pago.venda.id and de_novo.pagamento.troco_centavos == 2600
    assert conexao.execute("SELECT COUNT(*) FROM pagamentos").fetchone()[0] == 1
    assert produtos.obter_produto(conexao, BRAHMA).estoque == 26  # baixou uma vez só


def test_chave_de_envio_de_outra_comanda_e_recusada(conexao, operador, mesa):
    pagamentos.registrar_pagamento(conexao, mesa.id, "pix", 1000, operador.id, chave="envio-x")
    outra = comandas.abrir_balcao(conexao, "Ana", operador.id)
    comandas.lancar_item(conexao, outra.id, BRAHMA, operador.id)
    with pytest.raises(DadosInvalidosError):
        pagamentos.registrar_pagamento(conexao, outra.id, "pix", 800, operador.id, chave="envio-x")
    assert comandas.calcular_conta(conexao, outra.id).pago_centavos == 0


def test_mesmo_envio_chegando_duas_vezes_ao_mesmo_tempo(tmp_path, monkeypatch):
    """O mesmo formulário de pagamento parcial chega duas vezes juntas: só um pagamento vale."""
    from services import usuarios
    monkeypatch.setattr(config, "ITERACOES_PIN", 1000)
    caminho = tmp_path / "envio.db"
    con = conectar(caminho)
    migrar(con)
    garcom = usuarios.criar_gerente_inicial(con, "Garçom", "1234")
    caixa.abrir(con, 0, garcom.id)
    comanda_id = comandas.abrir_mesa(con, 1, garcom.id).id
    comandas.lancar_item(con, comanda_id, BRAHMA, garcom.id, quantidade=4)
    con.close()

    repetidos = []
    barreira = threading.Barrier(2)

    def envio():
        c = conectar(caminho)
        try:
            barreira.wait()
            repetidos.append(pagamentos.registrar_pagamento(c, comanda_id, "pix", 1000, garcom.id,
                                                            chave="mesmo-envio").repetido)
        finally:
            c.close()

    threads = [threading.Thread(target=envio) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(repetidos) == [False, True]
    con = conectar(caminho)
    assert con.execute("SELECT COUNT(*) FROM pagamentos").fetchone()[0] == 1
    assert comandas.calcular_conta(con, comanda_id).saldo_centavos == 2200
    con.close()
