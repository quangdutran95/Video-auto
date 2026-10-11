$wshell = New-Object -ComObject WScript.Shell
$proc = Get-Process chrome | Where-Object { $_.MainWindowTitle -like "*Google Flow*" } | Select-Object -First 1
if (-not $proc) {
    $proc = Get-Process chrome | Where-Object { $_.MainWindowTitle } | Select-Object -First 1
}

if ($proc) {
    $wshell.AppActivate($proc.Id)
    Start-Sleep -Milliseconds 500
    for ($i = 0; $i -lt 6; $i++) {
        $wshell.SendKeys("^{TAB}")
        Start-Sleep -Milliseconds 800
        # Get updated process title
        $p = Get-Process -Id $proc.Id
        Write-Host "Active Tab Title: $($p.MainWindowTitle)"
        if ($p.MainWindowTitle -like "*ImageFX*" -or $p.MainWindowTitle -like "*Image FX*" -or $p.MainWindowTitle -like "*kitchen*") {
            Write-Host "Found ImageFX tab!"
            break
        }
    }
} else {
    Write-Host "Error: Chrome not found"
}
