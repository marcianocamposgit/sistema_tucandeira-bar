import pytest

from services.formatacao import formatar_moeda


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
