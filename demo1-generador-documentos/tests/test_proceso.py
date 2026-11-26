"""
Tests de proceso.py: "Procesar planilla" completo sobre una COPIA temporal
del Excel de ejemplo, y ubicación exacta (hoja + celda) de cada problema.
"""

import shutil

import pytest
from openpyxl import load_workbook

from generador.config import PLANILLA_EJEMPLO
from generador.lectura import leer_planilla
from generador.proceso import ADVERTENCIA, ERROR, procesar_planilla


@pytest.fixture
def planilla(tmp_path):
    copia = tmp_path / "cotizaciones.xlsx"
    shutil.copy(PLANILLA_EJEMPLO, copia)
    shutil.copytree(PLANILLA_EJEMPLO.parent / "assets", tmp_path / "assets")
    return copia


def cambiar_empresa(ruta, campo, valor):
    wb = load_workbook(ruta)
    for fila in wb["Empresa"].iter_rows(min_row=2):
        if fila[0].value == campo:
            fila[1].value = valor
    wb.save(ruta)


def avisos(res, nivel):
    """{(n_cotizacion, dónde): mensaje} para comparar fácil."""
    return {(a.n_cotizacion, a.donde): a.mensaje for a in res.avisos if a.nivel == nivel}


def test_resultado_con_planilla_de_ejemplo(planilla, tmp_path):
    res = procesar_planilla(planilla, tmp_path / "salida")
    assert [n for n, _ in res.pdfs_nuevos] == [1001, 1002, 1004]   # 1007 rechazada: sin PDF
    assert res.descontadas == [1001]
    assert res.cotizaciones_con_errores == [1003, 1005, 1006]
    assert len(res.advertencias) == 1


def test_cada_error_dice_hoja_y_celda(planilla, tmp_path):
    res = procesar_planilla(planilla, tmp_path / "salida")
    errores = avisos(res, ERROR)
    assert "RUT" in errores[(1003, "Cotizaciones C4")]
    assert "XYZ-99" in errores[(1006, "Detalle B16")]
    assert "cantidad" in errores[(1006, "Detalle C17")]
    assert "productos" in errores[(1005, "Detalle")]
    assert "stock" in avisos(res, ADVERTENCIA)[(1004, "Detalle C15")]


def test_cada_problema_trae_como_corregirlo(planilla, tmp_path):
    res = procesar_planilla(planilla, tmp_path / "salida")
    assert all(a.ayuda for a in res.avisos)


def test_errores_primero_en_el_reporte(planilla, tmp_path):
    res = procesar_planilla(planilla, tmp_path / "salida")
    niveles = [a.nivel for a in res.avisos]
    assert niveles == sorted(niveles, key=lambda n: n != ERROR)


def test_segunda_vez_no_repite_pdf_ni_stock(planilla, tmp_path):
    procesar_planilla(planilla, tmp_path / "salida")
    res = procesar_planilla(planilla, tmp_path / "salida")
    assert res.pdfs_nuevos == [] and res.descontadas == []
    assert [n for n, _ in res.pdfs_existentes] == [1001, 1002, 1004]
    assert leer_planilla(planilla).inventario["TAL-01"]["stock"] == 2   # 4 - 2, una sola vez


def test_empresa_con_error_bloquea_todo_y_dice_la_celda(planilla, tmp_path):
    cambiar_empresa(planilla, "rut", "77.654.321-0")
    res = procesar_planilla(planilla, tmp_path / "salida")
    assert res.empresa_bloqueada
    assert res.pdfs_nuevos == [] and res.descontadas == []
    assert "rut" in avisos(res, ERROR)[(None, "Empresa B3")]
    assert leer_planilla(planilla).inventario["TAL-01"]["stock"] == 4   # stock intacto


def test_logo_faltante_es_advertencia_y_genera_igual(planilla, tmp_path):
    cambiar_empresa(planilla, "logo", "assets/otro_logo.png")
    res = procesar_planilla(planilla, tmp_path / "salida")
    assert not res.empresa_bloqueada
    assert len(res.pdfs_nuevos) == 3
    assert "logo" in avisos(res, ADVERTENCIA)[(None, "Empresa B9")]


def test_fila_de_detalle_sin_numero_se_ubica(planilla, tmp_path):
    wb = load_workbook(planilla)
    wb["Detalle"]["B30"] = "MAR-16"
    wb["Detalle"]["C30"] = 2
    wb.save(planilla)
    res = procesar_planilla(planilla, tmp_path / "salida")
    assert (None, "Detalle A30") in avisos(res, ADVERTENCIA)
