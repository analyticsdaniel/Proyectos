@echo off
REM Doble clic aqui y queda aplicado. No necesita permisos de administrador.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0pantalla-negra.ps1"
echo.
pause
