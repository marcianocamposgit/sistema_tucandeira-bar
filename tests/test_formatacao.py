import pytest

from services.erros import DadosInvalidosError
from services.formatacao import formatar_moeda, ler_moeda


@pytest.mark.parametrize("texto, centavos", [
    ("100", 10000),
    ("100,00", 10000),
    ("100,5", 10050),
    ("0,05", 5),
    ("1.234,56", 123456),
    ("R$ 1.234,56", 123456),
    (" 12,30 ", 1230),
    ("12.5", 1250),      # ponto decimal digitado no teclado do computador
    ("12.50", 1250),
    ("1.234", 123400),   # ponto de milhar
    ("1.000.000", 100000000),
    ("0", 0),
    ("7,", 700),
])
def test_ler_moeda(texto, centavos):
    assert ler_moeda(texto) == centavos


@pytest.mark.parametrize("texto", ["", "  ", None, "abc", "-10", "10,555", "1,2,3", "10,5a", "1.000.000,01"])
def test_ler_moeda_recusa_valor_invalido(texto):
    with pytest.raises(DadosInvalidosError):
        ler_moeda(texto)


@pytest.mark.parametrize("centavos", [0, 5, 1250, 123456, 99999999])
def test_ler_moeda_desfaz_formatar_moeda(centavos):
    assert ler_moeda(formatar_moeda(centavos)) == centavos


@pytest.mark.parametrize("centavos, esperado", [
    (0, "R$ 0,00"),
    (5, "R$ 0,05"),
    (2800, "R$ 28,00"),
    (123456, "R$ 1.234,56"),
    (123456789, "R$ 1.234.567,89"),
    (-1250, "-R$ 12,50"),
    (None, "R$ 0,00"),
])
def test_formatar_moeda(centavos, esperado):
    assert formatar_moeda(centavos) == esperado


@pytest.mark.parametrize("valor", [28.0, "2800", True])
def test_formatar_moeda_so_aceita_centavos_inteiros(valor):
    with pytest.raises(TypeError):
        formatar_moeda(valor)
