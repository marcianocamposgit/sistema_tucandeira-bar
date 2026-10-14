import pytest

import config
from database import conectar, migrar
from models import AutorizacaoGerente
from services import caixa, usuarios
from tests.auxiliares import PIN_GERENTE, PIN_OPERADOR


@pytest.fixture(autouse=True)
def pin_rapido(monkeypatch):
    """PBKDF2 com poucas iterações nos testes (no sistema real são 200 mil)."""
    monkeypatch.setattr(config, "ITERACOES_PIN", 1000)


@pytest.fixture
def conexao(tmp_path):
    con = conectar(tmp_path / "teste.db")
    migrar(con, "desenvolvimento")
    yield con
    con.close()


@pytest.fixture
def gerente(conexao):
    return usuarios.criar_gerente_inicial(conexao, "Gerente", PIN_GERENTE)


@pytest.fixture
def autorizacao(gerente):
    return AutorizacaoGerente(gerente.id, PIN_GERENTE)


@pytest.fixture
def operador(conexao, gerente, autorizacao):
    return usuarios.cadastrar(conexao, "Operador", PIN_OPERADOR, "operador", gerente.id, autorizacao)


@pytest.fixture
def caixa_aberto(conexao, operador):
    return caixa.abrir(conexao, 10000, operador.id)
