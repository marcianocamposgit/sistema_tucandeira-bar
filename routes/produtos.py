"""Tela de produtos e estoque.

- Lista com nome, categoria, preço, estoque e mínimo; filtro por categoria e
  "só alertas"; destaque para estoque zerado, negativo ou abaixo do mínimo.
- Qualquer usuário vê a lista e o histórico e dá entrada de mercadoria.
- Cadastrar, editar, desativar e reativar produtos e categorias pedem a
  autorização do gerente na hora; perda e ajuste de contagem pedem motivo e gerente.
- Histórico por produto: entradas, perdas, ajustes e baixas por venda.
- Importar planilha: baixar o modelo (cardápio atual), enviar o CSV preenchido,
  conferir linha a linha e gravar com a autorização do gerente.
"""
from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for

from routes.conexao import obter_conexao
from routes.seguranca import autorizacao_do_formulario, login_obrigatorio
from services import importacao, produtos
from services.erros import DadosInvalidosError, ErroDeNegocio, NaoEncontradoError
from services.formatacao import formatar_valor_campo, ler_inteiro, ler_moeda, plural, valor_para_campo

bp = Blueprint("produtos", __name__, url_prefix="/produtos")

ATALHOS_ENTRADA = ["Compra do fornecedor", "Reposição do depósito"]
ATALHOS_PERDA = ["Quebrou", "Venceu", "Consumo da casa", "Estragou"]
ATALHOS_AJUSTE = ["Contagem do estoque", "Correção de lançamento"]

SITUACOES = {"negativo": "Estoque negativo", "zerado": "Sem estoque", "abaixo_minimo": "Abaixo do mínimo", "ok": ""}


def _obter_ou_voltar(produto_id):
    try:
        return produtos.obter_produto(obter_conexao(), produto_id), None
    except NaoEncontradoError as erro:
        flash(str(erro), "erro")
        return None, redirect(url_for("produtos.lista"))


def _categoria_do_formulario():
    try:
        return int(request.form.get("categoria_id", ""))
    except ValueError:
        raise DadosInvalidosError("Escolha a categoria.") from None


# ============================================================
# LISTA E HISTÓRICO
# ============================================================
@bp.route("/")
@login_obrigatorio
def lista():
    conexao = obter_conexao()
    categoria_id = request.args.get("categoria", type=int)
    so_alertas = request.args.get("alertas") == "1"
    mostrar_inativos = request.args.get("inativos") == "1"
    lista_produtos = produtos.listar_produtos(conexao, incluir_inativos=mostrar_inativos, categoria_id=categoria_id)
    if so_alertas:
        lista_produtos = [p for p in lista_produtos if p.ativo and p.precisa_atencao]
    alertas = produtos.listar_alertas_estoque(conexao)
    return render_template(
        "produtos/lista.html",
        produtos=lista_produtos,
        categorias=produtos.listar_categorias(conexao),
        categoria_id=categoria_id,
        so_alertas=so_alertas,
        mostrar_inativos=mostrar_inativos,
        alertas_texto=plural(len(alertas), "produto precisa", "produtos precisam") if alertas else "",
        situacoes=SITUACOES,
    )


@bp.route("/<int:produto_id>")
@login_obrigatorio
def detalhe(produto_id):
    produto, voltar = _obter_ou_voltar(produto_id)
    if produto is None:
        return voltar
    return render_template("produtos/detalhe.html", produto=produto, situacoes=SITUACOES,
                           historico=produtos.historico_estoque(obter_conexao(), produto_id))


# ============================================================
# CADASTRO E EDIÇÃO (gerente)
# ============================================================
def _dados_do_formulario():
    return {
        "nome": request.form.get("nome", ""),
        "categoria_id": request.form.get("categoria_id", type=int),
        "preco": valor_para_campo(request.form.get("preco", "")),
        "estoque_inicial": request.form.get("estoque_inicial", "").strip(),
        "estoque_minimo": request.form.get("estoque_minimo", "").strip(),
    }


def _tela_formulario(dados, produto=None):
    return render_template("produtos/formulario.html", dados=dados, produto=produto,
                           categorias=produtos.listar_categorias(obter_conexao()))


