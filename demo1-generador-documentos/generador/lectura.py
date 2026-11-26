"""
lectura.py
----------
Lee la planilla Excel de cotizaciones y la convierte en estructuras simples de
Python (diccionarios y listas).

Este es el ÚNICO módulo que sabe que los datos vienen de Excel. El resto del
programa (validaciones, cálculos, PDF) recibe datos ya limpios. Si mañana el
cliente usa Google Sheets, solo hay que cambiar este archivo.

La planilla debe tener 3 hojas:
    - Empresa:       datos de la empresa que emite la cotización
    - Cotizaciones:  una fila por cotización
    - Detalle:       una fila por producto, unida a Cotizaciones por n_cotizacion
"""

import pandas as pd

# Columnas que DEBE tener cada hoja. Si falta alguna, avisamos con un mensaje
# claro en vez de dejar que el programa falle más adelante con un error confuso.
COLUMNAS_COTIZACIONES = [
    "n_cotizacion", "fecha", "rut_cliente", "razon_social",
    "contacto", "email", "validez_dias", "observaciones",
]
COLUMNAS_DETALLE = [
    "n_cotizacion", "codigo", "descripcion", "unidad",
    "cantidad", "precio_unitario_iva",
]

# Columnas de texto: aquí una celda vacía (NaN) se reemplaza por "".
# Las columnas numéricas NO se tocan: si vienen vacías, validaciones.py
# debe detectarlo y reportarlo.
TEXTO_COTIZACIONES = ["rut_cliente", "razon_social", "contacto", "email", "observaciones"]
TEXTO_DETALLE = ["codigo", "descripcion", "unidad"]


def _leer_hoja(ruta, nombre_hoja, columnas_requeridas, columnas_texto):
    """Lee una hoja, verifica sus columnas y limpia las celdas de texto vacías."""
    # dtype=str en las columnas de texto evita que pandas "adivine" mal el tipo
    # (por ejemplo, un código "0012" se leería como el número 12).
    df = pd.read_excel(ruta, sheet_name=nombre_hoja,
                       dtype={col: str for col in columnas_texto})

    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(
            f"A la hoja '{nombre_hoja}' le faltan las columnas: {', '.join(faltantes)}"
        )

    # Reemplazar NaN por "" SOLO en las columnas de texto, y quitar espacios
    # sobrantes al inicio y al final (" Ana " -> "Ana").
    for col in columnas_texto:
        df[col] = df[col].fillna("").str.strip()

    return df


def _leer_empresa(ruta):
    """Convierte la hoja Empresa (columnas campo | valor) en un diccionario."""
    df = pd.read_excel(ruta, sheet_name="Empresa", dtype=str).fillna("")
    # zip une las dos columnas fila a fila: {"nombre": "Ferretería...", "rut": ...}
    return dict(zip(df["campo"].str.strip(), df["valor"].str.strip()))


def leer_planilla(ruta):
    """
    Lee la planilla completa.

    Retorna una tupla (empresa, cotizaciones):
        empresa       -> dict con los datos del emisor
        cotizaciones  -> lista de dicts; cada uno trae una clave "items" con
                         la lista de sus productos (vacía si no tiene ninguno)
    """
    empresa = _leer_empresa(ruta)
    df_cot = _leer_hoja(ruta, "Cotizaciones", COLUMNAS_COTIZACIONES, TEXTO_COTIZACIONES)
    df_det = _leer_hoja(ruta, "Detalle", COLUMNAS_DETALLE, TEXTO_DETALLE)

    # Agrupar el detalle por número de cotización UNA sola vez.
    # Resultado: {1001: [item, item, ...], 1002: [...], ...}
    # (Es más eficiente que filtrar el detalle completo por cada cotización.)
    items_por_cotizacion = {
        n: grupo.drop(columns="n_cotizacion").to_dict("records")
        for n, grupo in df_det.groupby("n_cotizacion")
    }

    cotizaciones = []
    for fila in df_cot.to_dict("records"):
        # pandas entrega la fecha como Timestamp; la pasamos a fecha simple.
        if pd.notna(fila["fecha"]):
            fila["fecha"] = pd.Timestamp(fila["fecha"]).date()
        # .get(..., []) -> si la cotización no tiene productos, lista vacía.
        fila["items"] = items_por_cotizacion.get(fila["n_cotizacion"], [])
        cotizaciones.append(fila)

    return empresa, cotizaciones


COLUMNAS_PRODUCTOS = ["codigo", "descripcion", "unidad", "precio_unitario_iva"]
TEXTO_PRODUCTOS = ["codigo", "descripcion", "unidad"]


def leer_productos(ruta):
    """
    Lee el catálogo (hoja Productos). Retorna una lista de dicts.
    Se omiten las filas sin código, que suelen ser filas vacías al final.
    """
    df = _leer_hoja(ruta, "Productos", COLUMNAS_PRODUCTOS, TEXTO_PRODUCTOS)
    df = df[df["codigo"] != ""]
    return df.to_dict("records")


# Prueba rápida: ejecutar este archivo directamente muestra un resumen.
#   python -m generador.lectura   (desde la carpeta demo1-generador-documentos)
if __name__ == "__main__":
    empresa, cotizaciones = leer_planilla("datos_ejemplo/cotizaciones_ejemplo.xlsx")
    print("Empresa:", empresa["nombre"], "|", empresa["rut"])
    for c in cotizaciones:
        print(f"  N° {c['n_cotizacion']} | {c['fecha']} | {c['rut_cliente']} | "
              f"{c['razon_social']} | {len(c['items'])} productos | "
              f"obs: {c['observaciones']!r}")
