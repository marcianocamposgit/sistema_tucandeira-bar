"""Relatórios: totais de dinheiro, estoque e caixa por período."""
from datetime import date, datetime

import pytest

from services import caixa, comandas, configuracoes, pagamentos, produtos, relatorios
from services.erros import DadosInvalidosError

BRAHMA, HEINEKEN, WHISKY, CALABRESA, PASTEL = 1, 2, 3, 4, 5
DIA_14 = date(2026, 10, 14)
DIA_15 = date(2026, 10, 15)


def em(dia, hora, minuto=0):
    return datetime(2026, 10, dia, hora, minuto)


@pytest.fixture
def movimento(conexao, gerente, operador, autorizacao):
    """Uma noite de bar que passa da meia-noite (dia 14 para 15).

    Dia 14: Mesa 1 = 60,00 − desconto 5,00 = 55,00 (PIX 20 + dinheiro 35, recebeu 50);
            Balcão Ana = 24,00 (débito 10 estornado, depois crédito 24);
            Mesa 2: 1 pastel cancelado; Mesa 3 cancelada inteira (1 whisky).
    Dia 15 (00:10): Mesa 2 paga no PIX (1 pastel, 7,00). Caixa fechado à 01:00 com falta de 5,00 no dinheiro.
    """
    configuracoes.definir_desconto_permitido(conexao, True, gerente.id, autorizacao)
    caixa.abrir(conexao, 10000, operador.id, agora=em(14, 18))

    mesa1 = comandas.abrir_mesa(conexao, 1, operador.id, pessoas=2, agora=em(14, 19))
    comandas.lancar_item(conexao, mesa1.id, BRAHMA, operador.id, quantidade=4, agora=em(14, 19))
    comandas.lancar_item(conexao, mesa1.id, CALABRESA, operador.id, agora=em(14, 19))
    pagamentos.aplicar_desconto(conexao, mesa1.id, 500, "Cliente fiel", operador.id, autorizacao, agora=em(14, 20))
    pagamentos.registrar_pagamento(conexao, mesa1.id, "pix", 2000, operador.id, agora=em(14, 21))
    pagamentos.registrar_pagamento(conexao, mesa1.id, "dinheiro", 3500, operador.id, recebido_centavos=5000,
                                   agora=em(14, 23, 59))

    ana = comandas.abrir_balcao(conexao, "Ana", operador.id, agora=em(14, 20))
    comandas.lancar_item(conexao, ana.id, HEINEKEN, operador.id, quantidade=2, agora=em(14, 20))
    errado = pagamentos.registrar_pagamento(conexao, ana.id, "debito", 1000, operador.id, agora=em(14, 22))
    pagamentos.estornar_pagamento(conexao, errado.pagamento.id, "Forma errada", operador.id, autorizacao,
                                  agora=em(14, 22, 5))
    pagamentos.registrar_pagamento(conexao, ana.id, "credito", 2400, operador.id, agora=em(14, 23, 30))

    mesa2 = comandas.abrir_mesa(conexao, 2, operador.id, agora=em(14, 21))
    pastel = comandas.lancar_item(conexao, mesa2.id, PASTEL, operador.id, quantidade=2, agora=em(14, 21)).item
    comandas.cancelar_item(conexao, pastel.id, "Demorou demais", operador.id, autorizacao, agora=em(14, 23, 50))

    mesa3 = comandas.abrir_mesa(conexao, 3, operador.id, agora=em(14, 22))
    comandas.lancar_item(conexao, mesa3.id, WHISKY, operador.id, agora=em(14, 22))
    comandas.cancelar_comanda(conexao, mesa3.id, operador.id, motivo="Cliente foi embora", autorizacao=autorizacao,
                              agora=em(14, 23))

    pagamentos.registrar_pagamento(conexao, mesa2.id, "pix", 700, operador.id, agora=em(15, 0, 10))
    contado = {"dinheiro": 13000, "debito": 0, "credito": 2400, "pix": 2700}  # dinheiro esperado: 135,00
    caixa.fechar(conexao, contado, operador.id, autorizacao, agora=em(15, 1))
    return {"mesa1": mesa1, "ana": ana, "mesa2": mesa2, "mesa3": mesa3}


def test_periodos():
    quinta = date(2026, 10, 15)
    dia = relatorios.periodo("dia", quinta)
    assert (dia.inicio, dia.fim) == (quinta, quinta)
    intervalo = relatorios.periodo("intervalo", quinta, "2026-10-14", "2026-10-15")
    assert (intervalo.inicio, intervalo.fim) == (date(2026, 10, 14), quinta)
    semana = relatorios.periodo("semana", quinta)
    assert semana.inicio.weekday() == 0 and semana.fim == quinta and semana.inicio <= quinta
    assert relatorios.periodo("mes", quinta).inicio == date(2026, 10, 1)
    with pytest.raises(DadosInvalidosError):
        relatorios.periodo("intervalo", quinta, "2026-10-15", "2026-10-01")  # fim antes do início
    with pytest.raises(DadosInvalidosError):
        relatorios.periodo("intervalo", quinta, "", "2026-10-01")
    with pytest.raises(DadosInvalidosError):
        relatorios.periodo("intervalo", quinta, "2025-01-01", "2026-10-15")  # mais de um ano


