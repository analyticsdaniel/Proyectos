"""Pruebas de la normalizacion y la votacion de placas.

No necesitan modelo, ni GPU, ni OpenCV: este es el modulo puro del proyecto y
por eso es el primero que se prueba. Corren en menos de un segundo.
"""

from __future__ import annotations

import pytest

from reconocimiento.modelos import LecturaPlaca
from reconocimiento.placas_texto import (
    VotadorPlacas,
    distancia,
    limpiar,
    normalizar_placa,
)


def lectura(texto: str, confianza: float = 0.9, track: int | None = 7, segundo: float = 1.0):
    return LecturaPlaca(
        texto=texto,
        confianza=confianza,
        bbox=(0, 0, 10, 10),
        frame=int(segundo * 30),
        segundo=segundo,
        track_vehiculo=track,
    )


class TestLimpiar:
    def test_quita_lo_que_no_es_alfanumerico_y_sube_a_mayuscula(self):
        assert limpiar(" abc-123 ") == "ABC123"

    def test_texto_vacio_o_solo_simbolos_queda_vacio(self):
        assert limpiar("") == ""
        assert limpiar("--- .") == ""


class TestNormalizarPlaca:
    def test_placa_de_carro_bien_leida_pasa_igual(self):
        assert normalizar_placa("ABC123") == "ABC123"

    def test_placa_de_moto_bien_leida_pasa_igual(self):
        assert normalizar_placa("ABC12D") == "ABC12D"

    def test_tolera_basura_alrededor(self):
        assert normalizar_placa("CO ABC123 X") == "ABC123"

    def test_corrige_cero_por_o_donde_va_letra(self):
        assert normalizar_placa("0BC123") == "OBC123"

    def test_corrige_letra_por_digito_donde_va_numero(self):
        # La O de la cuarta posicion tiene que volverse cero.
        assert normalizar_placa("ABCO23") == "ABC023"

    @pytest.mark.parametrize("texto", ["", "12", "A1", "!!!!!!", "12345678901234"])
    def test_lo_que_no_encaja_devuelve_none(self, texto):
        assert normalizar_placa(texto) is None

    def test_gana_el_formato_que_menos_corrige(self):
        # Con los dos formatos, ABC12D es una moto leida perfecta y se respeta.
        assert normalizar_placa("ABC12D") == "ABC12D"
        # Pidiendo solo carros, la D se corrige a cero: una sola correccion,
        # que es justo la confusion tipica del OCR entre D y 0.
        assert normalizar_placa("ABC12D", formatos=("carro_co",)) == "ABC120"

    def test_no_inventa_placas_a_punta_de_correcciones(self):
        # Puros digitos: para que pasen como placa habria que cambiar tres
        # caracteres, y eso ya no es leer, es adivinar.
        assert normalizar_placa("456789") is None
        assert normalizar_placa("12345678901234") is None

    def test_formato_de_remolque_cuando_se_pide(self):
        assert normalizar_placa("AB1234", formatos=("remolque_co",)) == "AB1234"


class TestDistancia:
    def test_placas_iguales_distancia_cero(self):
        assert distancia("ABC123", "ABC123") == 0

    def test_cuenta_los_caracteres_distintos(self):
        assert distancia("ABC123", "ABC183") == 1

    def test_largos_distintos_devuelve_el_mayor(self):
        assert distancia("ABC123", "ABC12") == 6


class TestVotadorPlacas:
    def test_una_sola_lectura_no_alcanza(self):
        votador = VotadorPlacas(min_lecturas=2)
        votador.registrar(lectura("ABC123"))
        assert votador.consolidar() == []

    def test_dos_lecturas_coincidentes_dan_la_placa(self):
        votador = VotadorPlacas(min_lecturas=2)
        votador.registrar(lectura("ABC123", segundo=1.0))
        votador.registrar(lectura("ABC123", segundo=2.0))
        eventos = votador.consolidar()
        assert len(eventos) == 1
        assert eventos[0].placa == "ABC123"
        assert eventos[0].lecturas == 2
        assert eventos[0].primer_segundo == 1.0
        assert eventos[0].ultimo_segundo == 2.0

    def test_la_lectura_nitida_le_gana_a_dos_borrosas(self):
        votador = VotadorPlacas(min_lecturas=2)
        votador.registrar(lectura("ABC123", confianza=0.95))
        votador.registrar(lectura("ABC183", confianza=0.20))
        votador.registrar(lectura("ABC183", confianza=0.20))
        eventos = votador.consolidar()
        assert eventos[0].placa == "ABC123"
        assert 0.5 < eventos[0].confianza <= 1.0

    def test_la_basura_del_ocr_se_descarta_y_no_cuenta_como_lectura(self):
        votador = VotadorPlacas(min_lecturas=2)
        assert votador.registrar(lectura("###")) is None
        votador.registrar(lectura("ABC123"))
        votador.registrar(lectura("ABC123"))
        eventos = votador.consolidar()
        assert len(eventos) == 1
        assert eventos[0].lecturas == 2

    def test_vehiculos_distintos_no_se_mezclan(self):
        votador = VotadorPlacas(min_lecturas=2)
        for _ in range(2):
            votador.registrar(lectura("ABC123", track=1))
            votador.registrar(lectura("XYZ987", track=2))
        placas = sorted(evento.placa for evento in votador.consolidar())
        assert placas == ["ABC123", "XYZ987"]

    def test_sin_identificador_agrupa_por_la_placa_misma(self):
        votador = VotadorPlacas(min_lecturas=2)
        votador.registrar(lectura("ABC123", track=None, segundo=1.0))
        votador.registrar(lectura("ABC123", track=None, segundo=3.0))
        eventos = votador.consolidar()
        assert len(eventos) == 1
        assert eventos[0].track_vehiculo is None

    def test_los_eventos_salen_ordenados_por_tiempo(self):
        votador = VotadorPlacas(min_lecturas=2)
        for _ in range(2):
            votador.registrar(lectura("XYZ987", track=2, segundo=10.0))
            votador.registrar(lectura("ABC123", track=1, segundo=2.0))
        assert [evento.placa for evento in votador.consolidar()] == ["ABC123", "XYZ987"]
