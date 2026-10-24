"""Importação do cardápio por planilha: preços e estoque."""
import pytest

from services import importacao, produtos
from services.erros import DadosInvalidosError, PermissaoNegadaError
from models import AutorizacaoGerente
from tests.auxiliares import PIN_OPERADOR

CABECALHO = "Categoria;Produto;Preço;Estoque;Estoque mínimo\n"


def _produto(conexao, nome):
    return next(p for p in produtos.listar_produtos(conexao, incluir_inativos=True) if p.nome == nome)


def test_modelo_com_o_cardapio_atual_nao_muda_nada(conexao):
    modelo = importacao.modelo_csv(conexao)
    assert modelo.startswith("﻿Categoria;Produto;Preço;Estoque;Estoque mínimo\r\n")
    assert "Bebida;Brahma Lata;8,00;;0" in modelo  # estoque em branco: não mexe
    conferencia = importacao.conferir(conexao, modelo)
    assert not conferencia.tem_erros and not conferencia.tem_mudancas
    assert conferencia.iguais == 6 and conferencia.ausentes == []


def test_produto_novo_categoria_nova_e_alteracoes(conexao, gerente, autorizacao):
    texto = (CABECALHO
             + "Bebida;Brahma Lata;9,50;;24\n"          # preço e mínimo mudam, estoque fica
             + "Bebida;Heineken Long Neck;12,00;40;\n"  # só o estoque: ajuste de contagem
             + "bebida;Skol Lata;7;48;12\n"             # novo, categoria escrita em minúsculas
             + "Drinks;Caipirinha;R$ 18,00;;\n")        # categoria nova, estoque 0
    conferencia = importacao.conferir(conexao, texto)
    assert not conferencia.tem_erros
    assert [(l.produto, l.acao) for l in conferencia.linhas] == [
        ("Brahma Lata", "alterar"), ("Heineken Long Neck", "alterar"), ("Skol Lata", "novo"), ("Caipirinha", "novo")]
    assert conferencia.linhas[0].mudancas == ["Preço: R$ 8,00 → R$ 9,50", "Estoque mínimo: 0 → 24"]
    assert conferencia.linhas[1].mudancas == ["Estoque: 15 → 40 (ajuste de contagem)"]
    assert conferencia.categorias_novas == ["Drinks"]
    assert conferencia.ausentes == ["Whisky 50ml", "Porção Calabresa", "Pastel Carne", "Marlboro 20un"]
    assert produtos.obter_produto(conexao, _produto(conexao, "Brahma Lata").id).preco_centavos == 800  # nada gravado

    resultado = importacao.importar(conexao, texto, gerente.id, autorizacao)
    assert (resultado.novos, resultado.alterados, resultado.categorias_novas, resultado.desativados) == (2, 2, 1, 0)
    brahma, heineken = _produto(conexao, "Brahma Lata"), _produto(conexao, "Heineken Long Neck")
    assert (brahma.preco_centavos, brahma.estoque, brahma.estoque_minimo) == (950, 30, 24)
    assert heineken.estoque == 40
    assert [(m.tipo, m.quantidade, m.estoque_contado, m.motivo, m.autorizado_por)
            for m in produtos.listar_movimentos(conexao, heineken.id)] == [
        ("ajuste", 25, 40, "Importação da planilha do cardápio", gerente.id)]
    skol, caipirinha = _produto(conexao, "Skol Lata"), _produto(conexao, "Caipirinha")
    assert (skol.categoria_nome, skol.preco_centavos, skol.estoque, skol.estoque_minimo) == ("Bebida", 700, 48, 12)
    assert [(m.tipo, m.quantidade) for m in produtos.listar_movimentos(conexao, skol.id)] == [("entrada", 48)]
    assert (caipirinha.categoria_nome, caipirinha.estoque) == ("Drinks", 0)
    assert _produto(conexao, "Whisky 50ml").ativo  # quem não está na planilha continua como está
    # Importar de novo a mesma planilha não muda mais nada.
    with pytest.raises(DadosInvalidosError, match="Nada para importar"):
        importacao.importar(conexao, texto, gerente.id, autorizacao)


