# Protector de pantalla en negro

Deja el protector de pantalla de Windows en negro puro, sin ninguna
animacion, en reemplazo del protector **Cintas** que trae el equipo.

## 1. Que hace

Windows ya trae un protector de pantalla llamado **En blanco**
(`C:\Windows\System32\scrnsave.scr`). Ese protector no dibuja nada: pinta
la pantalla de negro y ahi se queda, igual a un monitor apagado. Es
exactamente el efecto que se busca; no hay que instalar nada de terceros.

El script hace tres cosas:

1. Cambia el protector activo por `scrnsave.scr` (pantalla negra).
2. Fija en cuantos minutos de inactividad entra.
3. Programa el apagado fisico del monitor unos minutos despues, para que la
   pantalla no se quede encendida iluminando negro toda la noche.

El cambio queda activo de inmediato. No pide permisos de administrador ni
obliga a cerrar sesion.

## 2. Como se aplica

Doble clic en `Aplicar-pantalla-negra.bat`.

O, desde PowerShell, con los valores que se quieran:

```powershell
.\pantalla-negra.ps1                                  # negro a los 5 min, monitor off a los 10
.\pantalla-negra.ps1 -Minutos 3                       # negro a los 3 min
.\pantalla-negra.ps1 -Minutos 5 -PedirContrasena      # pide contrasena al volver
.\pantalla-negra.ps1 -Minutos 5 -MinutosApagarMonitor 0   # no toca la energia
```

## 3. Como se deshace

```powershell
.\devolver-protector-anterior.ps1
```

Vuelve a poner Cintas (`Ribbons.scr`).

## 4. La ruta manual, sin script

Sirve la misma configuracion a mano:

1. Windows + R, pegar `control desk.cpl,,@screensaver` y Enter.
2. En la lista, elegir **En blanco** en lugar de **Cintas**.
3. Poner los minutos de espera y Aceptar.

## 5. Sobre el bloqueo con Windows + L

Windows + L muestra la pantalla de bloqueo con su imagen de fondo, no el
protector de pantalla. Para que tambien quede en negro hay dos caminos:

- Dejar que el monitor se apague solo: es lo que ya programa el script con
  `MinutosApagarMonitor`. Al bloquear y esperar esos minutos, la pantalla se
  apaga de verdad.
- Quitar la imagen de la pantalla de bloqueo, en Configuracion >
  Personalizacion > Pantalla de bloqueo, poniendo **Imagen** con un fondo
  negro solido.

## 6. Detalle tecnico

Los valores quedan escritos en `HKCU:\Control Panel\Desktop`:

| Valor | Contenido |
| --- | --- |
| `SCRNSAVE.EXE` | `C:\Windows\System32\scrnsave.scr` |
| `ScreenSaveActive` | `1` |
| `ScreenSaveTimeOut` | segundos de inactividad |
| `ScreenSaverIsSecure` | `1` si pide contrasena, `0` si no |

El script los difunde al sistema con `SystemParametersInfo` y
`UpdatePerUserSystemParameters`, por eso no hay que reiniciar. El apagado del
monitor se fija con `powercfg /change monitor-timeout-ac` y `-dc`.