def test_vendas_do_dia_e_formas_somam_o_total(conexao, movimento):
    dia14 = relatorios.periodo("dia", DIA_14)
    r = relatorios.resumo_vendas(conexao, dia14)
    assert (r.numero_vendas, r.subtotal_centavos, r.desconto_centavos, r.total_centavos) == (2, 8400, 500, 7900)
    # O débito estornado não conta; a soma das formas é o total vendido.
    assert r.por_forma == {"dinheiro": 3500, "debito": 0, "credito": 2400, "pix": 2000}
    assert sum(r.por_forma.values()) == r.total_centavos
    assert r.ticket_medio_centavos == 3950


def test_venda_depois_da_meia_noite_fica_no_outro_dia(conexao, movimento):
    r15 = relatorios.resumo_vendas(conexao, relatorios.periodo("dia", DIA_15))
    assert (r15.numero_vendas, r15.total_centavos, r15.por_forma["pix"]) == (1, 700, 700)
    juntos = relatorios.resumo_vendas(conexao, relatorios.periodo("intervalo", DIA_15, "2026-10-14", "2026-10-15"))
    assert (juntos.numero_vendas, juntos.total_centavos) == (3, 8600)
    vazio = relatorios.resumo_vendas(conexao, relatorios.periodo("dia", date(2026, 10, 13)))
    assert (vazio.numero_vendas, vazio.total_centavos, vazio.ticket_medio_centavos) == (0, 0, 0)


def test_produtos_mais_vendidos(conexao, movimento):
    vendidos = relatorios.produtos_mais_vendidos(conexao, relatorios.periodo("intervalo", DIA_15, "2026-10-14",
                                                                            "2026-10-15"))
    assert [(v.nome, v.quantidade, v.total_centavos) for v in vendidos] == [
        ("Brahma Lata", 4, 3200), ("Heineken Long Neck", 2, 2400), ("Porção Calabresa", 1, 2800),
        ("Pastel Carne", 1, 700)]
    # Cancelados (whisky e 1 pastel) não aparecem como vendidos.


def test_cancelamentos_e_descontos_com_responsavel(conexao, movimento):
    dia14 = relatorios.periodo("dia", DIA_14)
    ocorrencias = relatorios.cancelamentos(conexao, dia14)
    assert [(o.tipo, o.comanda, o.valor_centavos, o.motivo) for o in ocorrencias] == [
        ("item_cancelado", "Mesa 2", 700, "Demorou demais"),
        ("comanda_cancelada", "Mesa 3", 1500, "Cliente foi embora"),
        ("estorno", "Balcão — Ana", 1000, "Forma errada"),
    ]
    assert all(o.usuario_nome == "Operador" and o.autorizado_por_nome == "Gerente" for o in ocorrencias)
    assert ocorrencias[1].descricao == "1× Whisky 50ml"
    lista = relatorios.descontos(conexao, dia14)
    assert [(d.comanda, d.valor_centavos, d.motivo, d.autorizado_por_nome) for d in lista] == [
        ("Mesa 1", 500, "Cliente fiel", "Gerente")]
    assert relatorios.cancelamentos(conexao, relatorios.periodo("dia", DIA_15)) == []


def test_fechamento_de_caixa_com_diferencas(conexao, movimento):
    assert relatorios.fechamentos_caixa(conexao, relatorios.periodo("dia", DIA_14)) == []  # fechou no dia 15
    [f] = relatorios.fechamentos_caixa(conexao, relatorios.periodo("dia", DIA_15))
    diferencas = {c.forma: (c.esperado_centavos, c.contado_centavos, c.diferenca_centavos) for c in f.conferencias}
    assert diferencas == {"dinheiro": (13500, 13000, -500), "debito": (0, 0, 0), "credito": (2400, 2400, 0),
                          "pix": (2700, 2700, 0)}
    assert f.diferenca_total_centavos == -500


def test_estoque_em_alerta(conexao, gerente, autorizacao):
    produtos.ajustar_contagem(conexao, BRAHMA, 0, "Contagem", gerente.id, autorizacao)
    produtos.baixar_por_venda(conexao, WHISKY, 50)
    produtos.editar_produto(conexao, HEINEKEN, "Heineken Long Neck", 1, 1200, 99, gerente.id, autorizacao)
    assert [(p.nome, p.situacao_estoque) for p in relatorios.estoque_em_alerta(conexao)] == [
        ("Whisky 50ml", "negativo"), ("Brahma Lata", "zerado"), ("Heineken Long Neck", "abaixo_minimo")]


def test_csv_abre_certo_no_excel(conexao, movimento):
    dia14 = relatorios.periodo("dia", DIA_14)
    texto = relatorios.gerar_csv(relatorios.linhas_csv(conexao, "vendas", dia14))
    assert texto.startswith("﻿Item;Valor\r\n")
    assert "Total vendido (R$);79,00" in texto and "Descontos (R$);5,00" in texto and "Débito (R$);0,00" in texto
    caixas = relatorios.gerar_csv(relatorios.linhas_csv(conexao, "caixas", relatorios.periodo("dia", DIA_15)))
    assert caixas.splitlines()[1].endswith(";-5,00")
    cancelados = relatorios.linhas_csv(conexao, "cancelamentos", dia14)
    assert cancelados[1][:5] == ["14/10/2026 23:50", "Item cancelado", "Mesa 2", "1× Pastel Carne", "7,00"]
    with pytest.raises(DadosInvalidosError):
        relatorios.linhas_csv(conexao, "qualquer", dia14)
