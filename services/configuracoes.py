"""Configurações guardadas no banco (couvert artístico e dia de show)."""
from datetime import date

from database import transacao
from services.comum import exigir_centavos, registrar_auditoria, texto_data
from services.erros import DadosInvalidosError
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


def couvert_valor_centavos(conexao):
    return int(obter(conexao, "couvert_valor_centavos", "0") or 0)


def data_show(conexao):
    """Data (date) do próximo/atual dia de show, ou None."""
    texto = obter(conexao, "data_show", "")
    return date.fromisoformat(texto) if texto else None


def couvert_para_data(conexao, dia):
    """Couvert por pessoa que vale para comandas do caixa aberto em `dia`."""
    return couvert_valor_centavos(conexao) if data_show(conexao) == dia else 0


def configurar_couvert(conexao, valor_centavos, dia_show, usuario_id, autorizacao, agora=None):
    """Define o valor do couvert e o dia de show (None = sem show). Exige gerente."""
    exigir_centavos(valor_centavos, "o valor do couvert")
    if dia_show is not None and not isinstance(dia_show, date):
        raise DadosInvalidosError("Data do show inválida.")
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        _gravar(conexao, "couvert_valor_centavos", str(valor_centavos), usuario_id, agora)
        _gravar(conexao, "data_show", dia_show.isoformat() if dia_show else "", usuario_id, agora)
        registrar_auditoria(conexao, "couvert_configurado", usuario_id,
                            {"valor_centavos": valor_centavos,
                             "data_show": dia_show.isoformat() if dia_show else None},
                            autorizado_por=gerente.id, agora=agora)
