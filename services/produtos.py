"""Produtos, categorias e movimentos de estoque.

Regras:
- Cadastrar, editar, desativar e reativar produtos e categorias exige gerente.
- Entrada de mercadoria pode ser feita pelo operador.
- Perda e ajuste de contagem exigem motivo e autorização de gerente.
- O estoque pode ficar negativo (venda sem estoque é permitida, com aviso).
- `produtos.estoque` é o saldo atual, atualizado na mesma transação de cada movimento.
"""
from database import transacao
import hashlib

from models import Categoria, LinhaHistoricoEstoque, MovimentoEstoque, Produto, de_linha
from services.comum import (
    exigir_centavos,
    exigir_inteiro,
    exigir_texto,
    registrar_auditoria,
    texto_data,
    texto_opcional,
)
from services.erros import DadosInvalidosError, NaoEncontradoError, NomeDuplicadoError
from services.formatacao import plural
from services.usuarios import verificar_gerente

SQL_PRODUTOS = """
    SELECT p.*, c.nome AS categoria_nome
    FROM produtos p JOIN categorias c ON c.id = p.categoria_id
"""


def _produto(linha):
    return de_linha(Produto, linha, ativo=bool(linha["ativo"]))


def _categoria(linha):
    return de_linha(Categoria, linha, ativo=bool(linha["ativo"]))


# ============================================================
# CATEGORIAS
# ============================================================
def listar_categorias(conexao, incluir_inativas=False):
    filtro = "" if incluir_inativas else "WHERE ativo = 1"
    linhas = conexao.execute(f"SELECT * FROM categorias {filtro} ORDER BY ordem, nome").fetchall()
    return [_categoria(l) for l in linhas]


def obter_categoria(conexao, categoria_id):
    linha = conexao.execute("SELECT * FROM categorias WHERE id = ?", (categoria_id,)).fetchone()
    if linha is None:
        raise NaoEncontradoError("Categoria não encontrada.")
    return _categoria(linha)


def _validar_nome_categoria(conexao, nome, ignorar_id=None):
    nome = exigir_texto(nome, "o nome da categoria", maximo=30)
    if conexao.execute("SELECT 1 FROM categorias WHERE nome = ? COLLATE NOCASE AND id IS NOT ?",
                       (nome, ignorar_id)).fetchone():
        raise NomeDuplicadoError(f"Já existe a categoria {nome}.")
    return nome


def criar_categoria(conexao, nome, usuario_id, autorizacao, agora=None):
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        nome = _validar_nome_categoria(conexao, nome)
        ordem = conexao.execute("SELECT COALESCE(MAX(ordem), 0) + 1 FROM categorias").fetchone()[0]
        novo_id = conexao.execute("INSERT INTO categorias (nome, ordem) VALUES (?, ?)",
                                  (nome, ordem)).lastrowid
        registrar_auditoria(conexao, "categoria_criada", usuario_id, {"categoria_id": novo_id, "nome": nome},
                            autorizado_por=gerente.id, agora=agora)
    return obter_categoria(conexao, novo_id)


def renomear_categoria(conexao, categoria_id, nome, usuario_id, autorizacao, agora=None):
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        atual = obter_categoria(conexao, categoria_id)
        nome = _validar_nome_categoria(conexao, nome, ignorar_id=categoria_id)
        conexao.execute("UPDATE categorias SET nome = ? WHERE id = ?", (nome, categoria_id))
        registrar_auditoria(conexao, "categoria_renomeada", usuario_id,
                            {"categoria_id": categoria_id, "antes": atual.nome, "depois": nome},
                            autorizado_por=gerente.id, agora=agora)
    return obter_categoria(conexao, categoria_id)


def desativar_categoria(conexao, categoria_id, usuario_id, autorizacao, agora=None):
    """Só desativa categoria sem produtos ativos (para nenhum produto sumir sem querer)."""
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        obter_categoria(conexao, categoria_id)
        ativos = conexao.execute("SELECT COUNT(*) FROM produtos WHERE categoria_id = ? AND ativo = 1",
                                 (categoria_id,)).fetchone()[0]
        if ativos:
            raise DadosInvalidosError(
                f"A categoria tem {plural(ativos, 'produto ativo', 'produtos ativos')}. Mova ou desative os produtos antes.")
        conexao.execute("UPDATE categorias SET ativo = 0 WHERE id = ?", (categoria_id,))
        registrar_auditoria(conexao, "categoria_desativada", usuario_id, {"categoria_id": categoria_id},
                            autorizado_por=gerente.id, agora=agora)
    return obter_categoria(conexao, categoria_id)


