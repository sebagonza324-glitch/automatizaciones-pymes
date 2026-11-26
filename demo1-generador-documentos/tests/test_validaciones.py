"""Tests de validaciones.py. Ejecutar con:  pytest   (desde demo1-generador-documentos)"""

import math
from datetime import date

import pytest

from generador.validaciones import (email_es_valido, rut_es_valido, validar_cotizacion,
                                    validar_empresa)


# ----------------------------------------------------------------------
# RUT
# ----------------------------------------------------------------------
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


@pytest.mark.parametrize("email, esperado", [
    ("ventas@gmail.com", True), ("a.b@empresa.cl", True),
    ("", False), ("ventas", False), ("ventas@gmail", False), ("con espacio@gmail.com", False),
])
def test_email_es_valido(email, esperado):
    assert email_es_valido(email) == esperado


# ----------------------------------------------------------------------
# Hoja Empresa
# ----------------------------------------------------------------------
def empresa_ok():
    return {
        "razon_social": "Ferretería de Prueba SpA", "rut": "77.654.321-7",
        "direccion": "Calle 1", "telefono": "+56 9 1111 1111", "email": "ventas@gmail.com",
        "validez_dias": "15", "condiciones_pago": "Contado", "logo": "",
    }


def test_empresa_correcta(tmp_path):
    assert validar_empresa(empresa_ok(), tmp_path) == ([], [])


@pytest.mark.parametrize("campo", ["razon_social", "rut", "direccion", "telefono", "email",
                                   "validez_dias", "condiciones_pago"])
def test_empresa_falta_obligatorio_es_error(campo, tmp_path):
    empresa = empresa_ok()
    empresa[campo] = ""
    errores, _ = validar_empresa(empresa, tmp_path)
    assert any(campo in e for e in errores)


@pytest.mark.parametrize("campo, valor", [
    ("rut", "77.654.321-0"), ("email", "ventas"), ("validez_dias", "quince"),
    ("validez_dias", "0"), ("validez_dias", "2.5"),
])
def test_empresa_dato_invalido_es_error(campo, valor, tmp_path):
    empresa = empresa_ok()
    empresa[campo] = valor
    errores, _ = validar_empresa(empresa, tmp_path)
    assert any(campo in e for e in errores)


def test_logo_vacio_no_es_problema(tmp_path):
    assert validar_empresa(empresa_ok(), tmp_path) == ([], [])


def test_logo_inexistente_es_advertencia_no_error(tmp_path):
    empresa = empresa_ok()
    empresa["logo"] = "assets/no_existe.png"
    errores, advertencias = validar_empresa(empresa, tmp_path)
    assert errores == []
    assert any("logo" in a for a in advertencias)


def test_logo_existente_es_valido(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.png").write_bytes(b"png")
    empresa = empresa_ok()
    empresa["logo"] = "assets/logo.png"
    assert validar_empresa(empresa, tmp_path) == ([], [])


# ----------------------------------------------------------------------
# Cotizaciones contra Inventario
# ----------------------------------------------------------------------
INVENTARIO = {
    "MAR-16": {"codigo": "MAR-16", "descripcion": "Martillo", "unidad": "unidad",
               "precio_unitario_iva": 7990, "stock": 10},
    "SIN-PRECIO": {"codigo": "SIN-PRECIO", "descripcion": "X", "unidad": "unidad",
                   "precio_unitario_iva": math.nan, "stock": 10},
}


def cotizacion_ok():
    """Una cotización correcta; cada test le 'rompe' una cosa."""
    return {
        "n_cotizacion": 1, "fecha": date(2026, 11, 20), "estado": "pendiente",
        "rut_cliente": "76.123.456-0", "razon_social": "Cliente de prueba",
        "stock_descontado": None,
        "items": [{"codigo": "MAR-16", "cantidad": 2}],
    }


def test_cotizacion_correcta_no_tiene_problemas():
    assert validar_cotizacion(cotizacion_ok(), INVENTARIO) == ([], [])


def test_rut_invalido_es_error():
    cot = cotizacion_ok()
    cot["rut_cliente"] = "76.555.444-1"
    errores, _ = validar_cotizacion(cot, INVENTARIO)
    assert any("RUT" in e for e in errores)


def test_sin_productos_es_error():
    cot = cotizacion_ok()
    cot["items"] = []
    errores, _ = validar_cotizacion(cot, INVENTARIO)
    assert any("productos" in e for e in errores)


def test_codigo_inexistente_es_error():
    cot = cotizacion_ok()
    cot["items"] = [{"codigo": "XYZ-99", "cantidad": 1}]
    errores, _ = validar_cotizacion(cot, INVENTARIO)
    assert any("XYZ-99" in e and "no existe" in e for e in errores)


def test_producto_sin_precio_en_inventario_es_error():
    cot = cotizacion_ok()
    cot["items"] = [{"codigo": "SIN-PRECIO", "cantidad": 1}]
    errores, _ = validar_cotizacion(cot, INVENTARIO)
    assert any("precio" in e for e in errores)


@pytest.mark.parametrize("cantidad", [0, -5, math.nan, "", None, "dos"])
def test_cantidad_invalida_es_error(cantidad):
    cot = cotizacion_ok()
    cot["items"][0]["cantidad"] = cantidad
    errores, _ = validar_cotizacion(cot, INVENTARIO)
    assert any("cantidad" in e for e in errores)


def test_estado_invalido_es_error():
    cot = cotizacion_ok()
    cot["estado"] = "vendida"
    errores, _ = validar_cotizacion(cot, INVENTARIO)
    assert any("Estado" in e for e in errores)


def test_cantidad_mayor_al_stock_es_advertencia_no_error():
    cot = cotizacion_ok()
    cot["items"][0]["cantidad"] = 15      # stock 10
    errores, advertencias = validar_cotizacion(cot, INVENTARIO)
    assert errores == []
    assert any("stock" in a for a in advertencias)


def test_stock_suma_filas_repetidas_del_mismo_codigo():
    cot = cotizacion_ok()
    cot["items"] = [{"codigo": "MAR-16", "cantidad": 6}, {"codigo": "MAR-16", "cantidad": 6}]
    _, advertencias = validar_cotizacion(cot, INVENTARIO)
    assert any("12" in a for a in advertencias)


def test_sin_advertencia_de_stock_si_ya_se_desconto():
    """Si ya se descontó, el stock actual ya no incluye esas unidades."""
    cot = cotizacion_ok()
    cot["items"][0]["cantidad"] = 15
    cot["estado"] = "aceptada"
    cot["stock_descontado"] = date(2026, 11, 21)
    assert validar_cotizacion(cot, INVENTARIO) == ([], [])


def test_varios_errores_se_reportan_juntos():
    """La idea clave: el usuario ve TODOS los problemas de una vez."""
    cot = cotizacion_ok()
    cot["rut_cliente"] = "hola"
    cot["fecha"] = None
    cot["items"] = [{"codigo": "MAR-16", "cantidad": -1}, {"codigo": "XYZ", "cantidad": 1}]
    errores, _ = validar_cotizacion(cot, INVENTARIO)
    assert len(errores) == 4
