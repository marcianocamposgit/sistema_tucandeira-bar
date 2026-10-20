<#
    Tucandeira Rock Bar — instalação no computador do bar (servidor).

    Faz, em ordem:
      1. cria C:\TucandeiraBar\programa\ e C:\TucandeiraBar\dados\;
      2. copia o TucandeiraBar.exe (que está ao lado deste arquivo) para a pasta programa;
      3. libera a porta 5000 no Firewall do Windows, só na rede Privada (liberar_firewall.ps1);
      4. faz o servidor iniciar junto com o Windows (instalar_inicializacao.ps1);
      5. cria o atalho "Tucandeira Rock Bar" na Área de Trabalho;
      6. inicia o servidor.
    Os dados ficam em C:\TucandeiraBar\dados\ e nunca são apagados por este script.

    Como usar: dois cliques em INSTALAR.bat (ele pede permissão de administrador).
#>
$ErrorActionPreference = "Stop"
$Aqui = Split-Path -Parent $PSCommandPath
$PastaPrograma = "C:\TucandeiraBar\programa"
$PastaDados = "C:\TucandeiraBar\dados"
$Executavel = Join-Path $PastaPrograma "TucandeiraBar.exe"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Pedindo permissão de administrador..."
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

try {
    Write-Host "=== Tucandeira Rock Bar — instalação ===" -ForegroundColor Yellow

    $novo = Join-Path $Aqui "TucandeiraBar.exe"
    if (-not (Test-Path $novo)) { throw "Não encontrei o TucandeiraBar.exe ao lado deste script ($Aqui)." }

    Write-Host "1. Pastas $PastaPrograma e $PastaDados"
    New-Item -ItemType Directory -Force -Path $PastaPrograma, $PastaDados | Out-Null

    Write-Host "2. Copiando o programa"
    Get-Process TucandeiraBar -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    Copy-Item $novo $Executavel -Force

    Write-Host "3. Firewall (porta 5000, só rede Privada)"
    & (Join-Path $Aqui "liberar_firewall.ps1") -Porta 5000

    Write-Host "4. Iniciar junto com o Windows"
    & (Join-Path $Aqui "instalar_inicializacao.ps1") -Executavel $Executavel

    Write-Host "5. Atalho na Área de Trabalho"
    $atalho = (New-Object -ComObject WScript.Shell).CreateShortcut(
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "Tucandeira Rock Bar.lnk"))
    $atalho.TargetPath = $Executavel
    $atalho.WorkingDirectory = $PastaPrograma
    $atalho.IconLocation = "$Executavel,0"
    $atalho.Description = "Abre o servidor do Tucandeira Rock Bar (ou o sistema, se já estiver aberto)"
    $atalho.Save()

    Write-Host "6. Iniciando o servidor"
    Start-ScheduledTask -TaskName "Tucandeira Rock Bar - Servidor"

    Write-Host ""
    Write-Host "Instalação concluída." -ForegroundColor Green
    Write-Host "A janela do servidor mostra o endereço para digitar no tablet (ex.: http://192.168.0.10:5000)."
    Write-Host "Na primeira vez, o sistema pede para criar o usuário gerente."
} catch {
    Write-Host ""
    Write-Host "A instalação parou: $($_.Exception.Message)" -ForegroundColor Red
}
Read-Host "Tecle Enter para fechar"
