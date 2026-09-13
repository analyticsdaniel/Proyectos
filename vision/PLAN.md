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

## 10. Qué es el OCR y qué cuesta

**OCR** es reconocimiento óptico de caracteres: convertir una imagen que
contiene texto en texto que el computador puede manipular. En este proyecto es
la última etapa de tres. Primero YOLO encuentra el carro. Después se ubica el
rectángulo de la placa dentro del carro. Se recorta esa imagen, que suele medir
unos 120 por 50 píxeles, y el OCR es lo que dice qué letras y números hay ahí.

**Lo que cuesta, en las dos rutas posibles:**

1. **OCR local, que es la ruta del plan. Cero pesos.** EasyOCR o PaddleOCR son
   librerías gratuitas que se descargan una vez y corren en el computador. No
   cobran por imagen, no tienen mensualidad y no mandan nada a internet, que
   además resuelve la mitad de la nota legal de la sección 7.
2. **OCR en la nube, de pago.** Google Cloud Vision cobra USD 1,50 por cada
   1.000 imágenes, con las primeras 1.000 del mes gratis. Plate Recognizer, que
   es especializado en placas y no en texto genérico, cobra USD 50 al mes por
   50.000 lecturas, o USD 35 al mes por cámara con lecturas ilimitadas.

**La aritmética que decide.** Una hora de video a 30 fps, analizando uno de
cada tres frames, son 36.000 frames. Si en el 10 por ciento aparece un
vehículo, son 3.600 imágenes que mandar. En Google eso cuesta USD 5,40 por cada
hora de video. Local cuesta cero. Con grabación continua de una portería, ocho
horas diarias, la diferencia es del orden de USD 1.300 al año contra cero.

**Por qué se escoge el local, más allá del precio.** El OCR de pago acierta más
que el gratuito frame por frame, eso es cierto. Pero la votación entre frames
que ya está escrita en `placas_texto.py` cierra buena parte de esa diferencia,
porque un vehículo aparece en decenas de frames y basta con que unos pocos
salgan nítidos. Y sobre todo: **el cuello de botella no es el OCR, es la
resolución de la placa.** Ningún servicio de pago lee una placa de 40 píxeles.
Eso se arregla con lente, no con presupuesto de software.

---

## 11. Hardware

No hay cámaras hoy, así que esta sección define qué comprar, cuándo y por qué.
El orden importa: **la recomendación es no comprar nada todavía**, y las
razones están al final.

### 11.1 El error de dos millones de pesos que hay que evitar

La compra típica es un domo 4K gran angular, porque 4K suena a que lee todo. No
lee placas. Un 4K con lente de 2,8 mm a 10 metros pone unos 70 píxeles sobre la
placa, que no alcanza. Un 4MP con lente de 12 mm, que cuesta parecido y tiene
menos de la mitad de píxeles, pone 170 a esa misma distancia y sí lee.

**El lente manda sobre los megapíxeles.** Todo lo demás de esta sección sale de
ahí.

### 11.2 Primera regla: píxeles sobre la placa

Una placa colombiana mide 33 cm de ancho y el OCR necesita entre 90 y 150
píxeles sobre ese ancho. Eso son unos 300 a 450 píxeles por metro en el punto
exacto donde pasa el carro. La cuenta es:

    píxeles por metro = ancho del sensor en píxeles / (2 × distancia × tan(ángulo horizontal / 2))

Para una cámara de 4MP, que son 2.560 píxeles de ancho, el ancho de placa que
queda según el lente y la distancia:

| Lente | Ángulo | A 3 m | A 5 m | A 10 m | A 15 m | A 25 m |
|---|---|---|---|---|---|---|
| 2,8 mm | 100° | 118 px | 71 px | 36 px | 24 px | 14 px |
| 6 mm | 55° | 271 px | 162 px | 81 px | 54 px | 32 px |
| 12 mm | 28° | 565 px | 339 px | 169 px | 113 px | 68 px |
| 25 mm | 14° | 1146 px | 688 px | 344 px | 229 px | 138 px |

Todo lo que esté por debajo de 90 no se lee. La tabla se resume sola: con
lente ancho hay que estar prácticamente encima del carro, y de 10 metros en
adelante hace falta teleobjetivo.

