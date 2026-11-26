"""
inventario.py
-------------
Todo lo que conecta una cotización con el Inventario:

1. completar_items(): agrega descripción, unidad y precio a cada producto
   buscándolos en Inventario (nunca en las fórmulas de la hoja Detalle).

2. calcular_movimientos(): decide qué stock descontar o devolver según el
   estado de cada cotización. Reglas:

     estado      stock_descontado   acción
     ---------   ----------------   ---------------------------------------
     aceptada    vacío              DESCONTAR y anotar la fecha
     aceptada    con fecha          nada (ya se descontó: nunca dos veces)
     otro        con fecha          DEVOLVER y borrar la fecha
     otro        vacío              nada

   Si no hay stock suficiente para aceptar, NO se descuenta y se informa
   como error: el inventario nunca queda negativo.

Este módulo no lee ni escribe Excel: solo calcula. escritura.py aplica los
cambios. Así se puede testear sin archivos.
"""

from dataclasses import dataclass, field
from datetime import date


def completar_items(cotizacion, inventario):
    """
    Retorna los productos de la cotización con todos sus datos del Inventario.
    Supone que la cotización ya pasó las validaciones (códigos existen).
    """
    items = []
    for item in cotizacion["items"]:
        producto = inventario[item["codigo"]]
        items.append({
            "codigo": producto["codigo"],
            "descripcion": producto["descripcion"],
            "unidad": producto["unidad"],
            "cantidad": item["cantidad"],
            "precio_unitario_iva": producto["precio_unitario_iva"],
        })
    return items


def _cantidades_por_codigo(cotizacion):
    """Suma las cantidades por código (por si un código aparece en varias filas)."""
    total = {}
    for item in cotizacion["items"]:
        total[item["codigo"]] = total.get(item["codigo"], 0) + item["cantidad"]
    return total


@dataclass
class Movimientos:
    """Resultado de calcular_movimientos()."""
    cambios_stock: dict = field(default_factory=dict)    # {codigo: +n o -n}
    marcas: dict = field(default_factory=dict)            # {n_cotizacion: fecha o None}
    descontadas: list = field(default_factory=list)       # n° de cotizaciones descontadas
    devueltas: list = field(default_factory=list)         # n° de cotizaciones devueltas
    errores: list = field(default_factory=list)           # [(n_cotizacion, mensaje)]

    def hay_cambios(self):
        return bool(self.marcas)


def calcular_movimientos(cotizaciones, inventario, hoy=None):
    """
    Calcula los movimientos de stock para cotizaciones YA VALIDADAS.
    'hoy' se puede fijar para los tests.
    """
    hoy = hoy or date.today()
    mov = Movimientos()
    # Stock "disponible" que se va actualizando mientras se procesan las cotizaciones.
    disponible = {codigo: p.get("stock") for codigo, p in inventario.items()}

    def mover(cantidades, signo):
        for codigo, cantidad in cantidades.items():
            mov.cambios_stock[codigo] = mov.cambios_stock.get(codigo, 0) + signo * cantidad
            actual = disponible.get(codigo)
            if not _es_numero(actual):
                actual = 0   # stock vacío en Inventario: se toma como 0
            disponible[codigo] = actual + signo * cantidad

    # 1) Primero las devoluciones: liberan stock que otras cotizaciones pueden usar.
    for cot in cotizaciones:
        if cot["estado"] != "aceptada" and cot.get("stock_descontado"):
            mover(_cantidades_por_codigo(cot), +1)
            mov.marcas[cot["n_cotizacion"]] = None
            mov.devueltas.append(cot["n_cotizacion"])

    # 2) Después los descuentos, en orden de número de cotización.
    for cot in sorted(cotizaciones, key=lambda c: c["n_cotizacion"]):
        if cot["estado"] != "aceptada" or cot.get("stock_descontado"):
            continue
        cantidades = _cantidades_por_codigo(cot)
        faltantes = []
        for codigo, cantidad in cantidades.items():
            stock = disponible.get(codigo)
            if not _es_numero(stock):
                faltantes.append(f"{codigo} no tiene stock registrado en Inventario")
            elif cantidad > stock:
                faltantes.append(f"{codigo}: se piden {_num(cantidad)} y hay {_num(stock)}")
        if faltantes:
            mov.errores.append((cot["n_cotizacion"],
                                "Aceptada, pero no se descontó el stock por falta de unidades: "
                                + "; ".join(faltantes)))
            continue
        mover(cantidades, -1)
        mov.marcas[cot["n_cotizacion"]] = hoy
        mov.descontadas.append(cot["n_cotizacion"])

    return mov


def _es_numero(valor):
    """True si es int/float real (descarta None, texto y NaN; NaN != NaN)."""
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and valor == valor)


def _num(valor):
    return str(int(valor)) if float(valor).is_integer() else str(valor).replace(".", ",")
