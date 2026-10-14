"""Usuários, login por nome + PIN e autorização de gerente.

Regras:
- O login é feito escolhendo o usuário (pelo nome) e digitando o PIN de 4 dígitos.
- PINs podem se repetir entre usuários, e nada aqui revela se um PIN já existe.
- O PIN é guardado com PBKDF2 + salt, nunca em texto puro.
- Sempre deve existir pelo menos um gerente ativo.
"""
import hashlib
import hmac
import secrets

import config
from database import transacao
from models import AutorizacaoGerente, Usuario, de_linha
from models.usuarios import PERFIS
from services.comum import exigir_texto, registrar_auditoria, texto_data
from services.erros import (
    DadosInvalidosError,
    NaoEncontradoError,
    NomeDuplicadoError,
    PermissaoNegadaError,
    PinInvalidoError,
    UltimoGerenteError,
)

COLUNAS = "id, nome, perfil, ativo, criado_em, criado_por"


# ============================================================
# PIN
# ============================================================
def validar_pin(pin):
    if not isinstance(pin, str) or len(pin) != 4 or not pin.isdigit() or not pin.isascii():
        raise DadosInvalidosError("O PIN deve ter exatamente 4 números.")
    return pin


def gerar_hash_pin(pin, salt=None, iteracoes=None):
    """Devolve (pin_hash, pin_salt). O hash guarda o número de iterações usado."""
    iteracoes = iteracoes or config.ITERACOES_PIN
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), iteracoes)
    return f"{iteracoes}${digest.hex()}", salt


def _pin_confere(pin, pin_hash, pin_salt):
    try:
        iteracoes_texto, _ = pin_hash.split("$", 1)
        iteracoes = int(iteracoes_texto)
    except ValueError:
        return False
    calculado, _ = gerar_hash_pin(pin, pin_salt, iteracoes)
    return hmac.compare_digest(calculado, pin_hash)


# ============================================================
# CONSULTAS
# ============================================================
def _usuario(linha):
    return de_linha(Usuario, linha, ativo=bool(linha["ativo"]))


def existe_usuario(conexao):
    return conexao.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None


