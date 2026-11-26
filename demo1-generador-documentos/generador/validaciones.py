"""
validaciones.py
---------------
Reglas para decidir si una cotización está lista para convertirse en PDF.

Las funciones de este módulo NUNCA lanzan errores por datos malos: solo
responden True/False (o una lista de problemas). Quien las llama decide qué
hacer con esa información (por ejemplo, juntar todo en un reporte final).
"""

import math
import re

from .plantilla import ESTADOS


class Problema(str):
    """
    Un problema encontrado: es un texto (se puede imprimir, comparar y buscar
    dentro de él como cualquier str) que además sabe DÓNDE está y CÓMO
    corregirlo, para mostrarlo ordenado en la ventana.

        campo:  columna de la planilla donde está el problema ("rut_cliente")
        item:   el producto de Detalle afectado (dict), si corresponde
        ayuda:  sugerencia para corregirlo
        celda:  ubicación ya resuelta ("Detalle A12"), si se conoce de antemano

    Se hereda de str para que el código y los tests que ya trataban los
    problemas como texto sigan funcionando sin cambios.
    """

    def __new__(cls, mensaje, campo=None, item=None, ayuda="", celda=None):
        problema = super().__new__(cls, mensaje)
        problema.campo = campo
        problema.item = item
        problema.ayuda = ayuda
        problema.celda = celda
        return problema


def rut_es_valido(rut):
    """
    Verifica un RUT chileno con el algoritmo módulo 11.

    Acepta distintos formatos de escritura:
        "76.123.456-0", "76123456-0", " 76.123.456-k "
    Retorna True si el dígito verificador es correcto; False en cualquier
    otro caso (incluye entradas vacías o sin sentido, como "" o "hola").
    """
    # Si no es texto (por ejemplo, una celda numérica o vacía), no es un RUT.
    if not isinstance(rut, str):
        return False

    # Paso 1: normalizar. Quitar puntos y espacios, y pasar k -> K.
    rut = rut.replace(".", "").replace(" ", "").upper()

    # Paso 2: separar cuerpo y dígito verificador.
    # Debe haber exactamente un guion: "76123456-0" -> ["76123456", "0"]
    partes = rut.split("-")
    if len(partes) != 2:
        return False
    cuerpo, dv = partes

    # Paso 3: el cuerpo deben ser solo dígitos (rechaza "", "-5", "hola").
    if not cuerpo.isdigit():
        return False

    # Paso 4: módulo 11. Recorrer el cuerpo al revés multiplicando por la
    # serie 2,3,4,5,6,7,2,3,... y acumular la suma.
    suma = 0
    multiplicador = 2
    for digito in reversed(cuerpo):
        suma = suma + int(digito) * multiplicador
        multiplicador = multiplicador + 1
        if multiplicador > 7:
            multiplicador = 2

    # Paso 5: traducir el resultado a dígito verificador y comparar.
    resultado = 11 - (suma % 11)
    if resultado == 11:
        esperado = "0"
    elif resultado == 10:
        esperado = "K"
    else:
        esperado = str(resultado)  # texto, porque dv también es texto

    return esperado == dv


def formatear_rut(rut):
    """
    Lleva un RUT válido al formato estándar con puntos y guion.
        "76123456-0" -> "76.123.456-0"     " 11111112-k " -> "11.111.112-K"
    Si el RUT no es válido, retorna None.
    """
    if not rut_es_valido(rut):
        return None
    cuerpo, dv = rut.replace(".", "").replace(" ", "").upper().split("-")
    return f"{int(cuerpo):,}".replace(",", ".") + "-" + dv


