<#
.SYNOPSIS
    Deshace el cambio: vuelve a poner el protector de pantalla Cintas.

.DESCRIPTION
    Restaura el protector animado de Windows (Cintas / Ribbons.scr) y, si se
    indica, cambia tambien el apagado del monitor.

.PARAMETER Minutos
    Minutos de inactividad antes de que entre el protector. Por defecto 5.

.PARAMETER MinutosApagarMonitor
    Minutos antes de apagar el monitor. Use 0 para no tocar la energia.

.EXAMPLE
    .\devolver-protector-anterior.ps1
#>

[CmdletBinding()]
param(
    [ValidateRange(1, 600)]
    [int]$Minutos = 5,

    [ValidateRange(0, 600)]
    [int]$MinutosApagarMonitor = 0
)

$ErrorActionPreference = 'Stop'

$protector = Join-Path $env:WINDIR 'System32\Ribbons.scr'
if (-not (Test-Path -LiteralPath $protector)) {
    throw "No se encontro $protector."
}

$clave = 'HKCU:\Control Panel\Desktop'
Set-ItemProperty -Path $clave -Name 'SCRNSAVE.EXE'      -Value $protector
Set-ItemProperty -Path $clave -Name 'ScreenSaveActive'  -Value '1'
Set-ItemProperty -Path $clave -Name 'ScreenSaveTimeOut' -Value ([string]($Minutos * 60))

$argumentos = @('user32.dll,UpdatePerUserSystemParameters', '1', 'True')
Start-Process -FilePath 'rundll32.exe' -ArgumentList $argumentos -NoNewWindow -Wait

Write-Host "Protector restaurado: $protector a los $Minutos minuto(s)."

if ($MinutosApagarMonitor -gt 0) {
    powercfg /change monitor-timeout-ac $MinutosApagarMonitor | Out-Null
    powercfg /change monitor-timeout-dc $MinutosApagarMonitor | Out-Null
    Write-Host "Monitor se apaga    : a los $MinutosApagarMonitor minuto(s)"
}
