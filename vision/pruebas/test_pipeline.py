"""Pruebas del recorrido del video, con video sintetico y detector de mentiras.

No cargan YOLO ni bajan pesos: el detector se reemplaza por uno falso que
devuelve cajas conocidas. Asi se prueba lo que de verdad puede fallar, que es el
conteo, el CSV incremental y la reanudacion, y no el modelo, que ya viene
probado de fabrica.

Necesitan OpenCV, que es lo unico que se usa para fabricar el video de prueba.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2", reason="Estas pruebas necesitan OpenCV")

from reconocimiento.config import Config
from reconocimiento.modelos import Deteccion
from reconocimiento.pipeline import VideoNoAbre, analizar_video

FRAMES = 30
ANCHO, ALTO = 320, 240


class DetectorFalso:
    """Devuelve una persona que cruza el frame y un carro que aparece tarde.

    Personas: siempre el mismo track, o sea una sola persona unica.
    Carros: dos tracks distintos en la segunda mitad del video.
    """

    def __init__(self):
        self.llamadas = 0

    def reiniciar(self) -> None:
        self.llamadas = 0

    def detectar(self, frame, indice: int, segundo: float) -> list[Deteccion]:
        self.llamadas += 1
        x = min(indice * 5, ANCHO - 40)
        detecciones = [
            Deteccion(
                clase="person",
                confianza=0.9,
                bbox=(x, 40, x + 30, 120),
                frame=indice,
                segundo=segundo,
                track_id=1,
            )
        ]
        if indice >= FRAMES // 2:
            track = 2 if indice < (FRAMES * 3) // 4 else 3
            detecciones.append(
                Deteccion(
                    clase="car",
                    confianza=0.8,
                    bbox=(10, 150, 90, 210),
                    frame=indice,
                    segundo=segundo,
                    track_id=track,
                )
            )
        return detecciones


@pytest.fixture
def video(tmp_path: Path) -> Path:
    ruta = tmp_path / "prueba.mp4"
    escritor = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (ANCHO, ALTO))
    assert escritor.isOpened(), "OpenCV no pudo crear el video de prueba"
    for i in range(FRAMES):
        frame = np.full((ALTO, ANCHO, 3), i * 3 % 255, dtype=np.uint8)
        escritor.write(frame)
    escritor.release()
    return ruta


def configuracion(tmp_path: Path, **cambios) -> Config:
    base = dict(carpeta_salida=str(tmp_path / "salidas"), guardar_video=False)
    base.update(cambios)
    return Config(**base)


def filas_csv(ruta: Path) -> list[dict]:
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


class TestAnalizarVideo:
    def test_una_fila_de_csv_por_deteccion(self, video, tmp_path):
        config = configuracion(tmp_path)
        resumen = analizar_video(video, config=config, detector=DetectorFalso(), mostrar_avance=False)

        filas = filas_csv(Path(config.carpeta_salida) / "prueba.detecciones.csv")
        assert len(filas) == sum(resumen.conteo_por_clase.values())
        assert filas[0]["clase"] == "person"
        assert filas[0]["video"] == "prueba.mp4"
        assert int(filas[0]["ancho"]) == 30

    def test_cuenta_los_unicos_por_identificador_y_no_por_deteccion(self, video, tmp_path):
        config = configuracion(tmp_path)
        resumen = analizar_video(video, config=config, detector=DetectorFalso(), mostrar_avance=False)

        assert resumen.unicos_por_clase == {"car": 2, "person": 1}
        assert resumen.conteo_por_clase["person"] == FRAMES
        assert resumen.frames_analizados == FRAMES

    def test_el_salto_de_frames_analiza_menos_y_cuenta_los_mismos_unicos(self, video, tmp_path):
        config = configuracion(tmp_path, salto_frames=3)
        resumen = analizar_video(video, config=config, detector=DetectorFalso(), mostrar_avance=False)

        assert resumen.frames_analizados == 10
        assert resumen.unicos_por_clase == {"car": 2, "person": 1}

    def test_escribe_el_json_de_resumen_con_lo_que_se_lee_sin_abrir_el_csv(self, video, tmp_path):
        config = configuracion(tmp_path)
        analizar_video(video, config=config, detector=DetectorFalso(), mostrar_avance=False)

        datos = json.loads(
            (Path(config.carpeta_salida) / "prueba.resumen.json").read_text(encoding="utf-8")
        )
        assert datos["objetos_unicos_por_clase"] == {"car": 2, "person": 1}
        assert datos["video"] == "prueba.mp4"
        assert datos["frames_analizados"] == FRAMES
        assert "advertencia_conteo" in datos

    def test_no_acumula_detecciones_en_memoria_salvo_que_se_pida(self, video, tmp_path):
        config = configuracion(tmp_path)
        resumen = analizar_video(video, config=config, detector=DetectorFalso(), mostrar_avance=False)
        assert resumen.detecciones == []

        resumen_corto = analizar_video(
            video,
            config=configuracion(tmp_path / "otra", max_frames=3),
            detector=DetectorFalso(),
            guardar_detecciones=True,
            mostrar_avance=False,
        )
        assert len(resumen_corto.detecciones) == 3

    def test_genera_el_video_anotado_cuando_se_pide(self, video, tmp_path):
        config = configuracion(tmp_path, guardar_video=True)
        analizar_video(video, config=config, detector=DetectorFalso(), mostrar_avance=False)

        anotado = Path(config.carpeta_salida) / "prueba.anotado.mp4"
        assert anotado.exists() and anotado.stat().st_size > 0

    def test_video_que_no_existe_falla_de_una_y_con_mensaje_claro(self, tmp_path):
        with pytest.raises(VideoNoAbre) as error:
            analizar_video(tmp_path / "no_esta.mp4", config=configuracion(tmp_path))
        assert "No existe el archivo" in str(error.value)


class TestReanudar:
    def test_se_interrumpe_y_sigue_donde_iba(self, video, tmp_path):
        salidas = str(tmp_path / "salidas")

        analizar_video(
            video,
            config=configuracion(tmp_path, carpeta_salida=salidas, max_frames=10),
            detector=DetectorFalso(),
            mostrar_avance=False,
        )
        filas_primera = filas_csv(Path(salidas) / "prueba.detecciones.csv")
        assert len(filas_primera) == 10  # solo personas en la primera mitad

        resumen = analizar_video(
            video,
            config=configuracion(tmp_path, carpeta_salida=salidas),
            detector=DetectorFalso(),
            reanudar=True,
            mostrar_avance=False,
        )

        filas = filas_csv(Path(salidas) / "prueba.detecciones.csv")
        assert len(filas) == sum(resumen.conteo_por_clase.values())
        assert resumen.frames_analizados == FRAMES
        assert resumen.unicos_por_clase == {"car": 2, "person": 1}
        assert [f["frame"] for f in filas][:3] == ["0", "1", "2"]

    def test_el_estado_queda_en_disco_para_poder_reanudar(self, video, tmp_path):
        config = configuracion(tmp_path, max_frames=5)
        analizar_video(video, config=config, detector=DetectorFalso(), mostrar_avance=False)

        estado = json.loads(
            (Path(config.carpeta_salida) / "prueba.estado.json").read_text(encoding="utf-8")
        )
        assert estado["frames_analizados"] == 5
        assert estado["frames_leidos"] == 5
        assert "person:1" in estado["vistos"]
