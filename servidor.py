"""Servidor do Tucandeira Rock Bar (waitress, rede local). É também o TucandeiraBar.exe.

Uso:
    python servidor.py                  # abre a janela do servidor (endereços, backup, botão de parar)
    python servidor.py --sem-janela     # só no console (para quem desenvolve)
    python servidor.py --sem-navegador  # não abre o navegador deste computador ao iniciar

O executável roda sem janela de console: a janela é do Tkinter e não "congela"
com um clique, como o console do Windows no modo de edição rápida (QuickEdit).
No modo --sem-janela, o QuickEdit do console é desligado ao iniciar.

Ao iniciar: confere se o servidor já está aberto (a porta ocupada), faz o backup,
migra o banco se preciso, mostra os endereços e abre o navegador em localhost.
Enquanto roda: backup uma vez por dia e log em <pasta de dados>/logs/servidor.log.
"""
import argparse
import logging
import socket
import sys
import threading
import webbrowser
from logging.handlers import RotatingFileHandler

from waitress import create_server

import config
from app import create_app
from services import backup
from services.rede import enderecos_para_tablets

# Poucos aparelhos (tablet, PC, alguns celulares), cada um com a atualização
# automática a cada 5 s: 8 threads sobram e uma requisição lenta não trava as outras.
THREADS = 8

log = logging.getLogger("tucandeira")


# ============================================================
# LOG, CONSOLE E PORTA
# ============================================================
def configurar_log(pasta_dados):
    """Log em arquivo com rotação (1 MB × 6 arquivos) e, se houver console, na tela."""
    pasta_logs = pasta_dados / config.NOME_PASTA_LOGS
    pasta_logs.mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    arquivo = RotatingFileHandler(pasta_logs / "servidor.log", maxBytes=config.LOG_TAMANHO_MAXIMO,
                                  backupCount=config.LOG_ARQUIVOS_ANTIGOS, encoding="utf-8")
    arquivo.setFormatter(formato)
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(arquivo)
    if sys.stderr is not None:  # o executável não tem console
        tela = logging.StreamHandler()
        tela.setFormatter(formato)
        tela.setLevel(logging.WARNING)
        raiz.addHandler(tela)


def escrever(texto=""):
    """print() que não falha no executável sem console."""
    if sys.stdout is not None:
        print(texto, flush=True)


