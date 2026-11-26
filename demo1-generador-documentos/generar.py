"""
generar.py
----------
Versión de CONSOLA de "Procesar planilla" (la versión con ventana está en
app.py, pestaña "Procesar planilla"). Ambas usan generador/proceso.py, así
que hacen exactamente lo mismo; esta solo imprime el resultado como texto.

Sirve para automatizar (por ejemplo, programarla para que corra sola cada
mañana) o para usarla desde la terminal.

Uso:
    python generar.py                       -> usa datos/cotizaciones.xlsx
    python generar.py ruta/a/planilla.xlsx  -> usa otra planilla
"""

import sys
from pathlib import Path

from generador.config import CARPETA_SALIDA, preparar_planilla
from generador.proceso import procesar_planilla


def _titulo(texto):
    print(f"\n{texto}\n" + "-" * len(texto))


def _imprimir_avisos(avisos):
    for a in avisos:
        cotizacion = f"N° {a.n_cotizacion} · " if a.n_cotizacion else ""
        print(f"  {cotizacion}[{a.donde}] {a.mensaje}")
        if a.ayuda:
            print(f"      -> {a.ayuda}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")   # tildes y ñ en la consola de Windows

    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else preparar_planilla()
    print(f"Planilla: {ruta}")
    try:
        res = procesar_planilla(ruta)
    except (FileNotFoundError, ValueError) as e:
        print(f"\nERROR: no se pudo leer la planilla: {e}")
        return 1

    if res.empresa_bloqueada:
        _titulo("ERROR en la hoja Empresa: no se generó ningún PDF ni se movió stock")
        _imprimir_avisos(res.avisos)
        return 1

    _titulo("PDF")
    for n, ruta_pdf in res.pdfs_nuevos:
        print(f"  [OK] N° {n} -> {ruta_pdf.name}")
    for n, _ in res.pdfs_existentes:
        print(f"  [--] N° {n}: ya generada, se mantiene la original")

    if res.descontadas or res.devueltas:
        _titulo("Stock")
        for n in res.descontadas:
            print(f"  [-] N° {n} aceptada: stock descontado")
        for n in res.devueltas:
            print(f"  [+] N° {n} ya no está aceptada: stock devuelto")

    print(f"\nResumen: {len(res.pdfs_nuevos)} PDF nuevos, "
          f"{len(res.cotizaciones_con_errores)} cotizaciones con errores, "
          f"{len(res.advertencias)} advertencias.")
    if res.errores:
        _titulo("Errores (corrija en la planilla y vuelva a procesar)")
        _imprimir_avisos(res.errores)
    if res.advertencias:
        _titulo("Advertencias (no impiden generar)")
        _imprimir_avisos(res.advertencias)

    print(f"\nLos PDF están en: {CARPETA_SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
