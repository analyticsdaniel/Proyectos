"""Detectores de objetos. El pipeline solo conoce la interfaz, no el modelo."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from .config import Config
from .modelos import Deteccion


class Detector(Protocol):
    """Contrato minimo: entra un frame, salen detecciones."""

    def detectar(self, frame: np.ndarray, indice: int, segundo: float) -> list[Deteccion]:
        ...

    def reiniciar(self) -> None:
        """Se llama al empezar un video nuevo, para soltar el estado del rastreador."""


class DetectorYOLO:
    """Envuelve un modelo YOLO de ultralytics, con seguimiento opcional.

    El import de ultralytics es perezoso a proposito: asi los tests y las
    utilidades de texto corren sin tener instalado torch.
    """

    def __init__(self, config: Config):
        from ultralytics import YOLO  # import perezoso

        self.config = config
        self.modelo = YOLO(config.modelo)
        self.nombres: dict[int, str] = dict(self.modelo.names)
        self._indices_interes = [
            idx
            for idx, nombre in self.nombres.items()
            if nombre in config.clases_interes
        ] or None

    def reiniciar(self) -> None:
        if hasattr(self.modelo, "predictor") and self.modelo.predictor is not None:
            self.modelo.predictor.trackers = None
            self.modelo.predictor = None

    def detectar(self, frame: np.ndarray, indice: int, segundo: float) -> list[Deteccion]:
        comunes = dict(
            conf=self.config.confianza_min,
            iou=self.config.iou,
            imgsz=self.config.imgsz,
            device=self.config.dispositivo,
            classes=self._indices_interes,
            verbose=False,
        )
        if self.config.rastrear:
            resultados = self.modelo.track(
                frame, persist=True, tracker=self.config.tracker, **comunes
            )
        else:
            resultados = self.modelo.predict(frame, **comunes)

        return self._a_detecciones(resultados[0], indice, segundo)

    def _a_detecciones(self, resultado, indice: int, segundo: float) -> list[Deteccion]:
        cajas = getattr(resultado, "boxes", None)
        if cajas is None or len(cajas) == 0:
            return []

        xyxy = cajas.xyxy.cpu().numpy()
        confianzas = cajas.conf.cpu().numpy()
        clases = cajas.cls.cpu().numpy().astype(int)
        ids = (
            cajas.id.cpu().numpy().astype(int)
            if getattr(cajas, "id", None) is not None
            else [None] * len(clases)
        )

        detecciones: list[Deteccion] = []
        for caja, conf, cls, track_id in zip(xyxy, confianzas, clases, ids):
            nombre = self.nombres.get(int(cls), str(cls))
            if nombre not in self.config.clases_interes:
                continue
            x1, y1, x2, y2 = (int(round(v)) for v in caja)
            detecciones.append(
                Deteccion(
                    clase=nombre,
                    confianza=float(conf),
                    bbox=(x1, y1, x2, y2),
                    frame=indice,
                    segundo=segundo,
                    track_id=None if track_id is None else int(track_id),
                )
            )
        return detecciones


def construir_detector(config: Config) -> Detector:
    return DetectorYOLO(config)
