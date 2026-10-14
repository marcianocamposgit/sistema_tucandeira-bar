"""Popula o banco de DESENVOLVIMENTO com dados de demonstração.

Uso:
    python scripts/popular_demo.py             # banco vazio (só com o cardápio inicial)
    python scripts/popular_demo.py --recriar   # guarda um backup e recria o banco de desenvolvimento

Recusa-se a rodar no executável, fora da pasta data/ do projeto ou num banco
marcado como produção. Usa os próprios services (com o relógio simulado), então
os dados respeitam as mesmas regras do sistema.

Ainda sem vendas no passado: o service de pagamentos é da Etapa 6, que completa este script.
"""
import argparse
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
from database import ambiente_do_banco, conectar, migrar  # noqa: E402
from models import AutorizacaoGerente  # noqa: E402
from services import caixa, comandas, produtos, usuarios  # noqa: E402
from services.backup import fazer_backup  # noqa: E402

USUARIOS_DEMO = [
    # (nome, PIN, perfil)
    ("Gerente Demo", "1234", "gerente"),
    ("Ana", "1111", "operador"),
    ("Bruno", "2222", "operador"),
]

PRODUTOS_DEMO = [
    # (nome, categoria, preço em centavos, estoque inicial, estoque mínimo)
    ("Skol Lata", "Bebida", 700, 48, 24),
    ("Original 600ml", "Bebida", 1400, 24, 12),
    ("Budweiser Long Neck", "Bebida", 1100, 36, 12),
    ("Coca-Cola Lata", "Bebida", 600, 24, 12),
    ("Guaraná Lata", "Bebida", 600, 24, 12),
    ("Água sem Gás", "Bebida", 400, 30, 10),
    ("Caipirinha", "Bebida", 1800, 40, 10),
    ("Dose de Cachaça", "Bebida", 800, 30, 10),
    ("Energético", "Bebida", 1500, 6, 8),
    ("Gin Tônica", "Bebida", 2500, 20, 5),
    ("Batata Frita", "Tira-Gosto", 2500, 15, 5),
    ("Frango a Passarinho", "Tira-Gosto", 3200, 10, 4),
    ("Isca de Peixe", "Tira-Gosto", 3800, 3, 4),
    ("Mandioca Frita", "Tira-Gosto", 2200, 12, 4),
    ("Pastel Queijo", "Lanche", 700, 20, 10),
    ("X-Burguer", "Lanche", 2200, 15, 5),
    ("X-Tudo", "Lanche", 2800, 10, 5),
    ("Misto Quente", "Lanche", 1200, 12, 5),
    ("Lucky Strike 20un", "Cigarro", 1700, 10, 5),
    ("Isqueiro", "Cigarro", 600, 15, 5),
]

MINIMOS_INICIAIS = {"Brahma Lata": 24, "Heineken Long Neck": 12, "Whisky 50ml": 4,
                    "Porção Calabresa": 4, "Pastel Carne": 10, "Marlboro 20un": 5}


class AmbienteProibidoError(Exception):
    pass


class DemoJaPopuladaError(Exception):
    pass


def verificar_ambiente(pasta_dados, conexao, executavel=None):
    """Lança AmbienteProibidoError se o banco não for o de desenvolvimento."""
    executavel = config.EXECUTAVEL if executavel is None else executavel
    if executavel:
        raise AmbienteProibidoError("Os dados de demonstração não podem ser gerados pelo executável.")
    if Path(pasta_dados).resolve() != config.PASTA_DADOS_DESENVOLVIMENTO.resolve():
        raise AmbienteProibidoError(
            f"A pasta de dados ({pasta_dados}) não é a pasta data/ do projeto.")
    if ambiente_do_banco(conexao) != "desenvolvimento":
        raise AmbienteProibidoError("Este banco está marcado como produção. Nada foi alterado.")


