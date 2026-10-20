<#
    Tucandeira Rock Bar — começar com o banco limpo (depois da validação no bar).

    NÃO APAGA NADA: fecha o servidor e MOVE o banco da validação (tucandeira.db,
    -wal, -shm), os backups e os logs para C:\TucandeiraBar\dados\validacao_<data e hora>\.
    Ao abrir de novo, o servidor cria um banco vazio, só com o cardápio inicial, e
    pede para criar o usuário gerente. A secret_key continua a mesma.

    Use só uma vez, antes de começar a vender de verdade. Depois disso, o banco tem
    dados reais e nunca deve ser trocado.

    Como usar: dois cliques em COMECAR_BANCO_LIMPO.bat e digite LIMPAR para confirmar.
#>
param(
    [string]$PastaDados = "C:\TucandeiraBar\dados"
)

$ErrorActionPreference = "Stop"
$NomeTarefa = "Tucandeira Rock Bar - Servidor"

try {
    $banco = Join-Path $PastaDados "tucandeira.db"
    if (-not (Test-Path $banco)) { throw "Não há banco em ${PastaDados}: nada a fazer." }

    Write-Host "Isto guarda o banco atual (o da validação) numa pasta à parte e faz o sistema"
    Write-Host "começar do zero: sem usuários, sem vendas, sem caixas, só com o cardápio inicial."
    Write-Host "Use só antes de começar a vender de verdade." -ForegroundColor Yellow
    $resposta = Read-Host "Digite LIMPAR para confirmar"
    if ($resposta -cne "LIMPAR") { throw "Cancelado: nada foi mudado." }

    Write-Host "Fechando o servidor..."
    Get-Process TucandeiraBar -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3

    $destino = Join-Path $PastaDados ("validacao_" + (Get-Date -Format "yyyy-MM-dd_HH-mm-ss"))
    New-Item -ItemType Directory -Path $destino | Out-Null
    foreach ($nome in @("tucandeira.db", "tucandeira.db-wal", "tucandeira.db-shm", "backups", "logs")) {
        $item = Join-Path $PastaDados $nome
        if (Test-Path $item) { Move-Item $item $destino }
    }
    Write-Host "Banco da validação guardado em $destino" -ForegroundColor Green

    if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
        Start-ScheduledTask -TaskName $NomeTarefa
        Write-Host "Servidor aberto com o banco limpo. No navegador, crie o usuário gerente." -ForegroundColor Green
    } else {
        Write-Host "Abra o Tucandeira Rock Bar (atalho da Área de Trabalho) e crie o usuário gerente."
    }
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
}
Read-Host "Tecle Enter para fechar"