@bp.route("/novo", methods=["GET", "POST"])
@login_obrigatorio
def novo():
    if request.method == "GET":
        return _tela_formulario({"nome": "", "categoria_id": request.args.get("categoria", type=int), "preco": "",
                                 "estoque_inicial": "", "estoque_minimo": ""})
    dados = _dados_do_formulario()
    try:
        criado = produtos.cadastrar_produto(
            obter_conexao(), dados["nome"], _categoria_do_formulario(), ler_moeda(dados["preco"], "o preço"),
            g.usuario.id, autorizacao_do_formulario(),
            estoque_inicial=ler_inteiro(dados["estoque_inicial"] or "0", "o estoque inicial"),
            estoque_minimo=ler_inteiro(dados["estoque_minimo"] or "0", "o estoque mínimo"))
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return _tela_formulario(dados)
    flash(f"{criado.nome} cadastrado.", "sucesso")
    return redirect(url_for("produtos.detalhe", produto_id=criado.id))


@bp.route("/<int:produto_id>/editar", methods=["GET", "POST"])
@login_obrigatorio
def editar(produto_id):
    produto, voltar = _obter_ou_voltar(produto_id)
    if produto is None:
        return voltar
    if request.method == "GET":
        return _tela_formulario({"nome": produto.nome, "categoria_id": produto.categoria_id,
                                 "preco": formatar_valor_campo(produto.preco_centavos),
                                 "estoque_minimo": str(produto.estoque_minimo)}, produto)
    dados = _dados_do_formulario()
    try:
        produtos.editar_produto(
            obter_conexao(), produto_id, dados["nome"], _categoria_do_formulario(),
            ler_moeda(dados["preco"], "o preço"), ler_inteiro(dados["estoque_minimo"] or "0", "o estoque mínimo"),
            g.usuario.id, autorizacao_do_formulario())
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return _tela_formulario(dados, produto)
    flash("Produto alterado.", "sucesso")
    return redirect(url_for("produtos.detalhe", produto_id=produto_id))


@bp.route("/<int:produto_id>/<any(desativar, reativar):acao>", methods=["POST"])
@login_obrigatorio
def ativar(produto_id, acao):
    funcao = produtos.desativar_produto if acao == "desativar" else produtos.reativar_produto
    try:
        alterado = funcao(obter_conexao(), produto_id, g.usuario.id, autorizacao_do_formulario())
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
    else:
        flash(f"{alterado.nome} desativado: saiu do cardápio." if acao == "desativar"
              else f"{alterado.nome} reativado: voltou ao cardápio.", "sucesso")
    return redirect(url_for("produtos.detalhe", produto_id=produto_id))


# ============================================================
# MOVIMENTOS: ENTRADA, PERDA, AJUSTE
# ============================================================
MOVIMENTOS = {
    "entrada": {"titulo": "Entrada de mercadoria", "feito": "Entrada registrada", "rotulo": "Quantidade que chegou", "botao": "Registrar entrada",
                "atalhos": ATALHOS_ENTRADA, "gerente": False, "motivo": "Observação (opcional)"},
    "perda": {"titulo": "Perda", "feito": "Perda registrada", "rotulo": "Quantidade perdida", "botao": "Registrar perda",
              "atalhos": ATALHOS_PERDA, "gerente": True, "motivo": "Motivo"},
    "ajuste": {"titulo": "Ajuste de contagem", "feito": "Ajuste de contagem registrado", "rotulo": "Quantidade contada no estoque", "botao": "Registrar ajuste",
               "atalhos": ATALHOS_AJUSTE, "gerente": True, "motivo": "Motivo"},
}


@bp.route("/<int:produto_id>/<any(entrada, perda, ajuste):tipo>", methods=["GET", "POST"])
@login_obrigatorio
def movimento(produto_id, tipo):
    produto, voltar = _obter_ou_voltar(produto_id)
    if produto is None:
        return voltar
    dados = {"quantidade": request.form.get("quantidade", "").strip(), "motivo": request.form.get("motivo", "")}
    if request.method == "POST":
        conexao = obter_conexao()
        try:
            if tipo == "entrada":
                atualizado = produtos.registrar_entrada(conexao, produto_id, ler_inteiro(dados["quantidade"]),
                                                        g.usuario.id, observacao=dados["motivo"])
            elif tipo == "perda":
                atualizado = produtos.registrar_perda(conexao, produto_id, ler_inteiro(dados["quantidade"]),
                                                      dados["motivo"], g.usuario.id, autorizacao_do_formulario())
            else:
                atualizado = produtos.ajustar_contagem(conexao, produto_id,
                                                       ler_inteiro(dados["quantidade"], "a quantidade contada"),
                                                       dados["motivo"], g.usuario.id, autorizacao_do_formulario())
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash(f"{MOVIMENTOS[tipo]['feito']}. Estoque de {atualizado.nome} agora: "
                  f"{plural(atualizado.estoque, 'unidade', 'unidades')}.", "sucesso")
            return redirect(url_for("produtos.detalhe", produto_id=produto_id))
    return render_template("produtos/movimento.html", produto=produto, tipo=tipo, textos=MOVIMENTOS[tipo],
                           dados=dados, estoque_texto=plural(produto.estoque, "unidade", "unidades"))


