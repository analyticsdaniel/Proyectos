# Prompt de traspaso a una sesión local

Copiar todo lo que está debajo de la línea y pegarlo como primer mensaje en una
sesión de Claude Code corriendo en el computador de Daniel.

---

Vas a retomar un proyecto que empezó en una sesión de Claude Code en la web y
que ahora sigue acá, en mi computador con Windows. Lee esto completo antes de
tocar nada.

## 1. Lo primero

El repositorio es `https://github.com/analyticsdaniel/Proyectos` y la rama de
trabajo es `claude/ml-object-recognition-algorithm-diivyi`. Clónalo o actualízalo,
cámbiate a esa rama, y **lee `vision/PLAN.md` completo antes de escribir una
línea de código.** Ese documento es la autoridad: tiene 14 secciones con las
decisiones, los números medidos, el alcance negativo y las fases. Lo que sigue
acá es solo el resumen para que sepas qué buscar.

## 2. Qué es el proyecto

Un convertidor de video en tabla. Entra una grabación, sale un CSV con qué
objetos aparecieron, cuándo y cuántos únicos hubo. Detecta personas, carros,
motos, buses, camiones y bicicletas con YOLO, les asigna un identificador
estable con seguimiento para no contarlos dos veces, y opcionalmente lee placas
colombianas. No identifica personas, no hay reconocimiento facial, y eso no se
va a agregar.

## 3. Estado del código

Hay 434 líneas en `vision/reconocimiento/`, **ninguna ejecutada nunca**. Nada
está verificado, no hay pruebas y `ultralytics` no está instalado.

1. `modelos.py`. Estructuras entre etapas: `Deteccion`, `LecturaPlaca`,
   `EventoPlaca`, `Resumen`.
2. `config.py`. Todos los parámetros ajustables en un solo sitio.
3. `detectores.py`. Envoltorio de YOLO con seguimiento ByteTrack, detrás de un
   `Protocol` llamado `Detector`, con import perezoso de `ultralytics`.
4. `placas_texto.py`. Normalización de lecturas de OCR contra los formatos de
   placa colombianos y votación ponderada entre frames del mismo vehículo. Es
   el único módulo puro, sin OpenCV ni torch, y es por donde conviene empezar a
   probar.

Falta: el lector de placas con OCR, el recorrido del video, las salidas en CSV
y JSON, el video anotado, la línea de comandos, las pruebas y el README.

## 4. Decisiones ya tomadas, no las vuelvas a abrir

1. **Se filman dos escenas en momentos distintos**, calle y salón de clase. Por
   eso se construye primero la parte común, que sirve a las dos.
2. **`leer_placas` está en `False` por defecto** y así se queda. Un salón no
   paga el costo de una etapa de OCR que no usa.
3. **Las placas bajaron de prioridad.** Leerlas es lo más difícil, obliga a una
   cámara de COP 1.700.000 a 3.400.000, y ya existe resuelto de estantería por
   USD 35 al mes por cámara en Plate Recognizer. Si algún día se necesitan, se
   compran antes que construirse.
4. **El OCR es local, con EasyOCR o PaddleOCR, y cuesta cero.** La alternativa
   de nube cuesta USD 1,50 por cada 1.000 imágenes, que son USD 5,40 por hora
   de video analizada. No se usa.
5. **No se compra cámara todavía.** El lente se escoge con la distancia medida
   y esa distancia no se ha medido. Si se compra, tiene que ser de lente
   motorizado varifocal, que permite corregir el zoom ya instalada.
6. **El mejor destino comercial son los aforos vehiculares** para estudios de
   tránsito, porque el comprador ya paga hoy la versión manual de ese trabajo,
   hecha por una persona con un contador en una esquina. **Eso todavía es
   hipótesis sin verificar**, y está marcado así en el plan.

## 5. Números que ya están medidos, no los recalcules

1. **Placa colombiana:** 33 cm de ancho. El OCR necesita de 90 a 150 píxeles
   sobre ese ancho. Con una cámara 4MP, un lente de 2,8 mm deja 36 píxeles a 10
   metros y uno de 12 mm deja 169 a esa misma distancia. **El lente manda sobre
   los megapíxeles.**
