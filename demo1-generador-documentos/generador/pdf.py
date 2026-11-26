"""
pdf.py
------
Dibuja una cotización en PDF con reportlab.

Se usa "platypus", la parte de reportlab que arma el documento con bloques
(párrafos, tablas, imágenes, espacios) uno debajo del otro, como en Word.
Así no hay que calcular coordenadas a mano.

Los datos de la empresa (nombre, RUT, logo, validez, condiciones de pago)
salen de la hoja Empresa: nada está escrito a mano en este archivo.
"""

import re
import unicodedata
from datetime import timedelta

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .calculos import calcular_totales, formato_cantidad, formato_pesos, total_linea

# --- Estilo visual (cambiar aquí para adaptar a cada cliente) ---
COLOR_PRINCIPAL = colors.HexColor("#1F4E78")
COLOR_SUAVE = colors.HexColor("#EAF1F8")
COLOR_LINEA = colors.HexColor("#B7C9DB")
ALTO_LOGO = 2.2 * cm

_base = getSampleStyleSheet()
ESTILO_NORMAL = ParagraphStyle("normal", parent=_base["Normal"], fontSize=9, leading=12)
ESTILO_EMPRESA = ParagraphStyle("empresa", parent=ESTILO_NORMAL, fontSize=14,
                                leading=17, textColor=COLOR_PRINCIPAL, fontName="Helvetica-Bold")
ESTILO_TITULO = ParagraphStyle("titulo", parent=ESTILO_NORMAL, fontSize=16, leading=20,
                               alignment=TA_RIGHT, textColor=COLOR_PRINCIPAL,
                               fontName="Helvetica-Bold")
ESTILO_DERECHA = ParagraphStyle("derecha", parent=ESTILO_NORMAL, alignment=TA_RIGHT)
ESTILO_CELDA = ParagraphStyle("celda", parent=ESTILO_NORMAL, fontSize=8.5, leading=11)
ESTILO_PIE = ParagraphStyle("pie", parent=ESTILO_NORMAL, fontSize=7.5,
                            textColor=colors.grey, leading=10)
ESTILO_SUBTITULO = ParagraphStyle("subtitulo", parent=ESTILO_NORMAL, fontName="Helvetica-Bold",
                                  textColor=COLOR_PRINCIPAL)


def nombre_archivo(cotizacion):
    """'Gasfitería Rápida SpA' -> 'cotizacion_1004_Gasfiteria_Rapida_SpA.pdf'"""
    # Quitar tildes (í -> i, ñ -> n) para evitar problemas al adjuntar el archivo
    # en correos o WhatsApp, y reemplazar todo lo que no sea letra/número por "_".
    sin_tildes = unicodedata.normalize("NFKD", cotizacion["razon_social"])
    sin_tildes = sin_tildes.encode("ascii", "ignore").decode("ascii")
    nombre = re.sub(r"[^A-Za-z0-9]+", "_", sin_tildes).strip("_")
    return f"cotizacion_{cotizacion['n_cotizacion']}_{nombre[:40]}.pdf"


def _fecha(f):
    """date -> '20-11-2026'."""
    return f.strftime("%d-%m-%Y")


def _logo(ruta_logo):
    """Imagen del logo con alto fijo y ancho proporcional. None si no hay o falla."""
    if ruta_logo is None:
        return None
    try:
        ancho, alto = ImageReader(str(ruta_logo)).getSize()
        return Image(str(ruta_logo), width=ALTO_LOGO * ancho / alto, height=ALTO_LOGO)
    except Exception:
        return None   # archivo dañado o formato raro: el PDF sale sin logo


def _encabezado(empresa, cotizacion, ruta_logo):
    """[logo] datos de la empresa | N°, fecha y validez a la derecha."""
    datos = [
        Paragraph(empresa["razon_social"], ESTILO_EMPRESA),
        Paragraph(f"RUT: {empresa['rut']}", ESTILO_NORMAL),
    ]
    if empresa.get("giro"):
        datos.append(Paragraph(empresa["giro"], ESTILO_NORMAL))
    datos.append(Paragraph(empresa["direccion"], ESTILO_NORMAL))
    datos.append(Paragraph(f"{empresa['telefono']} · {empresa['email']}", ESTILO_NORMAL))
    if empresa.get("sitio_web"):
        datos.append(Paragraph(empresa["sitio_web"], ESTILO_NORMAL))

    fecha = cotizacion["fecha"]
    vence = fecha + timedelta(days=int(float(empresa["validez_dias"])))
    derecha = [
        Paragraph("COTIZACIÓN", ESTILO_TITULO),
        Paragraph(f"<b>N° {cotizacion['n_cotizacion']}</b>", ESTILO_DERECHA),
        Paragraph(f"Fecha: {_fecha(fecha)}", ESTILO_DERECHA),
        Paragraph(f"Válida hasta: {_fecha(vence)}", ESTILO_DERECHA),
    ]

    logo = _logo(ruta_logo)
    if logo:
        ancho_logo = logo.drawWidth + 0.4 * cm
        fila = [[logo, datos, derecha]]
        anchos = [ancho_logo, 11.5 * cm - ancho_logo, 6.5 * cm]
    else:
        fila = [[datos, derecha]]
        anchos = [11.5 * cm, 6.5 * cm]

    tabla = Table(fila, colWidths=anchos)
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, COLOR_PRINCIPAL),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
    ]))
    return tabla


