$max = 18
for ($i = 1; $i -le $max; $i++) {
  $r = docker info --format '{{.ServerVersion}}' 2>&1
  if ($LASTEXITCODE -eq 0 -and "$r" -notmatch 'error|Error|500') {
    Write-Output ("READY: " + $r + " (after " + $i + " tries)")
    exit 0
  }
  Start-Sleep -Seconds 5
}
Write-Output "NOT READY after $max tries"
docker info 2>&1 | Select-String 'Server Version|error|Error' | Select-Object -First 5
exit 1
