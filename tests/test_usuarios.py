import pytest

from models import AutorizacaoGerente
from services import usuarios
from services.erros import (
    DadosInvalidosError,
    NomeDuplicadoError,
    PermissaoNegadaError,
    PinInvalidoError,
    UltimoGerenteError,
)
from tests.auxiliares import PIN_GERENTE, PIN_OPERADOR


def test_pin_guardado_com_hash_e_salt(conexao, gerente):
    linha = conexao.execute("SELECT pin_hash, pin_salt FROM usuarios WHERE id = ?", (gerente.id,)).fetchone()
    assert PIN_GERENTE not in linha["pin_hash"]
    assert len(linha["pin_salt"]) == 32


@pytest.mark.parametrize("pin", ["123", "12345", "abcd", "12a4", "", None, 1234, "１２３４"])
def test_pin_precisa_ter_4_numeros(conexao, pin):
    with pytest.raises(DadosInvalidosError):
        usuarios.criar_gerente_inicial(conexao, "Gerente", pin)


def test_gerente_inicial_so_uma_vez(conexao, gerente):
    with pytest.raises(PermissaoNegadaError):
        usuarios.criar_gerente_inicial(conexao, "Outro", "9999")


def test_login_por_nome_e_pin(conexao, gerente, operador):
    assert usuarios.autenticar(conexao, operador.id, PIN_OPERADOR).id == operador.id
    assert conexao.execute("SELECT COUNT(*) FROM auditoria WHERE acao = 'login'").fetchone()[0] == 1
    with pytest.raises(PinInvalidoError) as erro:
        usuarios.autenticar(conexao, operador.id, PIN_GERENTE)
    assert str(erro.value) == "PIN incorreto."


def test_login_com_usuario_inexistente_ou_inativo_tem_a_mesma_mensagem(conexao, gerente, operador, autorizacao):
    with pytest.raises(PinInvalidoError) as inexistente:
        usuarios.autenticar(conexao, 999, PIN_OPERADOR)
    usuarios.desativar(conexao, operador.id, gerente.id, autorizacao)
    with pytest.raises(PinInvalidoError) as inativo:
        usuarios.autenticar(conexao, operador.id, PIN_OPERADOR)
    assert str(inexistente.value) == str(inativo.value) == "PIN incorreto."


def test_pin_igual_em_dois_usuarios_e_permitido(conexao, gerente, autorizacao):
    a = usuarios.cadastrar(conexao, "Ana", "1111", "operador", gerente.id, autorizacao)
    b = usuarios.cadastrar(conexao, "Bruno", "1111", "operador", gerente.id, autorizacao)
    assert usuarios.autenticar(conexao, a.id, "1111").nome == "Ana"
    assert usuarios.autenticar(conexao, b.id, "1111").nome == "Bruno"


def test_nome_duplicado_sem_diferenciar_maiusculas(conexao, gerente, autorizacao):
    usuarios.cadastrar(conexao, "Ana", "1111", "operador", gerente.id, autorizacao)
    with pytest.raises(NomeDuplicadoError):
        usuarios.cadastrar(conexao, "  ana ", "2222", "operador", gerente.id, autorizacao)


def test_cadastrar_exige_gerente(conexao, gerente, operador):
    with pytest.raises(PermissaoNegadaError):
        usuarios.cadastrar(conexao, "Ana", "1111", "operador", operador.id,
                           AutorizacaoGerente(gerente.id, "0000"))
    # PIN certo, mas de um operador: também é negado.
    with pytest.raises(PermissaoNegadaError):
        usuarios.cadastrar(conexao, "Ana", "1111", "operador", operador.id,
                           AutorizacaoGerente(operador.id, PIN_OPERADOR))
    with pytest.raises(PermissaoNegadaError):
        usuarios.cadastrar(conexao, "Ana", "1111", "operador", operador.id, None)


def test_listas_para_login_e_autorizacao(conexao, gerente, operador, autorizacao):
    usuarios.cadastrar(conexao, "Ana", "1111", "operador", gerente.id, autorizacao)
    assert [u.nome for u in usuarios.listar_ativos(conexao)] == ["Ana", "Gerente", "Operador"]
    assert [u.nome for u in usuarios.listar_gerentes(conexao)] == ["Gerente"]


def test_nao_desativa_nem_rebaixa_o_ultimo_gerente(conexao, gerente, operador, autorizacao):
    with pytest.raises(UltimoGerenteError):
        usuarios.desativar(conexao, gerente.id, gerente.id, autorizacao)
    with pytest.raises(UltimoGerenteError):
        usuarios.editar(conexao, gerente.id, "Gerente", "operador", gerente.id, autorizacao)
    # Com um segundo gerente, pode.
    segundo = usuarios.cadastrar(conexao, "Chefe", "4321", "gerente", gerente.id, autorizacao)
    usuarios.desativar(conexao, gerente.id, segundo.id, AutorizacaoGerente(segundo.id, "4321"))
    assert not usuarios.obter(conexao, gerente.id).ativo


def test_trocar_o_proprio_pin_e_o_de_outro(conexao, gerente, operador, autorizacao):
    with pytest.raises(PinInvalidoError):
        usuarios.trocar_pin(conexao, operador.id, "0000", operador.id, pin_atual="9999")
    usuarios.trocar_pin(conexao, operador.id, "0000", operador.id, pin_atual=PIN_OPERADOR)
    usuarios.autenticar(conexao, operador.id, "0000")
    # Trocar o PIN de outra pessoa exige gerente.
    with pytest.raises(PermissaoNegadaError):
        usuarios.trocar_pin(conexao, gerente.id, "1111", operador.id)
    usuarios.trocar_pin(conexao, operador.id, "2468", gerente.id, autorizacao=autorizacao)
    usuarios.autenticar(conexao, operador.id, "2468")
