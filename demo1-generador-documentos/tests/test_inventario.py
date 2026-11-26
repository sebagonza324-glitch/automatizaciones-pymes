"""Tests de inventario.py: completar productos y movimientos de stock (sin archivos)."""

from datetime import date

from generador.inventario import calcular_movimientos, completar_items

HOY = date(2026, 11, 26)


def inventario(stock_martillo=10, stock_sierra=3):
    return {
        "MAR-16": {"codigo": "MAR-16", "descripcion": "Martillo", "unidad": "unidad",
                   "precio_unitario_iva": 7990, "stock": stock_martillo},
        "SIE-01": {"codigo": "SIE-01", "descripcion": "Sierra", "unidad": "unidad",
                   "precio_unitario_iva": 69990, "stock": stock_sierra},
    }


def cot(n, estado, items, descontado=None):
    return {"n_cotizacion": n, "estado": estado, "stock_descontado": descontado,
            "items": [{"codigo": c, "cantidad": q} for c, q in items]}


def test_completar_items_toma_datos_del_inventario():
    items = completar_items(cot(1, "pendiente", [("MAR-16", 2)]), inventario())
    assert items == [{"codigo": "MAR-16", "descripcion": "Martillo", "unidad": "unidad",
                      "cantidad": 2, "precio_unitario_iva": 7990}]


def test_aceptada_se_descuenta_y_se_marca():
    mov = calcular_movimientos([cot(1, "aceptada", [("MAR-16", 4)])], inventario(), HOY)
    assert mov.cambios_stock == {"MAR-16": -4}
    assert mov.marcas == {1: HOY}
    assert mov.descontadas == [1]


def test_aceptada_ya_descontada_no_se_descuenta_dos_veces():
    mov = calcular_movimientos([cot(1, "aceptada", [("MAR-16", 4)], descontado=HOY)],
                               inventario(), HOY)
    assert not mov.hay_cambios()


def test_pendiente_y_rechazada_no_mueven_stock():
    cots = [cot(1, "pendiente", [("MAR-16", 4)]), cot(2, "rechazada", [("MAR-16", 4)])]
    assert not calcular_movimientos(cots, inventario(), HOY).hay_cambios()


def test_rechazada_despues_de_descontar_devuelve_stock():
    mov = calcular_movimientos([cot(1, "rechazada", [("MAR-16", 4)], descontado=HOY)],
                               inventario(), HOY)
    assert mov.cambios_stock == {"MAR-16": 4}
    assert mov.marcas == {1: None}       # se borra la fecha
    assert mov.devueltas == [1]


def test_stock_insuficiente_no_descuenta_y_es_error():
    mov = calcular_movimientos([cot(1, "aceptada", [("SIE-01", 5)])], inventario(), HOY)
    assert not mov.hay_cambios()
    assert len(mov.errores) == 1 and "SIE-01" in mov.errores[0][1]


def test_no_descuenta_nada_parcial():
    """Si un producto no alcanza, no se descuenta NINGUNO de esa cotización."""
    mov = calcular_movimientos([cot(1, "aceptada", [("MAR-16", 1), ("SIE-01", 5)])],
                               inventario(), HOY)
    assert mov.cambios_stock == {}


def test_dos_aceptadas_compiten_por_el_stock():
    """3 sierras: la N° 1 pide 2 (alcanza), la N° 2 pide 2 (ya no alcanza)."""
    cots = [cot(2, "aceptada", [("SIE-01", 2)]), cot(1, "aceptada", [("SIE-01", 2)])]
    mov = calcular_movimientos(cots, inventario(), HOY)
    assert mov.descontadas == [1]          # por orden de número, no de fila
    assert [n for n, _ in mov.errores] == [2]


def test_devolucion_libera_stock_para_otra_aceptada():
    """Se rechaza la N° 1 (devuelve 3 sierras) y se acepta la N° 2 (pide 3)."""
    cots = [cot(1, "rechazada", [("SIE-01", 3)], descontado=HOY),
            cot(2, "aceptada", [("SIE-01", 3)])]
    mov = calcular_movimientos(cots, inventario(stock_sierra=0), HOY)
    assert mov.devueltas == [1] and mov.descontadas == [2]
    assert mov.cambios_stock == {"SIE-01": 0}


def test_ejemplo_taladros_de_la_conversacion():
    """4 taladros, tres clientes cotizan 2 c/u y solo uno acepta: queda en 2, no en -2."""
    inv = {"TAL-01": {"codigo": "TAL-01", "stock": 4}}
    cots = [cot(1, "aceptada", [("TAL-01", 2)]), cot(2, "pendiente", [("TAL-01", 2)]),
            cot(3, "rechazada", [("TAL-01", 2)])]
    mov = calcular_movimientos(cots, inv, HOY)
    assert inv["TAL-01"]["stock"] + mov.cambios_stock["TAL-01"] == 2
