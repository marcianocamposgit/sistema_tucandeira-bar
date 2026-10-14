"""Formatação de valores para exibição.

Único lugar do sistema que transforma centavos em texto "R$ 1.234,56".
"""


def formatar_moeda(centavos):
    """Converte um valor em centavos (inteiro) para o formato 'R$ 1.234,56'.

    Valores negativos aparecem como '-R$ 12,50'. None vira 'R$ 0,00'.
    """
    if centavos is None:
        centavos = 0
    if not isinstance(centavos, int) or isinstance(centavos, bool):
        raise TypeError("formatar_moeda() recebe centavos como número inteiro.")
    sinal = "-" if centavos < 0 else ""
    reais, resto = divmod(abs(centavos), 100)
    reais_texto = f"{reais:,}".replace(",", ".")
    return f"{sinal}R$ {reais_texto},{resto:02d}"
