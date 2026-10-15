from datetime import datetime

import pytest

from models import AutorizacaoGerente
from services import produtos
from services.erros import DadosInvalidosError, NomeDuplicadoError, PermissaoNegadaError
from tests.auxiliares import PIN_OPERADOR


def _id_categoria(conexao, nome):
    return conexao.execute("SELECT id FROM categorias WHERE nome = ?", (nome,)).fetchone()[0]


def test_cardapio_inicial(conexao):
    cardapio = produtos.cardapio(conexao)
    assert [c.nome for c, _ in cardapio] == ["Bebida", "Tira-Gosto", "Lanche", "Cigarro"]
    assert [p.nome for p in cardapio[0][1]] == ["Brahma Lata", "Heineken Long Neck", "Whisky 50ml"]


def test_cadastrar_produto_com_estoque_inicial(conexao, gerente, autorizacao):
    p = produtos.cadastrar_produto(conexao, "Skol Lata", _id_categoria(conexao, "Bebida"), 700,
                                   gerente.id, autorizacao, estoque_inicial=24, estoque_minimo=6)
    assert (p.estoque, p.estoque_minimo, p.categoria_nome) == (24, 6, "Bebida")
    movimentos = produtos.listar_movimentos(conexao, p.id)
    assert [(m.tipo, m.quantidade, m.motivo) for m in movimentos] == [("entrada", 24, "Estoque inicial")]


def test_nome_duplicado_e_preco_negativo(conexao, gerente, autorizacao):
    bebida = _id_categoria(conexao, "Bebida")
    with pytest.raises(NomeDuplicadoError):
        produtos.cadastrar_produto(conexao, "brahma lata", bebida, 800, gerente.id, autorizacao)
    with pytest.raises(DadosInvalidosError):
        produtos.cadastrar_produto(conexao, "Skol", bebida, -100, gerente.id, autorizacao)
    with pytest.raises(DadosInvalidosError):
        produtos.cadastrar_produto(conexao, "Skol", bebida, 7.5, gerente.id, autorizacao)


def test_cadastro_exige_gerente(conexao, gerente, operador):
    with pytest.raises(PermissaoNegadaError):
        produtos.cadastrar_produto(conexao, "Skol", _id_categoria(conexao, "Bebida"), 700, operador.id,
                                   AutorizacaoGerente(operador.id, PIN_OPERADOR))


def test_editar_nao_mexe_no_estoque(conexao, gerente, autorizacao):
    p = produtos.editar_produto(conexao, 1, "Brahma Lata 350ml", _id_categoria(conexao, "Bebida"), 900, 10,
                                gerente.id, autorizacao)
    assert (p.nome, p.preco_centavos, p.estoque_minimo, p.estoque) == ("Brahma Lata 350ml", 900, 10, 30)


def test_produto_desativado_some_do_cardapio(conexao, gerente, autorizacao):
    produtos.desativar_produto(conexao, 1, gerente.id, autorizacao)
    nomes = [p.nome for _, lista in produtos.cardapio(conexao) for p in lista]
    assert "Brahma Lata" not in nomes
    assert len(produtos.listar_produtos(conexao, incluir_inativos=True)) == 6
    produtos.reativar_produto(conexao, 1, gerente.id, autorizacao)
    assert "Brahma Lata" in [p.nome for _, lista in produtos.cardapio(conexao) for p in lista]


def test_categorias(conexao, gerente, autorizacao):
    nova = produtos.criar_categoria(conexao, "Drinks", gerente.id, autorizacao)
    assert nova.ordem == 5
    with pytest.raises(NomeDuplicadoError):
        produtos.criar_categoria(conexao, "drinks", gerente.id, autorizacao)
    produtos.renomear_categoria(conexao, nova.id, "Drinques", gerente.id, autorizacao)
    # Categoria com produtos ativos não pode ser desativada.
    with pytest.raises(DadosInvalidosError):
        produtos.desativar_categoria(conexao, _id_categoria(conexao, "Cigarro"), gerente.id, autorizacao)
    produtos.desativar_categoria(conexao, nova.id, gerente.id, autorizacao)
    assert "Drinques" not in [c.nome for c in produtos.listar_categorias(conexao)]
    # Não dá para cadastrar produto em categoria desativada.
    with pytest.raises(DadosInvalidosError):
        produtos.cadastrar_produto(conexao, "Mojito", nova.id, 2000, gerente.id, autorizacao)


def test_entrada_perda_e_ajuste(conexao, gerente, operador, autorizacao):
    # Entrada pode ser feita pelo operador, sem PIN.
    assert produtos.registrar_entrada(conexao, 1, 10, operador.id, custo_unitario_centavos=450).estoque == 40
    assert produtos.registrar_perda(conexao, 1, 2, "Latas amassadas", operador.id, autorizacao).estoque == 38
    p = produtos.ajustar_contagem(conexao, 1, 35, "Contagem de sexta", operador.id, autorizacao)
    assert p.estoque == 35
    movimentos = produtos.listar_movimentos(conexao, 1)
    assert [(m.tipo, m.quantidade) for m in movimentos] == [("ajuste", -3), ("perda", -2), ("entrada", 10)]
    assert movimentos[0].estoque_contado == 35
    assert movimentos[0].autorizado_por_nome == "Gerente"