**El corolario que sorprende a todo el mundo:** un lente de 12 mm cubre 28
grados, que a 10 metros son 5 metros de ancho, o sea un carril. **Una sola
cámara no puede leer placas y ver la escena completa al tiempo.** Un montaje
real son dos cámaras: una ancha de contexto y una angosta apuntada al punto por
donde pasan los carros.

### 11.3 Segunda regla: obturador, que pesa más que la resolución

Un carro a 30 km/h se mueve 8,3 metros por segundo. Con obturador de 1/30 de
segundo recorre 28 cm mientras la foto se toma, y la placa sale barrida. No hay
resolución que arregle eso.

Un carácter de placa mide unos 4,5 cm, y el barrido tolerable es como un tercio
de eso, 1,5 cm. De ahí sale el obturador mínimo:

| Velocidad del vehículo | Obturador mínimo |
|---|---|
| 10 km/h, un carro entrando a una portería | 1/200 |
| 30 km/h, calle residencial | 1/550 |
| 50 km/h, avenida | 1/1000 |
| 80 km/h | 1/1500 |

Dos consecuencias de plata. La primera: **un resalto, un portón o una curva
valen más que una cámara mejor**, porque bajar el carro de 30 a 10 km/h
relaja el obturador casi tres veces. La segunda: obturador rápido significa
menos luz entrando, y por eso las cámaras de placas de verdad traen su propio
iluminador infrarrojo. Una cámara común de noche baja el obturador sola para
compensar, y ahí se pierde toda la placa.

### 11.4 Tercera regla: geometría, que es gratis

Ángulo horizontal y vertical por debajo de 30 grados respecto a la placa, ideal
por debajo de 15. Altura de montaje entre 1 y 1,5 metros si se puede, que es
mucho más bajo de lo que la gente instala. Apuntada al punto donde el carro va
más lento. Esto no cuesta nada y decide más que cualquier compra.

### 11.5 Los niveles de compra

**Nivel 0. Cero pesos, y es donde hay que empezar.** El celular en un trípode.
Un trípode con soporte de celular cuesta entre COP 40.000 y 80.000. Se graba en
modo pro a 1080p, obturador fijo en 1/500, enfoque manual. Con esto se hacen la
Fase 0 y la Fase 1 completas. No sirve para dejarlo 24/7 ni para grabar de
noche, y no hace falta que sirva todavía.

**Nivel 1. Salón de clase o conteo de personas. USD 40 a 120.** Una webcam
1080p si el computador está cerca, o una cámara IP wifi 2K. Aquí el lente ancho
sí es lo correcto, y el obturador no importa porque la gente se mueve lento.
Una persona se detecta bien desde 40 píxeles de alto, así que casi cualquier
cámara sirve.

**Nivel 2. Portería o calle, con placas. USD 250 a 600 por punto.** Cámara IP
tipo LPR o ANPR con PoE, 4MP a 30 fps, lente varifocal motorizado de 2,7 a 13,5
mm o de 8 a 32 mm, WDR de 120 dB o más para el contraste de los faros,
obturador ajustable y iluminador infrarrojo propio. Las que existen de fábrica
para esto son las series LPR de Hikvision, Dahua, Uniview y LTS, y hay
alternativas más baratas tipo Anpviz. Sumar el switch PoE, entre USD 30 y 60,
cable UTP exterior, y una UPS pequeña de USD 60 a 100 para que un corte de luz
no se lleve la grabación. Y la segunda cámara ancha de contexto, USD 60 a 120,
por lo dicho en 11.2.

**Nivel 3. Cómputo.** Para la Fase 1 procesando archivos, el computador actual
sirve aunque vaya lento: en CPU, YOLO nano sobre 1080p hace del orden de 5 a 15
frames por segundo, así que una hora de video toma una o dos horas analizando
uno de cada tres frames. Si se quiere tiempo real, una GPU NVIDIA usada tipo
RTX 3060 de 12 GB, entre USD 200 y 280, es el mejor peso por precio y lleva eso
a más de 60 frames por segundo. Si se quiere sin computador prendido, una
Raspberry Pi 5 con el kit Hailo de 26 TOPS sale sobre USD 190 entre las dos
piezas, y una Jetson Orin Nano ronda los USD 250.