def popular(conexao, hoje=None, dias=14, semente=42):
    """Cria os dados de demonstração. Devolve um resumo (dict)."""
    if usuarios.existe_usuario(conexao):
        raise DemoJaPopuladaError(
            "O banco já tem usuários. Use --recriar para começar de novo a partir de um banco vazio.")
    sorteio = random.Random(semente)
    hoje = hoje or date.today()
    inicio = datetime.combine(hoje - timedelta(days=dias + 1), time(14, 0))

    # --- Usuários ---
    nome, pin, _ = USUARIOS_DEMO[0]
    gerente = usuarios.criar_gerente_inicial(conexao, nome, pin, agora=inicio)
    autorizacao = AutorizacaoGerente(gerente.id, pin)
    operadores = [usuarios.cadastrar(conexao, n, p, perfil, gerente.id, autorizacao, agora=inicio)
                  for n, p, perfil in USUARIOS_DEMO[1:]]

    # --- Produtos ---
    categorias = {c.nome: c.id for c in produtos.listar_categorias(conexao)}
    for produto in produtos.listar_produtos(conexao):
        produtos.editar_produto(conexao, produto.id, produto.nome, produto.categoria_id, produto.preco_centavos,
                                MINIMOS_INICIAIS.get(produto.nome, 0), gerente.id, autorizacao, agora=inicio)
    for nome, categoria, preco, estoque, minimo in PRODUTOS_DEMO:
        produtos.cadastrar_produto(conexao, nome, categorias[categoria], preco, gerente.id, autorizacao,
                                   estoque_inicial=estoque, estoque_minimo=minimo, agora=inicio)
    lista_produtos = produtos.listar_produtos(conexao)

    # --- Dias passados: caixa aberto às 18h e fechado às 2h, com movimentos ---
    caixas_fechados = 0
    for atras in range(dias, 0, -1):
        dia = hoje - timedelta(days=atras)
        if dia.weekday() == 0:  # segunda: bar fechado
            continue
        abertura = datetime.combine(dia, time(18, 0))
        responsavel = sorteio.choice(operadores)
        caixa.abrir(conexao, sorteio.choice([10000, 15000, 20000]), responsavel.id, agora=abertura)
        if sorteio.random() < 0.5:
            caixa.registrar_suprimento(conexao, sorteio.choice([2000, 5000]), "Reforço de troco",
                                       responsavel.id, agora=abertura + timedelta(hours=2))
        if sorteio.random() < 0.4:
            caixa.registrar_sangria(conexao, sorteio.choice([3000, 5000]), "Pagamento de fornecedor (gelo)",
                                    responsavel.id, autorizacao, agora=abertura + timedelta(hours=3))
        if dia.weekday() in (2, 4):  # quarta e sexta: chega mercadoria
            for produto in sorteio.sample(lista_produtos, 4):
                produtos.registrar_entrada(conexao, produto.id, sorteio.choice([6, 12, 24]), responsavel.id,
                                           custo_unitario_centavos=produto.preco_centavos * 45 // 100,
                                           observacao="Compra semanal", agora=abertura - timedelta(hours=2))
        esperado = caixa.calcular_esperado(conexao, caixa.exigir_caixa_aberto(conexao).id)
        contado = dict(esperado)
        contado["dinheiro"] = max(0, esperado["dinheiro"] + sorteio.choice([0, 0, 0, -500, -200, 300, 1000]))
        caixa.fechar(conexao, contado, responsavel.id, autorizacao,
                     observacao=None if contado == esperado else "Diferença conferida",
                     agora=datetime.combine(dia + timedelta(days=1), time(2, 0)))
        caixas_fechados += 1

    # --- Perdas e ajustes de estoque ---
    por_nome = {p.nome: p for p in produtos.listar_produtos(conexao)}
    momento = datetime.combine(hoje - timedelta(days=2), time(17, 0))
    produtos.registrar_perda(conexao, por_nome["Heineken Long Neck"].id, 2, "Garrafas quebradas",
                             operadores[0].id, autorizacao, agora=momento)
    produtos.ajustar_contagem(conexao, por_nome["Whisky 50ml"].id, 3, "Contagem semanal",
                              operadores[1].id, autorizacao, agora=momento)
    produtos.ajustar_contagem(conexao, por_nome["Isqueiro"].id, 0, "Contagem semanal: acabou",
                              operadores[1].id, autorizacao, agora=momento)

    # --- Hoje: caixa aberto e algumas comandas em andamento ---
    agora = datetime.now()
    ana, bruno = operadores
    caixa.abrir(conexao, 15000, ana.id, agora=agora - timedelta(hours=2))

    def lancar(comanda, nome_produto, quantidade=1, observacao=None, por=ana, minutos_atras=30):
        return comandas.lancar_item(conexao, comanda.id, por_nome[nome_produto].id, por.id, quantidade,
                                    observacao, agora=agora - timedelta(minutes=minutos_atras)).item

    mesa2 = comandas.abrir_mesa(conexao, 2, ana.id, pessoas=3, agora=agora - timedelta(minutes=90))
    lancar(mesa2, "Brahma Lata", 4, minutos_atras=85)
    lancar(mesa2, "Porção Calabresa", observacao="bem passada", minutos_atras=80)
    lancar(mesa2, "Caipirinha", 2, por=bruno, minutos_atras=40)
    errado = lancar(mesa2, "Gin Tônica", minutos_atras=39)
    comandas.cancelar_item(conexao, errado.id, "Lançado na mesa errada", bruno.id, autorizacao,
                           agora=agora - timedelta(minutes=20))

    mesa5 = comandas.abrir_mesa(conexao, 5, bruno.id, pessoas=2, agora=agora - timedelta(minutes=70))
    lancar(mesa5, "Heineken Long Neck", 3, por=bruno, minutos_atras=65)
    lancar(mesa5, "Batata Frita", por=bruno, minutos_atras=60)
    comandas.marcar_conta_pedida(conexao, mesa5.id, bruno.id, agora=agora - timedelta(minutes=5))

    mesa3 = comandas.abrir_mesa(conexao, 3, ana.id, pessoas=4, agora=agora - timedelta(minutes=50))
    lancar(mesa3, "Original 600ml", 2, minutos_atras=48)
    mesa4 = comandas.abrir_mesa(conexao, 4, bruno.id, pessoas=2, agora=agora - timedelta(minutes=45))
    lancar(mesa4, "Isca de Peixe", por=bruno, minutos_atras=44)
    comandas.juntar_mesas(conexao, 3, 4, ana.id, agora=agora - timedelta(minutes=30))

    carlos = comandas.abrir_balcao(conexao, "Carlos", ana.id, agora=agora - timedelta(minutes=25))
    lancar(carlos, "X-Tudo", observacao="sem cebola", minutos_atras=24)
    lancar(carlos, "Coca-Cola Lata", minutos_atras=24)
    dani = comandas.abrir_balcao(conexao, "Dani", bruno.id, agora=agora - timedelta(minutes=10))
    lancar(dani, "Marlboro 20un", por=bruno, minutos_atras=1)  # ainda dá para remover sem PIN

    return {
        "usuarios": [(n, p, perfil) for n, p, perfil in USUARIOS_DEMO],
        "produtos": len(produtos.listar_produtos(conexao)),
        "caixas_fechados": caixas_fechados,
        "comandas_abertas": len(comandas.listar_abertas(conexao)),
    }


