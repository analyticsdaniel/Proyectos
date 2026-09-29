"""El recorrido del video: abrir, detectar, contar, escribir y poder reanudar.

Esta es la Fase 1 del plan. Sirve igual para la escena de calle y para la de
salon de clase, porque lo unico que cambia entre las dos son las clases que
interesan y el informe final, no el motor.

Tres reglas que vienen de la seccion 5 del plan y que el codigo cumple:

1. El video se valida al abrir y falla con un mensaje claro, no a los 40
   minutos.
2. El CSV se escribe de forma incremental y el estado se guarda cada pocos
   frames, de modo que un proceso caido se reanuda donde iba.
3. Nada se acumula en memoria: ni frames ni detecciones. Solo los contadores y
   el conjunto de identificadores vistos.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2

from .config import Config
from .detectores import Detector, construir_detector
from .modelos import Deteccion, Resumen
from .salidas import EscritorCSV, EscritorVideo, escribir_resumen

GUARDAR_ESTADO_CADA = 100
"""Cada cuantos frames analizados se guarda el punto de reanudacion."""


class VideoNoAbre(RuntimeError):
    """El video no se pudo abrir: codec raro, archivo a medias o ruta mala."""


@dataclass
class Progreso:
    """Lo unico que el pipeline mantiene vivo en memoria mientras corre."""

    frames_leidos: int = 0
    frames_analizados: int = 0
    conteo_por_clase: dict[str, int] = field(default_factory=dict)
    vistos: set[str] = field(default_factory=set)
    """Claves 'clase:track_id'. Un conjunto de cadenas cortas, no de objetos."""

    sin_track_por_clase: dict[str, int] = field(default_factory=dict)
    """Detecciones que llegaron sin identificador de seguimiento."""

    def registrar(self, deteccion: Deteccion) -> None:
        self.conteo_por_clase[deteccion.clase] = self.conteo_por_clase.get(deteccion.clase, 0) + 1
        if deteccion.track_id is None:
            self.sin_track_por_clase[deteccion.clase] = (
                self.sin_track_por_clase.get(deteccion.clase, 0) + 1
            )
        else:
            self.vistos.add(f"{deteccion.clase}:{deteccion.track_id}")

    def unicos_por_clase(self) -> dict[str, int]:
        unicos: dict[str, int] = {}
        for clave in self.vistos:
            clase = clave.rsplit(":", 1)[0]
            unicos[clase] = unicos.get(clase, 0) + 1
        return unicos

    def como_dict(self) -> dict:
        return {
            "frames_leidos": self.frames_leidos,
            "frames_analizados": self.frames_analizados,
            "conteo_por_clase": self.conteo_por_clase,
            "vistos": sorted(self.vistos),
            "sin_track_por_clase": self.sin_track_por_clase,
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Progreso":
        return cls(
            frames_leidos=int(datos.get("frames_leidos", 0)),
            frames_analizados=int(datos.get("frames_analizados", 0)),
            conteo_por_clase=dict(datos.get("conteo_por_clase", {})),
            vistos=set(datos.get("vistos", [])),
            sin_track_por_clase=dict(datos.get("sin_track_por_clase", {})),
        )


def abrir_video(ruta: str | Path) -> cv2.VideoCapture:
    """Abre el video o falla de una, con el motivo dicho en cristiano."""
    ruta = Path(ruta)
    if not str(ruta).lower().startswith(("rtsp://", "http://", "https://")):
        if not ruta.exists():
            raise VideoNoAbre(f"No existe el archivo: {ruta}")
        if ruta.stat().st_size == 0:
            raise VideoNoAbre(f"El archivo esta vacio: {ruta}")

    captura = cv2.VideoCapture(str(ruta))
    if not captura.isOpened():
        raise VideoNoAbre(
            f"OpenCV no pudo abrir {ruta}. Puede ser un codec que no trae, "
            "un archivo a medias o una direccion RTSP mal escrita."
        )
    return captura


def _ruta_estado(carpeta: Path, nombre: str) -> Path:
    return carpeta / f"{nombre}.estado.json"


def analizar_video(
    ruta_video: str | Path,
    config: Optional[Config] = None,
    detector: Optional[Detector] = None,
    reanudar: bool = False,
    guardar_detecciones: bool = False,
    mostrar_avance: bool = True,
) -> Resumen:
    """Recorre el video entero y deja CSV, JSON y, si se pidio, video anotado.

    `guardar_detecciones` llena `Resumen.detecciones` y solo sirve para videos
    cortos y pruebas: ver la seccion 13.5 del plan.
    """
    config = config or Config()
    ruta_video = Path(ruta_video)
    nombre = ruta_video.stem
    carpeta = Path(config.carpeta_salida)
    carpeta.mkdir(parents=True, exist_ok=True)

    captura = abrir_video(ruta_video)
    fps = captura.get(cv2.CAP_PROP_FPS) or 0.0
    frames_totales = int(captura.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    ancho = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    alto = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    ruta_estado = _ruta_estado(carpeta, nombre)
    progreso = Progreso()
    desde_frame = 0
    if reanudar and ruta_estado.exists():
        progreso = Progreso.desde_dict(json.loads(ruta_estado.read_text(encoding="utf-8")))
        desde_frame = progreso.frames_leidos
        captura.set(cv2.CAP_PROP_POS_FRAMES, desde_frame)
        if mostrar_avance:
            print(f"Reanudando {nombre} en el frame {desde_frame}.")

    detector = detector or construir_detector(config)
    if hasattr(detector, "reiniciar") and not reanudar:
        detector.reiniciar()

    csv_salida = EscritorCSV(
        carpeta / f"{nombre}.detecciones.csv", ruta_video.name, reanudar=reanudar
    )
    video_salida = None
    if config.guardar_video and ancho > 0 and alto > 0:
        video_salida = EscritorVideo(
            carpeta / f"{nombre}.anotado.mp4", fps, ancho, alto, config
        )

    detecciones_en_memoria: list[Deteccion] = []
    indice = desde_frame
    comenzo = time.perf_counter()

    try:
        while True:
            if config.max_frames is not None and progreso.frames_analizados >= config.max_frames:
                break
            ok, frame = captura.read()
            if not ok:
                break

            if indice % config.salto_frames == 0:
                segundo = indice / fps if fps > 0 else float(indice)
                detecciones = detector.detectar(frame, indice, segundo)
                for d in detecciones:
                    progreso.registrar(d)
                csv_salida.escribir(detecciones)
                if guardar_detecciones:
                    detecciones_en_memoria.extend(detecciones)
                if video_salida is not None:
                    video_salida.escribir(frame, detecciones)
                progreso.frames_analizados += 1

                if progreso.frames_analizados % GUARDAR_ESTADO_CADA == 0:
                    progreso.frames_leidos = indice + 1
                    ruta_estado.write_text(
                        json.dumps(progreso.como_dict(), ensure_ascii=False), encoding="utf-8"
                    )
                    if mostrar_avance:
                        transcurrido = time.perf_counter() - comenzo
                        hechos = progreso.frames_analizados
                        print(
                            f"  {hechos} frames analizados, "
                            f"{hechos / max(transcurrido, 1e-6):.1f} por segundo",
                            flush=True,
                        )
            indice += 1
    finally:
        progreso.frames_leidos = indice
        captura.release()
        csv_salida.cerrar()
        if video_salida is not None:
            video_salida.cerrar()
        ruta_estado.write_text(
            json.dumps(progreso.como_dict(), ensure_ascii=False), encoding="utf-8"
        )

    duracion = frames_totales / fps if fps > 0 and frames_totales > 0 else indice / (fps or 1)
    resumen = Resumen(
        video=ruta_video.name,
        frames_totales=frames_totales or indice,
        frames_analizados=progreso.frames_analizados,
        fps=fps,
        duracion_segundos=duracion,
        conteo_por_clase=dict(sorted(progreso.conteo_por_clase.items())),
        unicos_por_clase=dict(sorted(progreso.unicos_por_clase().items())),
        detecciones=detecciones_en_memoria,
    )

    segundos = time.perf_counter() - comenzo
    escribir_resumen(
        carpeta / f"{nombre}.resumen.json",
        resumen,
        extra={
            "salto_frames": config.salto_frames,
            "modelo": config.modelo,
            "dispositivo": config.dispositivo,
            "segundos_de_proceso": round(segundos, 2),
            "frames_por_segundo_de_proceso": round(
                progreso.frames_analizados / max(segundos, 1e-6), 2
            ),
            "detecciones_sin_identificador": dict(sorted(progreso.sin_track_por_clase.items())),
            "advertencia_conteo": (
                "Los unicos se cuentan por identificador de seguimiento. Si el "
                "rastreador pierde un objeto y le cambia el id, ese objeto cuenta "
                "dos veces. Las detecciones sin identificador no entran al conteo "
                "de unicos."
            ),
        },
    )
    return resumen
