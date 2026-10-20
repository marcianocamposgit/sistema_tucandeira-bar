<#
    Tucandeira Rock Bar — desinstalação do servidor.

    Remove, em ordem:
      1. o servidor aberto (fecha o TucandeiraBar);
      2. o início automático com o Windows (tarefa do Agendador);
      3. a regra do Firewall do Windows (porta 5000);
      4. o atalho "Tucandeira Rock Bar" da Área de Trabalho;
      5. a pasta do programa, C:\TucandeiraBar\programa\.

    A pasta de DADOS (C:\TucandeiraBar\dados\: banco com as vendas, caixas,
    usuários, backups e logs) é PRESERVADA. O script só a apaga se a pessoa
    digitar APAGAR depois do aviso; qualquer outra resposta mantém os dados.

    Como usar: dois cliques em DESINSTALAR.bat (ele pede permissão de administrador).
#>
$ErrorActionPreference = "Stop"
$Aqui = Split-Path -Parent $PSCommandPath
$PastaBase = "C:\TucandeiraBar"
$PastaPrograma = Join-Path $PastaBase "programa"
$PastaDados = Join-Path $PastaBase "dados"
$NomeTarefa = "Tucandeira Rock Bar - Servidor"
$NomeRegra = "Tucandeira Rock Bar (porta 5000)"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Pedindo permissão de administrador..."
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

try {
    Write-Host "=== Tucandeira Rock Bar — desinstalação ===" -ForegroundColor Yellow
    Write-Host "Remove o programa, o início automático, a regra do firewall e o atalho."
    Write-Host "Os dados (vendas, caixas, usuários, backups) em $PastaDados ficam guardados."
    $resposta = Read-Host "Digite SIM para desinstalar"
    if ($resposta -ne "SIM") { throw "Cancelado: nada foi mudado." }

    Write-Host "1. Fechando o servidor"
    Get-Process TucandeiraBar -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 3

    Write-Host "2. Início automático com o Windows"
    if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
        Write-Host "   tarefa removida"
    } else {
        Write-Host "   não estava configurado"
    }

    Write-Host "3. Regra do firewall"
    if (Get-NetFirewallRule -DisplayName $NomeRegra -ErrorAction SilentlyContinue) {
        Remove-NetFirewallRule -DisplayName $NomeRegra
        Write-Host "   regra '$NomeRegra' removida"
    } else {
        Write-Host "   não existia"
    }

    Write-Host "4. Atalho da Área de Trabalho"
    $atalho = Join-Path ([Environment]::GetFolderPath("Desktop")) "Tucandeira Rock Bar.lnk"
    if (Test-Path $atalho) { Remove-Item $atalho -Force; Write-Host "   atalho removido" } else { Write-Host "   não existia" }

    Write-Host "5. Pasta do programa"
    if (Test-Path $PastaPrograma) {
        Remove-Item $PastaPrograma -Recurse -Force
        Write-Host "   $PastaPrograma removida"
    } else {
        Write-Host "   não existia"
    }

    Write-Host ""
    Write-Host "Programa desinstalado." -ForegroundColor Green

    if (Test-Path $PastaDados) {
        Write-Host ""
        Write-Host "ATENÇÃO: em $PastaDados estão o banco com TODAS as vendas, caixas, usuários e" -ForegroundColor Yellow
        Write-Host "estoque do bar, além dos backups. Apagar não tem volta. Se vai reinstalar ou" -ForegroundColor Yellow
        Write-Host "atualizar, NÃO apague: o programa novo usa estes mesmos dados." -ForegroundColor Yellow
        $apagar = Read-Host "Para APAGAR os dados também, digite APAGAR. Para manter, só tecle Enter"
        if ($apagar -ceq "APAGAR") {
            Remove-Item $PastaDados -Recurse -Force
            Write-Host "Dados apagados." -ForegroundColor Red
        } else {
            Write-Host "Dados mantidos em $PastaDados." -ForegroundColor Green
        }
    }
    if ((Test-Path $PastaBase) -and -not (Get-ChildItem $PastaBase -Force)) {
        Remove-Item $PastaBase -Force  # só se ficou vazia
    }
} catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
}
Read-Host "Tecle Enter para fechar"
