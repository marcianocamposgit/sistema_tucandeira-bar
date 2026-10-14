"""Gera as versões da logo otimizadas para a web em static/img/.

Uso: python scripts/gerar_imagens.py
Rode de novo sempre que assets/logo.png mudar.
"""
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "assets" / "logo.png"
DESTINO = RAIZ / "static" / "img"

# Alturas em pixels: 1x e 2x para o cabeçalho (56) e para a página inicial (200).
ALTURAS = [56, 112, 200, 400]


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    with Image.open(ORIGEM) as original:
        logo = original.convert("RGBA")
        # Corta a área transparente em volta do escudo.
        logo = logo.crop(logo.getchannel("A").getbbox())
        for altura in ALTURAS:
            largura = round(logo.width * altura / logo.height)
            copia = logo.resize((largura, altura), Image.Resampling.LANCZOS)
            # Paleta de 256 cores com transparência: arquivos bem menores que RGBA.
            copia = copia.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
            caminho = DESTINO / f"logo-{altura}.png"
            copia.save(caminho, optimize=True)
            print(f"{caminho.relative_to(RAIZ)}  {largura}x{altura}  {caminho.stat().st_size // 1024} KB")


if __name__ == "__main__":
    sys.exit(main())