def test_desativar_os_que_nao_estao_na_planilha(conexao, gerente, autorizacao):
    texto = CABECALHO + "Bebida;Brahma Lata;8,00;;\nCigarro;Marlboro 20un;18,00;;\n"
    resultado = importacao.importar(conexao, texto, gerente.id, autorizacao, desativar_ausentes=True)
    assert resultado.desativados == 4
    assert [p.nome for p in produtos.listar_produtos(conexao)] == ["Brahma Lata", "Marlboro 20un"]
    # O produto desativado volta ao cardápio se aparecer numa planilha depois.
    volta = importacao.conferir(conexao, texto + "Bebida;Whisky 50ml;15,00;;\n")
    assert volta.linhas[2].mudancas == ["Volta ao cardápio (estava desativado)"]
    importacao.importar(conexao, texto + "Bebida;Whisky 50ml;15,00;;\n", gerente.id, autorizacao)
    assert _produto(conexao, "Whisky 50ml").ativo


def test_linhas_com_erro_impedem_a_importacao(conexao, gerente, autorizacao):
    texto = (CABECALHO
             + "Bebida;Skol Lata;sete;10;\n"
             + ";Água;4,00;;\n"
             + "Bebida;Guaraná;6,00;-3;abc\n"
             + "Bebida;skol lata;7,00;;\n"
             + "Bebida;Brahma Lata;10,00;;\n")
    conferencia = importacao.conferir(conexao, texto)
    assert conferencia.tem_erros and conferencia.com_erro == 4
    erros = {l.numero: l.erros for l in conferencia.linhas}
    assert erros[2] == ["Preço inválido: \"sete\" (use o formato 12,50)."]
    assert erros[3] == ["Falta a categoria."]
    assert erros[4] == ["O estoque não pode ser negativo.",
                        "Estoque mínimo inválido: \"abc\" (use um número inteiro, ex.: 24)."]
    assert erros[5] == ["O produto skol lata já aparece na linha 2."]
    with pytest.raises(DadosInvalidosError, match="linhas com erro"):
        importacao.importar(conexao, texto, gerente.id, autorizacao)
    assert _produto(conexao, "Brahma Lata").preco_centavos == 800  # a linha certa também não foi gravada


def test_planilha_sem_colunas_ou_xlsx(conexao):
    sem_preco = importacao.conferir(conexao, "Categoria;Produto\nBebida;Skol\n")
    assert sem_preco.erros_gerais and "faltou: Preço" in sem_preco.erros_gerais[0]
    assert importacao.conferir(conexao, "").erros_gerais == ["A planilha está vazia."]
    with pytest.raises(DadosInvalidosError, match="xlsx"):
        importacao.ler_arquivo(b"PK\x03\x04resto do arquivo")


def test_csv_do_excel_antigo_com_virgula(conexao):
    """Excel em português salvando 'CSV (separado por vírgulas)': cp1252, e às vezes ',' de separador."""
    bruto = 'Categoria,Produto,Preço,Estoque,Estoque mínimo\r\nLanche,Pão de Queijo,"5,50",1.000,0\r\n'.encode("cp1252")
    conferencia = importacao.conferir(conexao, importacao.ler_arquivo(bruto))
    [linha] = conferencia.linhas
    assert (linha.produto, linha.preco_centavos, linha.estoque, linha.acao) == ("Pão de Queijo", 550, 1000, "novo")


def test_importar_exige_gerente(conexao, operador):
    texto = CABECALHO + "Bebida;Skol Lata;7,00;10;\n"
    with pytest.raises(PermissaoNegadaError):
        importacao.importar(conexao, texto, operador.id, AutorizacaoGerente(operador.id, PIN_OPERADOR))
    assert "Skol Lata" not in [p.nome for p in produtos.listar_produtos(conexao)]


def test_planilha_da_validacao_no_banco_novo(tmp_path):
    """O VALIDACAO.md depende destes números (passo 0): banco de produção novo, sem cardápio."""
    from pathlib import Path
    from database import conectar, migrar
    con = conectar(tmp_path / "producao.db")
    migrar(con, "producao")
    texto = importacao.ler_arquivo((Path(__file__).resolve().parent.parent / "validacao_cardapio.csv").read_bytes())
    conferencia = importacao.conferir(con, texto)
    con.close()
    assert (conferencia.novos, conferencia.alterados, conferencia.iguais, conferencia.com_erro) == (13, 0, 0, 0)
    assert conferencia.ausentes == []
    assert conferencia.categorias_novas == ["Bebida", "Tira-Gosto", "Lanche", "Cigarro"]
