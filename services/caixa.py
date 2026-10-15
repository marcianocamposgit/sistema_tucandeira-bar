"""Controle de caixa: abertura, sangria, suprimento, conferência e fechamento.

Regras:
- Só um caixa aberto por vez; vendas só com caixa aberto.
- Sangria exige autorização de gerente; sangria e suprimento exigem motivo.
- Fechar exige gerente e só é possível sem comandas abertas ou com conta pedida.
- Esperado em dinheiro = fundo + pagamentos em dinheiro não estornados
  + suprimentos − sangrias. Nas outras formas = pagamentos não estornados.
"""
import sqlite3

import config
from database import transacao
from models import Caixa, CaixaMovimento, ConferenciaForma, ResultadoFechamento, de_linha
from services.comum import exigir_centavos, exigir_texto, registrar_auditoria, texto_data, texto_opcional
from services.erros import (
    CaixaFechadoError,
    CaixaJaAbertoError,
    ComandasAbertasError,
    DadosInvalidosError,
    NaoEncontradoError,
)
from services.usuarios import verificar_gerente

FORMAS = tuple(config.FORMAS_PAGAMENTO)


def _caixa(linha):
    return de_linha(Caixa, linha)


def caixa_aberto(conexao):
    """O caixa aberto agora, ou None."""
    linha = conexao.execute("SELECT * FROM caixas WHERE status = 'aberto'").fetchone()
    return _caixa(linha) if linha else None


def exigir_caixa_aberto(conexao):
    caixa = caixa_aberto(conexao)
    if caixa is None:
        raise CaixaFechadoError()
    return caixa


def ultimo_fechado(conexao):
    """O caixa fechado mais recente, ou None."""
    linha = conexao.execute(
        "SELECT * FROM caixas WHERE status = 'fechado' ORDER BY fechado_em DESC, id DESC LIMIT 1"
    ).fetchone()
    return _caixa(linha) if linha else None


def obter(conexao, caixa_id):
    linha = conexao.execute("SELECT * FROM caixas WHERE id = ?", (caixa_id,)).fetchone()
    if linha is None:
        raise NaoEncontradoError("Caixa não encontrado.")
    return _caixa(linha)


def abrir(conexao, valor_inicial_centavos, usuario_id, agora=None):
    """Abre o caixa com o fundo de troco."""
    exigir_centavos(valor_inicial_centavos, "o fundo de troco")
    try:
        with transacao(conexao):
            if caixa_aberto(conexao):
                raise CaixaJaAbertoError()
            novo_id = conexao.execute(
                """INSERT INTO caixas (status, valor_inicial_centavos, aberto_em, aberto_por)
                   VALUES ('aberto', ?, ?, ?)""",
                (valor_inicial_centavos, texto_data(agora), usuario_id),
            ).lastrowid
    except sqlite3.IntegrityError as erro:
        # Outro aparelho abriu o caixa no mesmo instante (índice único).
        raise CaixaJaAbertoError() from erro
    return obter(conexao, novo_id)


