"""Funções e constantes de apoio aos testes."""
from datetime import datetime

from database import transacao
from services.comum import texto_data

PIN_GERENTE = "1234"
PIN_OPERADOR = "5678"


def inserir_pagamento(conexao, comanda_id, forma, valor_centavos, usuario_id, estornado=False):
    """Pagamento direto no banco (o service de pagamentos é da Etapa 6)."""
    agora = texto_data(datetime.now())
    caixa_id = conexao.execute("SELECT caixa_id FROM comandas WHERE id = ?", (comanda_id,)).fetchone()[0]
    with transacao(conexao):
        conexao.execute(
            """INSERT INTO pagamentos (comanda_id, caixa_id, forma, valor_centavos, recebido_por, criado_em,
                                       estornado_em, estornado_por, estorno_autorizado_por, motivo_estorno)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (comanda_id, caixa_id, forma, valor_centavos, usuario_id, agora,
             agora if estornado else None, usuario_id if estornado else None,
             usuario_id if estornado else None, "teste" if estornado else None),
        )


def fechar_comanda_como_paga(conexao, comanda_id, usuario_id):
    """Simula o fim do pagamento (Etapa 6): marca paga e libera as mesas."""
    agora = texto_data(datetime.now())
    with transacao(conexao):
        conexao.execute("UPDATE comandas SET status = 'paga', fechada_em = ?, fechada_por = ? WHERE id = ?",
                        (agora, usuario_id, comanda_id))
        conexao.execute("UPDATE comanda_mesas SET liberada_em = ? WHERE comanda_id = ? AND liberada_em IS NULL",
                        (agora, comanda_id))
