"""
proceso.py
----------
"Procesar planilla": todo lo que antes hacía generar.py, pero SIN imprimir
nada. Retorna un objeto Resultado que después se muestra en la ventana
(app.py) o en la consola (generar.py). Separar la lógica de la pantalla
permite tener dos interfaces con exactamente el mismo comportamiento, y
testear la lógica sin abrir ventanas.

Pasos:
  1. Revisa la hoja Empresa. Si falta algo obligatorio, se detiene sin
     generar nada (todos los PDF saldrían incompletos).
  2. Valida cada cotización contra el Inventario.
  3. Genera el PDF de cada cotización correcta que todavía no tenga PDF.
     Los PDF que ya existen NO se sobrescriben: son lo que se le envió al
     cliente, con los precios de ese día.
  4. Mueve el stock: descuenta las aceptadas y devuelve las que dejaron de estarlo.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .config import CARPETA_SALIDA
from .escritura import aplicar_movimientos
from .inventario import calcular_movimientos, completar_items
from .lectura import leer_planilla
from .pdf import generar_pdf, nombre_archivo
from .plantilla import letra_columna
from .validaciones import validar_cotizacion, validar_empresa

ERROR = "error"
ADVERTENCIA = "advertencia"


@dataclass
class Aviso:
    """Una línea del reporte: qué pasa, dónde y cómo corregirlo."""
    nivel: str                  # ERROR o ADVERTENCIA
    mensaje: str
    donde: str = ""             # "Cotizaciones C4", "Detalle B16", "Empresa B3"...
    ayuda: str = ""
    n_cotizacion: int = None
    cliente: str = ""


@dataclass
class Resultado:
    ruta: Path
    avisos: list = field(default_factory=list)
    pdfs_nuevos: list = field(default_factory=list)        # [(n_cotizacion, Path)]
    pdfs_existentes: list = field(default_factory=list)    # [(n_cotizacion, Path)]
    descontadas: list = field(default_factory=list)        # n° de cotizaciones
    devueltas: list = field(default_factory=list)
    empresa_bloqueada: bool = False   # True = la hoja Empresa impidió generar

    @property
    def errores(self):
        return [a for a in self.avisos if a.nivel == ERROR]

    @property
    def advertencias(self):
        return [a for a in self.avisos if a.nivel == ADVERTENCIA]

    @property
    def cotizaciones_con_errores(self):
        return sorted({a.n_cotizacion for a in self.errores if a.n_cotizacion is not None})


def ubicar(problema, cotizacion=None, filas_empresa=None):
    """
    Traduce un Problema a una celda de Excel que el usuario pueda buscar.
        campo "rut_cliente" de la cotización en fila 4   -> "Cotizaciones C4"
        campo "cantidad" de un producto en fila 16       -> "Detalle C16"
        campo "rut" de la hoja Empresa (fila 3)          -> "Empresa B3"
    """
    campo = getattr(problema, "campo", None)
    if getattr(problema, "celda", None):
        return problema.celda

    if filas_empresa is not None:                       # problema de la hoja Empresa
        fila = filas_empresa.get(campo)
        return f"Empresa B{fila}" if fila else f"Empresa (agregar fila '{campo}')"

    item = getattr(problema, "item", None)
    if item is not None:                                # problema de un producto
        letra = letra_columna("Detalle", campo) or "A"
        return f"Detalle {letra}{item['fila']}" if item.get("fila") else "Detalle"

    if campo == "items":
        return "Detalle"
    if cotizacion is not None and cotizacion.get("fila"):
        letra = letra_columna("Cotizaciones", campo) or "A"
        return f"Cotizaciones {letra}{cotizacion['fila']}"
    return ""


def _aviso(nivel, problema, cotizacion=None, filas_empresa=None):
    return Aviso(
        nivel=nivel, mensaje=str(problema),
        donde=ubicar(problema, cotizacion, filas_empresa),
        ayuda=getattr(problema, "ayuda", ""),
        n_cotizacion=cotizacion["n_cotizacion"] if cotizacion else None,
        cliente=(cotizacion.get("razon_social") or "") if cotizacion else "",
    )


def procesar_planilla(ruta, carpeta_salida=CARPETA_SALIDA):
    """
    Procesa la planilla completa y retorna un Resultado.
    Lanza ValueError / FileNotFoundError si la planilla no se puede leer
    (falta una hoja o una columna): eso hay que arreglarlo antes de todo.
    """
    planilla = leer_planilla(ruta)
    res = Resultado(ruta=Path(ruta))

    # Problemas de filas sueltas detectados al leer (siempre advertencias)
    res.avisos += [_aviso(ADVERTENCIA, p) for p in planilla.advertencias]

    # --- 1. Empresa ---
    errores, advertencias = validar_empresa(planilla.empresa, planilla.carpeta)
    res.avisos += [_aviso(ERROR, p, filas_empresa=planilla.filas_empresa) for p in errores]
    res.avisos += [_aviso(ADVERTENCIA, p, filas_empresa=planilla.filas_empresa)
                   for p in advertencias]
    if errores:
        res.empresa_bloqueada = True
        return res

    # --- 2. Validar cotizaciones ---
    validas = []
    for cot in planilla.cotizaciones:
        errores, advertencias = validar_cotizacion(cot, planilla.inventario)
        res.avisos += [_aviso(ERROR, p, cot) for p in errores]
        res.avisos += [_aviso(ADVERTENCIA, p, cot) for p in advertencias]
        if not errores:
            validas.append(cot)

    # --- 3. PDF (solo los nuevos; no para las rechazadas) ---
    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(exist_ok=True)
    ruta_logo = planilla.ruta_logo()
    for cot in validas:
        if cot["estado"] == "rechazada":
            continue
        ruta_pdf = carpeta_salida / nombre_archivo(cot)
        if ruta_pdf.exists():
            res.pdfs_existentes.append((cot["n_cotizacion"], ruta_pdf))
            continue
        try:
            generar_pdf(planilla.empresa, cot, completar_items(cot, planilla.inventario),
                        ruta_pdf, ruta_logo)
            res.pdfs_nuevos.append((cot["n_cotizacion"], ruta_pdf))
        except PermissionError:
            res.avisos.append(Aviso(
                ERROR, f"No se pudo guardar {ruta_pdf.name}", donde="Carpeta salida",
                ayuda="El PDF está abierto en otro programa: ciérrelo y vuelva a procesar.",
                n_cotizacion=cot["n_cotizacion"], cliente=cot["razon_social"]))

    # --- 4. Stock ---
    mov = calcular_movimientos(validas, planilla.inventario)
    for n, mensaje in mov.errores:
        cot = next(c for c in validas if c["n_cotizacion"] == n)
        res.avisos.append(Aviso(
            ERROR, mensaje, donde=f"Cotizaciones {letra_columna('Cotizaciones', 'estado')}"
                                  f"{cot['fila']}",
            ayuda="Reponga stock en la hoja Inventario, o deje la cotización como "
                  "'pendiente' hasta tener las unidades.",
            n_cotizacion=n, cliente=cot["razon_social"]))
    if mov.hay_cambios():
        try:
            aplicar_movimientos(ruta, mov)
            res.descontadas, res.devueltas = mov.descontadas, mov.devueltas
        except PermissionError:
            res.avisos.append(Aviso(
                ERROR, "No se pudo mover el stock: la planilla está abierta en Excel",
                donde="Planilla", ayuda="Cierre el Excel y vuelva a procesar. "
                                        "No se modificó nada del stock."))

    # Ordenar: primero errores, después por número de cotización
    res.avisos.sort(key=lambda a: (a.nivel != ERROR, a.n_cotizacion or 0))
    return res