def desativar_quickedit():
    """Desliga o modo de edição rápida do console do Windows (um clique pausaria o servidor)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleTitleW("Tucandeira Rock Bar — Servidor")
        entrada = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        modo = ctypes.c_uint32()
        if kernel32.GetConsoleMode(entrada, ctypes.byref(modo)):
            ENABLE_QUICK_EDIT_MODE, ENABLE_EXTENDED_FLAGS = 0x0040, 0x0080
            kernel32.SetConsoleMode(entrada, (modo.value | ENABLE_EXTENDED_FLAGS) & ~ENABLE_QUICK_EDIT_MODE)
    except (AttributeError, OSError):
        pass


def porta_em_uso(porta):
    """True se outro programa (ex.: o servidor já aberto) está usando a porta.

    O waitress liga a porta com SO_REUSEADDR, que no Windows deixaria abrir um
    segundo servidor na mesma porta sem erro. Por isso o teste usa
    SO_EXCLUSIVEADDRUSE, que falha se a porta já estiver ocupada.
    """
    teste = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            teste.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        teste.bind((config.HOST, porta))
        return False
    except OSError:
        return True
    finally:
        teste.close()


# ============================================================
# BACKUP DIÁRIO
# ============================================================
def _backup_diario(app, parar):
    pasta = app.config["PASTA_DADOS"] / config.NOME_PASTA_BACKUPS
    while not parar.wait(config.VERIFICAR_BACKUP_DIARIO_MINUTOS * 60):
        try:
            feito = backup.backup_se_preciso(app.config["CAMINHO_BANCO"], pasta, manter=config.BACKUPS_MANTIDOS)
            if feito:
                log.info("Backup diário: %s", feito)
        except Exception:  # noqa: BLE001 — um backup que falha não pode derrubar o servidor
            log.exception("Falha no backup diário")


def texto_ultimo_backup(app):
    ultimo = backup.ultimo_backup(app.config["PASTA_DADOS"] / config.NOME_PASTA_BACKUPS)
    return f"Último backup: {ultimo[0]:%d/%m/%Y %H:%M}" if ultimo else "Último backup: nenhum ainda"


# ============================================================
# INÍCIO
# ============================================================
def _ler_argumentos(argv):
    parser = argparse.ArgumentParser(description="Servidor do Tucandeira Rock Bar.")
    parser.add_argument("--sem-janela", action="store_true", help="roda só no console, sem a janela")
    parser.add_argument("--sem-navegador", action="store_true", help="não abre o navegador ao iniciar")
    return parser.parse_args(argv)


def _avisar(titulo, mensagem, usar_janela, erro=False):
    escrever(f"{titulo}: {mensagem}")
    if usar_janela:
        try:
            import janela_servidor
            janela_servidor.aviso(titulo, mensagem, erro=erro)
        except Exception:  # noqa: BLE001 — sem a janela, o aviso fica no console e no log
            log.exception("Não foi possível mostrar o aviso")


def main(argv=None):
    args = _ler_argumentos(argv)
    usar_janela = not args.sem_janela
    pasta_dados = config.PASTA_DADOS
    configurar_log(pasta_dados)
    local = f"http://localhost:{config.PORTA}"

    if porta_em_uso(config.PORTA):
        log.warning("Porta %s ocupada: o servidor já está aberto (ou outro programa usa a porta).", config.PORTA)
        if not args.sem_navegador:
            webbrowser.open(local)
        _avisar("Tucandeira Rock Bar",
                f"O servidor já está aberto neste computador (porta {config.PORTA}).\n"
                f"O sistema foi aberto no navegador: {local}", usar_janela)
        return 0

    try:
        app = create_app(backup=True)
        servidor = create_server(app, host=config.HOST, port=config.PORTA, threads=THREADS, ident="Tucandeira")
    except Exception as erro:  # noqa: BLE001
        log.exception("O servidor não conseguiu iniciar")
        _avisar("Tucandeira Rock Bar — erro ao iniciar",
                f"O servidor não conseguiu iniciar:\n{erro}\n\nVeja o log em {pasta_dados / config.NOME_PASTA_LOGS}.",
                usar_janela, erro=True)
        return 1

    enderecos = enderecos_para_tablets(config.PORTA)
    log.info("Servidor %s iniciado em %s; tablets: %s; dados: %s", config.VERSAO, local,
             ", ".join(enderecos) or "(sem rede)", pasta_dados)
    parar_backup = threading.Event()
    threading.Thread(target=_backup_diario, args=(app, parar_backup), name="backup-diario", daemon=True).start()

    escrever("=" * 60)
    escrever(f"  TUCANDEIRA ROCK BAR — Servidor {config.VERSAO}")
    escrever("=" * 60)
    escrever(f"  Neste computador (caixa):  {local}")
    for endereco in enderecos:
        escrever(f"  Nos tablets e celulares:   {endereco}")
    escrever(f"  Pasta de dados: {pasta_dados}")
    escrever("  Não feche esta janela enquanto o bar estiver funcionando.")
    escrever("=" * 60)
    if not args.sem_navegador and config.ABRIR_NAVEGADOR_AO_INICIAR:
        threading.Timer(1.5, webbrowser.open, args=(local,)).start()

    parando = threading.Event()

    def parar_servidor():
        parando.set()
        servidor.close()

    janela = None
    if usar_janela:
        try:
            import janela_servidor
            janela = janela_servidor.JanelaServidor(
                {"local": local, "enderecos": enderecos, "pasta_dados": pasta_dados},
                texto_backup=lambda: texto_ultimo_backup(app),
                ao_parar=parar_servidor)
        except Exception:  # noqa: BLE001 — sem Tkinter (ou sem tela), segue no console
            log.exception("Janela do servidor indisponível; seguindo no console")
            janela = None

    if janela is None:
        desativar_quickedit()
        try:
            servidor.run()
        except KeyboardInterrupt:
            escrever("Servidor parado.")
        finally:
            parar_backup.set()
            log.info("Servidor parado")
        return 0

    def rodar_servidor():
        try:
            servidor.run()
        except Exception as erro:  # noqa: BLE001
            if parando.is_set():
                return  # fechado pela janela: o erro é só o socket sendo fechado
            log.exception("O servidor parou com erro")
            janela.falhou(f"O servidor parou com um erro:\n{erro}\n\nAbra o TucandeiraBar de novo.")

    threading.Thread(target=rodar_servidor, name="waitress", daemon=True).start()
    codigo = janela.rodar()
    parar_backup.set()
    log.info("Servidor parado pela janela (código %s)", codigo)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
