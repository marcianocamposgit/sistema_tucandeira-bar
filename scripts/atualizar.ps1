<#
    Tucandeira Rock Bar — atualização do programa.

    Fecha o servidor, troca C:\TucandeiraBar\programa\TucandeiraBar.exe pelo
    TucandeiraBar.exe que está ao lado deste arquivo e abre de novo. Os dados
    (C:\TucandeiraBar\dados\) não são tocados: ao abrir, a versão nova faz um
    backup e atualiza o banco sozinha. O programa antigo fica guardado como
    TucandeiraBar.anterior.exe, para voltar atrás se precisar.

    Como usar: com o bar sem movimento (de preferência com o caixa fechado),
    dois cliques em ATUALIZAR.bat.
#>
$ErrorActionPreference = "Stop"
$Aqui = Split-Path -Parent $PSCommandPath
$PastaPrograma = "C:\TucandeiraBar\programa"
$Executavel = Join-Path $PastaPrograma "TucandeiraBar.exe"
$NomeTarefa = "Tucandeira Rock Bar - Servidor"

try {
    $novo = Join-Path $Aqui "TucandeiraBar.exe"
    if (-not (Test-Path $novo)) { throw "Não encontrei o TucandeiraBar.exe novo ao lado deste script ($Aqui)." }
    if (-not (Test-Path $Executavel)) { throw "O sistema ainda não está instalado em $PastaPrograma. Use o INSTALAR.bat." }

    Write-Host "Fechando o servidor..."
    Get-Process TucandeiraBar -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3

    Copy-Item $Executavel (Join-Path $PastaPrograma "TucandeiraBar.anterior.exe") -Force
    Copy-Item $novo $Executavel -Force
    Write-Host "Programa trocado." -ForegroundColor Green

    if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
        Start-ScheduledTask -TaskName $NomeTarefa
    } else {
        Start-Process $Executavel -WorkingDirectory $PastaPrograma
    }
    Write-Host "Servidor aberto de novo. Confira na tela Sobre a versão nova e o último backup." -ForegroundColor Green
} catch {
    Write-Host "A atualização parou: $($_.Exception.Message)" -ForegroundColor Red
}
Read-Host "Tecle Enter para fechar"
