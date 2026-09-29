"""Reconocimiento de personas, vehiculos y placas en video.

Aqui solo se exponen las estructuras y la configuracion, que no dependen de
OpenCV ni de torch. El pipeline se importa aparte, `from reconocimiento.pipeline
import analizar_video`, para que las pruebas de texto corran sin tener nada de
vision instalado.
"""

from .config import Config
from .modelos import Deteccion, EventoPlaca, Resumen

__all__ = ["Config", "Deteccion", "EventoPlaca", "Resumen"]
