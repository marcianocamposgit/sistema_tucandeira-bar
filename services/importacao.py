"""Importação do cardápio por planilha (CSV, que o Excel abre e salva).

Colunas: Categoria; Produto; Preço; Estoque; Estoque mínimo.

Regras:
- Primeiro a planilha é conferida (nada é gravado) e a tela mostra, linha a linha,
  o que vai acontecer: produto novo, o que muda num produto existente, ou o erro.
- Só grava se nenhuma linha tiver erro, tudo numa transação única, com a
  autorização do gerente (a conferência é refeita na hora de gravar).
- O produto é reconhecido pelo nome (sem diferença de maiúsculas). Categoria que
  não existe é criada; categoria desativada é reativada.
- Estoque em branco = não mexe (produto novo começa com 0). Estoque preenchido num
  produto existente vira um ajuste de contagem (movimento de estoque com motivo).
  Por isso o modelo vem com o estoque em branco: assim um preço corrigido dias
  depois não volta o estoque para um número velho.
- Produtos que não estão na planilha continuam como estão, a não ser que o gerente
  marque "desativar os que não estão na planilha".
"""
import csv
import io
import re
import unicodedata

from database import transacao
from models.importacao import ConferenciaImportacao, LinhaImportacao, ResultadoImportacao
from services import produtos
from services.comum import registrar_auditoria
from services.erros import DadosInvalidosError
from services.formatacao import formatar_moeda, formatar_valor_campo, ler_moeda, plural
from services.usuarios import verificar_gerente

CABECALHO = ["Categoria", "Produto", "Preço", "Estoque", "Estoque mínimo"]
OBRIGATORIAS = ("categoria", "produto", "preco")
NOMES_COLUNAS = {"categoria": "Categoria", "produto": "Produto", "preco": "Preço"}
MAXIMO_LINHAS = 1000
MAXIMO_BYTES = 1024 * 1024
MOTIVO_AJUSTE = "Importação da planilha do cardápio"


# ============================================================
# MODELO
# ============================================================
def modelo_csv(conexao):
    """Planilha com o cardápio atual (produtos ativos), pronta para o dono editar.

    O estoque fica em branco: preencha só para produtos novos ou para corrigir a contagem.
    """
    linhas = [CABECALHO]
    for categoria, lista in produtos.cardapio(conexao):
        for p in lista:
            linhas.append([categoria.nome, p.nome, formatar_valor_campo(p.preco_centavos), "", p.estoque_minimo])
    saida = io.StringIO()
    csv.writer(saida, delimiter=";", lineterminator="\r\n").writerows(linhas)
    return "﻿" + saida.getvalue()


# ============================================================
# LEITURA DO ARQUIVO
# ============================================================
def ler_arquivo(conteudo):
    """Texto do arquivo enviado (bytes). Aceita CSV em UTF-8 (com ou sem BOM) ou no
    padrão antigo do Excel no Windows (cp1252). Recusa .xlsx com a explicação."""
    if not conteudo:
        raise DadosInvalidosError("Escolha o arquivo da planilha.")
    if len(conteudo) > MAXIMO_BYTES:
        raise DadosInvalidosError("O arquivo é grande demais para um cardápio (máximo 1 MB).")
    if conteudo[:2] == b"PK":
        raise DadosInvalidosError(
            "Este arquivo está no formato do Excel (.xlsx). No Excel, use Arquivo → Salvar como → "
            "\"CSV UTF-8 (delimitado por vírgulas)\" e envie o arquivo .csv.")
    try:
        return conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return conteudo.decode("cp1252", errors="replace")