**Almacenamiento.** Una cámara 4MP en H.265 gasta entre 4 y 6 Mbps, que son
unos 2,5 GB por hora y del orden de 55 GB por día en grabación continua. Un
disco de 4 TB, entre USD 80 y 100, guarda cerca de dos meses de una cámara. Si
solo interesa el CSV y no el video, se procesa y se descarta, y el
almacenamiento deja de ser un problema.

### 11.6 Costo total por escenario

Cifras aproximadas, a una tasa de referencia de COP 4.200 por dólar. **No pude
confirmar precios de retail colombiano desde acá**, así que estos números
sirven para decidir, no para presupuestar: hay que cotizar en Mercado Libre,
Alkosto o un distribuidor Hikvision o Dahua local antes de comprar.

| Escenario | Equipo | Aproximado |
|---|---|---|
| Fase 0 y Fase 1, las dos escenas | Trípode y el celular que ya tiene | COP 40.000 a 80.000 |
| Salón de clase permanente | Webcam o cámara IP wifi | COP 170.000 a 500.000 |
| Portería, un punto, con placas | Cámara LPR, cámara de contexto, switch PoE, cableado y UPS | COP 1.700.000 a 3.400.000 |
| Tiempo real en vez de por lotes | GPU usada RTX 3060 12 GB | COP 840.000 a 1.180.000 |
| Sin computador prendido | Raspberry Pi 5 con kit Hailo | COP 800.000 |

### 11.8 Modelos concretos, si se compra de todas formas

Consultado el 13 de septiembre de 2026. **No pude abrir las fichas de Amazon
desde el entorno de trabajo**, así que de cada una se conocen las
especificaciones que aparecen en el título del producto, y **no el precio, ni
la disponibilidad, ni si envía a Colombia.** Eso hay que verificarlo a mano.

**Primera opción, para distancias de 3 a 12 metros, que es el caso de una
portería o la entrada de un parqueadero.** Anpviz LPR/ANPR, 4MP a 30 fps, lente
motorizado de 2,7 a 13,5 mm, WDR de 120 dB, infrarrojo de 40 metros, IP67, PoE.
`https://www.amazon.com/Anpviz-Recognition-2-7-13-5mm-Motorized-Nightvision/dp/B0H11T45YZ`

**Segunda opción, para 10 a 30 metros, si la cámara tiene que ir lejos.**
Anpviz LPR/ANPR, 4MP a 30 o 60 fps, lente motorizado de 8 a 32 mm, WDR de 140
dB, sensor de 1/1,8 pulgadas, infrarrojo de 100 metros.
`https://www.amazon.com/License-Recognition-Camera-8-32mm-Vision/dp/B0H2MGXGDD`
Los 60 fps de esta son una ventaja real para vehículos rápidos, por lo de la
sección 11.3.

**La de referencia profesional**, más cara y la que usan las instalaciones de
verdad, es la Hikvision iDS-2CD7A46G0/P-IZHS de 8 a 32 mm. Esa **se consigue en
Colombia con distribuidor local**, lo que trae garantía y soporte que una
importación no da.

**Por qué cualquiera de las tres sirve sin haber medido la distancia:** las
tres tienen **lente motorizado varifocal**, o sea que el zoom se ajusta después
de instalada, mirando la imagen en el sitio. Eso es exactamente el seguro
contra el error de la sección 11.1. Un lente fijo obliga a acertar la distancia
antes de comprar; uno motorizado se corrige en el poste.

**Antes de pagar, dos verificaciones:**

1. **Envío a Colombia.** Poner el artículo en el carrito y cambiar la dirección
   de entrega a Colombia. Si no aplica, Amazon lo dice con un aviso de que no
   se puede enviar a esa ubicación. Muchos artículos de vendedores externos son
   solo Estados Unidos.
2. **El costo real contra el local.** Una importación suma el depósito de tasas
   de importación, el IVA del 19 por ciento y el arancel que corresponda, que
   en conjunto pueden agregar cerca de un 30 por ciento. Con eso encima, un
   distribuidor Hikvision o Dahua en Colombia puede salir igual o más barato, y
   además responde por la garantía.

### 11.7 Por qué no comprar nada todavía

El lente se escoge con la distancia medida, y esa distancia no se sabe hasta
pararse en el sitio donde iría la cámara. Comprar antes de la Fase 0 es
escoger el lente a ojo, que es exactamente el error de 11.1. La secuencia
correcta es: grabar con el celular, medir el ancho de placa que queda, y **de
esa medición sale el lente que hay que pedir**, no al revés.

