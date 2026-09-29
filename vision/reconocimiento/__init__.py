"""Reconocimiento de personas, vehiculos y placas en video."""

from .config import Config
from .modelos import Deteccion, EventoPlaca, Resumen

__all__ = ["Config", "Deteccion", "EventoPlaca", "Resumen"]