# ============================================================
# CATEGORIAS (gerente)
# ============================================================
@bp.route("/categorias", methods=["GET", "POST"])
@login_obrigatorio
def categorias():
    conexao = obter_conexao()
    if request.method == "POST":
        acao = request.form.get("acao", "")
        categoria_id = request.form.get("categoria_id", type=int)
        nome = request.form.get("nome", "")
        try:
            autorizacao = autorizacao_do_formulario()
            if acao == "criar":
                feita = produtos.criar_categoria(conexao, nome, g.usuario.id, autorizacao)
                mensagem = f"Categoria {feita.nome} criada. Ela aparece no cardápio quando tiver produtos."
            elif acao == "renomear":
                feita = produtos.renomear_categoria(conexao, categoria_id, nome, g.usuario.id, autorizacao)
                mensagem = f"Categoria renomeada para {feita.nome}."
            elif acao == "desativar":
                feita = produtos.desativar_categoria(conexao, categoria_id, g.usuario.id, autorizacao)
                mensagem = f"Categoria {feita.nome} desativada."
            elif acao == "reativar":
                feita = produtos.reativar_categoria(conexao, categoria_id, g.usuario.id, autorizacao)
                mensagem = f"Categoria {feita.nome} reativada."
            else:
                raise DadosInvalidosError("Ação inválida.")
        except ErroDeNegocio as erro:
            flash(str(erro), "erro")
        else:
            flash(mensagem, "sucesso")
        return redirect(url_for("produtos.categorias"))
    lista_categorias = produtos.listar_categorias(conexao, incluir_inativas=True)
    todos = produtos.listar_produtos(conexao)
    ativos = {c.id: plural(sum(1 for p in todos if p.categoria_id == c.id), "produto ativo", "produtos ativos")
              for c in lista_categorias}
    return render_template("produtos/categorias.html", categorias=lista_categorias, ativos=ativos)


# ============================================================
# IMPORTAR PLANILHA DO CARDÁPIO
# ============================================================
@bp.route("/importar")
@login_obrigatorio
def importar():
    return render_template("produtos/importar.html", conferencia=None)


@bp.route("/importar/modelo")
@login_obrigatorio
def modelo_planilha():
    return Response(
        importacao.modelo_csv(obter_conexao()).encode("utf-8"),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="cardapio_tucandeira.csv"'},
    )


@bp.route("/importar/conferir", methods=["POST"])
@login_obrigatorio
def conferir_planilha():
    """Passo 1: lê o arquivo e mostra a conferência (nada é gravado)."""
    arquivo = request.files.get("planilha")
    try:
        texto = importacao.ler_arquivo(arquivo.read() if arquivo else b"")
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return redirect(url_for("produtos.importar"))
    return render_template("produtos/importar.html", texto=texto,
                           nome_arquivo=arquivo.filename if arquivo else "",
                           conferencia=importacao.conferir(obter_conexao(), texto))


@bp.route("/importar/gravar", methods=["POST"])
@login_obrigatorio
def gravar_planilha():
    """Passo 2: grava (a conferência é refeita dentro da transação)."""
    texto = request.form.get("texto", "")
    conexao = obter_conexao()
    try:
        resultado = importacao.importar(conexao, texto, g.usuario.id, autorizacao_do_formulario(),
                                        desativar_ausentes=request.form.get("desativar_ausentes") == "1")
    except ErroDeNegocio as erro:
        flash(str(erro), "erro")
        return render_template("produtos/importar.html", texto=texto,
                               nome_arquivo=request.form.get("nome_arquivo", ""),
                               conferencia=importacao.conferir(conexao, texto))
    flash(importacao.resumo_resultado(resultado), "sucesso")
    return redirect(url_for("produtos.lista"))