2. **Obturador:** un carro a 30 km/h exige 1/550 o más rápido, si no la placa
   sale barrida. A 10 km/h basta 1/200. Un resalto vale más que una cámara
   mejor.
3. **Peso del video:** celular a 1080p30 son 7,5 GB por hora. Cámara IP 4MP en
   H.265 son 2,3 GB por hora. El CSV de esa misma hora pesa 8,6 MB, **más de
   250 veces menos**, así que lo razonable es procesar y descartar el video.
4. **RAM:** entre 1,5 y 2 GB con YOLO nano, 3 a 4 GB con el mediano. El
   pipeline nunca carga el video entero.
5. **Velocidad en CPU:** YOLO nano sobre 1080p da de 5 a 15 frames por segundo.
   Por eso existe `salto_frames`.

## 6. Un defecto conocido que hay que corregir en la Fase 1

`Resumen.detecciones` es una lista que acumularía todas las detecciones hasta
el final del video. Una jornada de 12 horas son 1,3 millones de objetos, entre
400 MB y 1 GB de memoria viva sin razón. **El camino normal tiene que escribir
cada detección al CSV apenas ocurre** y mantener en memoria solo los contadores
y la votación de placas. El campo queda solo para videos cortos y pruebas. Ya
está advertido en su docstring y en la sección 13.5 del plan.

## 7. Qué quiero que hagas en esta sesión, en este orden

**7.1 Lo que solo puedes hacer tú y la sesión de la nube no podía.** Esa sesión
tenía amazon.com bloqueado por la política de red del contenedor. Tú corres en
mi máquina y sales por mi internet, así que abre estas dos fichas con el
navegador y dime precio, disponibilidad y si envían a Colombia, poniendo el
artículo en el carrito con dirección de entrega en Colombia para ver el
depósito de tasas de importación:

- `https://www.amazon.com/Anpviz-Recognition-2-7-13-5mm-Motorized-Nightvision/dp/B0H11T45YZ`
  Anpviz LPR 4MP, lente motorizado 2,7 a 13,5 mm, para distancias de 3 a 12 metros.
- `https://www.amazon.com/License-Recognition-Camera-8-32mm-Vision/dp/B0H2MGXGDD`
  Anpviz LPR 4MP a 30 o 60 fps, lente motorizado 8 a 32 mm, para 10 a 30 metros.

Compara contra lo que cueste una Hikvision iDS-2CD7A46G0/P-IZHS con
distribuidor colombiano, que trae garantía local. Escribe el resultado en la
sección 11.8 de `vision/PLAN.md`, que hoy dice expresamente que esos datos no
se pudieron verificar.

**7.2 Dejar el entorno andando.** Entorno virtual propio del proyecto, con
`opencv-python`, `numpy` y `ultralytics`. Comprueba que YOLO descarga los pesos
y corre sobre una imagen cualquiera. Si tengo GPU NVIDIA, instala la versión de
torch con CUDA y dímelo, que cambia los tiempos de todo.

**7.3 Construir la Fase 1 completa**, que es la que sirve a las dos escenas y
no depende de que yo grabe nada. Está definida en la sección 8 del plan, con su
criterio de aceptación: recorrido del video, detección, seguimiento, conteo de
únicos, CSV incremental, JSON de resumen, video anotado y línea de comandos.
Más las pruebas de `placas_texto.py`, que corren sin modelo ni GPU.

## 8. Cómo trabajo

1. Todo en español: comentarios, docstrings, nombres de módulos y documentos.
2. Commits descriptivos en español, en la rama
   `claude/ml-object-recognition-algorithm-diivyi`. Nunca a `main`, y no abras
   pull request a menos que yo lo pida.
3. Cuando midas algo o decidas algo, escríbelo en `vision/PLAN.md` en el
   momento, no al final.
4. Si algo no se pudo verificar, dilo en el documento con esas palabras, como
   está hoy la sección 11.8. No rellenes con estimaciones presentadas como
   datos.
5. Un accionable al final de cada entrega, uno solo.