---

## 12. ¿Es el alcance el adecuado?

### 12.1 La respuesta corta

**Técnicamente sí, comercialmente no.** El alcance está bien armado como
ejercicio de ingeniería y mal medido como producto: tiene de más la parte
difícil que no paga, y de menos la parte fácil que sí. Las dos correcciones
están abajo.

### 12.2 Lo que de verdad se está construyendo

Conviene nombrarlo bien, porque el nombre cambia la decisión. Esto no es un
detector de carros. **Es un convertidor de video en tabla**: entra una hora de
grabación y sale un CSV con qué pasó, cuándo y cuántas veces. La detección es
una etapa de esa cadena, no el producto.

Y el detector no es el activo. YOLO está preentrenado, es gratuito y cualquiera
lo corre en diez líneas. **Todo lo valioso está en la parte aburrida:** poner
la cámara donde toca, consolidar los eventos en objetos únicos, y entregar algo
que alguien lea. Optimizar el modelo es el eje equivocado.

Eso además juega a su favor: la parte de ingeniería de datos, que es la que
convierte eventos en una tabla y en un informe, es exactamente su oficio. La
parte de visión es la commodity.

### 12.3 Dónde está mal medido el alcance hoy

**Sobra la parte de placas, y sobra por una razón dura.** Leerlas es lo más
difícil del proyecto, lo que obliga a la compra de COP 1.700.000 a 3.400.000
por punto, y lo único que ya es un producto terminado de estantería: Plate
Recognizer cobra USD 35 al mes por cámara, y las cámaras LPR de Hikvision o
Dahua traen el reconocimiento incorporado. **Construir desde cero algo que
cuesta USD 35 al mes solo se justifica si el volumen es enorme o si el dato no
puede salir del sitio.** Ninguna de las dos aplica hoy.

**Falta la salida que alguien compra.** Un CSV de detecciones no es un
entregable, es materia prima. Lo que se paga es el conteo por movimiento, la
hora pico, la composición vehicular. Eso está a unas 150 o 200 líneas del
seguimiento que ya está escrito, y es la brecha más rentable del proyecto.

### 12.4 Los usos que valen más, ordenados

Todos corren sobre el mismo pipeline de la Fase 1. Cambian las clases, la
cámara y el informe, no el motor.

**1. Aforos vehiculares para estudios de tránsito.** El mejor encaje, y por
lejos. Hoy ese trabajo lo hace una persona parada en una esquina con un
contador manual, por turnos de ocho o doce horas, y se factura por punto y por
día. El comprador ya existe, ya paga la versión manual, y no hay que
convencerlo del problema. El entregable es un conteo clasificado por tipo de
vehículo y por movimiento de giro, o sea un informe con tablas, que es
justamente lo que usted hace. **No necesita placas ni cámara cara**, porque
contar un bus no exige leerle nada.

**2. Seguridad industrial: casco, chaleco, zona restringida.** Ticket más alto
y comprador con presión regulatoria de la ARL. La misma cadena, con clases
distintas. El costo es que exige entrenar con imágenes propias, no sirve el
modelo de fábrica, y eso son semanas, no días.

**3. Aforo y permanencia en comercio.** Cuántos entran, a qué hora, cuánto se
quedan. Técnicamente lo más fácil de todo, casi gratis en hardware. El problema
no es técnico: es que hay que vender local por local y el ticket es bajo.

**4. Conteo de inventario o de piezas en bodega.** Encargo puntual, bien pago,
sin recurrencia.

**5. Control de acceso vehicular a conjuntos.** El que parecía el destino
natural y es el peor de los cinco, por lo de 12.3: compite contra hardware que
ya lo trae de fábrica.

### 12.5 Qué cambiaría del plan

1. **Dejar la Fase 1 intacta.** Es el activo reutilizable y sirve a los cinco
   usos.
2. **Bajar las placas de Fase 2 a opcional, y si algún día se necesitan,
   comprarlas en vez de construirlas.** USD 35 al mes contra semanas de trabajo
   propio.