def obter(conexao, usuario_id):
    linha = conexao.execute(f"SELECT {COLUNAS} FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if linha is None:
        raise NaoEncontradoError("Usuário não encontrado.")
    return _usuario(linha)


def listar_ativos(conexao):
    """Usuários que aparecem na tela de login, em ordem alfabética."""
    linhas = conexao.execute(
        f"SELECT {COLUNAS} FROM usuarios WHERE ativo = 1 ORDER BY nome COLLATE NOCASE"
    ).fetchall()
    return [_usuario(l) for l in linhas]


def listar_gerentes(conexao):
    """Gerentes ativos, para o quadro de autorização."""
    return [u for u in listar_ativos(conexao) if u.gerente]


def listar_todos(conexao):
    linhas = conexao.execute(
        f"SELECT {COLUNAS} FROM usuarios ORDER BY ativo DESC, nome COLLATE NOCASE"
    ).fetchall()
    return [_usuario(l) for l in linhas]


def _contar_gerentes_ativos(conexao):
    return conexao.execute(
        "SELECT COUNT(*) FROM usuarios WHERE perfil = 'gerente' AND ativo = 1"
    ).fetchone()[0]


# ============================================================
# LOGIN E AUTORIZAÇÃO
# ============================================================
def autenticar(conexao, usuario_id, pin, agora=None):
    """Confere o PIN do usuário escolhido. Erro sempre genérico (PinInvalidoError)."""
    linha = conexao.execute(
        f"SELECT {COLUNAS}, pin_hash, pin_salt FROM usuarios WHERE id = ? AND ativo = 1",
        (usuario_id,),
    ).fetchone()
    if linha is None or not isinstance(pin, str) or not _pin_confere(pin, linha["pin_hash"], linha["pin_salt"]):
        raise PinInvalidoError()
    with transacao(conexao):
        registrar_auditoria(conexao, "login", linha["id"], agora=agora)
    return _usuario(linha)


def verificar_gerente(conexao, autorizacao):
    """Confere a autorização (gerente + PIN) e devolve o gerente.

    Pode ser chamada dentro de uma transação (só lê o banco).
    """
    if not isinstance(autorizacao, AutorizacaoGerente):
        raise PermissaoNegadaError()
    linha = conexao.execute(
        f"""SELECT {COLUNAS}, pin_hash, pin_salt FROM usuarios
            WHERE id = ? AND ativo = 1 AND perfil = 'gerente'""",
        (autorizacao.gerente_id,),
    ).fetchone()
    if linha is None or not isinstance(autorizacao.pin, str) or \
            not _pin_confere(autorizacao.pin, linha["pin_hash"], linha["pin_salt"]):
        raise PermissaoNegadaError("Autorização negada: gerente ou PIN incorreto.")
    return _usuario(linha)


def autorizar_gerente(conexao, gerente_id, pin):
    """Atalho: monta a autorização e confere. Devolve o gerente."""
    return verificar_gerente(conexao, AutorizacaoGerente(gerente_id, pin))


# ============================================================
# CADASTRO
# ============================================================
def _validar_nome(conexao, nome, ignorar_id=None):
    nome = exigir_texto(nome, "o nome", maximo=40)
    existente = conexao.execute(
        "SELECT id FROM usuarios WHERE nome = ? COLLATE NOCASE AND id IS NOT ?", (nome, ignorar_id)
    ).fetchone()
    if existente:
        raise NomeDuplicadoError(f"Já existe um usuário chamado {nome}.")
    return nome


def _validar_perfil(perfil):
    if perfil not in PERFIS:
        raise DadosInvalidosError("Perfil inválido. Use Operador ou Gerente.")
    return perfil


def _inserir(conexao, nome, pin, perfil, criado_por, agora):
    pin_hash, pin_salt = gerar_hash_pin(pin)
    cursor = conexao.execute(
        """INSERT INTO usuarios (nome, pin_hash, pin_salt, perfil, criado_em, criado_por)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (nome, pin_hash, pin_salt, perfil, texto_data(agora), criado_por),
    )
    return cursor.lastrowid


def criar_gerente_inicial(conexao, nome, pin, agora=None):
    """Primeiro acesso: cria o gerente sem pedir autorização (só se não houver usuários)."""
    validar_pin(pin)
    with transacao(conexao):
        if existe_usuario(conexao):
            raise PermissaoNegadaError("O gerente inicial já foi criado.")
        nome = _validar_nome(conexao, nome)
        novo_id = _inserir(conexao, nome, pin, "gerente", None, agora)
        registrar_auditoria(conexao, "usuario_criado", novo_id,
                            {"usuario_id": novo_id, "nome": nome, "perfil": "gerente", "inicial": True},
                            agora=agora)
    return obter(conexao, novo_id)


def cadastrar(conexao, nome, pin, perfil, usuario_id, autorizacao, agora=None):
    """Cadastra um usuário. Exige autorização de gerente."""
    validar_pin(pin)
    _validar_perfil(perfil)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        nome = _validar_nome(conexao, nome)
        novo_id = _inserir(conexao, nome, pin, perfil, usuario_id, agora)
        registrar_auditoria(conexao, "usuario_criado", usuario_id,
                            {"usuario_id": novo_id, "nome": nome, "perfil": perfil},
                            autorizado_por=gerente.id, agora=agora)
    return obter(conexao, novo_id)


def editar(conexao, alvo_id, nome, perfil, usuario_id, autorizacao, agora=None):
    """Muda nome e perfil. Exige gerente; não pode deixar o bar sem gerente ativo."""
    _validar_perfil(perfil)
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        atual = obter(conexao, alvo_id)
        nome = _validar_nome(conexao, nome, ignorar_id=alvo_id)
        if atual.gerente and atual.ativo and perfil != "gerente" and _contar_gerentes_ativos(conexao) <= 1:
            raise UltimoGerenteError()
        conexao.execute("UPDATE usuarios SET nome = ?, perfil = ? WHERE id = ?", (nome, perfil, alvo_id))
        registrar_auditoria(conexao, "usuario_editado", usuario_id,
                            {"usuario_id": alvo_id, "antes": {"nome": atual.nome, "perfil": atual.perfil},
                             "depois": {"nome": nome, "perfil": perfil}},
                            autorizado_por=gerente.id, agora=agora)
    return obter(conexao, alvo_id)


def trocar_pin(conexao, alvo_id, novo_pin, usuario_id, pin_atual=None, autorizacao=None, agora=None):
    """Troca o PIN.

    O próprio usuário troca informando o PIN atual; para trocar o PIN de outra
    pessoa (ex.: esqueceu), é preciso autorização de gerente.
    """
    validar_pin(novo_pin)
    with transacao(conexao):
        autorizado_por = None
        if alvo_id == usuario_id and pin_atual is not None:
            linha = conexao.execute(
                "SELECT pin_hash, pin_salt FROM usuarios WHERE id = ? AND ativo = 1", (alvo_id,)
            ).fetchone()
            if linha is None or not _pin_confere(pin_atual, linha["pin_hash"], linha["pin_salt"]):
                raise PinInvalidoError("PIN atual incorreto.")
        else:
            autorizado_por = verificar_gerente(conexao, autorizacao).id
        obter(conexao, alvo_id)
        pin_hash, pin_salt = gerar_hash_pin(novo_pin)
        conexao.execute("UPDATE usuarios SET pin_hash = ?, pin_salt = ? WHERE id = ?",
                        (pin_hash, pin_salt, alvo_id))
        registrar_auditoria(conexao, "pin_trocado", usuario_id, {"usuario_id": alvo_id},
                            autorizado_por=autorizado_por, agora=agora)


def desativar(conexao, alvo_id, usuario_id, autorizacao, agora=None):
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        alvo = obter(conexao, alvo_id)
        if not alvo.ativo:
            return alvo
        if alvo.gerente and _contar_gerentes_ativos(conexao) <= 1:
            raise UltimoGerenteError()
        conexao.execute("UPDATE usuarios SET ativo = 0 WHERE id = ?", (alvo_id,))
        registrar_auditoria(conexao, "usuario_desativado", usuario_id, {"usuario_id": alvo_id},
                            autorizado_por=gerente.id, agora=agora)
    return obter(conexao, alvo_id)


def reativar(conexao, alvo_id, usuario_id, autorizacao, agora=None):
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        obter(conexao, alvo_id)
        conexao.execute("UPDATE usuarios SET ativo = 1 WHERE id = ?", (alvo_id,))
        registrar_auditoria(conexao, "usuario_reativado", usuario_id, {"usuario_id": alvo_id},
                            autorizado_por=gerente.id, agora=agora)
    return obter(conexao, alvo_id)
