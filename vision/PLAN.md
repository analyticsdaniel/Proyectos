# Plan de desarrollo: reconocimiento de personas, vehículos y placas en video

Documento de decisión previo a retomar el código. Se escribe antes de seguir
construyendo, porque la parte barata de equivocarse es esta.

---

## 1. Estado actual

Commit `8bb3d8f`, rama `claude/ml-object-recognition-algorithm-diivyi`. Hay 434
líneas de Python en `vision/reconocimiento/`, ninguna ejecutada todavía contra
un video real.

**Lo que existe:**

1. `modelos.py`, 98 líneas. Las estructuras que viajan entre etapas: detección,
   lectura cruda de placa, evento de placa consolidado y resumen del video.
2. `config.py`, 71 líneas. Todos los parámetros ajustables en un solo sitio:
   pesos del modelo, umbrales de confianza, clases de interés, muestreo de
   frames y carpetas de salida.
3. `detectores.py`, 99 líneas. Envoltorio de YOLO con seguimiento por
   ByteTrack, detrás de una interfaz, de modo que el pipeline no queda casado
   con el modelo. El import de `ultralytics` es perezoso.
4. `placas_texto.py`, 160 líneas. Normalización de lecturas de OCR contra los
   formatos de placa colombianos y votación entre frames del mismo vehículo.

**Lo que falta:** el lector de placas con OCR, el recorrido del video, las
salidas en CSV y JSON, el video anotado, la línea de comandos, las pruebas y el
README.

**Lo que no se ha probado:** nada. `ultralytics` ni siquiera quedó instalado.
Todo el código anterior está escrito pero no verificado.

---

## 2. La pregunta que hay que responder antes de escribir una línea más

El encargo original dice "filmar una clase". Con carros y placas de por medio,
caben dos lecturas y llevan a proyectos distintos:

1. **Una calle, un parqueadero o una portería.** Cámara fija, vehículos que
   entran y salen, placas a menos de 10 metros. Aquí las placas tienen sentido
   y el proyecto tiene destino comercial.
2. **Una clase, un salón, una grabación docente.** Personas sentadas, ningún
   carro. Aquí la mitad del código sobra y el trabajo real es conteo de
   asistentes y atención.

Las dos comparten el detector y el seguimiento. Se diferencian en todo lo
demás: el ángulo de cámara, la distancia, si la parte de placas existe y qué se
mide al final.

**Decidido el 13 de septiembre de 2026: las dos, en momentos distintos.** De
ahí salen tres consecuencias que mandan sobre el resto del documento:

1. Se construye primero la parte común, que sirve a los dos casos: detección,
   seguimiento, conteo de únicos y salidas.
2. La lectura de placas queda detrás de un interruptor en la configuración,
   `leer_placas`, **apagado por defecto**. Un salón de clase no paga el costo
   de una etapa de OCR que no va a usar.
3. La Fase 0 se corre dos veces, una por escena, porque el umbral que decide
   es distinto: en calle manda el ancho de la placa en píxeles, en salón manda
   el alto de la persona, y ese segundo umbral lo cumple casi cualquier
   grabación.

---

## 3. Especificación

**3.1 Rol.** Se escribe desde ingeniería de visión por computador, no desde
demo.

**3.2 El problema, en una frase.** Contar y registrar lo que pasa frente a una
cámara cuesta una persona mirando el video, y nadie se sienta a mirar tres
horas de grabación para saber cuántos carros entraron.

**3.3 El usuario.** Daniel. Antes: tiene un archivo de video en el disco y
ninguna forma de saber qué contiene sin verlo. Después: tiene un CSV con cada
objeto, su instante y su identificador, y un video anotado para revisar a ojo
los casos dudosos.

**3.4 Los pasos.** Deja el video en una carpeta de entrada. Corre un comando, o
no corre nada si ya está la tarea programada. Recibe tres archivos: el CSV de
eventos, el JSON de resumen y el video anotado.

**3.5 Qué puede hacer.** Detectar personas, carros, motos, buses, camiones y
bicicletas. Asignarle a cada uno un identificador estable para contarlo una
sola vez. Leer la placa de los vehículos cuando la resolución lo permita.
Contar únicos por clase. Exportar todo a CSV y JSON.

