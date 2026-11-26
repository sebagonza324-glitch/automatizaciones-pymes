"""
Tests de lectura, escritura y estructura de la planilla, sobre una COPIA
temporal del Excel de ejemplo (nunca se toca el original).
"""

import shutil
from datetime import date

import pytest
from openpyxl import load_workbook

from generador.config import PLANILLA_EJEMPLO
from generador.escritura import aplicar_movimientos, guardar_cotizacion, siguiente_numero
from generador.inventario import calcular_movimientos
from generador.lectura import leer_planilla
from generador.plantilla import FILAS_DETALLE
from generador.validaciones import formatear_rut


@pytest.fixture
def planilla(tmp_path):
    """tmp_path es una carpeta temporal que pytest crea y borra solo."""
    copia = tmp_path / "cotizaciones.xlsx"
    shutil.copy(PLANILLA_EJEMPLO, copia)
    shutil.copytree(PLANILLA_EJEMPLO.parent / "assets", tmp_path / "assets")
    return copia


# --- Estructura de la planilla de ejemplo ---

def test_planilla_tiene_las_cuatro_hojas(planilla):
    assert load_workbook(planilla).sheetnames == ["Cotizaciones", "Detalle", "Inventario", "Empresa"]


def test_detalle_tiene_lista_desplegable_de_codigos(planilla):
    ws = load_workbook(planilla)["Detalle"]
    listas = [dv for dv in ws.data_validations.dataValidation if dv.type == "list"]
    assert listas and listas[0].formula1 == "CodigosInventario"
    assert "B2" in listas[0].sqref


def test_detalle_tiene_formulas_buscarv(planilla):
    ws = load_workbook(planilla)["Detalle"]
    assert "VLOOKUP(B2,Inventario" in ws["D2"].value
    assert "VLOOKUP" in ws[f"F{FILAS_DETALLE + 1}"].value      # también en la última pre-cargada


def test_inventario_de_ejemplo_tiene_30_productos(planilla):
    assert len(leer_planilla(planilla).inventario) == 30


# --- Lectura ---

def test_lectura_ignora_filas_precargadas_vacias(planilla):
    p = leer_planilla(planilla)
    total_items = sum(len(c["items"]) for c in p.cotizaciones)
    assert total_items == 18           # las del ejemplo, no 500
    assert p.advertencias == []


def test_lectura_no_usa_las_formulas(planilla):
    """Detalle solo aporta código y cantidad; lo demás viene del Inventario."""
    p = leer_planilla(planilla)
    assert p.cotizaciones[0]["items"][0] == {"codigo": "CEM-25", "cantidad": 40, "fila": 2}


def test_logo_relativo_a_la_planilla(planilla):
    assert leer_planilla(planilla).ruta_logo() == planilla.parent / "assets" / "logo.png"


# --- Escritura ---

def test_siguiente_numero(planilla):
    assert siguiente_numero(planilla) == 1008   # el ejemplo llega hasta la 1007


def test_guardar_y_volver_a_leer(planilla):
    cot = {
        "n_cotizacion": 1008, "fecha": date(2026, 11, 26), "estado": "pendiente",
        "rut_cliente": "76.123.456-0", "razon_social": "Cliente de prueba",
        "contacto": "", "email": "", "observaciones": "",
        "items": [{"codigo": "CEM-25", "cantidad": 3}, {"codigo": "GUA-01", "cantidad": 2}],
    }
    guardar_cotizacion(planilla, cot)

    p = leer_planilla(planilla)
    nueva = p.cotizaciones[-1]
    assert nueva["n_cotizacion"] == 1008
    assert nueva["fecha"] == date(2026, 11, 26)
    assert nueva["items"] == [{"codigo": "CEM-25", "cantidad": 3, "fila": 20},
                              {"codigo": "GUA-01", "cantidad": 2, "fila": 21}]
    assert siguiente_numero(planilla) == 1009

    # Se escribió en la primera fila libre (no después de las 500 pre-cargadas)
    # y la lista desplegable sigue existiendo.
    ws = load_workbook(planilla)["Detalle"]
    assert ws.cell(row=20, column=1).value == 1008
    assert len(ws.data_validations.dataValidation) == 2


def test_aplicar_movimientos_descuenta_y_marca(planilla):
    p = leer_planilla(planilla)
    mov = calcular_movimientos([p.cotizaciones[0]], p.inventario, date(2026, 11, 26))  # 1001 aceptada
    aplicar_movimientos(planilla, mov)

    despues = leer_planilla(planilla)
    assert despues.inventario["CEM-25"]["stock"] == 120 - 40
    assert despues.inventario["TAL-01"]["stock"] == 4 - 2
    assert despues.cotizaciones[0]["stock_descontado"] == date(2026, 11, 26)

    # Segunda vez: ya marcada, no descuenta de nuevo
    mov2 = calcular_movimientos([despues.cotizaciones[0]], despues.inventario)
    assert not mov2.hay_cambios()


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
