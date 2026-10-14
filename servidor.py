"""Servidor de produção do Tucandeira Rock Bar (waitress, rede local).

Uso: python servidor.py
"""
import socket

from waitress import serve

import config
from app import create_app


def enderecos_locais():
    """IPs desta máquina na rede local (para digitar nos tablets e celulares)."""
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except socket.gaierror:
        pass
    # Descobre o IP da interface usada para sair da máquina (não envia nada).
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith("127."))


def main():
    app = create_app(backup=True)
    print("=" * 60)
    print("  TUCANDEIRA ROCK BAR — Servidor")
    print("=" * 60)
    print(f"  Neste computador (caixa):  http://localhost:{config.PORTA}")
    for ip in enderecos_locais():
        print(f"  Nos tablets e celulares:   http://{ip}:{config.PORTA}")
    print(f"  Pasta de dados: {app.config['PASTA_DADOS']}")
    print("  Não feche esta janela enquanto o bar estiver funcionando.")
    print("=" * 60)
    serve(app, host=config.HOST, port=config.PORTA, threads=8)


if __name__ == "__main__":
    main()