**3.6 Qué datos se guardan y dónde.** Todo en disco local, en la carpeta de
salidas del proyecto. Nada sale a internet. El CSV lleva clase, identificador,
instante, caja y confianza. El JSON lleva el resumen y las placas
consolidadas. Los pesos del modelo se descargan una vez y quedan en caché.

**3.7 Qué NO es y qué NO va a hacer.** Sección obligatoria:

1. **No identifica personas.** No hay reconocimiento facial, no hay base de
   rostros, no dice quién es nadie. Detecta que hay una persona, no cuál.
2. **No consulta la placa contra ninguna base oficial.** Ni RUNT, ni SIMIT, ni
   comparendos. Lee seis caracteres y ahí para.
3. **No funciona en tiempo real en la primera versión.** Procesa archivos ya
   grabados.
4. **No detecta comportamiento.** Ni peleas, ni robos, ni caídas, ni merodeo.
5. **No sirve como prueba legal.** Una lectura de OCR con votación es una
   estimación, no un acta.
6. **No es un sistema de vigilancia de terceros.** Grabar espacio ajeno,
   propiedad horizontal o empleados tiene reglas propias, ver sección 7.

---

## 4. La prueba barata, antes de construir más

La versión manual y fea que responde la única pregunta que importa toma quince
minutos y va antes que cualquier código nuevo:

1. Daniel graba 60 segundos con la cámara puesta donde iría de verdad.
2. Se extraen 20 frames y se recortan los vehículos.
3. **Daniel mira los recortes y cuenta cuántas placas lee él, a ojo.**

La regla es dura y no tiene vuelta: **si un humano no lee la placa en el
recorte, ningún modelo la va a leer.** El OCR necesita del orden de 90 a 150
píxeles de ancho sobre la placa misma. Una placa colombiana mide 33 cm de
ancho. Con un celular a 1080p y lente normal, eso se cumple hasta unos 6 a 8
metros de distancia, y se pierde con movimiento lateral rápido o con la placa a
más de 30 grados respecto a la cámara.

**Criterio de paso:** si Daniel lee 6 o más placas de 10 recortes, la fase de
placas se construye. Si lee menos de 3, no se construye, y el problema se
resuelve moviendo la cámara, no programando. Entre 3 y 6, se construye pero se
baja la expectativa a lectura asistida, es decir el sistema propone y un humano
confirma.

Lo mismo aplica a personas, con umbral distinto: una persona se detecta bien
desde 40 píxeles de alto, así que casi cualquier grabación sirve para contar
gente.

---

## 5. Diseñar para el fracaso

Lo que se diseña suponiendo que todo sale bien es un demo. Por cada paso, qué
pasa cuando no:

1. **El video no abre.** Códec raro, archivo a medias, ruta con tildes. El
   pipeline valida al abrir y falla con un mensaje claro, no a los 40 minutos.
2. **El modelo no descarga.** Sin internet, o proxy de por medio. Se acepta una
   ruta local de pesos y se documenta cómo descargarlos una vez.
3. **El proceso se cae a mitad de un video de dos horas.** Se escribe el CSV de
   forma incremental, no al final, y se guarda el número del último frame
   procesado para poder reanudar.
4. **El seguimiento pierde el vehículo y le cambia el id.** Un mismo carro
   cuenta dos veces. Se mitiga con la votación por placa, que vuelve a unir lo
   que el rastreador separó, y se reporta el conteo con esa advertencia.
5. **El OCR lee basura.** Ya está resuelto en `placas_texto.py`: lo que no
   encaja en un formato válido se descarta, y se exigen al menos dos lecturas
   coincidentes antes de dar una placa por buena.
6. **La cámara se mueve o cambia la luz.** El conteo se dispara. Se registra el
   número de detecciones por minuto y se marca el tramo cuando se sale de lo
   normal.
7. **El computador no da.** En CPU, YOLO nano sobre 1080p hace del orden de 5 a
   15 frames por segundo, así que una hora de video puede tomar dos horas. Por
   eso existe `salto_frames`: analizar uno de cada tres frames y perder muy
   poco, porque a 30 fps un carro aparece en decenas de frames.

---

## 6. Las cuatro preguntas

