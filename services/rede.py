"""Endereços desta máquina na rede local (para digitar nos tablets e celulares)."""
import socket


def enderecos_locais():
    """IPs IPv4 desta máquina, sem o 127.x (localhost) e sem o 169.254.x (rede sem DHCP)."""
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
    return sorted((ip for ip in ips if not ip.startswith(("127.", "169.254."))),
                  key=lambda ip: tuple(int(parte) for parte in ip.split(".")))


def enderecos_para_tablets(porta):
    """['http://192.168.0.10:5000', ...]"""
    return [f"http://{ip}:{porta}" for ip in enderecos_locais()]
