<#
    Tucandeira Rock Bar — inicia o servidor junto com o Windows.

    Cria a tarefa "Tucandeira Rock Bar - Servidor" no Agendador de Tarefas:
      - roda o TucandeiraBar.exe quando o usuário entra no Windows (logon), na
        sessão dele, para a janela do servidor aparecer na tela;
      - sem limite de tempo (o padrão do Windows pararia a tarefa depois de 3 dias);
      - se o servidor fechar com erro, o Windows tenta abrir de novo a cada 1 minuto (até 3 vezes);
      - nunca abre duas cópias ao mesmo tempo.
    Rodar de novo substitui a tarefa (não duplica).

    Como usar (PowerShell como ADMINISTRADOR):
        powershell -ExecutionPolicy Bypass -File .\instalar_inicializacao.ps1
        powershell -ExecutionPolicy Bypass -File .\instalar_inicializacao.ps1 -Executavel "D:\outro\TucandeiraBar.exe"
    Para desfazer (o servidor deixa de iniciar sozinho):
        powershell -ExecutionPolicy Bypass -File .\instalar_inicializacao.ps1 -Desfazer
#>
param(
    [string]$Executavel = "C:\TucandeiraBar\programa\TucandeiraBar.exe",
    [switch]$Desfazer
)

$ErrorActionPreference = "Stop"
$NomeTarefa = "Tucandeira Rock Bar - Servidor"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Abra o PowerShell como administrador (botão direito > Executar como administrador) e rode de novo." -ForegroundColor Red
    exit 1
}

if ($Desfazer) {
    if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
        Write-Host "Tarefa '$NomeTarefa' removida: o servidor não inicia mais sozinho." -ForegroundColor Green
    } else {
        Write-Host "A tarefa '$NomeTarefa' não existia." -ForegroundColor Yellow
    }
    exit 0
}

if (-not (Test-Path $Executavel)) {
    Write-Host "Não encontrei o programa em $Executavel. Copie o TucandeiraBar.exe para lá primeiro." -ForegroundColor Red
    exit 1
}

$usuario = "$env:USERDOMAIN\$env:USERNAME"
$acao = New-ScheduledTaskAction -Execute $Executavel -WorkingDirectory (Split-Path $Executavel)
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User $usuario
$quem = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew -StartWhenAvailable

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho -Principal $quem -Settings $config `
    -Description "Servidor do sistema do Tucandeira Rock Bar (tablets e caixa)." -Force | Out-Null

Write-Host "Tarefa criada: '$NomeTarefa'." -ForegroundColor Green
Write-Host "O servidor vai abrir sozinho sempre que $usuario entrar no Windows."
Write-Host "Para iniciar agora sem reiniciar o computador: Start-ScheduledTask -TaskName '$NomeTarefa'"
