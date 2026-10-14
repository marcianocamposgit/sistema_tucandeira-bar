from datetime import datetime, timedelta

from database import conectar, migrar
from services.backup import fazer_backup, listar_backups


def _criar_banco(caminho):
    con = conectar(caminho)
    migrar(con)
    con.close()


def test_sem_banco_nao_faz_backup(tmp_path):
    assert fazer_backup(tmp_path / "nao_existe.db", tmp_path / "backups") is None
    assert not (tmp_path / "backups").exists()


def test_backup_e_copia_valida_do_banco(tmp_path):
    banco = tmp_path / "tucandeira.db"
    _criar_banco(banco)
    destino = fazer_backup(banco, tmp_path / "backups", momento=datetime(2026, 10, 14, 20, 30, 5))
    assert destino.name == "tucandeira_2026-10-14_20-30-05.db"
    copia = conectar(destino)
    assert copia.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 6
    copia.close()


def test_mantem_so_os_7_mais_recentes(tmp_path):
    banco = tmp_path / "tucandeira.db"
    _criar_banco(banco)
    pasta = tmp_path / "backups"
    inicio = datetime(2026, 10, 1, 18, 0, 0)
    for dia in range(10):
        fazer_backup(banco, pasta, manter=7, momento=inicio + timedelta(days=dia))
    nomes = [a.name for a in listar_backups(pasta)]
    assert len(nomes) == 7
    assert nomes[0] == "tucandeira_2026-10-04_18-00-00.db"
    assert nomes[-1] == "tucandeira_2026-10-10_18-00-00.db"


def test_dois_backups_no_mesmo_segundo_nao_se_sobrescrevem(tmp_path):
    banco = tmp_path / "tucandeira.db"
    _criar_banco(banco)
    momento = datetime(2026, 10, 14, 20, 0, 0)
    a = fazer_backup(banco, tmp_path / "backups", momento=momento)
    b = fazer_backup(banco, tmp_path / "backups", momento=momento)
    assert a != b and a.exists() and b.exists()


def test_rotacao_nao_apaga_outros_arquivos(tmp_path):
    banco = tmp_path / "tucandeira.db"
    _criar_banco(banco)
    pasta = tmp_path / "backups"
    pasta.mkdir()
    (pasta / "copia_manual.db").write_text("não apagar")
    for segundo in range(3):
        fazer_backup(banco, pasta, manter=1, momento=datetime(2026, 10, 14, 20, 0, segundo))
    assert (pasta / "copia_manual.db").exists()
    assert len(listar_backups(pasta)) == 1
