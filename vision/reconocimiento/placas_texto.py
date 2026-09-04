"""Limpieza, validacion y votacion de las lecturas de placa.

Este modulo es puro texto: no importa OpenCV ni torch, y por eso es el que
se puede probar en frio. Aqui esta la parte que mas mejora el resultado
final, porque el OCR de una placa en video acierta poco frame a frame pero
mucho cuando se vota entre todas las lecturas del mismo vehiculo.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from .modelos import EventoPlaca, LecturaPlaca

# L = letra, D = digito. Un formato es solo una plantilla de posiciones.
FORMATOS: dict[str, str] = {
    "carro_co": "LLLDDD",   # ABC123
    "moto_co": "LLLDDL",    # ABC12D
    "remolque_co": "LLDDDD",  # AB1234
    "generico_6": "??????",
}

# El OCR confunde estos pares. La correccion depende de si la posicion
# espera letra o digito, por eso hay dos tablas y no una.
A_DIGITO = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1",
                          "S": "5", "B": "8", "Z": "2", "G": "6", "A": "4",
                          "T": "7", "J": "1"})
A_LETRA = str.maketrans({"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z",
                         "6": "G", "4": "A", "7": "T"})

_NO_ALFANUM = re.compile(r"[^A-Z0-9]")


def limpiar(texto: str) -> str:
    """Deja solo letras y digitos en mayuscula."""
    return _NO_ALFANUM.sub("", texto.upper())


def _forzar_formato(candidato: str, plantilla: str) -> str | None:
    """Empuja cada caracter al tipo que la plantilla exige en esa posicion."""
    if len(candidato) != len(plantilla):
        return None
    salida = []
    for caracter, tipo in zip(candidato, plantilla):
        if tipo == "L":
            corregido = caracter.translate(A_LETRA)
            if not corregido.isalpha():
                return None
        elif tipo == "D":
            corregido = caracter.translate(A_DIGITO)
            if not corregido.isdigit():
                return None
        else:
            corregido = caracter
        salida.append(corregido)
    return "".join(salida)


def normalizar_placa(texto: str, formatos: tuple[str, ...] = ("carro_co", "moto_co")) -> str | None:
    """Convierte una lectura cruda de OCR en una placa valida, o None.

    Tolera basura alrededor: si el OCR devuelve 'CO ABC123 X' encuentra
    la ventana que si encaja en alguno de los formatos pedidos.
    """
    limpio = limpiar(texto)
    if not limpio:
        return None

    plantillas = [FORMATOS[f] for f in formatos if f in FORMATOS]
    for plantilla in plantillas:
        largo = len(plantilla)
        if len(limpio) < largo:
            continue
        for inicio in range(len(limpio) - largo + 1):
            forzado = _forzar_formato(limpio[inicio:inicio + largo], plantilla)
            if forzado is not None:
                return forzado
    return None


def distancia(a: str, b: str) -> int:
    """Cuantos caracteres difieren entre dos placas del mismo largo."""
    if len(a) != len(b):
        return max(len(a), len(b))
    return sum(1 for x, y in zip(a, b) if x != y)


@dataclass
class _Acumulado:
    votos: dict[str, float]
    lecturas: int
    clase_vehiculo: str
    primer_segundo: float
    ultimo_segundo: float


class VotadorPlacas:
    """Junta todas las lecturas de un mismo vehiculo y decide una sola placa.

    Cada lectura vota con el peso de su confianza, de modo que una lectura
    nitida pesa mas que tres borrosas.
    """

    def __init__(self, min_lecturas: int = 2, formatos: tuple[str, ...] = ("carro_co", "moto_co")):
        self.min_lecturas = min_lecturas
        self.formatos = formatos
        self._por_track: dict[object, _Acumulado] = {}
        self._sin_track: list[tuple[str, float, float]] = []

    def registrar(self, lectura: LecturaPlaca, clase_vehiculo: str = "car") -> str | None:
        placa = normalizar_placa(lectura.texto, self.formatos)
        if placa is None:
            return None

        clave = lectura.track_vehiculo
        if clave is None:
            # Sin id de seguimiento se agrupa por la placa misma.
            clave = f"placa:{placa}"

        acumulado = self._por_track.get(clave)
        if acumulado is None:
            self._por_track[clave] = _Acumulado(
                votos=defaultdict(float),
                lecturas=0,
                clase_vehiculo=clase_vehiculo,
                primer_segundo=lectura.segundo,
                ultimo_segundo=lectura.segundo,
            )
            acumulado = self._por_track[clave]

        acumulado.votos[placa] += max(lectura.confianza, 0.01)
        acumulado.lecturas += 1
        acumulado.ultimo_segundo = max(acumulado.ultimo_segundo, lectura.segundo)
        acumulado.primer_segundo = min(acumulado.primer_segundo, lectura.segundo)
        if clase_vehiculo:
            acumulado.clase_vehiculo = clase_vehiculo
        return placa

    def consolidar(self) -> list[EventoPlaca]:
        eventos: list[EventoPlaca] = []
        for clave, acumulado in self._por_track.items():
            if acumulado.lecturas < self.min_lecturas:
                continue
            placa, peso = max(acumulado.votos.items(), key=lambda par: par[1])
            total = sum(acumulado.votos.values()) or 1.0
            eventos.append(
                EventoPlaca(
                    placa=placa,
                    track_vehiculo=clave if isinstance(clave, int) else None,
                    clase_vehiculo=acumulado.clase_vehiculo,
                    lecturas=acumulado.lecturas,
                    confianza=peso / total,
                    primer_segundo=acumulado.primer_segundo,
                    ultimo_segundo=acumulado.ultimo_segundo,
                )
            )
        eventos.sort(key=lambda e: e.primer_segundo)
        return eventos
