"""Servidor de produção do Tucandeira Rock Bar (waitress, rede local).

Uso: python servidor.py
"""
from waitress import serve

import config
from app import create_app
from services.rede import enderecos_para_tablets

# Poucos aparelhos (tablet, PC, alguns celulares), cada um com a atualização
# automática a cada 5 s: 8 threads sobram e uma requisição lenta não trava as outras.
THREADS = 8


def main():
    app = create_app(backup=True)
    print("=" * 60)
    print("  TUCANDEIRA ROCK BAR — Servidor")
    print("=" * 60)
    print(f"  Neste computador (caixa):  http://localhost:{config.PORTA}")
    for endereco in enderecos_para_tablets(config.PORTA):
        print(f"  Nos tablets e celulares:   {endereco}")
    print(f"  Pasta de dados: {app.config['PASTA_DADOS']}")
    print("  Não feche esta janela enquanto o bar estiver funcionando.")
    print("=" * 60)
    serve(app, host=config.HOST, port=config.PORTA, threads=THREADS)


if __name__ == "__main__":
    main()
