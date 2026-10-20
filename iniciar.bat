@echo off
chcp 65001 >nul
title Tucandeira Rock Bar - Servidor
cd /d "%~dp0"

echo Encerrando servidor anterior (se houver)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /c:":5000 " ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1

rem O servidor abre o navegador sozinho. --sem-janela: fica neste console (QuickEdit desligado).
python servidor.py --sem-janela
pause