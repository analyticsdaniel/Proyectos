"""Parametros del analisis. Todo lo ajustable vive aqui."""

from __future__ import annotations

from dataclasses import dataclass, field

# Clases del dataset COCO que interesan en video de calle o de patio.
CLASES_PERSONAS = ("person",)
CLASES_VEHICULOS = ("car", "motorcycle", "bus", "truck", "bicycle")


@dataclass
class Config:
    # --- Deteccion ---
    modelo: str = "yolov8n.pt"
    """Pesos YOLO. yolov8n es el mas rapido; yolov8s/m/l aciertan mas y van mas lento."""

    confianza_min: float = 0.35
    iou: float = 0.5
    imgsz: int = 640
    dispositivo: str = "cpu"
    """'cpu', '0' para la primera GPU, 'mps' en Mac."""

    clases_interes: tuple[str, ...] = CLASES_PERSONAS + CLASES_VEHICULOS

    # --- Seguimiento ---
    rastrear: bool = True
    """Con seguimiento, cada objeto recibe un id estable y se cuenta una sola vez."""

    tracker: str = "bytetrack.yaml"

    # --- Muestreo de frames ---
    salto_frames: int = 1
    """1 analiza todos los frames. 3 analiza uno de cada tres: tres veces mas rapido."""

    max_frames: int | None = None
    """Corta el analisis a los primeros N frames analizados. Util para probar."""

    # --- Placas ---
    leer_placas: bool = True
    modelo_placas: str | None = None
    """Pesos YOLO entrenados para placas. Si es None se usa el detector por contornos."""

    confianza_placa: float = 0.30
    confianza_ocr_min: float = 0.35
    min_lecturas_placa: int = 2
    """Cuantas lecturas coincidentes se exigen antes de dar una placa por buena."""

    formatos_placa: tuple[str, ...] = ("carro_co", "moto_co")
    idiomas_ocr: tuple[str, ...] = ("en",)

    # --- Salidas ---
    guardar_video: bool = True
    guardar_recortes_placa: bool = False
    carpeta_salida: str = "salidas"

    # --- Presentacion ---
    colores: dict[str, tuple[int, int, int]] = field(
        default_factory=lambda: {
            "person": (60, 180, 75),
            "car": (0, 130, 200),
            "motorcycle": (245, 130, 48),
            "bus": (145, 30, 180),
            "truck": (70, 70, 200),
            "bicycle": (128, 128, 0),
            "placa": (255, 225, 25),
        }
    )

    def color_de(self, clase: str) -> tuple[int, int, int]:
        return self.colores.get(clase, (200, 200, 200))
