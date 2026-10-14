from datetime import date

import pytest

import config
from database import conectar, migrar
from scripts import popular_demo
from services import caixa, comandas, produtos, usuarios


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
    situacoes = {p.nome: p.situacao_estoque for p in produtos.listar_alertas_estoque(con)}
    assert situacoes["Isqueiro"] == "zerado" and situacoes["Isca de Peixe"] == "abaixo_minimo"


def test_nao_popula_duas_vezes(banco_dev):
    _, con = banco_dev
    popular_demo.popular(con, hoje=date(2026, 10, 14))
    with pytest.raises(popular_demo.DemoJaPopuladaError):
        popular_demo.popular(con)