def reativar_categoria(conexao, categoria_id, usuario_id, autorizacao, agora=None):
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        obter_categoria(conexao, categoria_id)
        conexao.execute("UPDATE categorias SET ativo = 1 WHERE id = ?", (categoria_id,))
        registrar_auditoria(conexao, "categoria_reativada", usuario_id, {"categoria_id": categoria_id},
                            autorizado_por=gerente.id, agora=agora)
    return obter_categoria(conexao, categoria_id)


# ============================================================
# PRODUTOS
# ============================================================
def obter_produto(conexao, produto_id):
    linha = conexao.execute(f"{SQL_PRODUTOS} WHERE p.id = ?", (produto_id,)).fetchone()
    if linha is None:
        raise NaoEncontradoError("Produto não encontrado.")
    return _produto(linha)


def listar_produtos(conexao, incluir_inativos=False, categoria_id=None):
    condicoes, parametros = [], []
    if not incluir_inativos:
        condicoes.append("p.ativo = 1")
    if categoria_id is not None:
        condicoes.append("p.categoria_id = ?")
        parametros.append(categoria_id)
    where = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""
    linhas = conexao.execute(f"{SQL_PRODUTOS} {where} ORDER BY c.ordem, p.nome", parametros).fetchall()
    return [_produto(l) for l in linhas]


def cardapio(conexao):
    """Categorias ativas com seus produtos ativos: [(Categoria, [Produto, ...]), ...]."""
    produtos = listar_produtos(conexao)
    resultado = []
    for categoria in listar_categorias(conexao):
        da_categoria = [p for p in produtos if p.categoria_id == categoria.id]
        if da_categoria:
            resultado.append((categoria, da_categoria))
    return resultado


def assinatura_cardapio(conexao):
    """Texto curto que muda quando o cardápio muda (produto ou categoria criado,
    editado, desativado). A tela da comanda compara para se recarregar sozinha."""
    partes = [f"c{c.id}:{c.nome}:{c.ordem}" for c in listar_categorias(conexao)]
    partes += [f"p{p.id}:{p.nome}:{p.categoria_id}:{p.preco_centavos}" for p in listar_produtos(conexao)]
    return hashlib.sha1("|".join(partes).encode("utf-8")).hexdigest()[:12]


def listar_alertas_estoque(conexao):
    """Produtos ativos com estoque negativo, zerado ou abaixo do mínimo."""
    return [p for p in listar_produtos(conexao) if p.precisa_atencao]


def _validar_nome_produto(conexao, nome, ignorar_id=None):
    nome = exigir_texto(nome, "o nome do produto", maximo=60)
    if conexao.execute("SELECT 1 FROM produtos WHERE nome = ? COLLATE NOCASE AND id IS NOT ?",
                       (nome, ignorar_id)).fetchone():
        raise NomeDuplicadoError(f"Já existe o produto {nome}.")
    return nome


def _validar_categoria_ativa(conexao, categoria_id):
    categoria = obter_categoria(conexao, categoria_id)
    if not categoria.ativo:
        raise DadosInvalidosError(f"A categoria {categoria.nome} está desativada.")
    return categoria


def cadastrar_produto(conexao, nome, categoria_id, preco_centavos, usuario_id, autorizacao,
                      estoque_inicial=0, estoque_minimo=0, agora=None):
    """Cadastra um produto. O estoque inicial entra como movimento de entrada."""
    exigir_centavos(preco_centavos, "o preço")
    exigir_inteiro(estoque_inicial, "o estoque inicial", minimo=0)
    exigir_inteiro(estoque_minimo, "o estoque mínimo", minimo=0)
    momento = texto_data(agora)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        nome = _validar_nome_produto(conexao, nome)
        _validar_categoria_ativa(conexao, categoria_id)
        novo_id = conexao.execute(
            """INSERT INTO produtos (nome, categoria_id, preco_centavos, estoque, estoque_minimo,
                                     criado_em, atualizado_em)
               VALUES (?, ?, ?, 0, ?, ?, ?)""",
            (nome, categoria_id, preco_centavos, estoque_minimo, momento, momento),
        ).lastrowid
        if estoque_inicial:
            _inserir_movimento(conexao, novo_id, "entrada", estoque_inicial, usuario_id,
                               motivo="Estoque inicial", agora=agora)
        registrar_auditoria(conexao, "produto_criado", usuario_id,
                            {"produto_id": novo_id, "nome": nome, "preco_centavos": preco_centavos},
                            autorizado_por=gerente.id, agora=agora)
    return obter_produto(conexao, novo_id)