3. **Meter una Fase 2 nueva: línea de aforo y matriz de giros.** Que el usuario
   dibuje una línea sobre el primer frame, y el sistema cuente cada vez que un
   objeto rastreado la cruza, con dirección y clase. Con dos o más líneas sale
   la matriz origen destino, que es el corazón de un estudio de tránsito. Son
   unas 150 líneas sobre el seguimiento que ya existe. **Es el cambio con mejor
   relación entre esfuerzo y valor de todo el documento.**
4. **Meter una Fase 3 nueva: el informe.** Conteo por intervalos de 15 minutos,
   hora pico, composición por clase, y una hoja lista para entregar. Sin esto
   no hay producto, hay script.

### 12.6 Las cuatro preguntas, sobre el alcance ampliado

**Plata.** Con el alcance de hoy, ninguna, y ya estaba dicho en 6.1. Con
aforos, sí hay: reemplaza un costo laboral que alguien ya está pagando. **Pero
eso todavía no es un hecho verificado, es una hipótesis mía**, y hay que
confirmarla antes de escribir otra línea.

**Volumen.** No depende de publicar. Pasa.

**Activo si muere.** Mejora respecto al alcance anterior: queda un pipeline que
sirve a cinco mercados en vez de uno, más el dato medido.

**Criterio de matar.** Se mantiene el 15 de octubre de 2026 de la sección 6.4
para las placas, y se agrega uno para la dirección nueva: si al 30 de
septiembre de 2026 ninguna firma de estudios de tránsito confirma que paga por
aforos, la hipótesis de 12.4 queda desmentida y el proyecto vuelve a ser
aprendizaje, sin más inversión de tiempo.

### 12.7 Lo que NO hay que hacer

1. **No ampliar a reconocimiento facial.** Cambia el régimen legal completo, de
   dato personal a dato sensible y biométrico, y con eso el proyecto pasa de
   necesitar un aviso a necesitar un abogado.
2. **No perseguir un modelo mejor.** El modelo de fábrica ya acierta más que la
   calidad del video que va a recibir. El cuello de botella es la cámara y el
   sitio.
3. **No construir cinco usos a la vez.** El pipeline es común, pero cada informe
   es otro producto.
4. **No comprar la cámara LPR antes de tener el primer comprador.** Es la única
   compra grande del proyecto y es la que menos se necesita.

---

## 13. Cómo llega el video al computador y cuánta memoria pide

### 13.1 Las tres rutas de entrada

**Ruta A. Celular, que es la de las fases 0 y 1.** Se graba en el celular y el
archivo se pasa al computador **por cable USB**, arrastrándolo desde la carpeta
DCIM. Nada más.

**Con una advertencia que vale todo el proyecto: no mandar el video por
WhatsApp.** WhatsApp recomprime a resolución y tasa de bits mucho más bajas, y
lo primero que se pierde en esa recompresión es justamente el detalle fino de
la placa, que son los píxeles por los que se compró el trípode. Lo mismo aplica
a Telegram como foto o a cualquier cosa que diga comprimir. Si tiene que ir por
nube, Google Drive subiendo el archivo como archivo, nunca como foto, y en
calidad original.

Segunda razón para el cable: una jornada de 12 horas son unos 30 GB. Por USB 3
eso se copia en unos 4 minutos. Por una subida doméstica de 20 Mbps se demora
más de 3 horas.

**Ruta B. Cámara IP, que es la del Nivel 2.** Aquí no hay que pasar ningún
archivo, y esa es la ventaja. Una cámara IP publica lo que ve como un flujo
RTSP en la red local, con una dirección del estilo
`rtsp://usuario:clave@192.168.1.50:554/stream1`. **El código no cambia:**
OpenCV abre esa dirección igual que abre un archivo, cambiando una sola línea.

    cv2.VideoCapture("video.mp4")      # archivo
    cv2.VideoCapture("rtsp://...")     # cámara en vivo

El cable físico es uno solo, UTP, y con PoE lleva datos y corriente al tiempo
hasta unos 100 metros, así que la cámara no necesita toma de luz propia.

**Ruta C, que es la que sobra.** Tarjeta microSD dentro de la cámara, sacarla a
mano y copiarla. Funciona, pero obliga a que alguien vaya y vuelva, que es
exactamente lo que no queremos. Sirve solo como respaldo si se cae la red.

### 13.2 Cuánto pesa el video

