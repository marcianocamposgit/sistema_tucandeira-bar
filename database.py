"""Banco de dados SQLite: conexão, transações e criação/migração do esquema.

Este módulo não depende do Flask. A ligação com as requisições (uma conexão
por requisição) fica em routes/conexao.py.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

FORMATO_DATA_HORA = "%Y-%m-%d %H:%M:%S"


def agora_texto():
    """Data e hora local no formato gravado no banco (ISO, sem fuso)."""
    return datetime.now().strftime(FORMATO_DATA_HORA)


def conectar(caminho_banco):
    """Abre uma conexão já configurada para uso simultâneo por vários aparelhos.

    A conexão fica em modo autocommit (isolation_level=None): as transações
    são abertas explicitamente com transacao().
    """
    conexao = sqlite3.connect(str(caminho_banco), timeout=5, isolation_level=None)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA journal_mode = WAL")
    conexao.execute("PRAGMA synchronous = NORMAL")
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 5000")
    return conexao


@contextmanager
def transacao(conexao):
    """Executa um bloco numa transação única (BEGIN IMMEDIATE ... COMMIT).

    BEGIN IMMEDIATE reserva a escrita logo no início, então duas operações
    simultâneas (ex.: dois tablets na mesma comanda) rodam uma de cada vez.
    Em caso de erro, desfaz tudo (ROLLBACK) e repassa a exceção.
    """
    if conexao.in_transaction:
        raise RuntimeError("Já existe uma transação aberta nesta conexão.")
    conexao.execute("BEGIN IMMEDIATE")
    try:
        yield conexao
    except BaseException:
        conexao.execute("ROLLBACK")
        raise
    else:
        conexao.execute("COMMIT")


# ============================================================
# ESQUEMA — VERSÃO 1
# Valores em centavos (INTEGER). Datas em texto ISO 'YYYY-MM-DD HH:MM:SS'.
# ============================================================
ESQUEMA_V1 = """
CREATE TABLE usuarios (
    id          INTEGER PRIMARY KEY,
    nome        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pin_hash    TEXT NOT NULL,
    pin_salt    TEXT NOT NULL,
    perfil      TEXT NOT NULL CHECK (perfil IN ('operador', 'gerente')),
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_em   TEXT NOT NULL,
    criado_por  INTEGER REFERENCES usuarios(id)
);

CREATE TABLE configuracoes (
    chave           TEXT PRIMARY KEY,
    valor           TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL,
    atualizado_por  INTEGER REFERENCES usuarios(id)
);

CREATE TABLE auditoria (
    id              INTEGER PRIMARY KEY,
    acao            TEXT NOT NULL,
    detalhes        TEXT,
    usuario_id      INTEGER REFERENCES usuarios(id),
    autorizado_por  INTEGER REFERENCES usuarios(id),
    criado_em       TEXT NOT NULL
);

