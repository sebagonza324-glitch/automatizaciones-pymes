"""
calculos.py
-----------
Montos de una cotización. Los precios del Excel vienen CON IVA (el valor real
que paga el cliente); desde ahí se obtiene el subtotal neto y el IVA.

Regla para que todo cuadre:
    1. total = suma de (cantidad x precio con IVA)      <- valor real
    2. neto  = total / 1,19, redondeado al peso
    3. iva   = total - neto  (restando, no multiplicando)
Como el IVA se obtiene restando, neto + iva SIEMPRE es igual al total.
"""

from decimal import Decimal, ROUND_HALF_UP

TASA_IVA = Decimal("0.19")


def redondear_pesos(valor):
    """
    Redondea al peso entero "como en el colegio" (0,5 sube).

    Ojo: el round() de Python usa "redondeo bancario" (round(2.5) da 2),
    por eso se usa Decimal con ROUND_HALF_UP.
    """
    return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def total_linea(item):
    """Total de un producto: cantidad x precio unitario con IVA."""
    return redondear_pesos(Decimal(str(item["cantidad"])) * Decimal(str(item["precio_unitario_iva"])))


def calcular_totales(items):
    """Retorna un dict con 'total', 'neto' e 'iva' (enteros, en pesos)."""
    total = sum(total_linea(item) for item in items)
    neto = redondear_pesos(Decimal(total) / (1 + TASA_IVA))
    iva = total - neto
    return {"total": total, "neto": neto, "iva": iva}


def formato_pesos(monto):
    """12345678 -> '$12.345.678' (separador de miles chileno)."""
    return "$" + f"{int(monto):,}".replace(",", ".")


def formato_cantidad(cantidad):
    """40 -> '40'   2.5 -> '2,5'   (sin decimales innecesarios)."""
    if float(cantidad).is_integer():
        return str(int(cantidad))
    return str(cantidad).replace(".", ",")
