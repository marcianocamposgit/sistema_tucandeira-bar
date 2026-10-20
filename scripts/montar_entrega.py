"""Monta a pasta de entrega para o bar a partir do executável já gerado.

Uso: python scripts/montar_entrega.py   (o scripts/gerar_exe.ps1 chama sozinho)

Cria dist/TucandeiraBar-<versão>/ e dist/TucandeiraBar-<versão>.zip com:
    TucandeiraBar.exe            o servidor (roda sem Python)
    INSTALAR.bat                 instala no computador do bar (pede administrador)
    ATUALIZAR.bat                troca o programa por uma versão nova (os dados ficam)
    COMECAR_BANCO_LIMPO.bat      guarda o banco da validação e começa do zero
    scripts .ps1                 usados pelos .bat (firewall, início com o Windows...)
    modelo_cardapio.csv          planilha do cardápio para o dono preencher
    README.md e VALIDACAO.md     instruções
"""
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
from database import conectar, migrar  # noqa: E402
from services import importacao  # noqa: E402

DIST = RAIZ / "dist"
SCRIPTS = RAIZ / "scripts"
ARQUIVOS_SCRIPTS = ["INSTALAR.bat", "ATUALIZAR.bat", "COMECAR_BANCO_LIMPO.bat", "instalar.ps1", "atualizar.ps1",
                    "comecar_banco_limpo.ps1", "liberar_firewall.ps1", "instalar_inicializacao.ps1"]


def modelo_cardapio():
    """O modelo da planilha com o cardápio inicial (o mesmo de um banco novo)."""
    with tempfile.TemporaryDirectory() as pasta:
        conexao = conectar(Path(pasta) / "modelo.db")
        try:
            migrar(conexao, "producao")
            return importacao.modelo_csv(conexao)
        finally:
            conexao.close()


def main():
    executavel = DIST / "TucandeiraBar.exe"
    if not executavel.exists():
        print("Gere o executável primeiro: scripts\\gerar_exe.ps1")
        return 1
    nome = f"TucandeiraBar-{config.VERSAO}"
    destino = DIST / nome
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    shutil.copy2(executavel, destino)
    for arquivo in ARQUIVOS_SCRIPTS:
        shutil.copy2(SCRIPTS / arquivo, destino)
    for arquivo in ("README.md", "VALIDACAO.md", "validacao_cardapio.csv"):
        shutil.copy2(RAIZ / arquivo, destino)
    (destino / "modelo_cardapio.csv").write_bytes(modelo_cardapio().encode("utf-8"))

    zip_final = shutil.make_archive(str(DIST / nome), "zip", root_dir=DIST, base_dir=nome)
    print(f"Pasta de entrega: {destino}")
    for item in sorted(destino.iterdir()):
        print(f"    {item.name}")
    print(f"Arquivo para levar ao bar: {zip_final} ({Path(zip_final).stat().st_size // (1024 * 1024)} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
