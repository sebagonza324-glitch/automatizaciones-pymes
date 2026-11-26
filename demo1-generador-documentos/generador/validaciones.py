"""
validaciones.py
---------------
Reglas para decidir si una cotización está lista para convertirse en PDF.

Las funciones de este módulo NUNCA lanzan errores por datos malos: solo
responden True/False (o una lista de problemas). Quien las llama decide qué
hacer con esa información (por ejemplo, juntar todo en un reporte final).
"""

import math


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


def validar_cotizacion(cotizacion):
    """
    Revisa una cotización completa (dict con su lista de "items").

    Retorna una LISTA de problemas en lenguaje simple. Lista vacía = todo OK.
    Así el usuario ve todos los errores de una vez y los corrige juntos,
    en vez de corregir, ejecutar y descubrir el siguiente error.
    """
    problemas = []

    if not rut_es_valido(cotizacion.get("rut_cliente")):
        rut = cotizacion.get("rut_cliente") or "(vacío)"
        problemas.append(f"RUT del cliente inválido: {rut}")

    if not cotizacion.get("razon_social"):
        problemas.append("Falta la razón social (nombre) del cliente")

    if not cotizacion.get("fecha"):
        problemas.append("Falta la fecha")

    items = cotizacion.get("items", [])
    if not items:
        problemas.append("No tiene productos")

    for item in items:
        codigo = item.get("codigo") or "(sin código)"
        if not item.get("descripcion"):
            problemas.append(f"Producto {codigo}: falta la descripción")
        if not _es_numero_positivo(item.get("cantidad")):
            problemas.append(
                f"Producto {codigo}: la cantidad debe ser mayor que 0 "
                f"(tiene {item.get('cantidad')})"
            )
        if not _es_numero_positivo(item.get("precio_unitario_iva")):
            problemas.append(
                f"Producto {codigo}: el precio debe ser mayor que 0 "
                f"(tiene {item.get('precio_unitario_iva')})"
            )

    return problemas
