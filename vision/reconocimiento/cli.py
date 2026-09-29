"""Linea de comandos: un video entra, tres archivos salen.

    python -m reconocimiento grabacion.mp4
    python -m reconocimiento grabacion.mp4 --salto 3 --dispositivo 0
    python -m reconocimiento rtsp://usuario:clave@192.168.1.50:554/stream1

El caso de salon de clase se corre con --clases person, que apaga los vehiculos
y hace el analisis mas rapido.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import CLASES_PERSONAS, CLASES_VEHICULOS, Config
from .pipeline import VideoNoAbre, analizar_video


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reconocimiento",
        description=(
            "Convierte un video en una tabla: que objetos aparecieron, cuando "
            "y cuantos unicos hubo."
        ),
    )
    parser.add_argument("video", help="Archivo de video o direccion RTSP de una camara.")
    parser.add_argument(
        "--salida", default="salidas", help="Carpeta donde quedan CSV, JSON y video anotado."
    )
    parser.add_argument(
        "--modelo", default="yolov8n.pt", help="Pesos YOLO. yolov8n es el mas rapido."
    )
    parser.add_argument(
        "--dispositivo",
        default="cpu",
        help="'cpu', o '0' para la primera GPU NVIDIA. Con GPU va varias veces mas rapido.",
    )
    parser.add_argument(
        "--salto",
        type=int,
        default=1,
        help="Analizar uno de cada N frames. 3 es tres veces mas rapido y se pierde muy poco.",
    )
    parser.add_argument(
        "--confianza", type=float, default=0.35, help="Confianza minima para aceptar una deteccion."
    )
    parser.add_argument(
        "--clases",
        nargs="+",
        default=list(CLASES_PERSONAS + CLASES_VEHICULOS),
        help="Clases de interes, en ingles de COCO. Ejemplo para un salon: --clases person",
    )
    parser.add_argument(
        "--max-frames", type=int, default=None, help="Cortar a los primeros N frames analizados."
    )
    parser.add_argument(
        "--sin-video", action="store_true", help="No generar el video anotado. Va mas rapido."
    )
    parser.add_argument(
        "--sin-seguimiento",
        action="store_true",
        help="Apagar el rastreador. Sin el no hay conteo de unicos.",
    )
    parser.add_argument(
        "--reanudar",
        action="store_true",
        help="Seguir donde quedo la corrida anterior, en vez de empezar de cero.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)

    config = Config(
        modelo=args.modelo,
        confianza_min=args.confianza,
        dispositivo=args.dispositivo,
        clases_interes=tuple(args.clases),
        salto_frames=max(1, args.salto),
        max_frames=args.max_frames,
        rastrear=not args.sin_seguimiento,
        guardar_video=not args.sin_video,
        carpeta_salida=args.salida,
    )

    try:
        resumen = analizar_video(args.video, config=config, reanudar=args.reanudar)
    except VideoNoAbre as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    carpeta = Path(config.carpeta_salida)
    nombre = Path(args.video).stem
    print()
    print(f"Video:             {resumen.video}")
    print(f"Frames analizados: {resumen.frames_analizados} de {resumen.frames_totales}")
    print(f"Duracion:          {resumen.duracion_segundos:.1f} segundos a {resumen.fps:.1f} fps")
    print()
    print("Objetos unicos por clase:")
    if resumen.unicos_por_clase:
        for clase, cuantos in resumen.unicos_por_clase.items():
            detecciones = resumen.conteo_por_clase.get(clase, 0)
            print(f"  {clase:<12} {cuantos:>5}   ({detecciones} detecciones)")
    else:
        print("  ninguno")
    print()
    print(f"CSV:     {carpeta / (nombre + '.detecciones.csv')}")
    print(f"Resumen: {carpeta / (nombre + '.resumen.json')}")
    if config.guardar_video:
        print(f"Video:   {carpeta / (nombre + '.anotado.mp4')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
