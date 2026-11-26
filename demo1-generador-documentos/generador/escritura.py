"""
escritura.py
------------
Guarda cotizaciones nuevas en la planilla Excel (agrega filas al final).

Se usa openpyxl directamente (y no pandas) porque así se conserva el formato
de la planilla: colores de encabezado, anchos de columna, formato de fechas y
de pesos. pandas reescribiría el archivo completo y perdería todo eso.

Las columnas se buscan por su NOMBRE en el encabezado, no por su posición:
si el cliente reordena las columnas del Excel, esto sigue funcionando.
"""

from openpyxl import load_workbook


def siguiente_numero(ruta):
    """Número para la próxima cotización: el mayor existente + 1."""
    wb = load_workbook(ruta, read_only=True)
    try:
        ws = wb["Cotizaciones"]
        encabezado = [c.value for c in next(ws.iter_rows(max_row=1))]
        col = encabezado.index("n_cotizacion")
        numeros = [
            fila[col] for fila in ws.iter_rows(min_row=2, values_only=True)
            if isinstance(fila[col], (int, float))
        ]
    finally:
        wb.close()
    return int(max(numeros)) + 1 if numeros else 1


def _agregar_fila(ws, datos):
    """
    Agrega una fila con 'datos' (dict columna -> valor) al final de la hoja,
    copiando el formato numérico (fecha, $) de la fila de arriba.
    """
    encabezado = [c.value for c in ws[1]]
    ws.append([datos.get(col, "") for col in encabezado])

    nueva = ws.max_row
    if nueva > 2:
        for col in range(1, len(encabezado) + 1):
            arriba = ws.cell(row=nueva - 1, column=col)
            ws.cell(row=nueva, column=col).number_format = arriba.number_format


def guardar_cotizacion(ruta, cotizacion):
    """
    Agrega la cotización a la hoja Cotizaciones y sus productos a Detalle.

    Si el Excel está abierto, Windows no deja guardar y se lanza
    PermissionError: quien llama debe avisarle al usuario que lo cierre.
    """
    wb = load_workbook(ruta)
    _agregar_fila(wb["Cotizaciones"], cotizacion)
    for item in cotizacion["items"]:
        _agregar_fila(wb["Detalle"], {**item, "n_cotizacion": cotizacion["n_cotizacion"]})
    wb.save(ruta)