def _normalizar(texto):
    """'Estoque Mínimo ' → 'estoqueminimo' (sem acento, espaço nem pontuação)."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", sem_acento.lower())


def _coluna(cabecalho):
    nome = _normalizar(cabecalho)
    if nome.startswith("categ"):
        return "categoria"
    if nome in ("produto", "nome", "nomedoproduto", "descricao"):
        return "produto"
    if nome.startswith(("preco", "valor")):
        return "preco"
    if "minimo" in nome or nome == "estoquemin":
        return "estoque_minimo"
    if nome.startswith(("estoque", "quantidade", "qtd")):
        return "estoque"
    return None


def _separador(primeira_linha):
    return max([";", ",", "\t"], key=primeira_linha.count)


def _limpar(texto):
    return (texto or "").replace("\xa0", " ").strip()


def _ler_quantidade(texto, campo):
    """'24' → 24; em branco → None. Aceita '1.000' (milhar) e '24,0' (Excel)."""
    limpo = _limpar(texto).replace(" ", "")
    if not limpo:
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", limpo):
        limpo = limpo.replace(".", "")
    limpo = re.sub(r"[,.]0+$", "", limpo)
    if re.fullmatch(r"-\d+", limpo):
        raise DadosInvalidosError(f"O {campo} não pode ser negativo.")
    if not re.fullmatch(r"\d+", limpo):
        raise DadosInvalidosError(f"{campo.capitalize()} inválido: \"{_limpar(texto)}\" (use um número inteiro, ex.: 24).")
    return int(limpo)


def _ler_linhas(texto, conferencia):
    """Lê o CSV. Devolve [(número da linha, {coluna: texto})], ou [] com o erro geral anotado."""
    linhas_texto = (texto or "").lstrip("﻿").splitlines()
    while linhas_texto and not linhas_texto[0].strip(" ;,\t"):
        linhas_texto.pop(0)
    if not linhas_texto:
        conferencia.erros_gerais.append("A planilha está vazia.")
        return []
    leitor = csv.reader(io.StringIO("\n".join(linhas_texto)), delimiter=_separador(linhas_texto[0]))
    cabecalho = next(leitor)
    colunas = [_coluna(c) for c in cabecalho]
    faltando = [NOMES_COLUNAS[c] for c in OBRIGATORIAS if c not in colunas]
    if faltando:
        conferencia.erros_gerais.append(
            "A primeira linha precisa ter os nomes das colunas: Categoria, Produto, Preço, Estoque e "
            f"Estoque mínimo (faltou: {', '.join(faltando)}). Baixe o modelo para ver o formato.")
        return []
    resultado = []
    for numero, valores in enumerate(leitor, start=2):
        if not any(_limpar(v) for v in valores):
            continue  # linha em branco
        dados = {}
        for coluna, valor in zip(colunas, valores):
            if coluna and coluna not in dados:
                dados[coluna] = valor
        resultado.append((numero, dados))
    if len(resultado) > MAXIMO_LINHAS:
        conferencia.erros_gerais.append(f"A planilha tem linhas demais (máximo {MAXIMO_LINHAS}).")
        return []
    if not resultado:
        conferencia.erros_gerais.append("A planilha só tem a linha dos nomes das colunas, sem nenhum produto.")
    return resultado


# ============================================================
# CONFERÊNCIA (não grava nada)
# ============================================================
def _validar_linha(numero, dados):
    linha = LinhaImportacao(numero, _limpar(dados.get("categoria")), _limpar(dados.get("produto")))
    if not linha.categoria:
        linha.erros.append("Falta a categoria.")
    elif len(linha.categoria) > 30:
        linha.erros.append("O nome da categoria pode ter no máximo 30 letras.")
    if not linha.produto:
        linha.erros.append("Falta o nome do produto.")
    elif len(linha.produto) > 60:
        linha.erros.append("O nome do produto pode ter no máximo 60 letras.")
    try:
        linha.preco_centavos = ler_moeda(_limpar(dados.get("preco")), "o preço")
    except DadosInvalidosError:
        texto = _limpar(dados.get("preco"))
        linha.erros.append(f"Preço inválido: \"{texto}\" (use o formato 12,50)." if texto else "Falta o preço.")
    for coluna, campo in (("estoque", "estoque"), ("estoque_minimo", "estoque mínimo")):
        try:
            setattr(linha, coluna, _ler_quantidade(dados.get(coluna), campo))
        except DadosInvalidosError as erro:
            linha.erros.append(str(erro))
    return linha


def _comparar(linha, atual, categorias, conferencia):
    """Preenche a ação e as mudanças da linha comparando com o produto do banco."""
    categoria = categorias.get(linha.categoria.lower())
    nome_categoria = categoria.nome if categoria else linha.categoria
    if atual is None:
        linha.acao = "novo"
        partes = [nome_categoria, formatar_moeda(linha.preco_centavos),
                  f"estoque {linha.estoque or 0}", f"mínimo {linha.estoque_minimo or 0}"]
        linha.mudancas.append("Produto novo: " + ", ".join(partes))
        return
    linha.produto_id = atual.id
    if atual.nome != linha.produto:
        linha.mudancas.append(f"Nome: {atual.nome} → {linha.produto}")
    if atual.categoria_nome.lower() != linha.categoria.lower():
        linha.mudancas.append(f"Categoria: {atual.categoria_nome} → {nome_categoria}")
    if atual.preco_centavos != linha.preco_centavos:
        linha.mudancas.append(f"Preço: {formatar_moeda(atual.preco_centavos)} → {formatar_moeda(linha.preco_centavos)}")
    if linha.estoque_minimo is not None and atual.estoque_minimo != linha.estoque_minimo:
        linha.mudancas.append(f"Estoque mínimo: {atual.estoque_minimo} → {linha.estoque_minimo}")
    if linha.estoque is not None and atual.estoque != linha.estoque:
        linha.mudancas.append(f"Estoque: {atual.estoque} → {linha.estoque} (ajuste de contagem)")
    if not atual.ativo:
        linha.mudancas.append("Volta ao cardápio (estava desativado)")
    linha.acao = "alterar" if linha.mudancas else "igual"


def conferir(conexao, texto):
    """Confere a planilha contra o cardápio atual, sem gravar nada."""
    conferencia = ConferenciaImportacao()
    lidas = _ler_linhas(texto, conferencia)
    if conferencia.erros_gerais:
        return conferencia

    categorias = {c.nome.lower(): c for c in produtos.listar_categorias(conexao, incluir_inativas=True)}
    existentes = {p.nome.lower(): p for p in produtos.listar_produtos(conexao, incluir_inativos=True)}
    vistos, categorias_da_planilha = {}, {}
    for numero, dados in lidas:
        linha = _validar_linha(numero, dados)
        chave = linha.produto.lower()
        if linha.produto and chave in vistos:
            linha.erros.append(f"O produto {linha.produto} já aparece na linha {vistos[chave]}.")
        elif linha.produto:
            vistos[chave] = numero
        if linha.categoria:
            # Mesma categoria escrita de jeitos diferentes ("bebida", "Bebida") vira uma só.
            linha.categoria = categorias_da_planilha.setdefault(linha.categoria.lower(), linha.categoria)
        if not linha.erros:
            _comparar(linha, existentes.get(chave), categorias, conferencia)
        conferencia.linhas.append(linha)

    for chave, nome in categorias_da_planilha.items():
        existente = categorias.get(chave)
        if existente is None:
            conferencia.categorias_novas.append(nome)
        elif not existente.ativo:
            conferencia.categorias_reativadas.append(existente.nome)
    conferencia.ausentes = [p.nome for p in existentes.values() if p.ativo and p.nome.lower() not in vistos]
    return conferencia


# ============================================================
# IMPORTAÇÃO (grava tudo ou nada)
# ============================================================
def importar(conexao, texto, usuario_id, autorizacao, desativar_ausentes=False, agora=None):
    """Grava a planilha conferida numa transação única. Exige gerente.

    Lança DadosInvalidosError se a planilha tiver erros ou nada a mudar.
    """
    with transacao(conexao):
        gerente = verificar_gerente(conexao, autorizacao)
        conferencia = conferir(conexao, texto)
        if conferencia.tem_erros:
            raise DadosInvalidosError("A planilha tem linhas com erro. Corrija e envie de novo.")
        desativar = conferencia.ausentes if desativar_ausentes else []
        if not conferencia.tem_mudancas and not desativar:
            raise DadosInvalidosError("Nada para importar: o cardápio já está igual à planilha.")

        categorias = {c.nome.lower(): c for c in produtos.listar_categorias(conexao, incluir_inativas=True)}
        ids_categorias = {}
        for linha in conferencia.linhas:
            chave = linha.categoria.lower()
            if chave in ids_categorias:
                continue
            existente = categorias.get(chave)
            if existente is None:
                ids_categorias[chave] = produtos._inserir_categoria(conexao, linha.categoria, usuario_id,
                                                                    gerente.id, agora)
            else:
                if not existente.ativo:
                    produtos._reativar_categoria(conexao, existente.id, usuario_id, gerente.id, agora)
                ids_categorias[chave] = existente.id

        for linha in conferencia.linhas:
            categoria_id = ids_categorias[linha.categoria.lower()]
            if linha.acao == "novo":
                produtos._inserir_produto(conexao, linha.produto, categoria_id, linha.preco_centavos,
                                          linha.estoque or 0, linha.estoque_minimo or 0, usuario_id,
                                          gerente.id, agora)
            elif linha.acao == "alterar":
                atual = produtos.obter_produto(conexao, linha.produto_id)
                minimo = atual.estoque_minimo if linha.estoque_minimo is None else linha.estoque_minimo
                if (atual.nome, atual.categoria_id, atual.preco_centavos, atual.estoque_minimo) != (
                        linha.produto, categoria_id, linha.preco_centavos, minimo):
                    produtos._atualizar_produto(conexao, atual.id, linha.produto, categoria_id,
                                                linha.preco_centavos, minimo, usuario_id, gerente.id, agora)
                if not atual.ativo:
                    produtos._gravar_ativo(conexao, atual.id, True, usuario_id, gerente.id, agora)
                if linha.estoque is not None and linha.estoque != atual.estoque:
                    produtos._gravar_ajuste(conexao, atual.id, linha.estoque, MOTIVO_AJUSTE, usuario_id,
                                            gerente.id, agora)

        por_nome = {p.nome.lower(): p for p in produtos.listar_produtos(conexao)}
        for nome in desativar:
            produtos._gravar_ativo(conexao, por_nome[nome.lower()].id, False, usuario_id, gerente.id, agora)

        resultado = ResultadoImportacao(conferencia.novos, conferencia.alterados,
                                        len(conferencia.categorias_novas), len(desativar))
        registrar_auditoria(conexao, "cardapio_importado", usuario_id,
                            {"novos": resultado.novos, "alterados": resultado.alterados,
                             "categorias_novas": conferencia.categorias_novas, "desativados": desativar},
                            autorizado_por=gerente.id, agora=agora)
    return resultado


def resumo_resultado(resultado):
    """'Cardápio importado: 3 produtos novos, 2 alterados...'"""
    partes = []
    if resultado.novos:
        partes.append(plural(resultado.novos, "produto novo", "produtos novos"))
    if resultado.alterados:
        partes.append(plural(resultado.alterados, "produto alterado", "produtos alterados"))
    if resultado.categorias_novas:
        partes.append(plural(resultado.categorias_novas, "categoria nova", "categorias novas"))
    if resultado.desativados:
        partes.append(plural(resultado.desativados, "produto desativado", "produtos desativados"))
    return "Cardápio importado: " + ", ".join(partes) + "."
