"""Backup automático do banco de dados.

Usa a API de backup do sqlite3, que gera uma cópia consistente mesmo com o
banco em modo WAL e com outros aparelhos usando o sistema.
"""
import re
import sqlite3
from datetime import datetime
from pathlib import Path

PREFIXO = "tucandeira_"
PADRAO_NOME = re.compile(r"^tucandeira_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(_\d+)?\.db$")


def _nome_livre(pasta_backups, momento):
    base = f"{PREFIXO}{momento.strftime('%Y-%m-%d_%H-%M-%S')}"
    destino = pasta_backups / f"{base}.db"
    numero = 2
    while destino.exists():
        destino = pasta_backups / f"{base}_{numero}.db"
        numero += 1
    return destino


def listar_backups(pasta_backups):
    """Backups existentes, do mais antigo para o mais novo."""
    pasta_backups = Path(pasta_backups)
    if not pasta_backups.is_dir():
        return []
    arquivos = [a for a in pasta_backups.iterdir() if a.is_file() and PADRAO_NOME.match(a.name)]
    # O nome começa pela data e hora, então a ordem alfabética é a cronológica.
    return sorted(arquivos, key=lambda a: a.name)


def fazer_backup(caminho_banco, pasta_backups, manter=7, momento=None):
    """Copia o banco para a pasta de backups e apaga os mais antigos.

    Mantém só os `manter` backups mais recentes. Devolve o caminho do backup
    criado, ou None se o banco ainda não existir.
    """
    caminho_banco = Path(caminho_banco)
    if not caminho_banco.exists():
        return None
    if manter < 1:
        raise ValueError("É preciso manter pelo menos 1 backup.")

    pasta_backups = Path(pasta_backups)
    pasta_backups.mkdir(parents=True, exist_ok=True)
    destino = _nome_livre(pasta_backups, momento or datetime.now())

    origem = sqlite3.connect(str(caminho_banco))
    copia = sqlite3.connect(str(destino))
    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()

    for antigo in listar_backups(pasta_backups)[:-manter]:
        antigo.unlink()
    return destino
