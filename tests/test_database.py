import sqlite3
import threading

import pytest

import database
from database import conectar, migrar, transacao


@pytest.fixture
def conexao(tmp_path):
    con = conectar(tmp_path / "teste.db")
    migrar(con, "desenvolvimento")
    yield con
    con.close()


def test_banco_criado_em_wal_com_chaves_estrangeiras(conexao):
    assert conexao.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert database.versao_esquema(conexao) == database.VERSAO_ESQUEMA


def test_carga_inicial_com_6_produtos_e_4_categorias(conexao):
    categorias = [l["nome"] for l in conexao.execute("SELECT nome FROM categorias ORDER BY ordem")]
    assert categorias == ["Bebida", "Tira-Gosto", "Lanche", "Cigarro"]
    produtos = conexao.execute(
        """SELECT p.nome, c.nome AS categoria, p.preco_centavos, p.estoque
           FROM produtos p JOIN categorias c ON c.id = p.categoria_id ORDER BY p.id"""
    ).fetchall()
    assert [tuple(p) for p in produtos] == database.PRODUTOS_INICIAIS
    assert conexao.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0


def test_migrar_de_novo_nao_duplica(conexao):
    assert migrar(conexao, "desenvolvimento") == []
    assert conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 6
    assert conexao.execute("SELECT COUNT(*) FROM categorias").fetchone()[0] == 4


def test_ambiente_gravado_na_criacao(tmp_path):
    con = conectar(tmp_path / "producao.db")
    migrar(con, "producao")
    assert database.ambiente_do_banco(con) == "producao"
    # Migrar depois com outro ambiente não troca o que foi gravado na criação.
    migrar(con, "desenvolvimento")
    assert database.ambiente_do_banco(con) == "producao"
    con.close()


def test_ambiente_invalido(tmp_path):
    con = conectar(tmp_path / "x.db")
    with pytest.raises(ValueError):
        migrar(con, "teste")
    con.close()


def test_banco_mais_novo_que_o_programa(tmp_path):
    con = conectar(tmp_path / "futuro.db")
    con.execute(f"PRAGMA user_version = {database.VERSAO_ESQUEMA + 1}")
    with pytest.raises(RuntimeError):
        migrar(con)
    con.close()


def test_transacao_desfaz_tudo_em_caso_de_erro(conexao):
    with pytest.raises(ZeroDivisionError):
        with transacao(conexao):
            conexao.execute("UPDATE produtos SET estoque = 999")
            1 / 0
    assert conexao.execute("SELECT MAX(estoque) FROM produtos").fetchone()[0] == 30


def test_transacao_nao_aninha(conexao):
    with transacao(conexao):
        with pytest.raises(RuntimeError):
            with transacao(conexao):
                pass


def _criar_usuario_e_caixa(con):
    agora = database.agora_texto()
    with transacao(con):
        usuario = con.execute(
            """INSERT INTO usuarios (nome, pin_hash, pin_salt, perfil, criado_em)
               VALUES ('Gerente', 'h', 's', 'gerente', ?)""", (agora,)).lastrowid
        caixa = con.execute(
            """INSERT INTO caixas (status, valor_inicial_centavos, aberto_em, aberto_por)
               VALUES ('aberto', 10000, ?, ?)""", (agora, usuario)).lastrowid
    return usuario, caixa


def _abrir_comanda_mesa(con, mesa, usuario, caixa):
    agora = database.agora_texto()
    with transacao(con):
        comanda = con.execute(
            """INSERT INTO comandas (tipo, caixa_id, taxa_servico_ativa, aberta_em, aberta_por)
               VALUES ('mesa', ?, 1, ?, ?)""", (caixa, agora, usuario)).lastrowid
        con.execute(
            """INSERT INTO comanda_mesas (comanda_id, mesa, principal, vinculada_em)
               VALUES (?, ?, 1, ?)""", (comanda, mesa, agora))
    return comanda


def test_so_um_caixa_aberto(conexao):
    usuario, _ = _criar_usuario_e_caixa(conexao)
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            """INSERT INTO caixas (status, valor_inicial_centavos, aberto_em, aberto_por)
               VALUES ('aberto', 0, ?, ?)""", (database.agora_texto(), usuario))


