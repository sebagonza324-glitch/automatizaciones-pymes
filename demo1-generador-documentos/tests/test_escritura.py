"""Tests de escritura.py y de la lectura del catálogo, sobre una COPIA temporal del Excel."""

import shutil
from datetime import date

import pytest

from generador.config import PLANILLA_EJEMPLO
from generador.escritura import guardar_cotizacion, siguiente_numero
from generador.lectura import leer_planilla, leer_productos
from generador.validaciones import formatear_rut


@pytest.fixture
def planilla(tmp_path):
    """tmp_path es una carpeta temporal que pytest crea y borra solo."""
    copia = tmp_path / "cotizaciones.xlsx"
    shutil.copy(PLANILLA_EJEMPLO, copia)
    return copia


def test_siguiente_numero(planilla):
    assert siguiente_numero(planilla) == 1006   # el ejemplo llega hasta la 1005


def test_guardar_y_volver_a_leer(planilla):
    cot = {
        "n_cotizacion": 1006, "fecha": date(2026, 11, 26),
        "rut_cliente": "76.123.456-0", "razon_social": "Cliente de prueba",
        "contacto": "", "email": "", "validez_dias": 10, "observaciones": "",
        "items": [
            {"codigo": "CEM-25", "descripcion": "Cemento saco 25 kg", "unidad": "saco",
             "cantidad": 3, "precio_unitario_iva": 5490},
            {"codigo": "GUA-01", "descripcion": "Guantes de trabajo (par)", "unidad": "par",
             "cantidad": 2, "precio_unitario_iva": 1990},
        ],
    }
    guardar_cotizacion(planilla, cot)

    _, cotizaciones = leer_planilla(planilla)
    nueva = cotizaciones[-1]
    assert nueva["n_cotizacion"] == 1006
    assert nueva["fecha"] == date(2026, 11, 26)
    assert nueva["razon_social"] == "Cliente de prueba"
    assert [i["codigo"] for i in nueva["items"]] == ["CEM-25", "GUA-01"]
    assert siguiente_numero(planilla) == 1007


def test_leer_catalogo(planilla):
    productos = leer_productos(planilla)
    codigos = [p["codigo"] for p in productos]
    assert "CEM-25" in codigos
    assert all(p["precio_unitario_iva"] > 0 for p in productos)


@pytest.mark.parametrize("entrada, salida", [
    ("76123456-0", "76.123.456-0"),
    (" 76.123.456-0 ", "76.123.456-0"),
    ("11111112-k", "11.111.112-K"),
    ("1234567-4", "1.234.567-4"),
    ("76.555.444-1", None),        # inválido
    ("hola", None),
])
def test_formatear_rut(entrada, salida):
    assert formatear_rut(entrada) == salida