def _es_numero_positivo(valor):
    """True si 'valor' es un número real mayor que 0 (descarta vacíos/NaN)."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return False
    if math.isnan(valor):
        return False
    return valor > 0


def email_es_valido(email):
    """Revisión simple de formato: algo@algo.algo, sin espacios."""
    return isinstance(email, str) and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is not None


# ----------------------------------------------------------------------
# Hoja Empresa
# ----------------------------------------------------------------------
CAMPOS_EMPRESA_OBLIGATORIOS = [
    "razon_social", "rut", "direccion", "telefono", "email", "validez_dias", "condiciones_pago",
]
EXTENSIONES_LOGO = {".png", ".jpg", ".jpeg"}


def validar_empresa(empresa, carpeta_planilla):
    """
    Revisa la hoja Empresa. Retorna (errores, advertencias).

    Errores: faltan datos obligatorios o están mal -> no se genera NINGÚN PDF,
    porque todos saldrían incompletos.
    Advertencias: datos opcionales con problemas (por ejemplo, el logo no se
    encuentra) -> los PDF se generan igual.
    """
    errores, advertencias = [], []

    for campo in CAMPOS_EMPRESA_OBLIGATORIOS:
        if not empresa.get(campo):
            errores.append(Problema(
                f"Falta '{campo}'", campo=campo,
                ayuda=f"Escriba el dato en la columna 'valor' de la fila '{campo}'. "
                      "Si la fila no existe, agréguela."))

    if empresa.get("rut") and not rut_es_valido(empresa["rut"]):
        errores.append(Problema(
            f"'rut' inválido: {empresa['rut']}", campo="rut",
            ayuda="Revise los números y el dígito verificador. Formato: 77.654.321-7"))

    if empresa.get("email") and not email_es_valido(empresa["email"]):
        errores.append(Problema(
            f"'email' no tiene formato de correo: {empresa['email']}", campo="email",
            ayuda="Debe ser como ventas@gmail.com, sin espacios."))

    if empresa.get("validez_dias"):
        try:
            dias = float(empresa["validez_dias"])
            if dias <= 0 or not dias.is_integer():
                raise ValueError
        except ValueError:
            errores.append(Problema(
                f"'validez_dias' debe ser un número entero mayor que 0 "
                f"(tiene {empresa['validez_dias']})", campo="validez_dias",
                ayuda="Escriba solo el número de días, por ejemplo 15."))

    logo = empresa.get("logo", "")
    if logo:
        ruta = carpeta_planilla / logo
        if not ruta.is_file():
            advertencias.append(Problema(
                f"No se encontró el logo '{logo}': los PDF salen sin logo", campo="logo",
                ayuda=f"Copie el archivo del logo en {ruta.parent} con el nombre "
                      f"'{ruta.name}', o deje la celda vacía."))
        elif ruta.suffix.lower() not in EXTENSIONES_LOGO:
            advertencias.append(Problema(
                f"El logo '{logo}' debe ser PNG o JPG: los PDF salen sin logo", campo="logo",
                ayuda="Guarde el logo como .png o .jpg y actualice la ruta."))

    return errores, advertencias


# ----------------------------------------------------------------------
# Cotizaciones
# ----------------------------------------------------------------------
ESTADOS_VALIDOS = ESTADOS   # definidos en plantilla.py (lista desplegable de Excel)


def validar_cotizacion(cotizacion, inventario):
    """
    Revisa una cotización completa contra el Inventario.
    Retorna (errores, advertencias): listas de Problema (textos en lenguaje
    simple que además saben en qué columna y producto están).

    Errores -> no se genera el PDF ni se mueve stock.
    Advertencias -> se genera igual, pero se avisa (por ejemplo, poco stock).

    Se devuelven TODOS los problemas juntos, para que el usuario corrija todo
    de una vez en vez de corregir, ejecutar y descubrir el siguiente error.
    """
    errores, advertencias = [], []

    if not rut_es_valido(cotizacion.get("rut_cliente")):
        rut = cotizacion.get("rut_cliente") or "(vacío)"
        errores.append(Problema(
            f"RUT del cliente inválido: {rut}", campo="rut_cliente",
            ayuda="Revise los números y el dígito verificador. Formato: 12.345.678-9"))

    if not cotizacion.get("razon_social"):
        errores.append(Problema("Falta la razón social (nombre) del cliente",
                                campo="razon_social", ayuda="Escriba el nombre del cliente."))

    if not cotizacion.get("fecha"):
        errores.append(Problema("Falta la fecha", campo="fecha",
                                ayuda="Escriba la fecha como 26-11-2026."))

    estado = cotizacion.get("estado") or "pendiente"
    if estado not in ESTADOS_VALIDOS:
        errores.append(Problema(
            f"Estado '{estado}' no válido", campo="estado",
            ayuda=f"Elija de la lista desplegable: {', '.join(ESTADOS_VALIDOS)}."))

    items = cotizacion.get("items", [])
    if not items:
        errores.append(Problema(
            "No tiene productos", campo="items",
            ayuda=f"Agregue filas en la hoja Detalle con n_cotizacion "
                  f"{cotizacion.get('n_cotizacion')}, el código y la cantidad."))

    pedido_por_codigo = {}   # para revisar stock sumando filas repetidas del mismo código
    for item in items:
        codigo = item.get("codigo") or ""
        cantidad = item.get("cantidad")

        if not codigo:
            errores.append(Problema("Hay un producto sin código", campo="codigo", item=item,
                                    ayuda="Elija el código de la lista desplegable."))
            continue
        producto = inventario.get(codigo)
        if producto is None:
            errores.append(Problema(
                f"El código {codigo} no existe en Inventario", campo="codigo", item=item,
                ayuda="Elija un código de la lista desplegable, o agregue el producto "
                      "en la hoja Inventario."))
            continue
        if not _es_numero_positivo(producto.get("precio_unitario_iva")):
            errores.append(Problema(
                f"El producto {codigo} no tiene un precio válido en Inventario",
                campo="codigo", item=item,
                ayuda=f"Escriba el precio con IVA de {codigo} en la hoja Inventario."))
        if not _es_numero_positivo(cantidad):
            errores.append(Problema(
                f"Producto {codigo}: la cantidad debe ser mayor que 0 (tiene {cantidad})",
                campo="cantidad", item=item, ayuda="Escriba un número mayor que 0."))
            continue
        pedido_por_codigo[codigo] = pedido_por_codigo.get(codigo, 0) + cantidad

    # Stock: solo se advierte si todavía no se descontó (si ya se descontó,
    # el stock actual ya no incluye estas unidades y la comparación no sirve).
    if not cotizacion.get("stock_descontado"):
        for codigo, pedido in pedido_por_codigo.items():
            stock = inventario[codigo].get("stock")
            if _es_numero(stock) and pedido > stock:
                item = next(i for i in items if i.get("codigo") == codigo)
                advertencias.append(Problema(
                    f"Producto {codigo}: se cotizan {_num(pedido)} y hay {_num(stock)} en stock",
                    campo="cantidad", item=item,
                    ayuda="Se puede cotizar igual. Para aceptarla habrá que reponer stock "
                          "o bajar la cantidad."))

    return errores, advertencias


def _es_numero(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and not math.isnan(valor))


def _num(valor):
    """3.0 -> '3'   2.5 -> '2,5'."""
    return str(int(valor)) if float(valor).is_integer() else str(valor).replace(".", ",")


