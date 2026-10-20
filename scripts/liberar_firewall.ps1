<#
    Tucandeira Rock Bar — libera a porta do sistema no Firewall do Windows.

    Cria UMA regra de entrada, só para a porta do sistema (TCP) e só no perfil
    de rede PRIVADA. Redes públicas (café, hotel, rede de visitantes) continuam
    bloqueadas. Rodar de novo não duplica a regra.

    Como usar (PowerShell como ADMINISTRADOR, na pasta onde está este arquivo):
        powershell -ExecutionPolicy Bypass -File .\liberar_firewall.ps1
        powershell -ExecutionPolicy Bypass -File .\liberar_firewall.ps1 -Porta 5001
    Para desfazer (remover a regra):
        powershell -ExecutionPolicy Bypass -File .\liberar_firewall.ps1 -Desfazer
#>
param(
    [int]$Porta = 5000,
    [switch]$Desfazer
)

$ErrorActionPreference = "Stop"
$NomeRegra = "Tucandeira Rock Bar (porta $Porta)"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Abra o PowerShell como administrador (botão direito > Executar como administrador) e rode de novo." -ForegroundColor Red
    exit 1
}

$existente = Get-NetFirewallRule -DisplayName $NomeRegra -ErrorAction SilentlyContinue
if ($existente) {
    Remove-NetFirewallRule -DisplayName $NomeRegra
}

if ($Desfazer) {
    if ($existente) {
        Write-Host "Regra '$NomeRegra' removida." -ForegroundColor Green
    } else {
        Write-Host "A regra '$NomeRegra' não existia." -ForegroundColor Yellow
    }
    exit 0
}

New-NetFirewallRule -DisplayName $NomeRegra `
    -Description "Acesso dos tablets e celulares ao sistema do bar, só na rede privada." `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Porta -Profile Private | Out-Null
Write-Host "Regra criada: '$NomeRegra' (entrada, TCP $Porta, só rede Privada)." -ForegroundColor Green

Write-Host ""
Write-Host "Redes deste computador (a do bar precisa estar como Private):"
Get-NetConnectionProfile | Format-Table -AutoSize Name, InterfaceAlias, NetworkCategory
$publicas = Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq "Public" }
foreach ($rede in $publicas) {
    Write-Host ("A rede '{0}' ({1}) está como Pública. Se for a rede do bar, mude para Privada:" -f $rede.Name, $rede.InterfaceAlias) -ForegroundColor Yellow
    Write-Host ("    Set-NetConnectionProfile -InterfaceAlias '{0}' -NetworkCategory Private" -f $rede.InterfaceAlias)
}
