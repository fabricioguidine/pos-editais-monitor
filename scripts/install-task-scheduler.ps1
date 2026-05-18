# Registra o worker do pos-editais-monitor no Task Scheduler do Windows.
# - Dispara: no logon do usuario
# - Atraso: 90s (esperar Docker Desktop subir)
# - Reinicia: se falhar
# - Roda: oculto (sem janela)
#
# Para desinstalar:  schtasks /Delete /TN "PosEditaisMonitorWorker" /F

$ErrorActionPreference = "Stop"

$root = (Resolve-Path "$PSScriptRoot\..").Path
$cmd  = Join-Path $root "scripts\start-worker.cmd"
$logs = Join-Path $root "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

if (-not (Test-Path $cmd)) {
  Write-Error "Worker cmd nao encontrado: $cmd"
  exit 1
}

# Action: executa o .cmd no diretorio do projeto
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
  -Argument "/c `"$cmd`"" `
  -WorkingDirectory $root

# Trigger: logon do usuario atual, com 90s de delay
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT90S"

# Settings: nao parar se rodar mais de 72h, restart on failure
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -RestartCount 5 `
  -RestartInterval (New-TimeSpan -Minutes 5) `
  -ExecutionTimeLimit (New-TimeSpan -Days 0)

# Principal: roda como usuario logado, sem privilegio elevado
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$taskName = "PosEditaisMonitorWorker"

# Remove anterior se existe
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
  Write-Host "Removida task anterior."
}

$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "pos-editais-monitor worker (APScheduler diario)"
Register-ScheduledTask -TaskName $taskName -InputObject $task | Out-Null

Write-Host ""
Write-Host "OK: Task registrada como '$taskName'."
Write-Host "    Comando:  $cmd"
Write-Host "    Trigger:  At logon (delay 90s)"
Write-Host "    Logs:     $logs\worker.log"
Write-Host ""
Write-Host "Testar agora (manualmente):  schtasks /Run /TN $taskName"
Write-Host "Ver status:                  schtasks /Query /TN $taskName /FO LIST /V"
Write-Host "Desinstalar:                 schtasks /Delete /TN $taskName /F"