CREATE TABLE categorias (
    id      INTEGER PRIMARY KEY,
    nome    TEXT NOT NULL UNIQUE COLLATE NOCASE,
    ordem   INTEGER NOT NULL DEFAULT 0,
    ativo   INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE produtos (
    id              INTEGER PRIMARY KEY,
    nome            TEXT NOT NULL UNIQUE COLLATE NOCASE,
    categoria_id    INTEGER NOT NULL REFERENCES categorias(id),
    preco_centavos  INTEGER NOT NULL CHECK (preco_centavos >= 0),
    estoque         INTEGER NOT NULL DEFAULT 0,
    estoque_minimo  INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    ativo           INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_em       TEXT NOT NULL,
    atualizado_em   TEXT NOT NULL
);

CREATE TABLE movimentos_estoque (
    id                       INTEGER PRIMARY KEY,
    produto_id               INTEGER NOT NULL REFERENCES produtos(id),
    tipo                     TEXT NOT NULL CHECK (tipo IN ('entrada', 'perda', 'ajuste')),
    quantidade               INTEGER NOT NULL,
    estoque_contado          INTEGER,
    custo_unitario_centavos  INTEGER CHECK (custo_unitario_centavos >= 0),
    motivo                   TEXT,
    usuario_id               INTEGER NOT NULL REFERENCES usuarios(id),
    autorizado_por           INTEGER REFERENCES usuarios(id),
    criado_em                TEXT NOT NULL,
    CHECK (tipo <> 'entrada' OR quantidade > 0),
    CHECK (tipo <> 'perda' OR quantidade < 0),
    CHECK (tipo <> 'ajuste' OR estoque_contado IS NOT NULL),
    CHECK (tipo = 'entrada' OR (motivo IS NOT NULL AND autorizado_por IS NOT NULL))
);
CREATE INDEX idx_movimentos_estoque_produto ON movimentos_estoque(produto_id, criado_em);

CREATE TABLE caixas (
    id                      INTEGER PRIMARY KEY,
    status                  TEXT NOT NULL CHECK (status IN ('aberto', 'fechado')),
    valor_inicial_centavos  INTEGER NOT NULL CHECK (valor_inicial_centavos >= 0),
    aberto_em               TEXT NOT NULL,
    aberto_por              INTEGER NOT NULL REFERENCES usuarios(id),
    fechado_em              TEXT,
    fechado_por             INTEGER REFERENCES usuarios(id),
    observacao              TEXT
);
-- Só pode existir um caixa aberto por vez.
CREATE UNIQUE INDEX idx_caixas_um_aberto ON caixas(status) WHERE status = 'aberto';

CREATE TABLE caixa_movimentos (
    id              INTEGER PRIMARY KEY,
    caixa_id        INTEGER NOT NULL REFERENCES caixas(id),
    tipo            TEXT NOT NULL CHECK (tipo IN ('sangria', 'suprimento')),
    valor_centavos  INTEGER NOT NULL CHECK (valor_centavos > 0),
    motivo          TEXT NOT NULL,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    autorizado_por  INTEGER REFERENCES usuarios(id),
    criado_em       TEXT NOT NULL,
    CHECK (tipo <> 'sangria' OR autorizado_por IS NOT NULL)
);

CREATE TABLE caixa_conferencias (
    id                  INTEGER PRIMARY KEY,
    caixa_id            INTEGER NOT NULL REFERENCES caixas(id),
    forma               TEXT NOT NULL CHECK (forma IN ('dinheiro', 'debito', 'credito', 'pix')),
    esperado_centavos   INTEGER NOT NULL,
    contado_centavos    INTEGER NOT NULL,
    diferenca_centavos  INTEGER NOT NULL,
    UNIQUE (caixa_id, forma)
);

CREATE TABLE comandas (
    id                          INTEGER PRIMARY KEY,
    tipo                        TEXT NOT NULL CHECK (tipo IN ('mesa', 'balcao')),
    nome_cliente                TEXT,
    pessoas                     INTEGER NOT NULL DEFAULT 1 CHECK (pessoas >= 1),
    status                      TEXT NOT NULL DEFAULT 'aberta'
                                CHECK (status IN ('aberta', 'conta_pedida', 'paga', 'unida', 'cancelada')),
    caixa_id                    INTEGER NOT NULL REFERENCES caixas(id),
    unida_a                     INTEGER REFERENCES comandas(id),
    aberta_em                   TEXT NOT NULL,
    aberta_por                  INTEGER NOT NULL REFERENCES usuarios(id),
    fechada_em                  TEXT,
    fechada_por                 INTEGER REFERENCES usuarios(id),
    motivo_cancelamento         TEXT,
    cancelamento_autorizado_por INTEGER REFERENCES usuarios(id),
    CHECK (tipo <> 'balcao' OR nome_cliente IS NOT NULL),
    CHECK (status <> 'unida' OR unida_a IS NOT NULL)
);
CREATE INDEX idx_comandas_status ON comandas(status);

CREATE TABLE comanda_mesas (
    id            INTEGER PRIMARY KEY,
    comanda_id    INTEGER NOT NULL REFERENCES comandas(id),
    mesa          INTEGER NOT NULL CHECK (mesa >= 1),
    principal     INTEGER NOT NULL DEFAULT 0 CHECK (principal IN (0, 1)),
    vinculada_em  TEXT NOT NULL,
    liberada_em   TEXT
);
-- Uma mesa só pode estar ligada a uma comanda por vez: o próprio banco impede
-- que dois aparelhos abram a mesma mesa ao mesmo tempo.
CREATE UNIQUE INDEX idx_comanda_mesas_mesa_ocupada ON comanda_mesas(mesa) WHERE liberada_em IS NULL;
CREATE INDEX idx_comanda_mesas_comanda ON comanda_mesas(comanda_id);

CREATE TABLE itens_comanda (
    id                       INTEGER PRIMARY KEY,
    comanda_id               INTEGER NOT NULL REFERENCES comandas(id),
    produto_id               INTEGER NOT NULL REFERENCES produtos(id),
    nome_produto             TEXT NOT NULL,
    preco_unitario_centavos  INTEGER NOT NULL CHECK (preco_unitario_centavos >= 0),
    quantidade               INTEGER NOT NULL CHECK (quantidade >= 0),
    observacao               TEXT,
    lancado_por              INTEGER NOT NULL REFERENCES usuarios(id),
    lancado_em               TEXT NOT NULL
);
CREATE INDEX idx_itens_comanda_comanda ON itens_comanda(comanda_id);

CREATE TABLE item_ajustes (
    id              INTEGER PRIMARY KEY,
    item_id         INTEGER NOT NULL REFERENCES itens_comanda(id),
    tipo            TEXT NOT NULL CHECK (tipo IN ('remocao', 'cancelamento')),
    quantidade      INTEGER NOT NULL CHECK (quantidade > 0),
    motivo          TEXT,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    autorizado_por  INTEGER REFERENCES usuarios(id),
    criado_em       TEXT NOT NULL,
    CHECK (tipo <> 'cancelamento' OR (motivo IS NOT NULL AND autorizado_por IS NOT NULL))
);
CREATE INDEX idx_item_ajustes_item ON item_ajustes(item_id);

CREATE TABLE descontos (
    id               INTEGER PRIMARY KEY,
    comanda_id       INTEGER NOT NULL REFERENCES comandas(id),
    valor_centavos   INTEGER NOT NULL CHECK (valor_centavos > 0),
    motivo           TEXT NOT NULL,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id),
    autorizado_por   INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em        TEXT NOT NULL
);
CREATE INDEX idx_descontos_comanda ON descontos(comanda_id);

