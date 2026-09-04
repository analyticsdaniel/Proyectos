"""Estructuras de datos que viajan entre las etapas del pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Deteccion:
    """Un objeto detectado en un frame concreto."""

    clase: str
    confianza: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2 en pixeles
    frame: int
    segundo: float
    track_id: Optional[int] = None

    @property
    def ancho(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def alto(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> int:
        return max(0, self.ancho) * max(0, self.alto)

    @property
    def centro(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)


@dataclass
class LecturaPlaca:
    """Una lectura cruda de placa en un frame. Aun no es la placa final."""

    texto: str
    confianza: float
    bbox: tuple[int, int, int, int]
    frame: int
    segundo: float
    track_vehiculo: Optional[int] = None


@dataclass
class EventoPlaca:
    """Placa consolidada para un vehiculo, tras votar entre todas sus lecturas."""

    placa: str
    track_vehiculo: Optional[int]
    clase_vehiculo: str
    lecturas: int
    confianza: float
    primer_segundo: float
    ultimo_segundo: float


@dataclass
class Resumen:
    """Resultado completo del analisis de un video."""

    video: str
    frames_totales: int
    frames_analizados: int
    fps: float
    duracion_segundos: float
    conteo_por_clase: dict[str, int] = field(default_factory=dict)
    unicos_por_clase: dict[str, int] = field(default_factory=dict)
    placas: list[EventoPlaca] = field(default_factory=list)
    detecciones: list[Deteccion] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "video": self.video,
            "frames_totales": self.frames_totales,
            "frames_analizados": self.frames_analizados,
            "fps": round(self.fps, 3),
            "duracion_segundos": round(self.duracion_segundos, 2),
            "detecciones_por_clase": self.conteo_por_clase,
            "objetos_unicos_por_clase": self.unicos_por_clase,
            "placas": [
                {
                    "placa": p.placa,
                    "track_vehiculo": p.track_vehiculo,
                    "clase_vehiculo": p.clase_vehiculo,
                    "lecturas": p.lecturas,
                    "confianza": round(p.confianza, 3),
                    "primer_segundo": round(p.primer_segundo, 2),
                    "ultimo_segundo": round(p.ultimo_segundo, 2),
                }
                for p in self.placas
            ],
        }
