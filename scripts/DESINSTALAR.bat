@echo off
rem Remove o servidor do Tucandeira Rock Bar (os dados ficam guardados, a menos que voce confirme).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desinstalar.ps1"
