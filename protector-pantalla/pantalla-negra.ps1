<#
.SYNOPSIS
    Deja el protector de pantalla de Windows en negro puro, sin animacion.

.DESCRIPTION
    Cambia el protector de pantalla actual (Cintas, Burbujas, Mystify, etc.)
    por el protector "En blanco" de Windows (scrnsave.scr), que no dibuja
    nada: solo una pantalla negra, como si el monitor estuviera apagado.

    Ademas deja el monitor programado para apagarse fisicamente un rato
    despues, para que el equipo no se quede iluminando en negro toda la noche.

    No requiere permisos de administrador ni cerrar sesion: el cambio queda
    activo de inmediato.

.PARAMETER Minutos
    Minutos de inactividad antes de que entre la pantalla negra. Por defecto 5.

.PARAMETER MinutosApagarMonitor
    Minutos de inactividad antes de que el monitor se apague de verdad.
    Por defecto 10. Use 0 para no tocar la configuracion de energia.

.PARAMETER PedirContrasena
    Si se indica, al mover el mouse pide la contrasena para volver a entrar.

.EXAMPLE
    .\pantalla-negra.ps1

.EXAMPLE
    .\pantalla-negra.ps1 -Minutos 3 -PedirContrasena

.EXAMPLE
    .\pantalla-negra.ps1 -Minutos 5 -MinutosApagarMonitor 0
#>

[CmdletBinding()]
param(
    [ValidateRange(1, 600)]
    [int]$Minutos = 5,

    [ValidateRange(0, 600)]
    [int]$MinutosApagarMonitor = 10,

    [switch]$PedirContrasena
)

$ErrorActionPreference = 'Stop'

# 1. Ubicar el protector "En blanco" que trae Windows
$protectorNegro = Join-Path $env:WINDIR 'System32\scrnsave.scr'
if (-not (Test-Path -LiteralPath $protectorNegro)) {
    throw "No se encontro el protector en blanco en $protectorNegro. Esta instalacion de Windows no lo tiene."
}

$clave = 'HKCU:\Control Panel\Desktop'

# 2. Dejar constancia de que habia antes
$anterior = (Get-ItemProperty -Path $clave -Name 'SCRNSAVE.EXE' -ErrorAction SilentlyContinue).'SCRNSAVE.EXE'
if ([string]::IsNullOrWhiteSpace($anterior)) { $anterior = '(ninguno)' }
Write-Host "Protector anterior : $anterior"

# 3. Aplicar la pantalla negra
$segundos = $Minutos * 60
$seguro = '0'
if ($PedirContrasena) { $seguro = '1' }

Set-ItemProperty -Path $clave -Name 'SCRNSAVE.EXE'        -Value $protectorNegro
Set-ItemProperty -Path $clave -Name 'ScreenSaveActive'    -Value '1'
Set-ItemProperty -Path $clave -Name 'ScreenSaveTimeOut'   -Value ([string]$segundos)
Set-ItemProperty -Path $clave -Name 'ScreenSaverIsSecure' -Value $seguro

# 4. Empujar el cambio al sistema, sin cerrar sesion
$firma = @'
[DllImport("user32.dll", SetLastError = true)]
public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, IntPtr pvParam, uint fWinIni);
'@
if (-not ('Win32.Param' -as [type])) {
    Add-Type -Namespace Win32 -Name Param -MemberDefinition $firma
}

$SPI_SETSCREENSAVEACTIVE  = 0x0011
$SPI_SETSCREENSAVETIMEOUT = 0x000F
$difundir = 0x01 -bor 0x02   # SPIF_UPDATEINIFILE | SPIF_SENDCHANGE

[void][Win32.Param]::SystemParametersInfo($SPI_SETSCREENSAVEACTIVE, 1, [IntPtr]::Zero, $difundir)
[void][Win32.Param]::SystemParametersInfo($SPI_SETSCREENSAVETIMEOUT, $segundos, [IntPtr]::Zero, $difundir)

$argumentos = @('user32.dll,UpdatePerUserSystemParameters', '1', 'True')
Start-Process -FilePath 'rundll32.exe' -ArgumentList $argumentos -NoNewWindow -Wait

Write-Host "Protector nuevo    : $protectorNegro (negro, sin animacion)"
Write-Host "Entra a los        : $Minutos minuto(s) de inactividad"
if ($PedirContrasena) {
    Write-Host "Pide contrasena    : si"
} else {
    Write-Host "Pide contrasena    : no"
}

# 5. Que el monitor se apague de verdad un rato despues
if ($MinutosApagarMonitor -gt 0) {
    if ($MinutosApagarMonitor -le $Minutos) {
        $MinutosApagarMonitor = $Minutos + 5
        Write-Warning "El apagado del monitor iba antes o al tiempo que la pantalla negra. Se corrio a $MinutosApagarMonitor minutos."
    }
    powercfg /change monitor-timeout-ac $MinutosApagarMonitor | Out-Null
    powercfg /change monitor-timeout-dc $MinutosApagarMonitor | Out-Null
    Write-Host "Monitor se apaga   : a los $MinutosApagarMonitor minuto(s)"
}

Write-Host ""
Write-Host "Listo. Para probarlo: deje el equipo quieto $Minutos minutos, o bloquee con Windows+L y espere."