CREATE TABLE pagamentos (
    id                      INTEGER PRIMARY KEY,
    comanda_id              INTEGER NOT NULL REFERENCES comandas(id),
    caixa_id                INTEGER NOT NULL REFERENCES caixas(id),
    forma                   TEXT NOT NULL CHECK (forma IN ('dinheiro', 'debito', 'credito', 'pix')),
    valor_centavos          INTEGER NOT NULL CHECK (valor_centavos > 0),
    recebido_centavos       INTEGER,
    troco_centavos          INTEGER NOT NULL DEFAULT 0 CHECK (troco_centavos >= 0),
    recebido_por            INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em               TEXT NOT NULL,
    estornado_em            TEXT,
    estornado_por           INTEGER REFERENCES usuarios(id),
    estorno_autorizado_por  INTEGER REFERENCES usuarios(id),
    motivo_estorno          TEXT,
    CHECK (forma = 'dinheiro' OR troco_centavos = 0),
    CHECK (estornado_em IS NULL
           OR (estornado_por IS NOT NULL AND estorno_autorizado_por IS NOT NULL AND motivo_estorno IS NOT NULL))
);
CREATE INDEX idx_pagamentos_comanda ON pagamentos(comanda_id);
CREATE INDEX idx_pagamentos_caixa ON pagamentos(caixa_id);

CREATE TABLE vendas (
    id                     INTEGER PRIMARY KEY,
    comanda_id             INTEGER NOT NULL UNIQUE REFERENCES comandas(id),
    caixa_id               INTEGER NOT NULL REFERENCES caixas(id),
    pessoas                INTEGER NOT NULL CHECK (pessoas >= 1),
    subtotal_centavos      INTEGER NOT NULL,
    desconto_centavos      INTEGER NOT NULL DEFAULT 0,
    total_centavos         INTEGER NOT NULL,
    fechada_por            INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em              TEXT NOT NULL
);
CREATE INDEX idx_vendas_criado_em ON vendas(criado_em);
CREATE INDEX idx_vendas_caixa ON vendas(caixa_id);

