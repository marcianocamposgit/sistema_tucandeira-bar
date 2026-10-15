@echo off
chcp 65001 >nul
title Tucandeira Rock Bar - Servidor
cd /d "%~dp0"

echo Encerrando servidor anterior (se houver)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /c:":5000 " ^| findstr LISTENING') do taskkill /PID %%p /F >nul 2>&1

echo Abrindo o navegador em alguns segundos...
start "" /min cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5000"

python servidor.py
pause