def _inserir_movimento(conexao, caixa_id, tipo, valor, motivo, usuario_id, autorizado_por, agora):
    novo_id = conexao.execute(
        """INSERT INTO caixa_movimentos (caixa_id, tipo, valor_centavos, motivo, usuario_id,
                                         autorizado_por, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (caixa_id, tipo, valor, motivo, usuario_id, autorizado_por, texto_data(agora)),
    ).lastrowid
    linha = conexao.execute("SELECT * FROM caixa_movimentos WHERE id = ?", (novo_id,)).fetchone()
    return de_linha(CaixaMovimento, linha)


def registrar_suprimento(conexao, valor_centavos, motivo, usuario_id, agora=None):
    """Entrada de dinheiro no caixa (ex.: reforço de troco)."""
    exigir_centavos(valor_centavos, "o valor", permitir_zero=False)
    motivo = exigir_texto(motivo, "o motivo do suprimento", maximo=200)
    with transacao(conexao):
        caixa = exigir_caixa_aberto(conexao)
        return _inserir_movimento(conexao, caixa.id, "suprimento", valor_centavos, motivo,
                                  usuario_id, None, agora)


def _conferir_sangria(conexao, valor_centavos, motivo):
    """Valor, motivo e limite do dinheiro em caixa. Devolve (caixa, motivo limpo)."""
    exigir_centavos(valor_centavos, "o valor", permitir_zero=False)
    motivo = exigir_texto(motivo, "o motivo da sangria", maximo=200)
    caixa = exigir_caixa_aberto(conexao)
    if valor_centavos > calcular_esperado(conexao, caixa.id)["dinheiro"]:
        raise DadosInvalidosError("A sangria é maior que o dinheiro que deveria estar no caixa.")
    return caixa, motivo


def validar_sangria(conexao, valor_centavos, motivo):
    """Confere a sangria antes de pedir o PIN do gerente (não grava nada)."""
    _conferir_sangria(conexao, valor_centavos, motivo)


def registrar_sangria(conexao, valor_centavos, motivo, usuario_id, autorizacao, agora=None):
    """Retirada de dinheiro do caixa. Exige gerente e não pode passar do dinheiro em caixa."""
    with transacao(conexao):
        # Confere de novo dentro da transação: outro aparelho pode ter mexido no caixa.
        caixa, motivo = _conferir_sangria(conexao, valor_centavos, motivo)
        gerente = verificar_gerente(conexao, autorizacao)
        return _inserir_movimento(conexao, caixa.id, "sangria", valor_centavos, motivo,
                                  usuario_id, gerente.id, agora)


def listar_movimentos(conexao, caixa_id):
    linhas = conexao.execute(
        """SELECT m.*, u.nome AS usuario_nome FROM caixa_movimentos m
           JOIN usuarios u ON u.id = m.usuario_id
           WHERE m.caixa_id = ? ORDER BY m.criado_em, m.id""",
        (caixa_id,),
    ).fetchall()
    return [de_linha(CaixaMovimento, l) for l in linhas]


def calcular_esperado(conexao, caixa_id):
    """Quanto deveria haver em cada forma de pagamento: {'dinheiro': ..., 'debito': ..., ...}."""
    caixa = obter(conexao, caixa_id)
    esperado = {forma: 0 for forma in FORMAS}
    for linha in conexao.execute(
        """SELECT forma, SUM(valor_centavos) AS total FROM pagamentos
           WHERE caixa_id = ? AND estornado_em IS NULL GROUP BY forma""",
        (caixa_id,),
    ):
        esperado[linha["forma"]] = linha["total"]
    movimentos = conexao.execute(
        """SELECT COALESCE(SUM(CASE WHEN tipo = 'suprimento' THEN valor_centavos ELSE 0 END), 0),
                  COALESCE(SUM(CASE WHEN tipo = 'sangria' THEN valor_centavos ELSE 0 END), 0)
           FROM caixa_movimentos WHERE caixa_id = ?""",
        (caixa_id,),
    ).fetchone()
    esperado["dinheiro"] += caixa.valor_inicial_centavos + movimentos[0] - movimentos[1]
    return esperado


def _validar_contado(contado):
    if not isinstance(contado, dict) or set(contado) != set(FORMAS):
        raise DadosInvalidosError("Informe o valor contado de todas as formas de pagamento.")
    for forma in FORMAS:
        exigir_centavos(contado[forma], f"o valor contado em {config.FORMAS_PAGAMENTO[forma]}")
    return contado


def conferencia(conexao, contado, caixa_id=None):
    """Prévia da conferência (esperado x contado x diferença), sem gravar nada."""
    caixa = obter(conexao, caixa_id) if caixa_id else exigir_caixa_aberto(conexao)
    _validar_contado(contado)
    esperado = calcular_esperado(conexao, caixa.id)
    return [ConferenciaForma(forma, esperado[forma], contado[forma]) for forma in FORMAS]


def comandas_pendentes(conexao, caixa_id):
    """Comandas abertas ou com conta pedida, que impedem o fechamento."""
    from services import comandas  # import aqui para evitar ciclo (comandas usa caixa)
    return comandas.listar_pendentes(conexao, caixa_id)


def fechar(conexao, contado, usuario_id, autorizacao, observacao=None, agora=None):
    """Fecha o caixa gravando a conferência. Exige gerente e nenhuma comanda pendente."""
    _validar_contado(contado)
    observacao = texto_opcional(observacao)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        caixa = exigir_caixa_aberto(conexao)
        pendentes = comandas_pendentes(conexao, caixa.id)
        if pendentes:
            raise ComandasAbertasError(pendentes)
        esperado = calcular_esperado(conexao, caixa.id)
        conferencias = [ConferenciaForma(forma, esperado[forma], contado[forma]) for forma in FORMAS]
        for c in conferencias:
            conexao.execute(
                """INSERT INTO caixa_conferencias (caixa_id, forma, esperado_centavos, contado_centavos,
                                                   diferenca_centavos)
                   VALUES (?, ?, ?, ?, ?)""",
                (caixa.id, c.forma, c.esperado_centavos, c.contado_centavos, c.diferenca_centavos),
            )
        conexao.execute(
            """UPDATE caixas SET status = 'fechado', fechado_em = ?, fechado_por = ?, observacao = ?
               WHERE id = ?""",
            (texto_data(agora), gerente.id, observacao, caixa.id),
        )
        registrar_auditoria(conexao, "caixa_fechado", usuario_id, {"caixa_id": caixa.id},
                            autorizado_por=gerente.id, agora=agora)
    return ResultadoFechamento(obter(conexao, caixa.id), conferencias)


def obter_conferencia(conexao, caixa_id):
    """Conferência gravada de um caixa já fechado."""
    linhas = conexao.execute(
        "SELECT * FROM caixa_conferencias WHERE caixa_id = ? ORDER BY id", (caixa_id,)
    ).fetchall()
    return [ConferenciaForma(l["forma"], l["esperado_centavos"], l["contado_centavos"]) for l in linhas]


def resumo_fechamento(conexao, caixa_id):
    """Caixa fechado com a conferência gravada (para a tela de resumo)."""
    caixa = obter(conexao, caixa_id)
    if caixa.aberto:
        raise DadosInvalidosError("Este caixa ainda está aberto.")
    return ResultadoFechamento(caixa, obter_conferencia(conexao, caixa_id))
