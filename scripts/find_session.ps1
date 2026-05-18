Get-ChildItem 'C:\Users\fabri\.claude\projects\C--Users-fabri\' -File -Filter '*.jsonl' |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 |
  ForEach-Object {
    Write-Output ($_.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss') + '  ' + $_.BaseName)
  }
