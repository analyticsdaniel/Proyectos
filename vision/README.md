# Reconocimiento de personas, vehículos y placas en video

Un convertidor de video en tabla. Entra una grabación, sale un CSV con qué
objetos aparecieron, cuándo y cuántos únicos hubo.

Las decisiones, los números y el alcance negativo están en [PLAN.md](PLAN.md),
que es la autoridad. Esto es solo el manual de uso.

**Lo que no hace, y no va a hacer:** no identifica personas, no hay
reconocimiento facial, no consulta ninguna placa contra ninguna base oficial y
no sirve como prueba legal. Ver la sección 3.7 del plan.

---

## Instalar

El entorno virtual de este computador vive **fuera del repositorio**, en
`C:\Users\Daniel Sanchez\.venvs\vision`, porque Windows tiene desactivadas las
rutas largas y torch no cabe bajo la ruta de `DS Files - Origen`. Son binarios
que se regeneran con un comando, así que tampoco hay que respaldarlos.

Para rehacerlo desde cero, o en otro computador:

```
py -3.14 -m venv C:\Users\<usuario>\.venvs\vision
C:\Users\<usuario>\.venvs\vision\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
C:\Users\<usuario>\.venvs\vision\Scripts\python.exe -m pip install ultralytics opencv-python numpy pytest
```

La primera línea de torch es la de **GPU NVIDIA con CUDA 13**. Sin tarjeta
NVIDIA se instala `pip install torch torchvision` a secas, que trae la versión
de CPU y funciona igual, más lento.

Comprobar que la GPU quedó visible:

```
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Los pesos de YOLO se descargan solos la primera vez y quedan en `pesos/`.

## Usar

```
python -m reconocimiento grabacion.mp4
```

Deja tres archivos en `salidas/`:

| Archivo | Qué trae |
|---|---|
| `<video>.detecciones.csv` | Una fila por detección: clase, identificador, frame, segundo, caja y confianza |
| `<video>.resumen.json` | Conteo por clase, objetos únicos, velocidad de proceso y advertencias |
| `<video>.anotado.mp4` | El video con las cajas dibujadas, para revisar a ojo |

Opciones que valen la pena:

| Opción | Para qué |
|---|---|
| `--salto 3` | Analiza uno de cada tres frames. Tres veces más rápido y se pierde muy poco, porque a 30 fps un carro aparece en decenas de frames |
| `--dispositivo 0` | Usa la primera GPU NVIDIA. En este PC pasa de 19 a 40 frames por segundo |
| `--sin-video` | No dibuja el video anotado. **Es la opción más rentable:** dibujar cuesta más que detectar |
| `--clases person` | Solo personas. Es el caso del salón de clase |
| `--reanudar` | Sigue donde quedó la corrida anterior, si el proceso se cayó |
| `--max-frames 100` | Corta rápido, para probar |

Un salón de clase, entonces:

```
python -m reconocimiento clase.mp4 --clases person --salto 3 --dispositivo 0
```

Una cámara IP en vivo, sin cambiar una línea de código:

```
python -m reconocimiento rtsp://usuario:clave@192.168.1.50:554/stream1
```

## Si el proceso se cae

El CSV se escribe detección por detección y el punto de reanudación se guarda
cada 100 frames analizados, en `salidas/<video>.estado.json`. Volver a correr el
mismo comando con `--reanudar` sigue donde iba, sin repetir lo hecho ni perder
los contadores.

## Probar

```
python -m pytest pruebas -q
```

34 pruebas, menos de un segundo, sin descargar nada y sin tocar la GPU. Las de
`placas_texto` no necesitan siquiera OpenCV; las del pipeline usan un video
sintético y un detector falso, así que no cargan YOLO.

## Velocidad medida en este PC

RTX 4070 Laptop de 8 GB, video 1080p, `yolov8n`, todos los frames:

| Configuración | Frames por segundo | Una hora de video tarda |
|---|---|---|
| GPU, sin video anotado | 39,7 | 45 minutos |
| CPU, sin video anotado | 19,0 | 1 hora 35 minutos |
| GPU, con video anotado | 16,8 | 1 hora 47 minutos |

Con `--salto 3` cada uno de esos tiempos se divide entre tres.

## Qué falta

La Fase 2 del plan, que es la línea de aforo y la matriz de giros, y la Fase 3,
que es el informe. Las placas siguen apagadas por defecto y bajas de prioridad,
por lo que dice la sección 12.3 del plan.
