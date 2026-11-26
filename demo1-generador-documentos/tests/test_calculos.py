"""Tests de calculos.py."""

import pytest

from generador.calculos import (calcular_totales, formato_cantidad, formato_pesos,
                                redondear_pesos, total_linea)


def item(cantidad, precio):
    return {"cantidad": cantidad, "precio_unitario_iva": precio}


def test_total_linea():
    assert total_linea(item(40, 5490)) == 219600


def test_totales_cotizacion_1001():
    """Mismos números que el PDF de ejemplo de la cotización 1001."""
    items = [item(40, 5490), item(60, 3290), item(2, 39990), item(10, 1890)]
    assert calcular_totales(items) == {"total": 515880, "neto": 433513, "iva": 82367}


@pytest.mark.parametrize("precio", [1, 990, 11990, 39990, 123457, 999999])
def test_neto_mas_iva_siempre_cuadra(precio):
    """Por muy 'feo' que sea el precio, neto + IVA debe dar exactamente el total."""
    t = calcular_totales([item(3, precio)])
    assert t["neto"] + t["iva"] == t["total"]


def test_redondeo_hacia_arriba_en_medio_peso():
    # round(2.5) de Python da 2 (redondeo bancario); en pesos queremos 3.
    assert redondear_pesos(2.5) == 3
    assert redondear_pesos(2.4) == 2


@pytest.mark.parametrize("monto, texto", [
    (0, "$0"), (990, "$990"), (5490, "$5.490"), (515880, "$515.880"), (12345678, "$12.345.678"),
])
def test_formato_pesos(monto, texto):
    assert formato_pesos(monto) == texto


def test_formato_cantidad():
    assert formato_cantidad(40) == "40"
    assert formato_cantidad(2.5) == "2,5"