def editar_produto(conexao, produto_id, nome, categoria_id, preco_centavos, estoque_minimo,
                   usuario_id, autorizacao, agora=None):
    """Edita dados do produto. O estoque só muda por movimentos (entrada, perda, ajuste)."""
    exigir_centavos(preco_centavos, "o preço")
    exigir_inteiro(estoque_minimo, "o estoque mínimo", minimo=0)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        atual = obter_produto(conexao, produto_id)
        nome = _validar_nome_produto(conexao, nome, ignorar_id=produto_id)
        if categoria_id != atual.categoria_id:
            _validar_categoria_ativa(conexao, categoria_id)
        conexao.execute(
            """UPDATE produtos SET nome = ?, categoria_id = ?, preco_centavos = ?, estoque_minimo = ?,
                                   atualizado_em = ?
               WHERE id = ?""",
            (nome, categoria_id, preco_centavos, estoque_minimo, texto_data(agora), produto_id),
        )
        registrar_auditoria(
            conexao, "produto_editado", usuario_id,
            {"produto_id": produto_id,
             "antes": {"nome": atual.nome, "categoria_id": atual.categoria_id,
                       "preco_centavos": atual.preco_centavos, "estoque_minimo": atual.estoque_minimo},
             "depois": {"nome": nome, "categoria_id": categoria_id,
                        "preco_centavos": preco_centavos, "estoque_minimo": estoque_minimo}},
            autorizado_por=gerente.id, agora=agora)
    return obter_produto(conexao, produto_id)


def _alterar_ativo(conexao, produto_id, ativo, acao, usuario_id, autorizacao, agora):
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        produto = obter_produto(conexao, produto_id)
        if ativo:
            _validar_categoria_ativa(conexao, produto.categoria_id)
        conexao.execute("UPDATE produtos SET ativo = ?, atualizado_em = ? WHERE id = ?",
                        (1 if ativo else 0, texto_data(agora), produto_id))
        registrar_auditoria(conexao, acao, usuario_id, {"produto_id": produto_id},
                            autorizado_por=gerente.id, agora=agora)
    return obter_produto(conexao, produto_id)


def desativar_produto(conexao, produto_id, usuario_id, autorizacao, agora=None):
    """O produto some do cardápio; comandas e vendas antigas continuam com ele."""
    return _alterar_ativo(conexao, produto_id, False, "produto_desativado", usuario_id, autorizacao, agora)


def reativar_produto(conexao, produto_id, usuario_id, autorizacao, agora=None):
    return _alterar_ativo(conexao, produto_id, True, "produto_reativado", usuario_id, autorizacao, agora)


