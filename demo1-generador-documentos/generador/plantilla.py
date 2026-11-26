"""
plantilla.py
------------
Estructura de la planilla Excel: hojas, columnas, fórmulas y listas
desplegables. La usan el script que crea la planilla de ejemplo y
escritura.py (para que cada fila nueva tenga sus fórmulas).

Idea clave: las fórmulas son SOLO para que el usuario vea en Excel la
descripción y el precio mientras escribe. El programa nunca las lee:
openpyxl escribe fórmulas pero no las calcula (eso lo hace Excel al abrir
el archivo), así que su valor podría no existir. Python busca todo
directamente en la hoja Inventario.
"""

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

ESTADOS = ("pendiente", "aceptada", "rechazada")

# Cuántas filas de Detalle se dejan listas con fórmulas y lista desplegable.
# Si se necesitan más, escritura.py agrega las fórmulas a cada fila nueva.
FILAS_DETALLE = 500
# Hasta qué fila de Inventario llega la lista de códigos (deja espacio para crecer).
FILAS_INVENTARIO = 1000

FMT_PESOS = '"$"#,##0'
FMT_FECHA = "DD-MM-YYYY"

AZUL = "1F4E78"
GRIS = "7F7F7F"
FONDO_CALCULADO = PatternFill("solid", fgColor="EDEDED")

# Hoja -> lista de (columna, ancho, formato). El orden define la posición.
COLUMNAS = {
    "Cotizaciones": [
        ("n_cotizacion", 14, None), ("fecha", 12, FMT_FECHA), ("rut_cliente", 14, None),
        ("razon_social", 32, None), ("contacto", 18, None), ("email", 24, None),
        ("observaciones", 30, None), ("estado", 12, None), ("stock_descontado", 17, FMT_FECHA),
    ],
    "Detalle": [
        ("n_cotizacion", 14, None), ("codigo", 12, None), ("cantidad", 10, None),
        ("descripcion", 38, None), ("unidad", 10, None),
        ("precio_unitario_iva", 19, FMT_PESOS), ("total", 14, FMT_PESOS),
    ],
    "Inventario": [
        ("codigo", 10, None), ("descripcion", 40, None), ("unidad", 10, None),
        ("precio_unitario_iva", 19, FMT_PESOS), ("stock", 8, None),
    ],
    "Empresa": [("campo", 18, None), ("valor", 52, None), ("ayuda", 62, None)],
}

# Columnas que llena el programa o una fórmula: encabezado gris = "no escribir".
COLUMNAS_AUTOMATICAS = {
    "Cotizaciones": {"stock_descontado"},
    "Detalle": {"descripcion", "unidad", "precio_unitario_iva", "total"},
}


def letra_columna(hoja, columna):
    """letra_columna("Detalle", "cantidad") -> "C". None si la columna no existe."""
    nombres = [c[0] for c in COLUMNAS[hoja]]
    if columna not in nombres:
        return None
    return get_column_letter(nombres.index(columna) + 1)


def formulas_detalle(fila):
    """
    Fórmulas de las columnas D a G de una fila de Detalle.

    Se escriben con los nombres en INGLÉS (VLOOKUP, IFERROR): así se guardan
    dentro del archivo .xlsx, y Excel en español las muestra traducidas
    (BUSCARV, SI.ERROR). Se usa BUSCARV y no BUSCARX porque BUSCARX solo
    existe en Excel 2021/365.
    """
    def buscar(col_inventario, si_no_existe):
        return (f'=IF(B{fila}="","",IFERROR(VLOOKUP(B{fila},Inventario!$A:$E,'
                f'{col_inventario},FALSE),"{si_no_existe}"))')

    return {
        "D": buscar(2, "¡Código no existe!"),   # descripción
        "E": buscar(3, ""),                       # unidad
        "F": buscar(4, ""),                       # precio unitario con IVA
        "G": f'=IF(OR(B{fila}="",C{fila}=""),"",IFERROR(C{fila}*F{fila},""))',  # total
    }


def escribir_formulas_detalle(ws, fila):
    """Pone las fórmulas, el fondo gris y el formato $ en una fila de Detalle."""
    for letra, formula in formulas_detalle(fila).items():
        celda = ws[f"{letra}{fila}"]
        celda.value = formula
        celda.fill = FONDO_CALCULADO
        if letra in ("F", "G"):
            celda.number_format = FMT_PESOS


