import pytest

from services import caixa, comandas
from services.erros import (
    CaixaFechadoError,
    CaixaJaAbertoError,
    ComandasAbertasError,
    DadosInvalidosError,
    PermissaoNegadaError,
)
from tests.auxiliares import fechar_comanda_como_paga, inserir_pagamento

CONTADO_ZERO = {"dinheiro": 0, "debito": 0, "credito": 0, "pix": 0}


def test_abrir_e_so_um_caixa_aberto(conexao, operador):
    assert caixa.caixa_aberto(conexao) is None
    with pytest.raises(CaixaFechadoError):
        caixa.exigir_caixa_aberto(conexao)
    aberto = caixa.abrir(conexao, 10000, operador.id)
    assert aberto.aberto and aberto.valor_inicial_centavos == 10000
    with pytest.raises(CaixaJaAbertoError):
        caixa.abrir(conexao, 5000, operador.id)


def test_sangria_exige_gerente_e_motivo(conexao, operador, autorizacao, caixa_aberto):
    with pytest.raises(PermissaoNegadaError):
        caixa.registrar_sangria(conexao, 2000, "Pagamento do gelo", operador.id, None)
    with pytest.raises(DadosInvalidosError):
        caixa.registrar_sangria(conexao, 2000, "", operador.id, autorizacao)
    with pytest.raises(DadosInvalidosError):
        caixa.registrar_suprimento(conexao, 0, "Troco", operador.id)
    # Não dá para tirar mais dinheiro do que deveria haver no caixa.
    with pytest.raises(DadosInvalidosError):
        caixa.registrar_sangria(conexao, 10001, "Depósito", operador.id, autorizacao)


def test_conferencia_e_fechamento(conexao, gerente, operador, autorizacao, caixa_aberto):
    caixa.registrar_suprimento(conexao, 5000, "Reforço de troco", operador.id)
    caixa.registrar_sangria(conexao, 3000, "Compra de gelo", operador.id, autorizacao)
    mesa = comandas.abrir_mesa(conexao, 1, operador.id)
    inserir_pagamento(conexao, mesa.id, "dinheiro", 4000, operador.id)
    inserir_pagamento(conexao, mesa.id, "pix", 2500, operador.id)
    inserir_pagamento(conexao, mesa.id, "debito", 1800, operador.id)
    inserir_pagamento(conexao, mesa.id, "credito", 9900, operador.id, estornado=True)  # não conta
    fechar_comanda_como_paga(conexao, mesa.id, operador.id)

    esperado = caixa.calcular_esperado(conexao, caixa_aberto.id)
    # Dinheiro = fundo 100 + vendas 40 + suprimento 50 − sangria 30 = 160
    assert esperado == {"dinheiro": 16000, "debito": 1800, "credito": 0, "pix": 2500}

    contado = {"dinheiro": 15800, "debito": 1800, "credito": 0, "pix": 2500}
    previa = caixa.conferencia(conexao, contado)
    assert [c.diferenca_centavos for c in previa] == [-200, 0, 0, 0]

    resultado = caixa.fechar(conexao, contado, operador.id, autorizacao, observacao="Faltou troco")
    assert not resultado.caixa.aberto and resultado.caixa.fechado_por == gerente.id
    assert resultado.diferenca_total_centavos == -200
    gravada = caixa.obter_conferencia(conexao, caixa_aberto.id)
    assert [(c.forma, c.esperado_centavos, c.contado_centavos) for c in gravada] == [
        ("dinheiro", 16000, 15800), ("debito", 1800, 1800), ("credito", 0, 0), ("pix", 2500, 2500)]
    assert caixa.caixa_aberto(conexao) is None


def test_fechar_exige_gerente_e_todas_as_formas(conexao, operador, autorizacao, caixa_aberto):
    with pytest.raises(PermissaoNegadaError):
        caixa.fechar(conexao, CONTADO_ZERO, operador.id, None)
    with pytest.raises(DadosInvalidosError):
        caixa.fechar(conexao, {"dinheiro": 10000}, operador.id, autorizacao)


def test_nao_fecha_com_comandas_pendentes(conexao, operador, autorizacao, caixa_aberto):
    mesa = comandas.abrir_mesa(conexao, 2, operador.id)
    balcao = comandas.abrir_balcao(conexao, "João", operador.id)
    comandas.lancar_item(conexao, balcao.id, 1, operador.id)
    comandas.marcar_conta_pedida(conexao, balcao.id, operador.id)
    with pytest.raises(ComandasAbertasError) as erro:
        caixa.fechar(conexao, {**CONTADO_ZERO, "dinheiro": 10000}, operador.id, autorizacao)
    assert [c.identificacao for c in erro.value.comandas] == ["Mesa 2", "Balcão — João"]
    assert erro.value.comandas[1].status == "conta_pedida"
    assert erro.value.comandas[1].saldo_centavos == 800
    assert caixa.caixa_aberto(conexao) is not None

    # Comanda cancelada não bloqueia o fechamento.
    comandas.cancelar_comanda(conexao, mesa.id, operador.id)
    inserir_pagamento(conexao, balcao.id, "pix", 800, operador.id)
    fechar_comanda_como_paga(conexao, balcao.id, operador.id)
    caixa.fechar(conexao, {**CONTADO_ZERO, "dinheiro": 10000, "pix": 800}, operador.id, autorizacao)
    assert caixa.caixa_aberto(conexao) is None
