"""Configurações do bar guardadas no banco (tabela configuracoes).

- permitir_desconto: desligada por padrão; só o gerente liga ou desliga.
"""
from database import transacao
from services.comum import registrar_auditoria, texto_data
from services.usuarios import verificar_gerente


def obter(conexao, chave, padrao=None):
    linha = conexao.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
    return linha["valor"] if linha else padrao


def _gravar(conexao, chave, valor, usuario_id, agora):
    conexao.execute(
        """INSERT INTO configuracoes (chave, valor, atualizado_em, atualizado_por) VALUES (?, ?, ?, ?)
           ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor,
               atualizado_em = excluded.atualizado_em, atualizado_por = excluded.atualizado_por""",
        (chave, valor, texto_data(agora), usuario_id),
    )


def desconto_permitido(conexao):
    """True se o dono permitiu dar desconto (a tela só mostra o botão nesse caso)."""
    return obter(conexao, "permitir_desconto", "0") == "1"


def definir_desconto_permitido(conexao, permitido, usuario_id, autorizacao, agora=None):
    """Liga ou desliga o desconto. Exige gerente e fica registrado na auditoria."""
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        antes = desconto_permitido(conexao)
        _gravar(conexao, "permitir_desconto", "1" if permitido else "0", usuario_id, agora)
        registrar_auditoria(conexao, "desconto_ligado" if permitido else "desconto_desligado", usuario_id,
                            {"antes": antes, "depois": bool(permitido)}, autorizado_por=gerente.id, agora=agora)
    return bool(permitido)