def test_perda_e_ajuste_exigem_gerente_e_motivo(conexao, gerente, operador, autorizacao):
    sem_pin = AutorizacaoGerente(gerente.id, "0000")
    with pytest.raises(PermissaoNegadaError):
        produtos.registrar_perda(conexao, 1, 2, "Quebrou", operador.id, sem_pin)
    with pytest.raises(PermissaoNegadaError):
        produtos.ajustar_contagem(conexao, 1, 20, "Contagem", operador.id, None)
    with pytest.raises(DadosInvalidosError):
        produtos.registrar_perda(conexao, 1, 2, "  ", operador.id, autorizacao)
    assert produtos.obter_produto(conexao, 1).estoque == 30
    assert produtos.listar_movimentos(conexao, 1) == []


def test_baixa_por_venda_pode_ficar_negativa(conexao, gerente):
    from database import transacao
    with transacao(conexao):
        p = produtos.baixar_por_venda(conexao, 4, 10)  # Porção Calabresa tem 8
    assert p.estoque == -2 and p.situacao_estoque == "negativo"
    assert "Porção Calabresa" in [a.nome for a in produtos.listar_alertas_estoque(conexao)]


def test_situacao_do_estoque(conexao, gerente, autorizacao):
    produtos.editar_produto(conexao, 1, "Brahma Lata", _id_categoria(conexao, "Bebida"), 800, 40,
                            gerente.id, autorizacao)
    assert produtos.obter_produto(conexao, 1).situacao_estoque == "abaixo_minimo"
    produtos.ajustar_contagem(conexao, 2, 0, "Acabou", gerente.id, autorizacao)
    assert produtos.obter_produto(conexao, 2).situacao_estoque == "zerado"
    assert produtos.obter_produto(conexao, 3).situacao_estoque == "ok"


def test_historico_fecha_com_o_estoque_incluindo_vendas(conexao, gerente, operador, autorizacao):
    from services import caixa, comandas, pagamentos
    skol = produtos.cadastrar_produto(conexao, "Skol Lata", _id_categoria(conexao, "Bebida"), 700,
                                      gerente.id, autorizacao, estoque_inicial=10,
                                      agora=datetime(2026, 10, 15, 18, 0))
    produtos.registrar_entrada(conexao, skol.id, 12, operador.id, agora=datetime(2026, 10, 15, 18, 5))
    produtos.registrar_perda(conexao, skol.id, 2, "Lata amassada", operador.id, autorizacao,
                             agora=datetime(2026, 10, 15, 18, 10))
    caixa.abrir(conexao, 0, operador.id, agora=datetime(2026, 10, 15, 18, 15))
    c = comandas.abrir_balcao(conexao, "Ana", operador.id, agora=datetime(2026, 10, 15, 18, 20))
    comandas.lancar_item(conexao, c.id, skol.id, operador.id, quantidade=3, agora=datetime(2026, 10, 15, 18, 20))
    pagamentos.registrar_pagamento(conexao, c.id, "pix", 2100, operador.id, agora=datetime(2026, 10, 15, 18, 30))
    produtos.ajustar_contagem(conexao, skol.id, 15, "Contagem do fim do dia", operador.id, autorizacao,
                              agora=datetime(2026, 10, 15, 19, 0))

    historico = produtos.historico_estoque(conexao, skol.id)
    assert [(h.tipo, h.quantidade) for h in historico] == [
        ("ajuste", -2), ("venda", -3), ("perda", -2), ("entrada", 12), ("entrada", 10)]
    assert historico[1].descricao == f"Comanda {c.id}" and historico[1].tipo_nome == "Venda"
    assert historico[0].autorizado_por_nome == "Gerente"
    # A soma do histórico é o estoque atual.
    assert sum(h.quantidade for h in historico) == produtos.obter_produto(conexao, skol.id).estoque == 15


def test_assinatura_do_cardapio_muda_quando_o_cardapio_muda(conexao, gerente, autorizacao):
    antes = produtos.assinatura_cardapio(conexao)
    assert produtos.assinatura_cardapio(conexao) == antes  # nada mudou
    produtos.registrar_entrada(conexao, 1, 5, gerente.id)  # estoque não muda o cardápio
    assert produtos.assinatura_cardapio(conexao) == antes
    produtos.desativar_produto(conexao, 1, gerente.id, autorizacao)
    depois = produtos.assinatura_cardapio(conexao)
    assert depois != antes
    produtos.criar_categoria(conexao, "Doses", gerente.id, autorizacao)
    assert produtos.assinatura_cardapio(conexao) != depois
