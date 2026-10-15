"""Formatação de valores para exibição.

Único lugar do sistema que transforma centavos em texto "R$ 1.234,56"
(e o texto digitado pelo usuário de volta em centavos).
"""
import re
from datetime import datetime

from database import FORMATO_DATA_HORA
from services.erros import DadosInvalidosError

# Maior valor aceito num campo de dinheiro: R$ 1.000.000,00.
MAXIMO_CENTAVOS = 100_000_000

_DECIMAL_COM_PONTO = re.compile(r"^\d+\.\d{1,2}$")
_VALOR = re.compile(r"^(\d+)(?:,(\d{0,2}))?$")


def ler_moeda(texto, campo="o valor"):
    """Converte o valor digitado ("100", "100,5", "1.234,56", "R$ 12,00") em centavos.

    Aceita vírgula como separador decimal (padrão do Brasil) e ponto como
    separador de milhar. Um ponto seguido de 1 ou 2 dígitos no fim ("12.5")
    é lido como decimal, para quem digita no teclado do computador.
    Lança DadosInvalidosError com mensagem pronta se o texto não for um valor válido.
    """
    limpo = (texto or "").replace("R$", "").replace(" ", "").strip()
    if not limpo:
        raise DadosInvalidosError(f"Informe {campo}.")
    if "," not in limpo and _DECIMAL_COM_PONTO.match(limpo):
        limpo = limpo.replace(".", ",")
    else:
        limpo = limpo.replace(".", "")
    encontrado = _VALOR.match(limpo)
    if not encontrado:
        raise DadosInvalidosError(f"Valor inválido em {campo}. Use o formato 1.234,56.")
    reais, centavos = encontrado.group(1), (encontrado.group(2) or "").ljust(2, "0")
    valor = int(reais) * 100 + int(centavos)
    if valor > MAXIMO_CENTAVOS:
        raise DadosInvalidosError(f"Valor alto demais em {campo}.")
    return valor


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


def formatar_valor_campo(centavos):
    """Centavos no formato do campo de valor, sem o "R$" ('1.234,56').

    Usado para devolver ao campo, já formatado, um valor digitado como "500".
    """
    return formatar_moeda(centavos).replace("R$ ", "")


def valor_para_campo(texto):
    """Texto digitado num campo de valor, formatado se for um valor válido ("500" → "500,00").

    Texto inválido volta como foi digitado, para o usuário corrigir.
    """
    try:
        return formatar_valor_campo(ler_moeda(texto))
    except DadosInvalidosError:
        return texto or ""


def plural(quantidade, singular, no_plural):
    """Quantidade com a palavra certa: plural(1, "pessoa", "pessoas") → '1 pessoa'; 0 e 2+ usam o plural.

    Nunca escrever "pessoa(s)": usar esta função (também é o filtro Jinja `plural`).
    """
    return f"{quantidade} {singular if quantidade == 1 else no_plural}"


def formatar_data_hora(texto):
    """Data/hora do banco ('2026-10-14 21:35:10') no formato '14/10/2026 21:35'."""
    if not texto:
        return ""
    return datetime.strptime(texto, FORMATO_DATA_HORA).strftime("%d/%m/%Y %H:%M")
