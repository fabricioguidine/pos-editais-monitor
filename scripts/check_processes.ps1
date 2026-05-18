Get-Process | Where-Object {
  $_.ProcessName -match 'python|pem|cmd'
} | Format-Table Id, ProcessName, StartTime -AutoSize

Write-Output "---"
$log = "C:\Users\fabri\Documents\repos\pos-editais-monitor\logs\worker.log"
if (Test-Path $log) {
  Write-Output "log size: $((Get-Item $log).Length) bytes"
  Get-Content $log -Tail 20
} else {
  Write-Output "no log file yet"
}