CREATE TABLE itens_venda (
    id                       INTEGER PRIMARY KEY,
    venda_id                 INTEGER NOT NULL REFERENCES vendas(id),
    produto_id               INTEGER NOT NULL REFERENCES produtos(id),
    nome_produto             TEXT NOT NULL,
    preco_unitario_centavos  INTEGER NOT NULL,
    quantidade               INTEGER NOT NULL CHECK (quantidade > 0),
    subtotal_centavos        INTEGER NOT NULL
);
CREATE INDEX idx_itens_venda_venda ON itens_venda(venda_id);
CREATE INDEX idx_itens_venda_produto ON itens_venda(produto_id);
"""

# Carga inicial: cardápio da versão antiga (legado_tkinter/main.py), valores copiados.
CATEGORIAS_INICIAIS = ["Bebida", "Tira-Gosto", "Lanche", "Cigarro"]
PRODUTOS_INICIAIS = [
    # (nome, categoria, preço em centavos, estoque)
    ("Brahma Lata", "Bebida", 800, 30),
    ("Heineken Long Neck", "Bebida", 1200, 15),
    ("Whisky 50ml", "Bebida", 1500, 12),
    ("Porção Calabresa", "Tira-Gosto", 2800, 8),
    ("Pastel Carne", "Lanche", 700, 15),
    ("Marlboro 20un", "Cigarro", 1800, 10),
]


def _comandos_sql(script):
    """Separa um script SQL em comandos, ignorando linhas de comentário."""
    linhas = [linha for linha in script.splitlines() if not linha.strip().startswith("--")]
    return [cmd.strip() for cmd in "\n".join(linhas).split(";") if cmd.strip()]


def _migracao_1(conexao, ambiente):
    """Cria todas as tabelas da versão 2.0 e faz a carga inicial."""
    for comando in _comandos_sql(ESQUEMA_V1):
        conexao.execute(comando)

    agora = agora_texto()
    configuracoes = {
        "ambiente": ambiente,
        # Desconto é opcional, a critério do dono: desligado até um gerente ligar.
        "permitir_desconto": "0",
    }
    for chave, valor in configuracoes.items():
        conexao.execute(
            "INSERT INTO configuracoes (chave, valor, atualizado_em) VALUES (?, ?, ?)",
            (chave, valor, agora),
        )

    ids_categorias = {}
    for ordem, nome in enumerate(CATEGORIAS_INICIAIS, start=1):
        cursor = conexao.execute(
            "INSERT INTO categorias (nome, ordem) VALUES (?, ?)", (nome, ordem)
        )
        ids_categorias[nome] = cursor.lastrowid

    for nome, categoria, preco, estoque in PRODUTOS_INICIAIS:
        conexao.execute(
            """INSERT INTO produtos
               (nome, categoria_id, preco_centavos, estoque, estoque_minimo, criado_em, atualizado_em)
               VALUES (?, ?, ?, ?, 0, ?, ?)""",
            (nome, ids_categorias[categoria], preco, estoque, agora, agora),
        )


def _migracao_2(conexao, ambiente):
    """Chave de cada toque em "lançar": se a rede falhar e o tablet reenviar o mesmo
    toque, o item não é lançado duas vezes (índice único)."""
    conexao.execute("ALTER TABLE itens_comanda ADD COLUMN chave_toque TEXT")
    conexao.execute(
        "CREATE UNIQUE INDEX idx_itens_comanda_chave ON itens_comanda(chave_toque) WHERE chave_toque IS NOT NULL"
    )


def _migracao_3(conexao, ambiente):
    """Chave de cada envio da tela de pagamento: se o mesmo formulário chegar duas vezes
    (toque duplo, rede instável, F5), o pagamento não é lançado de novo (índice único)."""
    conexao.execute("ALTER TABLE pagamentos ADD COLUMN chave_envio TEXT")
    conexao.execute(
        "CREATE UNIQUE INDEX idx_pagamentos_chave ON pagamentos(chave_envio) WHERE chave_envio IS NOT NULL"
    )


# Cada posição da lista leva o banco da versão N para a N+1.
# Para mudar a estrutura no futuro, acrescente uma função no fim (nunca altere as antigas).
MIGRACOES = [_migracao_1, _migracao_2, _migracao_3]
VERSAO_ESQUEMA = len(MIGRACOES)


def versao_esquema(conexao):
    return conexao.execute("PRAGMA user_version").fetchone()[0]


def migrar(conexao, ambiente="producao"):
    """Leva o banco até a versão atual do esquema, sem perder dados.

    Cada migração roda numa transação própria junto com a troca do
    user_version: ou aplica tudo, ou nada. Devolve a lista de versões aplicadas.
    """
    if ambiente not in ("desenvolvimento", "producao"):
        raise ValueError(f"Ambiente inválido: {ambiente!r}")
    versao_atual = versao_esquema(conexao)
    if versao_atual > VERSAO_ESQUEMA:
        raise RuntimeError(
            f"O banco está na versão {versao_atual}, mais nova que a deste programa "
            f"({VERSAO_ESQUEMA}). Atualize o sistema antes de usar este banco."
        )
    aplicadas = []
    for numero in range(versao_atual + 1, VERSAO_ESQUEMA + 1):
        with transacao(conexao):
            MIGRACOES[numero - 1](conexao, ambiente)
            conexao.execute(f"PRAGMA user_version = {numero}")
        aplicadas.append(numero)
    return aplicadas


def ambiente_do_banco(conexao):
    """'desenvolvimento' ou 'producao', gravado na criação do banco."""
    linha = conexao.execute(
        "SELECT valor FROM configuracoes WHERE chave = 'ambiente'"
    ).fetchone()
    return linha["valor"] if linha else None