**6.1 ¿Con qué plata se paga y en cuánto tiempo?** Como está descrito hoy, con
ninguna. Si el destino es una clase o un experimento propio, esto es
aprendizaje, no ingreso, y hay que llamarlo así en vez de venderlo como
valioso. Los caminos donde sí hay plata son concretos y todos exigen la lectura
uno de la sección 2: control de acceso vehicular en conjuntos y parqueaderos,
que hoy se paga con un vigilante anotando en un cuaderno, y conteo de aforo
para comercio. **Ninguno de los dos se decide desde el código, se decide
consiguiendo el primer sitio que deje poner la cámara.**

**6.2 ¿Depende de publicar volumen?** No. Pasa.

**6.3 ¿Qué activo queda si esto muere?** El pipeline, que es reutilizable para
cualquier problema de video, y el número medido de la sección 4, que es un dato
propio que hoy no existe escrito en ninguna parte. Pasa, con la condición de
documentar el resultado de la prueba.

**6.4 ¿Cuál es el criterio de matarla, con umbral y fecha?** Se escribe ahora,
no cuando duela. **Al 15 de octubre de 2026**, si sobre video propio el sistema
no consolida correctamente al menos 6 de cada 10 placas de vehículos que pasen
a menos de 8 metros, se mata la parte de placas y el proyecto queda reducido a
conteo de personas y vehículos, que sí funciona. Si además para esa fecha no
hay un sitio real donde ponerlo, se archiva completo y queda como código
disponible, sin seguir invirtiendo.

---

## 7. Nota legal, tres líneas

Grabar en espacio público es legal. Una placa y una persona identificable son
dato personal bajo la Ley 1581 de 2012, así que tratarlos exige finalidad
declarada y aviso visible si es propiedad privada, conjunto o empresa. Para uso
propio sobre video propio no hay problema, y si el destino es un tercero se
necesita su autorización por escrito antes de la primera grabación.

---

## 8. Fases, con criterio de aceptación

Cada fase entrega algo que corre. Ninguna depende de la siguiente para servir.

**Fase 0. Medir si el video sirve.** Script corto que toma un video, extrae
frames, recorta vehículos y personas, y reporta el ancho en píxeles de cada
placa estimada. Sin esto, todo lo demás es fe.
*Aceptación:* una tabla con la distribución de anchos y los recortes en disco
para que Daniel los mire. Decisión escrita de construir placas o no.

**Fase 1. El pipeline que ya sirve sin placas.** Recorrido del video, detección,
seguimiento, conteo de únicos, CSV incremental, JSON de resumen y video
anotado. Más la línea de comandos.
*Aceptación:* sobre un video de un minuto, el CSV tiene una fila por detección,
el conteo de personas únicas no se desvía más del 20 por ciento del conteo
manual, y el proceso se puede interrumpir y reanudar.

**Fase 2. Placas.** Solo si la Fase 0 pasa, y solo para la escena de calle.
Detección de la región de la placa, OCR y enganche con la votación que ya está
escrita. Queda detrás de `leer_placas`, apagado por defecto, de modo que el
caso de salón nunca la ejecuta.
*Aceptación:* 6 de 10 placas correctas en las condiciones de la sección 6.4.

**Fase 3. Pruebas y README.** Pruebas sobre la normalización y la votación, que
no necesitan modelo ni GPU, más un video sintético para el pipeline.
*Aceptación:* la suite corre en menos de 30 segundos sin descargar nada.

**Fase 4. Que no haya que hacer nada.** Carpeta de entrada vigilada y tarea
programada de Windows que procesa lo que aparezca y deja los resultados en
disco.
*Aceptación:* Daniel copia un video a la carpeta y no toca nada más.

---

## 9. Mecanismo

Script local de Python con entorno virtual propio, ejecutado a mano durante las
fases 0 a 3. Desde la Fase 4, tarea programada de Windows sobre una carpeta de
entrada, porque el criterio es que Daniel no tenga que hacer nada. No hay bot
de Telegram por ahora: no hay nada que avisar hasta que el conteo signifique
algo para alguien.

---

## 10. El accionable, uno solo

**Grabar 60 segundos con la cámara donde iría de verdad, en la escena de
calle.** Es la única de las dos cuyo umbral está en duda, y sin ese video no se
puede decidir si la Fase 2 existe. La Fase 1 no depende de esto y puede
arrancar en paralelo.