def test_mesa_nao_pode_ter_duas_comandas_abertas(conexao):
    usuario, caixa = _criar_usuario_e_caixa(conexao)
    _abrir_comanda_mesa(conexao, 3, usuario, caixa)
    with pytest.raises(sqlite3.IntegrityError):
        _abrir_comanda_mesa(conexao, 3, usuario, caixa)
    # A transação que falhou não deixa comanda solta.
    assert conexao.execute("SELECT COUNT(*) FROM comandas").fetchone()[0] == 1
    # Depois de liberada, a mesa pode ser aberta de novo.
    conexao.execute("UPDATE comanda_mesas SET liberada_em = ? WHERE mesa = 3", (database.agora_texto(),))
    _abrir_comanda_mesa(conexao, 3, usuario, caixa)


def test_uma_venda_por_comanda(conexao):
    usuario, caixa = _criar_usuario_e_caixa(conexao)
    comanda = _abrir_comanda_mesa(conexao, 1, usuario, caixa)
    sql = """INSERT INTO vendas (comanda_id, caixa_id, pessoas, subtotal_centavos, total_centavos,
                                 fechada_por, criado_em)
             VALUES (?, ?, 1, 800, 880, ?, ?)"""
    conexao.execute(sql, (comanda, caixa, usuario, database.agora_texto()))
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(sql, (comanda, caixa, usuario, database.agora_texto()))


def test_regras_do_banco_para_estorno_e_cancelamento(conexao):
    usuario, caixa = _criar_usuario_e_caixa(conexao)
    comanda = _abrir_comanda_mesa(conexao, 1, usuario, caixa)
    agora = database.agora_texto()
    # Estorno sem motivo é recusado pelo próprio banco.
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            """INSERT INTO pagamentos (comanda_id, caixa_id, forma, valor_centavos, recebido_por,
                                       criado_em, estornado_em, estornado_por, estorno_autorizado_por)
               VALUES (?, ?, 'pix', 500, ?, ?, ?, ?, ?)""",
            (comanda, caixa, usuario, agora, agora, usuario, usuario))
    # Troco só existe em dinheiro.
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            """INSERT INTO pagamentos (comanda_id, caixa_id, forma, valor_centavos, troco_centavos,
                                       recebido_por, criado_em)
               VALUES (?, ?, 'credito', 500, 100, ?, ?)""", (comanda, caixa, usuario, agora))
    # Forma de pagamento desconhecida.
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            """INSERT INTO pagamentos (comanda_id, caixa_id, forma, valor_centavos, recebido_por, criado_em)
               VALUES (?, ?, 'cheque', 500, ?, ?)""", (comanda, caixa, usuario, agora))
    # Perda de estoque sem PIN de gerente é recusada.
    with pytest.raises(sqlite3.IntegrityError):
        conexao.execute(
            """INSERT INTO movimentos_estoque (produto_id, tipo, quantidade, motivo, usuario_id, criado_em)
               VALUES (1, 'perda', -2, 'quebrou', ?, ?)""", (usuario, agora))


def test_dois_aparelhos_escrevendo_ao_mesmo_tempo(tmp_path):
    """Várias conexões (como vários tablets) gravando juntas sem perder nada."""
    caminho = tmp_path / "concorrencia.db"
    con = conectar(caminho)
    migrar(con)
    usuario, caixa = _criar_usuario_e_caixa(con)
    comanda = _abrir_comanda_mesa(con, 1, usuario, caixa)
    con.close()

    erros = []

    def lancar_itens():
        c = conectar(caminho)
        try:
            for _ in range(25):
                with transacao(c):
                    c.execute(
                        """INSERT INTO itens_comanda (comanda_id, produto_id, nome_produto,
                               preco_unitario_centavos, quantidade, lancado_por, lancado_em)
                           VALUES (?, 1, 'Brahma Lata', 800, 1, ?, ?)""",
                        (comanda, usuario, database.agora_texto()))
        except Exception as erro:  # noqa: BLE001 - o teste só registra
            erros.append(erro)
        finally:
            c.close()

    threads = [threading.Thread(target=lancar_itens) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert erros == []
    con = conectar(caminho)
    assert con.execute("SELECT COUNT(*) FROM itens_comanda").fetchone()[0] == 100
    con.close()
