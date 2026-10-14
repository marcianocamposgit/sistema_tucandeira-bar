"""Configurações do Tucandeira Rock Bar.

Todos os caminhos e valores ajustáveis do sistema ficam aqui, num único lugar.
"""
import os
import sys
from pathlib import Path

# === CAMINHOS ===
# Arquivos do programa (templates, static, assets). No executável do PyInstaller,
# eles ficam na pasta temporária indicada por sys._MEIPASS.
EXECUTAVEL = getattr(sys, "frozen", False)
if EXECUTAVEL:
    PASTA_PROGRAMA = Path(getattr(sys, "_MEIPASS")).resolve()
else:
    PASTA_PROGRAMA = Path(__file__).resolve().parent

PASTA_TEMPLATES = PASTA_PROGRAMA / "templates"
PASTA_STATIC = PASTA_PROGRAMA / "static"
PASTA_ASSETS = PASTA_PROGRAMA / "assets"

# Pasta de dados (banco, backups, secret_key, logs), sempre separada do programa.
PASTA_DADOS_DESENVOLVIMENTO = Path(__file__).resolve().parent / "data"
PASTA_DADOS_PRODUCAO = Path(r"C:\TucandeiraBar\dados")


def pasta_dados_padrao():
    """Pasta de dados: variável TUCANDEIRA_DADOS, ou o padrão de cada ambiente."""
    if os.environ.get("TUCANDEIRA_DADOS"):
        return Path(os.environ["TUCANDEIRA_DADOS"]).resolve()
    if EXECUTAVEL:
        return PASTA_DADOS_PRODUCAO
    return PASTA_DADOS_DESENVOLVIMENTO


PASTA_DADOS = pasta_dados_padrao()
NOME_BANCO = "tucandeira.db"
NOME_PASTA_BACKUPS = "backups"

# === SERVIDOR ===
HOST = "0.0.0.0"
PORTA = 5000

# === REGRAS DO BAR ===
NUM_MESAS = 8
TAXA_SERVICO_PERCENTUAL = 10
PRAZO_REMOCAO_ITEM_MINUTOS = 2
FORMAS_PAGAMENTO = {
    "dinheiro": "Dinheiro",
    "debito": "Débito",
    "credito": "Crédito",
    "pix": "PIX",
}

# === SEGURANÇA ===
# Iterações do PBKDF2 para guardar os PINs (quanto maior, mais lento de quebrar).
ITERACOES_PIN = 200_000

# === SESSÃO E TELAS ===
TEMPO_SESSAO_MINUTOS = 15
INTERVALO_ATUALIZACAO_MESAS = 5  # segundos

# === BACKUP ===
BACKUPS_MANTIDOS = 7

# === VERSÃO ===
VERSAO = "2.0-dev"
