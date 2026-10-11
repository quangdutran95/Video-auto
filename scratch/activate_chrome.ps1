Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
}
"@

$proc = Get-Process chrome | Where-Object { $_.MainWindowTitle } | Select-Object -First 1
if ($proc) {
    $hwnd = $proc.MainWindowHandle
    # 9 = SW_RESTORE, 5 = SW_SHOW
    [Win32]::ShowWindowAsync($hwnd, 9)
    [Win32]::ShowWindowAsync($hwnd, 5)
    
    $wshell = New-Object -ComObject WScript.Shell
    Start-Sleep -Milliseconds 500
    if ($wshell.AppActivate($proc.Id)) {
        Start-Sleep -Milliseconds 500
        $wshell.SendKeys("%s") # Send Alt+S to toggle/reload
        Write-Host "Success: Activated Chrome window '$($proc.MainWindowTitle)' and sent Alt+S"
    } else {
        Write-Host "Warning: Restored window but could not AppActivate"
    }
} else {
    Write-Host "Error: No Chrome window with non-empty title found"
}
