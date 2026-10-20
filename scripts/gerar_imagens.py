"""Gera, a partir de assets/logo.png:

- static/img/: versões da logo otimizadas para a web (cabeçalho e página inicial);
- static/icones/: ícones do PWA (192 e 512, apple-touch-icon e favicon), com a
  logo centralizada sobre o fundo verde do bar;
- assets/tucandeira.ico: ícone do executável TucandeiraBar.exe.

Uso: python scripts/gerar_imagens.py
Rode de novo sempre que assets/logo.png mudar.
"""
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "assets" / "logo.png"
DESTINO = RAIZ / "static" / "img"
DESTINO_ICONES = RAIZ / "static" / "icones"
ICONE_EXE = RAIZ / "assets" / "tucandeira.ico"
VERDE = (0, 77, 38, 255)  # #004d26

# Ícones quadrados: (nome do arquivo, lado em pixels).
ICONES = [("icone-192.png", 192), ("icone-512.png", 512), ("apple-touch-icon.png", 180), ("favicon-32.png", 32)]
# A logo ocupa 76% do lado: fica dentro da "área segura" dos ícones adaptáveis do Android.
OCUPACAO = 0.76

# Alturas em pixels: 1x e 2x para o cabeçalho (56) e para a página inicial (200).
ALTURAS = [56, 112, 200, 400]


def icone_quadrado(logo, lado):
    """Logo centralizada num quadrado verde."""
    fundo = Image.new("RGBA", (lado, lado), VERDE)
    escala = OCUPACAO * lado / max(logo.width, logo.height)
    tamanho = (max(1, round(logo.width * escala)), max(1, round(logo.height * escala)))
    copia = logo.resize(tamanho, Image.Resampling.LANCZOS)
    fundo.alpha_composite(copia, ((lado - tamanho[0]) // 2, (lado - tamanho[1]) // 2))
    return fundo.convert("RGB")


def gerar_icones(logo):
    DESTINO_ICONES.mkdir(parents=True, exist_ok=True)
    for nome, lado in ICONES:
        caminho = DESTINO_ICONES / nome
        icone = icone_quadrado(logo, lado).quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                                                    dither=Image.Dither.NONE)
        icone.save(caminho, optimize=True)
        print(f"{caminho.relative_to(RAIZ)}  {lado}x{lado}  {caminho.stat().st_size // 1024} KB")
    icone_quadrado(logo, 256).save(ICONE_EXE, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"{ICONE_EXE.relative_to(RAIZ)}  (ícone do executável)")


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    with Image.open(ORIGEM) as original:
        logo = original.convert("RGBA")
        # Corta a área transparente em volta do escudo.
        logo = logo.crop(logo.getchannel("A").getbbox())
        gerar_icones(logo)
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
