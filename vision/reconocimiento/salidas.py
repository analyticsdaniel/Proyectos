"""Escritura de resultados: CSV incremental, JSON de resumen y video anotado.

El CSV se escribe deteccion por deteccion, apenas ocurre, y no al final. Esa es
la correccion de la seccion 13.5 del plan: una jornada de 12 horas son del orden
de 1,3 millones de detecciones, y acumularlas en memoria son cientos de megas
sin ninguna razon. Escribiendo al vuelo, el consumo es constante y da igual si
el video dura un minuto o doce horas.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Optional

import cv2
import numpy as np

from .config import Config
from .modelos import Deteccion, Resumen

COLUMNAS_CSV = (
    "video",
    "frame",
    "segundo",
    "clase",
    "track_id",
    "x1",
    "y1",
    "x2",
    "y2",
    "ancho",
    "alto",
    "confianza",
)


class EscritorCSV:
    """Escribe una fila por deteccion y vacia el buffer cada pocas filas.

    Se vacia seguido a proposito: si el proceso se cae a mitad de un video de
    dos horas, lo escrito hasta ese momento ya esta en disco.
    """

    def __init__(self, ruta: Path, video: str, cada: int = 50, reanudar: bool = False):
        self.ruta = Path(ruta)
        self.video = video
        self.cada = max(1, cada)
        self._desde_ultimo = 0
        self.filas_escritas = 0

        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        nuevo = reanudar is False or not self.ruta.exists()
        self._archivo = open(self.ruta, "w" if nuevo else "a", newline="", encoding="utf-8")
        self._csv = csv.writer(self._archivo)
        if nuevo:
            self._csv.writerow(COLUMNAS_CSV)
            self._archivo.flush()

    def escribir(self, detecciones: Iterable[Deteccion]) -> None:
        for d in detecciones:
            x1, y1, x2, y2 = d.bbox
            self._csv.writerow(
                (
                    self.video,
                    d.frame,
                    f"{d.segundo:.3f}",
                    d.clase,
                    "" if d.track_id is None else d.track_id,
                    x1,
                    y1,
                    x2,
                    y2,
                    d.ancho,
                    d.alto,
                    f"{d.confianza:.4f}",
                )
            )
            self.filas_escritas += 1
            self._desde_ultimo += 1
        if self._desde_ultimo >= self.cada:
            self._archivo.flush()
            self._desde_ultimo = 0

    def cerrar(self) -> None:
        if not self._archivo.closed:
            self._archivo.flush()
            self._archivo.close()

    def __enter__(self) -> "EscritorCSV":
        return self

    def __exit__(self, *_) -> None:
        self.cerrar()


class EscritorVideo:
    """Video anotado con las cajas, la clase y el identificador de seguimiento.

    Es para revisar a ojo los casos dudosos, no para archivar: pesa como el
    original. Si el codec no esta disponible avisa y sigue sin video, porque
    perder la anotacion no justifica perder el analisis entero.
    """

    def __init__(self, ruta: Path, fps: float, ancho: int, alto: int, config: Config):
        self.ruta = Path(ruta)
        self.config = config
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        fps_seguro = fps if fps and fps > 0 else 25.0
        self._video = cv2.VideoWriter(
            str(self.ruta), cv2.VideoWriter_fourcc(*"mp4v"), fps_seguro, (ancho, alto)
        )
        self.activo = self._video.isOpened()
        if not self.activo:
            print(f"AVISO: no se pudo abrir el video de salida {self.ruta}. Se sigue sin el.")

    def escribir(self, frame: np.ndarray, detecciones: Iterable[Deteccion]) -> None:
        if not self.activo:
            return
        self._video.write(self.anotar(frame, detecciones))

    def anotar(self, frame: np.ndarray, detecciones: Iterable[Deteccion]) -> np.ndarray:
        salida = frame.copy()
        for d in detecciones:
            x1, y1, x2, y2 = d.bbox
            color = self.config.color_de(d.clase)
            cv2.rectangle(salida, (x1, y1), (x2, y2), color, 2)
            etiqueta = d.clase if d.track_id is None else f"{d.clase} #{d.track_id}"
            etiqueta = f"{etiqueta} {d.confianza:.2f}"
            (ancho_texto, alto_texto), _ = cv2.getTextSize(
                etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                salida, (x1, max(0, y1 - alto_texto - 6)), (x1 + ancho_texto + 4, y1), color, -1
            )
            cv2.putText(
                salida,
                etiqueta,
                (x1 + 2, max(10, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        return salida

    def cerrar(self) -> None:
        if self.activo:
            self._video.release()
            self.activo = False


def escribir_resumen(ruta: Path, resumen: Resumen, extra: Optional[dict] = None) -> Path:
    """Guarda el resumen en JSON. Es lo que se lee sin abrir el CSV."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = resumen.como_dict()
    if extra:
        datos.update(extra)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    return ruta