# ============================================================
# MOVIMENTOS DE ESTOQUE
# ============================================================
def _inserir_movimento(conexao, produto_id, tipo, quantidade, usuario_id, motivo=None,
                       autorizado_por=None, estoque_contado=None, custo_unitario_centavos=None,
                       agora=None):
    """Grava o movimento e atualiza o saldo. Chamar dentro de uma transação."""
    conexao.execute(
        """INSERT INTO movimentos_estoque (produto_id, tipo, quantidade, estoque_contado,
               custo_unitario_centavos, motivo, usuario_id, autorizado_por, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (produto_id, tipo, quantidade, estoque_contado, custo_unitario_centavos, motivo,
         usuario_id, autorizado_por, texto_data(agora)),
    )
    conexao.execute("UPDATE produtos SET estoque = estoque + ?, atualizado_em = ? WHERE id = ?",
                    (quantidade, texto_data(agora), produto_id))


def registrar_entrada(conexao, produto_id, quantidade, usuario_id, custo_unitario_centavos=None,
                      observacao=None, agora=None):
    """Entrada de mercadoria (compra). Não exige gerente."""
    exigir_inteiro(quantidade, "a quantidade", minimo=1)
    if custo_unitario_centavos is not None:
        exigir_centavos(custo_unitario_centavos, "o custo")
    observacao = texto_opcional(observacao)
    with transacao(conexao):
        obter_produto(conexao, produto_id)
        _inserir_movimento(conexao, produto_id, "entrada", quantidade, usuario_id, motivo=observacao,
                           custo_unitario_centavos=custo_unitario_centavos, agora=agora)
    return obter_produto(conexao, produto_id)


def registrar_perda(conexao, produto_id, quantidade, motivo, usuario_id, autorizacao, agora=None):
    """Perda (quebra, vencimento...). `quantidade` é positiva; o estoque diminui."""
    exigir_inteiro(quantidade, "a quantidade", minimo=1)
    motivo = exigir_texto(motivo, "o motivo da perda", maximo=200)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        obter_produto(conexao, produto_id)
        _inserir_movimento(conexao, produto_id, "perda", -quantidade, usuario_id, motivo=motivo,
                           autorizado_por=gerente.id, agora=agora)
    return obter_produto(conexao, produto_id)


def ajustar_contagem(conexao, produto_id, estoque_contado, motivo, usuario_id, autorizacao, agora=None):
    """Ajuste de inventário: informa quanto foi contado e grava a diferença."""
    exigir_inteiro(estoque_contado, "o estoque contado", minimo=0)
    motivo = exigir_texto(motivo, "o motivo do ajuste", maximo=200)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        produto = obter_produto(conexao, produto_id)
        _inserir_movimento(conexao, produto_id, "ajuste", estoque_contado - produto.estoque, usuario_id,
                           motivo=motivo, autorizado_por=gerente.id, estoque_contado=estoque_contado,
                           agora=agora)
    return obter_produto(conexao, produto_id)


def listar_movimentos(conexao, produto_id, limite=100):
    linhas = conexao.execute(
        """SELECT m.*, u.nome AS usuario_nome, g.nome AS autorizado_por_nome
           FROM movimentos_estoque m
           JOIN usuarios u ON u.id = m.usuario_id
           LEFT JOIN usuarios g ON g.id = m.autorizado_por
           WHERE m.produto_id = ? ORDER BY m.criado_em DESC, m.id DESC LIMIT ?""",
        (produto_id, limite),
    ).fetchall()
    return [de_linha(MovimentoEstoque, l) for l in linhas]


def historico_estoque(conexao, produto_id, limite=100):
    """Movimentos de estoque e baixas por venda do produto, do mais recente ao mais antigo.

    A baixa por venda não fica em movimentos_estoque (vem de itens_venda), mas
    aparece aqui para o histórico fechar com o estoque atual.
    """
    linhas = []
    for m in listar_movimentos(conexao, produto_id, limite):
        if m.tipo == "ajuste":
            descricao = f"Contado: {m.estoque_contado}. {m.motivo}"
        else:
            descricao = m.motivo or ""
        linhas.append(LinhaHistoricoEstoque(m.criado_em, m.tipo, m.quantidade, descricao, m.usuario_nome,
                                            m.autorizado_por_nome))
    vendas = conexao.execute(
        """SELECT v.criado_em, v.comanda_id, SUM(iv.quantidade) AS quantidade, u.nome AS usuario_nome
           FROM itens_venda iv
           JOIN vendas v ON v.id = iv.venda_id
           JOIN usuarios u ON u.id = v.fechada_por
           WHERE iv.produto_id = ?
           GROUP BY v.id ORDER BY v.criado_em DESC, v.id DESC LIMIT ?""",
        (produto_id, limite),
    ).fetchall()
    for v in vendas:
        linhas.append(LinhaHistoricoEstoque(v["criado_em"], "venda", -v["quantidade"],
                                            f"Comanda {v['comanda_id']}", v["usuario_nome"]))
    linhas.sort(key=lambda linha: linha.criado_em, reverse=True)
    return linhas[:limite]


def baixar_por_venda(conexao, produto_id, quantidade, agora=None):
    """Baixa de estoque de uma venda (o registro fica em itens_venda).

    Chamar DENTRO da transação do pagamento. Pode deixar o estoque negativo.
    Devolve o produto atualizado (para avisar estoque baixo ou negativo).
    """
    exigir_inteiro(quantidade, "a quantidade", minimo=1)
    conexao.execute("UPDATE produtos SET estoque = estoque - ?, atualizado_em = ? WHERE id = ?",
                    (quantidade, texto_data(agora), produto_id))
    return obter_produto(conexao, produto_id)
