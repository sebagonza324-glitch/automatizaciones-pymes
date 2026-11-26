"""Tests de validaciones.py. Ejecutar con:  pytest   (desde demo1-generador-documentos)"""

import math
from datetime import date

import pytest

from generador.validaciones import rut_es_valido, validar_cotizacion


# parametrize ejecuta el mismo test con cada par (entrada, resultado esperado).
@pytest.mark.parametrize("rut, esperado", [
    # RUT válidos: estos son los que de verdad prueban el algoritmo
    ("76.123.456-0", True),      # con puntos
    ("76123456-0", True),        # sin puntos
    (" 76.123.456-0 ", True),    # con espacios
    ("12.345.678-5", True),
    ("11.111.112-K", True),      # termina en K
    ("11111112-k", True),        # termina en k minúscula
    # RUT inválidos
    ("76.555.444-1", False),     # dígito verificador incorrecto
    ("11.111.112-0", False),     # debería ser K
    ("", False),
    ("hola", False),
    ("12345678", False),         # sin guion
    ("1-2-3", False),            # más de un guion
    ("-5", False),               # negativo
    ("-76.123.456-0", False),    # RUT negativo
    (None, False),               # celda vacía
    (76123456, False),           # número en vez de texto
])
def test_rut_es_valido(rut, esperado):
    assert rut_es_valido(rut) == esperado


def cotizacion_ok():
    """Una cotización correcta; cada test le 'rompe' una cosa."""
    return {
        "n_cotizacion": 1, "fecha": date(2026, 11, 20),
        "rut_cliente": "76.123.456-0", "razon_social": "Cliente de prueba",
        "items": [{"codigo": "A1", "descripcion": "Martillo",
                   "cantidad": 2, "precio_unitario_iva": 5990}],
    }


def test_cotizacion_correcta_no_tiene_problemas():
    assert validar_cotizacion(cotizacion_ok()) == []


def test_rut_invalido_se_reporta():
    cot = cotizacion_ok()
    cot["rut_cliente"] = "76.555.444-1"
    assert any("RUT" in p for p in validar_cotizacion(cot))


def test_sin_productos_se_reporta():
    cot = cotizacion_ok()
    cot["items"] = []
    assert any("productos" in p for p in validar_cotizacion(cot))


@pytest.mark.parametrize("cantidad", [0, -5, math.nan, "", None])
def test_cantidad_invalida_se_reporta(cantidad):
    cot = cotizacion_ok()
    cot["items"][0]["cantidad"] = cantidad
    assert any("cantidad" in p for p in validar_cotizacion(cot))


def test_precio_negativo_se_reporta():
    cot = cotizacion_ok()
    cot["items"][0]["precio_unitario_iva"] = -100
    assert any("precio" in p for p in validar_cotizacion(cot))


def test_varios_errores_se_reportan_juntos():
    """La idea clave: el usuario ve TODOS los problemas de una vez."""
    cot = cotizacion_ok()
    cot["rut_cliente"] = "hola"
    cot["fecha"] = None
    cot["items"][0]["cantidad"] = -1
    assert len(validar_cotizacion(cot)) == 3
