from datetime import date

import pytest

import config
from database import conectar, migrar
from scripts import popular_demo
from services import caixa, comandas, configuracoes, produtos, usuarios


@pytest.fixture
def banco_dev(tmp_path, monkeypatch):
    """Simula a pasta data/ do projeto numa pasta temporária."""
    monkeypatch.setattr(config, "PASTA_DADOS_DESENVOLVIMENTO", tmp_path)
    con = conectar(tmp_path / config.NOME_BANCO)
    migrar(con, "desenvolvimento")
    yield tmp_path, con
    con.close()


def test_recusa_banco_de_producao(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PASTA_DADOS_DESENVOLVIMENTO", tmp_path)
    con = conectar(tmp_path / config.NOME_BANCO)
    migrar(con, "producao")
    with pytest.raises(popular_demo.AmbienteProibidoError):
        popular_demo.verificar_ambiente(tmp_path, con, executavel=False)
    con.close()


def test_recusa_outra_pasta_de_dados(banco_dev, tmp_path_factory):
    _, con = banco_dev
    with pytest.raises(popular_demo.AmbienteProibidoError):
        popular_demo.verificar_ambiente(tmp_path_factory.mktemp("outra"), con, executavel=False)


def test_recusa_no_executavel(banco_dev):
    pasta, con = banco_dev
    with pytest.raises(popular_demo.AmbienteProibidoError):
        popular_demo.verificar_ambiente(pasta, con, executavel=True)


def test_aceita_banco_de_desenvolvimento(banco_dev):
    pasta, con = banco_dev
    popular_demo.verificar_ambiente(pasta, con, executavel=False)


def test_main_recusa_producao_sem_alterar_nada(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "PASTA_DADOS", tmp_path)
    con = conectar(tmp_path / config.NOME_BANCO)
    migrar(con, "producao")
    con.close()
    assert popular_demo.main(["--recriar"]) == 1
    assert "Recusado" in capsys.readouterr().out
    con = conectar(tmp_path / config.NOME_BANCO)
    assert not usuarios.existe_usuario(con)
    con.close()


def test_popular(banco_dev):
    _, con = banco_dev
    resumo = popular_demo.popular(con, hoje=date(2026, 10, 14))  # quarta-feira
    assert [u.nome for u in usuarios.listar_ativos(con)] == ["Ana", "Bruno", "Gerente Demo"]
    assert usuarios.autenticar(con, usuarios.listar_gerentes(con)[0].id, "1234").gerente
    assert resumo["produtos"] == 26
    assert resumo["caixas_fechados"] == 12  # 14 dias menos 2 segundas-feiras
    fechados = con.execute("SELECT COUNT(*) FROM caixas WHERE status = 'fechado'").fetchone()[0]
    assert fechados == 12 and caixa.caixa_aberto(con) is not None
    assert resumo["comandas_abertas"] == 5
    estados = {e.numero: e.status for e in comandas.estado_mesas(con)}
    assert (estados[2], estados[3], estados[4], estados[5]) == ("ocupada", "ocupada", "ocupada", "conta_pedida")
    mesa2 = comandas.calcular_conta(con, comandas.comanda_da_mesa(con, 2).id)
    assert mesa2.pago_centavos == 3200 and mesa2.saldo_centavos > 0


def _contar(con, sql):
    return con.execute(sql).fetchone()[0]


def test_popular_cria_historico_de_vendas(banco_dev):
    _, con = banco_dev
    resumo = popular_demo.popular(con, hoje=date(2026, 10, 14))
    assert resumo["vendas"] > 100
    assert _contar(con, "SELECT COUNT(*) FROM vendas") == resumo["vendas"]
    # As 4 formas de pagamento, pagamentos parciais, troco, estornos e descontos.
    formas = {l[0] for l in con.execute("SELECT DISTINCT forma FROM pagamentos")}
    assert formas == {"dinheiro", "debito", "credito", "pix"}
    assert _contar(con, "SELECT COUNT(*) FROM (SELECT comanda_id FROM pagamentos GROUP BY comanda_id "
                        "HAVING COUNT(*) > 1)") > 0
    assert _contar(con, "SELECT COUNT(*) FROM pagamentos WHERE troco_centavos > 0") > 0
    assert _contar(con, "SELECT COUNT(*) FROM pagamentos WHERE estornado_em IS NOT NULL") > 0
    assert _contar(con, "SELECT COUNT(*) FROM descontos") > 0
    assert _contar(con, "SELECT COUNT(*) FROM item_ajustes WHERE tipo = 'cancelamento'") > 0
    assert _contar(con, "SELECT COUNT(*) FROM item_ajustes WHERE tipo = 'remocao'") > 0
    # Cada venda fechada bate com os pagamentos não estornados da comanda.
    assert _contar(con, """SELECT COUNT(*) FROM vendas v WHERE v.total_centavos <> (
        SELECT COALESCE(SUM(valor_centavos), 0) FROM pagamentos p
        WHERE p.comanda_id = v.comanda_id AND p.estornado_em IS NULL)""") == 0
    # Conferência gravada = pagamentos do caixa (o esperado considera as vendas).
    assert _contar(con, """SELECT COUNT(*) FROM caixa_conferencias c WHERE c.forma <> 'dinheiro'
        AND c.esperado_centavos <> (SELECT COALESCE(SUM(valor_centavos), 0) FROM pagamentos p
            WHERE p.caixa_id = c.caixa_id AND p.forma = c.forma AND p.estornado_em IS NULL)""") == 0
    # Vendas sem estoque deixam produtos negativos, e o desconto termina desligado (padrão).
    assert any(p.situacao_estoque == "negativo" for p in produtos.listar_alertas_estoque(con))
    assert not configuracoes.desconto_permitido(con)


def test_nao_popula_duas_vezes(banco_dev):
    _, con = banco_dev
    popular_demo.popular(con, hoje=date(2026, 10, 14))
    with pytest.raises(popular_demo.DemoJaPopuladaError):
        popular_demo.popular(con)
