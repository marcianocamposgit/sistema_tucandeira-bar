# -*- mode: python ; coding: utf-8 -*-
# Receita do PyInstaller para o TucandeiraBar.exe (servidor do bar).
#
# Gerar:  powershell -ExecutionPolicy Bypass -File scripts\gerar_exe.ps1
#         (ou: python -m PyInstaller --noconfirm --clean TucandeiraBar.spec)
#
# - Um arquivo só (onefile), sem janela de console (console=False): a janela do
#   servidor é a do Tkinter (janela_servidor.py), que não trava com clique.
# - templates/, static/ e assets/ vão embutidos; config.py os encontra em sys._MEIPASS.
# - Os dados NUNCA vão no executável: ficam em C:\TucandeiraBar\dados\ (config.py).

a = Analysis(
    ["servidor.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("templates", "templates"),
        ("static", "static"),
        ("assets/logo.png", "assets"),
        ("assets/tucandeira.ico", "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Pillow e pytest só servem para gerar imagens e para os testes; legado_tkinter não é importado.
    excludes=["PIL", "pytest", "_pytest", "legado_tkinter", "tests", "scripts"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="TucandeiraBar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/tucandeira.ico",
)