def _recriar(caminho_banco):
    """Guarda um backup do banco de desenvolvimento e o apaga (com -wal e -shm)."""
    backup = fazer_backup(caminho_banco, caminho_banco.parent / config.NOME_PASTA_BACKUPS,
                          manter=config.BACKUPS_MANTIDOS)
    for sufixo in ("", "-wal", "-shm"):
        arquivo = Path(f"{caminho_banco}{sufixo}")
        if arquivo.exists():
            arquivo.unlink()
    return backup


def main(argv=None):
    parser = argparse.ArgumentParser(description="Dados de demonstração para o banco de desenvolvimento.")
    parser.add_argument("--recriar", action="store_true",
                        help="guarda um backup e recria o banco de desenvolvimento antes de popular")
    args = parser.parse_args(argv)

    pasta_dados = config.PASTA_DADOS
    caminho_banco = Path(pasta_dados) / config.NOME_BANCO
    if not caminho_banco.exists():
        print(f"Banco não encontrado em {caminho_banco}. Rode 'python app.py' uma vez para criá-lo.")
        return 1

    conexao = conectar(caminho_banco)
    try:
        verificar_ambiente(pasta_dados, conexao)
        if args.recriar:
            conexao.close()
            backup = _recriar(caminho_banco)
            print(f"Backup do banco anterior: {backup}")
            conexao = conectar(caminho_banco)
            migrar(conexao, "desenvolvimento")
        else:
            if usuarios.existe_usuario(conexao):
                raise DemoJaPopuladaError(
                    "O banco já tem usuários. Use --recriar para começar de novo a partir de um banco vazio.")
            backup = fazer_backup(caminho_banco, Path(pasta_dados) / config.NOME_PASTA_BACKUPS,
                                  manter=config.BACKUPS_MANTIDOS)
            print(f"Backup antes de popular: {backup}")
        resumo = popular(conexao)
    except (AmbienteProibidoError, DemoJaPopuladaError) as erro:
        print(f"Recusado: {erro}")
        return 1
    finally:
        conexao.close()

    print("\nDados de demonstração criados:")
    print(f"  {resumo['produtos']} produtos ativos")
    print(f"  {resumo['caixas_fechados']} caixas fechados nos dias anteriores")
    print(f"  caixa de hoje aberto com {resumo['comandas_abertas']} comandas em andamento")
    print("\nUsuários (nome / PIN):")
    for nome, pin, perfil in resumo["usuarios"]:
        print(f"  {nome:<14} {pin}   ({perfil})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
