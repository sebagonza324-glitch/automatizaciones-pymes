"""
crear_planilla_ejemplo.py
-------------------------
Crea datos_ejemplo/cotizaciones_ejemplo.xlsx y datos_ejemplo/assets/logo.png
con datos 100 % FICTICIOS. Sirve también como plantilla para un cliente nuevo:
se cambian los datos de este archivo y se vuelve a ejecutar.

Uso (desde demo1-generador-documentos):
    python -m herramientas.crear_planilla_ejemplo

Los casos de prueba están puestos a propósito para mostrar el reporte:
    1001 aceptada   -> se descuenta del stock la primera vez
    1002 pendiente  -> OK
    1003 pendiente  -> RUT inválido (error)
    1004 pendiente  -> pide más esmeriles que el stock (advertencia)
    1005 pendiente  -> sin productos (error)
    1006 pendiente  -> código inexistente y cantidad 0 (errores)
    1007 rechazada  -> no hace nada
"""

from datetime import date

from PIL import Image, ImageDraw, ImageFont

from generador.config import PLANILLA_EJEMPLO
from generador.plantilla import crear_planilla


def _rut(numero, dv=None):
    """Arma un RUT con puntos; calcula el dígito verificador si no se entrega."""
    if dv is None:
        suma, mult = 0, 2
        for d in reversed(str(numero)):
            suma += int(d) * mult
            mult = 2 if mult == 7 else mult + 1
        r = 11 - suma % 11
        dv = "0" if r == 11 else "K" if r == 10 else str(r)
    return f"{numero:,}".replace(",", ".") + "-" + dv


EMPRESA = [
    ("razon_social", "Ferretería El Martillo SpA (ficticia)", "Obligatorio. Nombre legal de la empresa."),
    ("rut", _rut(77654321), "Obligatorio. Con puntos y guion: 77.654.321-7"),
    ("giro", "Venta al por menor de artículos de ferretería", "Opcional."),
    ("direccion", "Av. Ejemplo 1234, Santiago", "Obligatorio."),
    ("telefono", "+56 9 1234 5678", "Obligatorio."),
    ("email", "ventas@elmartillo.example", "Obligatorio. Correo de contacto, por ejemplo ventas@gmail.com"),
    ("sitio_web", "www.elmartillo.example", "Opcional. Si se deja vacío no aparece en el PDF."),
    ("logo", "assets/logo.png", "Opcional. Ruta del logo (PNG o JPG) relativa a la carpeta de esta "
                                "planilla. Si está vacío o no existe, el PDF sale sin logo."),
    ("validez_dias", 15, "Obligatorio. Días de validez de cada cotización."),
    ("condiciones_pago", "50% al confirmar el pedido y 50% contra entrega. "
                         "Transferencia bancaria o efectivo.",
     "Obligatorio. Se imprime al pie de cada cotización."),
]

INVENTARIO = [
    # codigo, descripcion, unidad, precio con IVA, stock
    ("CEM-25", "Cemento saco 25 kg", "saco", 5490, 120),
    ("FIE-8", "Fierro estriado 8 mm x 6 m", "unidad", 3290, 200),
    ("FIE-10", "Fierro estriado 10 mm x 6 m", "unidad", 4990, 150),
    ("ARE-01", "Arena gruesa (saco 25 kg)", "saco", 1990, 80),
    ("GRA-01", "Gravilla (saco 25 kg)", "saco", 2190, 60),
    ("TAL-01", "Taladro percutor 650W", "unidad", 39990, 4),
    ("ESM-01", "Esmeril angular 4 1/2\" 850W", "unidad", 34990, 2),
    ("SIE-01", "Sierra circular 7 1/4\" 1400W", "unidad", 69990, 3),
    ("MAR-16", "Martillo carpintero 16 oz", "unidad", 7990, 25),
    ("DES-SET", "Set destornilladores 6 piezas", "set", 8990, 18),
    ("HUI-5", "Huincha de medir 5 m", "unidad", 3990, 30),
    ("NIV-60", "Nivel de aluminio 60 cm", "unidad", 9990, 12),
    ("CLA-25", "Clavo corriente 2,5\" (kg)", "kg", 1890, 90),
    ("CLA-4", "Clavo corriente 4\" (kg)", "kg", 1790, 70),
    ("TOR-6", "Tornillo volcanita 6x1\" (caja 100)", "caja", 2990, 40),
    ("TAR-8", "Tarugo plástico 8 mm (bolsa 100)", "bolsa", 2490, 35),
    ("PIN-GL", "Pintura látex blanca 1 galón", "galón", 14990, 22),
    ("PIN-ESM", "Esmalte sintético 1/4 galón", "unidad", 8990, 0),
    ("BRO-3", "Brocha 3\"", "unidad", 2490, 45),
    ("RODI-9", "Rodillo 9\" con bandeja", "unidad", 6990, 15),
    ("LIJ-120", "Lija al agua grano 120", "pliego", 590, 300),
    ("PLA-15", "Plancha OSB 15 mm", "unidad", 18990, 30),
    ("VOL-10", "Plancha volcanita 10 mm 1,2 x 2,4 m", "unidad", 7990, 50),
    ("PVC-110", "Tubo PVC sanitario 110 mm x 3 m", "unidad", 8990, 20),
    ("COD-110", "Codo PVC 110 mm 45°", "unidad", 1290, 60),
    ("TEF-12", "Cinta teflón 12 mm", "unidad", 590, 100),
    ("LLA-PA", "Llave de paso 1/2\"", "unidad", 7490, 10),
    ("SIL-01", "Silicona transparente 280 ml", "unidad", 3490, 40),
    ("GUA-01", "Guantes de trabajo (par)", "par", 1990, 50),
    ("LEN-01", "Lentes de seguridad", "unidad", 2990, 35),
]