| Fuente | Tasa | Por hora | Por jornada de 12 h |
|---|---|---|---|
| Celular 1080p a 30 fps | 17 Mbps | 7,5 GB | 90 GB |
| Celular 1080p a 60 fps | 30 Mbps | 13,5 GB | 162 GB |
| Celular 4K a 30 fps | 50 Mbps | 22,5 GB | 270 GB |
| Cámara IP 4MP en H.265 | 5 Mbps | 2,3 GB | 27 GB |
| Cámara IP 4MP en H.264 | 10 Mbps | 4,5 GB | 54 GB |

Dos lecturas. La primera: **el celular pesa tres a seis veces más que la cámara
IP** para menos calidad útil, porque graba con códec y tasa pensados para ver,
no para archivar. La segunda: los 60 segundos de la Fase 0 pesan 225 MB, o sea
nada, y no hay que preocuparse por disco hasta que haya jornadas completas.

Para grabación continua de una cámara IP en H.265: 55 GB al día, 1,6 TB al mes.
Un disco de 4 TB, entre COP 340.000 y 420.000, aguanta dos meses de una cámara
o dos semanas de cuatro.

### 13.3 La decisión que ahorra el disco entero

**Si lo que importa es el conteo, el video no se guarda.** Se procesa por
bloques y se descarta, y queda solo la tabla.

| Qué se guarda | Por hora |
|---|---|
| El video | 2.300 MB |
| El CSV de detecciones | 8,6 MB |
| Solo recortes de placa en JPEG | 10 MB por cada 1.000 vehículos |

La tabla pesa **más de 250 veces menos que el video**. Un año entero de conteo
cabe en lo que ocupa un día de grabación. Lo razonable es guardar la tabla
siempre, los recortes de los casos dudosos, y el video solo de los minutos
alrededor de algo que haya que mirar con ojos.

### 13.4 Cuánta RAM pide el programa

Aquí memoria significa otra cosa, y la respuesta es tranquilizadora: **el
pipeline nunca carga el video entero.** Lee frame por frame y suelta el
anterior. Un frame de 1080p ocupa 6,2 MB en memoria, y es lo único del video
que está adentro en un instante dado.

| Configuración | RAM del proceso |
|---|---|
| YOLO nano en CPU, 1080p | 1,5 a 2 GB |
| YOLO medium en CPU | 3 a 4 GB |
| En GPU, YOLO nano a 640 px | menos de 2 GB de VRAM |

Con 8 GB de RAM va bien y con 16 GB sobra. Cualquier computador de trabajo de
los últimos años sirve. La GPU importa para la velocidad, no para que quepa.

### 13.5 El defecto que esta pregunta destapó

Hay un problema real en el código ya escrito, y conviene dejarlo anotado en vez
de descubrirlo con el disco lleno. En `modelos.py`, la clase `Resumen` tiene un
campo `detecciones` que es una lista, y el pipeline tal como está pensado la
iría llenando hasta el final del video.

Una jornada de 12 horas analizando uno de cada tres frames son 432.000 frames,
y con tres objetos promedio por frame, **1,3 millones de detecciones acumuladas
en memoria**, que son del orden de 400 MB a 1 GB de objetos de Python vivos sin
ninguna razón.

**Corrección para la Fase 1:** el campo `detecciones` se usa solo para videos
cortos y pruebas, y el camino normal escribe cada detección al CSV apenas
ocurre y mantiene en memoria únicamente los contadores y la votación de placas,
que son unos pocos kilobytes. Con eso el consumo se vuelve constante y da igual
si el video dura un minuto o doce horas. Esto ya estaba insinuado en el punto 3
de la sección 5, pero no estaba escrito como requisito, y ahora lo está.

---

## 14. El accionable, uno solo

**Llamar a dos firmas de estudios de tránsito o movilidad y preguntar qué
pagan hoy por un día de aforo vehicular en un punto.** Dos llamadas, quince
minutos, cero pesos. Si pagan, la sección 12.4 deja de ser hipótesis mía y el
proyecto tiene comprador antes de tener producto, que es el orden correcto. Si
no pagan, se evita construir cuatro fases para nadie.

El trípode de COP 40.000 a 80.000 y los 60 segundos de grabación siguen siendo
el prerrequisito técnico, y la Fase 1 puede arrancar en paralelo porque sirve
en los cinco escenarios. Pero la llamada va primero, porque es la única que
puede cambiar la respuesta a todo lo demás.
