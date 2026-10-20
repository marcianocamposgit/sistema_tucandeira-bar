<#
    Tucandeira Rock Bar — gera o TucandeiraBar.exe e o pacote de entrega.

    1. roda todos os testes (para se algum falhar);
    2. gera dist\TucandeiraBar.exe com o PyInstaller (receita: TucandeiraBar.spec);
    3. monta dist\TucandeiraBar-<versão>\ e dist\TucandeiraBar-<versão>.zip (scripts\montar_entrega.py).

    Como usar (na pasta do projeto, com o Python e o requirements.txt instalados):
        powershell -ExecutionPolicy Bypass -File scripts\gerar_exe.ps1
#>
$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $Raiz

Write-Host "1. Testes" -ForegroundColor Yellow
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "Os testes falharam: o executável não foi gerado." -ForegroundColor Red; exit 1 }

Write-Host "2. Executável (PyInstaller)" -ForegroundColor Yellow
python -m PyInstaller --noconfirm --clean TucandeiraBar.spec
if ($LASTEXITCODE -ne 0) { Write-Host "O PyInstaller falhou." -ForegroundColor Red; exit 1 }

Write-Host "3. Pacote de entrega" -ForegroundColor Yellow
python scripts\montar_entrega.py
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "Pronto." -ForegroundColor Green
