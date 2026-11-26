"""
lectura.py
----------
Lee la planilla Excel y la convierte en estructuras simples de Python.

Este es (junto con escritura.py) el ÚNICO módulo que sabe que los datos
vienen de Excel. El resto del programa recibe datos ya limpios.

Hojas:
    - Empresa:       configuración (campo | valor | ayuda)
    - Inventario:    catálogo con precios y stock
    - Cotizaciones:  una fila por cotización (datos del cliente y estado)
    - Detalle:       una fila por producto cotizado. Solo se leen
                     n_cotizacion, codigo y cantidad: las demás columnas
                     son fórmulas para el usuario y el programa NO las usa.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .validaciones import Problema

COLUMNAS_COTIZACIONES = [
    "n_cotizacion", "fecha", "rut_cliente", "razon_social", "contacto",
    "email", "observaciones", "estado", "stock_descontado",
]
TEXTO_COTIZACIONES = ["rut_cliente", "razon_social", "contacto", "email", "observaciones", "estado"]

COLUMNAS_DETALLE = ["n_cotizacion", "codigo", "cantidad"]   # lo único que escribe el usuario
COLUMNAS_INVENTARIO = ["codigo", "descripcion", "unidad", "precio_unitario_iva", "stock"]


@dataclass
class Planilla:
    """Todo lo que se leyó de la planilla."""
    ruta: Path
    empresa: dict                       # {"razon_social": ..., "rut": ..., ...}
    inventario: dict                    # {"CEM-25": {codigo, descripcion, ...}, ...}
    cotizaciones: list                  # dicts con su lista "items" [{codigo, cantidad, fila}]
    advertencias: list = field(default_factory=list)   # problemas de filas sueltas
    filas_empresa: dict = field(default_factory=dict)  # {"rut": 3, ...} fila de cada campo

    @property
    def carpeta(self):
        """Carpeta de la planilla: las rutas de la hoja Empresa son relativas a ella."""
        return self.ruta.parent

    def ruta_logo(self):
        """Ruta del logo si está configurado Y el archivo existe; si no, None."""
        valor = self.empresa.get("logo", "")
        if not valor:
            return None
        ruta = self.carpeta / valor
        return ruta if ruta.is_file() else None


def _leer_hoja(ruta, nombre_hoja, columnas_requeridas, columnas_texto, usecols=None):
    """Lee una hoja, verifica sus columnas y limpia las celdas de texto vacías."""
    try:
        df = pd.read_excel(ruta, sheet_name=nombre_hoja, usecols=usecols,
                           dtype={col: str for col in columnas_texto})
    except ValueError as e:
        if "Worksheet named" in str(e):
            raise ValueError(f"La planilla no tiene la hoja '{nombre_hoja}'") from e
        raise

    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(
            f"A la hoja '{nombre_hoja}' le faltan las columnas: {', '.join(faltantes)}"
        )

    # Reemplazar NaN por "" SOLO en las columnas de texto y quitar espacios
    # sobrantes. Los números vacíos quedan como NaN para que validaciones.py
    # los detecte.
    for col in columnas_texto:
        df[col] = df[col].fillna("").astype(str).str.strip()
    return df


def _a_fecha(valor):
    """Timestamp de pandas -> date. Vacío -> None."""
    if pd.isna(valor) or valor == "":
        return None
    try:
        return pd.Timestamp(valor).date()
    except (ValueError, TypeError):
        return None


def _a_entero(valor):
    """1001.0 -> 1001. Vacío o texto -> None."""
    try:
        if pd.isna(valor):
            return None
        return int(float(valor))
    except (ValueError, TypeError):
        return None


def _leer_empresa(ruta):
    """
    Hoja Empresa (campo | valor | ayuda) -> (dict {campo: valor}, dict {campo: fila}).
    La fila sirve para decirle al usuario exactamente qué celda corregir.
    """
    df = _leer_hoja(ruta, "Empresa", ["campo", "valor"], ["campo", "valor"])
    valores, filas = {}, {}
    for fila_excel, (campo, valor) in enumerate(zip(df["campo"], df["valor"]), start=2):
        if campo:
            valores[campo] = valor
            filas[campo] = fila_excel
    return valores, filas


def _leer_inventario(ruta, advertencias):
    """Hoja Inventario -> dict {codigo: producto}. El código se guarda en MAYÚSCULAS."""
    df = _leer_hoja(ruta, "Inventario", COLUMNAS_INVENTARIO, ["codigo", "descripcion", "unidad"])
    inventario = {}
    for fila_excel, p in enumerate(df.to_dict("records"), start=2):
        codigo = p["codigo"].upper()
        if not codigo:
            continue
        if codigo in inventario:
            advertencias.append(Problema(
                f"El código {codigo} está repetido; se usa la primera aparición",
                celda=f"Inventario A{fila_excel}",
                ayuda="Cada código debe aparecer una sola vez. Borre o cambie esta fila."))
            continue
        p["codigo"] = codigo
        p["fila"] = fila_excel
        inventario[codigo] = p
    return inventario


def _leer_detalle(ruta, advertencias):
    """
    Hoja Detalle -> dict {n_cotizacion: [ {codigo, cantidad, fila}, ... ]}.

    La hoja trae cientos de filas con fórmulas pre-cargadas pero vacías:
    se descartan las filas donde el usuario no escribió nada.
    """
    df = _leer_hoja(ruta, "Detalle", COLUMNAS_DETALLE, ["codigo"], usecols="A:C")
    items = {}
    for fila_excel, d in enumerate(df.to_dict("records"), start=2):
        n = _a_entero(d["n_cotizacion"])
        tiene_cantidad = not pd.isna(d["cantidad"]) and d["cantidad"] != ""
        if n is None and not d["codigo"] and not tiene_cantidad:
            continue    # fila vacía
        if n is None:
            advertencias.append(Problema(
                "Tiene producto pero no n_cotizacion; se ignora",
                celda=f"Detalle A{fila_excel}",
                ayuda="Escriba el número de la cotización a la que pertenece este producto."))
            continue
        items.setdefault(n, []).append(
            {"codigo": d["codigo"].upper(), "cantidad": d["cantidad"], "fila": fila_excel})
    return items


def leer_planilla(ruta):
    """Lee la planilla completa y retorna un objeto Planilla."""
    ruta = Path(ruta)
    advertencias = []
    empresa, filas_empresa = _leer_empresa(ruta)
    inventario = _leer_inventario(ruta, advertencias)
    items_por_cotizacion = _leer_detalle(ruta, advertencias)

    df_cot = _leer_hoja(ruta, "Cotizaciones", COLUMNAS_COTIZACIONES, TEXTO_COTIZACIONES)
    cotizaciones = []
    for fila_excel, c in enumerate(df_cot.to_dict("records"), start=2):
        n = _a_entero(c["n_cotizacion"])
        if n is None:
            if c["rut_cliente"] or c["razon_social"]:
                advertencias.append(Problema(
                    "Tiene datos pero no n_cotizacion; se ignora",
                    celda=f"Cotizaciones A{fila_excel}",
                    ayuda="Escriba el número de la cotización."))
            continue
        c["n_cotizacion"] = n
        c["fila"] = fila_excel
        c["fecha"] = _a_fecha(c["fecha"])
        c["stock_descontado"] = _a_fecha(c["stock_descontado"])
        c["estado"] = c["estado"].lower() or "pendiente"   # vacío = pendiente
        c["items"] = items_por_cotizacion.pop(n, [])
        cotizaciones.append(c)

    # Productos cuyo n_cotizacion no existe en la hoja Cotizaciones
    for n, items in sorted(items_por_cotizacion.items()):
        advertencias.append(Problema(
            f"Hay productos para la cotización N° {n}, que no existe en Cotizaciones; "
            "se ignoran", celda=f"Detalle A{items[0]['fila']}",
            ayuda="Revise el número, o agregue la cotización en la hoja Cotizaciones."))

    return Planilla(ruta, empresa, inventario, cotizaciones, advertencias, filas_empresa)


# Prueba rápida: python -m generador.lectura   (desde demo1-generador-documentos)
if __name__ == "__main__":
    from .config import PLANILLA_EJEMPLO
    p = leer_planilla(PLANILLA_EJEMPLO)
    print("Empresa:", p.empresa.get("razon_social"), "| logo:", p.ruta_logo())
    print("Inventario:", len(p.inventario), "productos")
    for c in p.cotizaciones:
        print(f"  N° {c['n_cotizacion']} | {c['estado']:9} | {c['razon_social']} | "
              f"{[(i['codigo'], i['cantidad']) for i in c['items']]}")
    print("Advertencias:", p.advertencias)
