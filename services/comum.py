"""Funções auxiliares usadas por vários services (sem Flask)."""
import json
from datetime import datetime

from database import FORMATO_DATA_HORA
from services.erros import DadosInvalidosError


def texto_data(agora=None):
    """Data/hora no formato do banco. `agora` permite simular o relógio."""
    return (agora or datetime.now()).strftime(FORMATO_DATA_HORA)


def ler_data(texto):
    return datetime.strptime(texto, FORMATO_DATA_HORA)


def exigir_texto(valor, campo, maximo=120):
    """Texto obrigatório, sem espaços nas pontas."""
    texto = (valor or "").strip()
    if not texto:
        raise DadosInvalidosError(f"Informe {campo}.")
    if len(texto) > maximo:
        raise DadosInvalidosError(f"{campo.capitalize()} pode ter no máximo {maximo} caracteres.")
    return texto


def texto_opcional(valor, maximo=200):
    texto = (valor or "").strip()
    if len(texto) > maximo:
        raise DadosInvalidosError(f"O texto pode ter no máximo {maximo} caracteres.")
    return texto or None


def exigir_inteiro(valor, campo, minimo=None, maximo=None):
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise DadosInvalidosError(f"{campo.capitalize()} deve ser um número inteiro.")
    if minimo is not None and valor < minimo:
        raise DadosInvalidosError(f"{campo.capitalize()} não pode ser menor que {minimo}.")
    if maximo is not None and valor > maximo:
        raise DadosInvalidosError(f"{campo.capitalize()} não pode ser maior que {maximo}.")
    return valor


def exigir_centavos(valor, campo, permitir_zero=True):
    """Valor em centavos: inteiro, nunca negativo."""
    return exigir_inteiro(valor, campo, minimo=0 if permitir_zero else 1)


def registrar_auditoria(conexao, acao, usuario_id, detalhes=None, autorizado_por=None, agora=None):
    """Registra operações que não têm tabela própria (quem fez, quando e o quê).

    Deve ser chamada dentro da transação da operação.
    """
    conexao.execute(
        """INSERT INTO auditoria (acao, detalhes, usuario_id, autorizado_por, criado_em)
           VALUES (?, ?, ?, ?, ?)""",
        (acao, json.dumps(detalhes, ensure_ascii=False) if detalhes else None,
         usuario_id, autorizado_por, texto_data(agora)),
    )