def aplicar_validaciones(wb):
    """
    (Re)crea las listas desplegables y reglas de Excel. Se llama al crear la
    planilla y cada vez que el programa la guarda, por si se perdieron.

    La lista de códigos apunta a un NOMBRE ("CodigosInventario") y no
    directamente a otra hoja: es la forma más compatible entre versiones
    de Excel y la que openpyxl conserva sin problemas.
    """
    # openpyxl no calcula fórmulas: se le pide a Excel recalcular todo al abrir.
    wb.calculation.fullCalcOnLoad = True

    wb.defined_names["CodigosInventario"] = DefinedName(
        "CodigosInventario", attr_text=f"Inventario!$A$2:$A${FILAS_INVENTARIO}")

    ws = wb["Detalle"]
    ws.data_validations.dataValidation = []
    codigos = DataValidation(
        type="list", formula1="CodigosInventario", allow_blank=True,
        showErrorMessage=True, errorTitle="Código no válido",
        error="Elija un código de la lista (hoja Inventario).")
    cantidad = DataValidation(
        type="decimal", operator="greaterThan", formula1="0", allow_blank=True,
        showErrorMessage=True, errorTitle="Cantidad no válida",
        error="La cantidad debe ser un número mayor que 0.")
    ws.add_data_validation(codigos)
    ws.add_data_validation(cantidad)
    ultima = max(FILAS_DETALLE + 1, ws.max_row)
    codigos.add(f"B2:B{ultima}")
    cantidad.add(f"C2:C{ultima}")

    ws = wb["Cotizaciones"]
    ws.data_validations.dataValidation = []
    estado = DataValidation(
        type="list", formula1='"' + ",".join(ESTADOS) + '"', allow_blank=True,
        showErrorMessage=True, errorTitle="Estado no válido",
        error="El estado debe ser: " + ", ".join(ESTADOS) + ".")
    ws.add_data_validation(estado)
    estado.add(f"H2:H{max(FILAS_INVENTARIO, ws.max_row)}")


def _hoja(wb, nombre, filas):
    """Crea una hoja con encabezado con estilo, anchos, formatos y filas de datos."""
    ws = wb.create_sheet(nombre)
    columnas = COLUMNAS[nombre]
    automaticas = COLUMNAS_AUTOMATICAS.get(nombre, set())
    ws.append([c[0] for c in columnas])

    for i, (col, ancho, _fmt) in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=i)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=GRIS if col in automaticas else AZUL)
        celda.alignment = Alignment(horizontal="center")
        ws.column_dimensions[celda.column_letter].width = ancho

    for fila in filas:
        ws.append([fila.get(c[0]) for c in columnas])
        for i, (_col, _ancho, fmt) in enumerate(columnas, start=1):
            if fmt:
                ws.cell(row=ws.max_row, column=i).number_format = fmt

    ws.freeze_panes = "A2"
    return ws


def crear_planilla(ruta, empresa, inventario, cotizaciones, detalle):
    """
    Crea una planilla nueva con la estructura completa.

    empresa:      lista de dicts {campo, valor, ayuda}
    inventario:   lista de dicts {codigo, descripcion, unidad, precio_unitario_iva, stock}
    cotizaciones: lista de dicts con las columnas de Cotizaciones
    detalle:      lista de dicts {n_cotizacion, codigo, cantidad}
    """
    wb = Workbook()
    wb.remove(wb.active)

    _hoja(wb, "Cotizaciones", cotizaciones)

    ws_det = _hoja(wb, "Detalle", detalle)
    for fila in range(2, FILAS_DETALLE + 2):
        escribir_formulas_detalle(ws_det, fila)

    _hoja(wb, "Inventario", inventario)

    ws_emp = _hoja(wb, "Empresa", empresa)
    for fila in ws_emp.iter_rows(min_row=2, min_col=3, max_col=3):
        fila[0].font = Font(italic=True, color=GRIS)   # columna "ayuda" en gris
        fila[0].alignment = Alignment(wrap_text=True, vertical="top")

    aplicar_validaciones(wb)
    wb.save(ruta)