COTIZACIONES = [
    # n, fecha, rut, razón social, contacto, email, observaciones, estado
    (1001, date(2026, 11, 20), _rut(76123456), "Constructora Los Robles SpA", "Ana Pérez",
     "ana@ejemplo.cl", "Despacho incluido en Santiago", "aceptada"),
    (1002, date(2026, 11, 21), _rut(12345678), "Juan Soto (particular)", "Juan Soto",
     "juan@ejemplo.cl", "", "pendiente"),
    (1003, date(2026, 11, 22), _rut(76555444, dv="1"), "Inmobiliaria Prueba Ltda.", "Carla Díaz",
     "carla@ejemplo.cl", "RUT inválido a propósito", "pendiente"),
    (1004, date(2026, 11, 24), _rut(76987654), "Gasfitería Rápida SpA", "Pedro Rojas",
     "pedro@ejemplo.cl", "Pide más esmeriles que el stock a propósito", "pendiente"),
    (1005, date(2026, 11, 25), _rut(15876543), "María González (particular)", "María González",
     "maria@ejemplo.cl", "Sin productos a propósito", "pendiente"),
    (1006, date(2026, 11, 25), _rut(76345678), "Comercial Sur Ltda.", "Luis Muñoz",
     "luis@ejemplo.cl", "Código inexistente y cantidad 0 a propósito", "pendiente"),
    (1007, date(2026, 11, 26), _rut(77222333), "Taller Mecánico Díaz SpA", "Rosa Díaz",
     "rosa@ejemplo.cl", "", "rechazada"),
]

DETALLE = [
    (1001, "CEM-25", 40), (1001, "FIE-8", 60), (1001, "TAL-01", 2), (1001, "CLA-25", 10),
    (1002, "PIN-GL", 3), (1002, "BRO-3", 2), (1002, "RODI-9", 1),
    (1003, "PLA-15", 20), (1003, "TOR-6", 5),
    (1004, "PVC-110", 8), (1004, "COD-110", 12), (1004, "TEF-12", 10), (1004, "LLA-PA", 3),
    (1004, "ESM-01", 3),
    (1006, "XYZ-99", 5), (1006, "CLA-4", 0),
    (1007, "GUA-01", 10), (1007, "LEN-01", 10),
]


def crear_logo(ruta):
    """Logo ficticio simple: cuadrado azul redondeado con las iniciales."""
    escala = 4   # se dibuja grande y se achica, para bordes suaves
    lado = 160 * escala
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, lado - 1, lado - 1), radius=32 * escala, fill="#1F4E78")
    d.rounded_rectangle((14 * escala, 14 * escala, lado - 14 * escala, lado - 14 * escala),
                        radius=22 * escala, outline="#F2A900", width=5 * escala)
    try:
        fuente = ImageFont.truetype("arialbd.ttf", 70 * escala)
    except OSError:
        fuente = ImageFont.load_default(size=70 * escala)
    d.text((lado / 2, lado / 2), "EM", font=fuente, fill="white", anchor="mm")
    img.resize((160, 160), Image.LANCZOS).save(ruta)


def main():
    columnas_cot = ["n_cotizacion", "fecha", "rut_cliente", "razon_social", "contacto",
                    "email", "observaciones", "estado"]
    crear_planilla(
        PLANILLA_EJEMPLO,
        empresa=[dict(zip(("campo", "valor", "ayuda"), f)) for f in EMPRESA],
        inventario=[dict(zip(("codigo", "descripcion", "unidad", "precio_unitario_iva", "stock"), f))
                    for f in INVENTARIO],
        cotizaciones=[dict(zip(columnas_cot, f)) for f in COTIZACIONES],
        detalle=[dict(zip(("n_cotizacion", "codigo", "cantidad"), f)) for f in DETALLE],
    )
    carpeta_assets = PLANILLA_EJEMPLO.parent / "assets"
    carpeta_assets.mkdir(exist_ok=True)
    crear_logo(carpeta_assets / "logo.png")
    print(f"Creado: {PLANILLA_EJEMPLO}")
    print(f"Creado: {carpeta_assets / 'logo.png'}")


if __name__ == "__main__":
    main()
