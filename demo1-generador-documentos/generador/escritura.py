"""
escritura.py
------------
Cambios que el programa hace en la planilla Excel:
    - guardar_cotizacion(): agrega una cotización nueva (la usa el formulario)
    - aplicar_movimientos(): actualiza el stock del Inventario y la columna
      stock_descontado de Cotizaciones

Se usa openpyxl directamente (y no pandas) porque así se conserva el formato
de la planilla: colores, anchos, formatos de fecha y pesos, fórmulas y listas
desplegables. Las columnas se buscan por su NOMBRE en el encabezado, no por
su posición.

Si el Excel está abierto, Windows no deja guardar y se lanza PermissionError:
quien llama debe avisarle al usuario que lo cierre.
"""

from openpyxl import load_workbook

from .plantilla import FMT_FECHA, aplicar_validaciones, escribir_formulas_detalle


def _columnas(ws):
    """{nombre_columna: número_de_columna} según el encabezado (fila 1)."""
    return {c.value: c.column for c in ws[1] if c.value}


def _primera_fila_vacia(ws, columnas):
    """
    Primera fila (desde la 2) donde TODAS las 'columnas' están vacías.
    No se usa ws.append() porque Detalle tiene cientos de filas pre-cargadas
    con fórmulas: append escribiría después de todas ellas.
    """
    fila = 2
    while any(ws.cell(row=fila, column=c).value not in (None, "") for c in columnas):
        fila += 1
    return fila


def siguiente_numero(ruta):
    """Número para la próxima cotización: el mayor existente + 1."""
    wb = load_workbook(ruta, read_only=True)
    try:
        ws = wb["Cotizaciones"]
        encabezado = [c.value for c in next(ws.iter_rows(max_row=1))]
        col = encabezado.index("n_cotizacion")
        numeros = [
            fila[col] for fila in ws.iter_rows(min_row=2, values_only=True)
            if fila and isinstance(fila[col], (int, float))
        ]
    finally:
        wb.close()
    return int(max(numeros)) + 1 if numeros else 1


def guardar_cotizacion(ruta, cotizacion):
    """
    Agrega la cotización a Cotizaciones y sus productos (solo código y
    cantidad) a Detalle. Las fórmulas de Detalle muestran el resto en Excel.
    """
    wb = load_workbook(ruta)

    ws = wb["Cotizaciones"]
    cols = _columnas(ws)
    fila = _primera_fila_vacia(ws, [cols["n_cotizacion"]])
    for nombre, col in cols.items():
        if nombre in cotizacion and nombre != "items":
            ws.cell(row=fila, column=col, value=cotizacion[nombre])
    ws.cell(row=fila, column=cols["fecha"]).number_format = FMT_FECHA

    ws = wb["Detalle"]
    cols = _columnas(ws)
    usadas = [cols["n_cotizacion"], cols["codigo"], cols["cantidad"]]
    for item in cotizacion["items"]:
        fila = _primera_fila_vacia(ws, usadas)
        ws.cell(row=fila, column=cols["n_cotizacion"], value=cotizacion["n_cotizacion"])
        ws.cell(row=fila, column=cols["codigo"], value=item["codigo"])
        ws.cell(row=fila, column=cols["cantidad"], value=item["cantidad"])
        escribir_formulas_detalle(ws, fila)   # por si la fila está más allá de las pre-cargadas

    aplicar_validaciones(wb)
    wb.save(ruta)


def aplicar_movimientos(ruta, movimientos):
    """
    Aplica un objeto Movimientos (ver inventario.py):
        - suma/resta en la columna stock de Inventario
        - anota o borra la fecha en stock_descontado de Cotizaciones
    Todo se guarda de una sola vez: o se aplica todo o nada.
    """
    if not movimientos.hay_cambios():
        return
    wb = load_workbook(ruta)

    ws = wb["Inventario"]
    cols = _columnas(ws)
    aplicados = set()   # si un código está repetido, se usa la primera fila (igual que lectura.py)
    for fila in range(2, ws.max_row + 1):
        codigo = str(ws.cell(row=fila, column=cols["codigo"]).value or "").strip().upper()
        if codigo in movimientos.cambios_stock and codigo not in aplicados:
            aplicados.add(codigo)
            celda = ws.cell(row=fila, column=cols["stock"])
            actual = celda.value if isinstance(celda.value, (int, float)) else 0
            celda.value = actual + movimientos.cambios_stock[codigo]

    ws = wb["Cotizaciones"]
    cols = _columnas(ws)
    for fila in range(2, ws.max_row + 1):
        n = ws.cell(row=fila, column=cols["n_cotizacion"]).value
        if isinstance(n, (int, float)) and int(n) in movimientos.marcas:
            celda = ws.cell(row=fila, column=cols["stock_descontado"])
            celda.value = movimientos.marcas[int(n)]
            celda.number_format = FMT_FECHA

    aplicar_validaciones(wb)
    wb.save(ruta)