def _datos_cliente(cotizacion):
    """Recuadro con los datos del cliente."""
    filas = [
        ["Cliente:", cotizacion["razon_social"], "RUT:", cotizacion["rut_cliente"]],
        ["Contacto:", cotizacion.get("contacto", ""), "Email:", cotizacion.get("email", "")],
    ]
    tabla = Table(filas, colWidths=[2.2 * cm, 8.3 * cm, 1.5 * cm, 6 * cm])
    tabla.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_SUAVE),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _tabla_productos(items):
    """Tabla de productos: código, descripción, unidad, cantidad, precios."""
    filas = [["Código", "Descripción", "Unidad", "Cant.", "Precio unit.", "Total"]]
    for item in items:
        filas.append([
            item["codigo"],
            Paragraph(item["descripcion"], ESTILO_CELDA),  # Paragraph: texto largo baja de línea
            item["unidad"],
            formato_cantidad(item["cantidad"]),
            formato_pesos(item["precio_unitario_iva"]),
            formato_pesos(total_linea(item)),
        ])

    tabla = Table(filas, colWidths=[2 * cm, 7.2 * cm, 1.8 * cm, 1.4 * cm, 2.7 * cm, 2.9 * cm],
                  repeatRows=1)  # si hay muchas filas, el encabezado se repite en cada página
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRINCIPAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),           # números a la derecha
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_SUAVE]),  # filas alternadas
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, COLOR_LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _tabla_totales(items):
    """Subtotal neto, IVA y total, alineados a la derecha."""
    t = calcular_totales(items)
    filas = [
        ["Subtotal neto", formato_pesos(t["neto"])],
        ["IVA (19%)", formato_pesos(t["iva"])],
        ["TOTAL", formato_pesos(t["total"])],
    ]
    tabla = Table(filas, colWidths=[3.5 * cm, 3 * cm], hAlign="RIGHT")
    tabla.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("BACKGROUND", (0, -1), (-1, -1), COLOR_PRINCIPAL),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def generar_pdf(empresa, cotizacion, items, ruta_salida, ruta_logo=None):
    """
    Crea el PDF de UNA cotización en 'ruta_salida'.

    items:     productos ya completados con el Inventario (inventario.completar_items)
    ruta_logo: Path del logo, o None para un PDF sin logo
    """
    doc = SimpleDocTemplate(
        str(ruta_salida), pagesize=letter,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"Cotización N° {cotizacion['n_cotizacion']}",
        author=empresa["razon_social"],
    )

    bloques = [
        _encabezado(empresa, cotizacion, ruta_logo),
        Spacer(1, 0.5 * cm),
        _datos_cliente(cotizacion),
        Spacer(1, 0.5 * cm),
        _tabla_productos(items),
        Spacer(1, 0.4 * cm),
        _tabla_totales(items),
        Spacer(1, 0.4 * cm),
        Paragraph("Precios unitarios con IVA incluido.", ESTILO_PIE),
    ]

    if cotizacion.get("observaciones"):
        bloques += [Spacer(1, 0.3 * cm),
                    Paragraph(f"<b>Observaciones:</b> {cotizacion['observaciones']}", ESTILO_NORMAL)]

    bloques += [
        Spacer(1, 0.5 * cm),
        Paragraph("Condiciones de pago", ESTILO_SUBTITULO),
        Spacer(1, 0.1 * cm),
        Paragraph(empresa["condiciones_pago"], ESTILO_NORMAL),
        Spacer(1, 1 * cm),
        Paragraph("Este documento es una cotización y no constituye documento tributario. "
                  "Generado automáticamente.", ESTILO_PIE),
    ]

    doc.build(bloques)
