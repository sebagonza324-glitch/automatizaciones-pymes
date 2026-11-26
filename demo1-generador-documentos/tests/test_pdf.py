"""Tests de pdf.py: el PDF se genera con logo, sin logo y con un logo dañado."""

from datetime import date

import pytest

from generador.config import PLANILLA_EJEMPLO
from generador.pdf import generar_pdf, nombre_archivo

EMPRESA = {
    "razon_social": "Ferretería de Prueba SpA", "rut": "77.654.321-7", "giro": "",
    "direccion": "Calle 1", "telefono": "+56 9 1111 1111", "email": "ventas@gmail.com",
    "sitio_web": "", "validez_dias": "15", "condiciones_pago": "Contado",
}
COTIZACION = {
    "n_cotizacion": 1, "fecha": date(2026, 11, 26), "rut_cliente": "76.123.456-0",
    "razon_social": "Gasfitería Rápida SpA", "contacto": "", "email": "", "observaciones": "",
}
ITEMS = [{"codigo": "MAR-16", "descripcion": "Martillo", "unidad": "unidad",
          "cantidad": 2, "precio_unitario_iva": 7990}]


def es_pdf(ruta):
    return ruta.exists() and ruta.read_bytes()[:5] == b"%PDF-"


def test_pdf_con_logo(tmp_path):
    ruta = tmp_path / "con_logo.pdf"
    generar_pdf(EMPRESA, COTIZACION, ITEMS, ruta, PLANILLA_EJEMPLO.parent / "assets" / "logo.png")
    assert es_pdf(ruta)


def test_pdf_sin_logo(tmp_path):
    ruta = tmp_path / "sin_logo.pdf"
    generar_pdf(EMPRESA, COTIZACION, ITEMS, ruta, None)
    assert es_pdf(ruta)


def test_logo_danado_no_rompe_el_pdf(tmp_path):
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"esto no es una imagen")
    ruta = tmp_path / "logo_malo.pdf"
    generar_pdf(EMPRESA, COTIZACION, ITEMS, ruta, logo)
    assert es_pdf(ruta)


@pytest.mark.parametrize("razon, esperado", [
    ("Gasfitería Rápida SpA", "cotizacion_1_Gasfiteria_Rapida_SpA.pdf"),
    ("Muñoz & Cía. Ltda.", "cotizacion_1_Munoz_Cia_Ltda.pdf"),
])
def test_nombre_archivo_sin_tildes(razon, esperado):
    assert nombre_archivo({**COTIZACION, "razon_social": razon}) == esperado
