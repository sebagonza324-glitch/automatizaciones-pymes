"""
generar.py
----------
Generación MASIVA: lee la planilla completa, valida cada cotización, genera
un PDF por cada una que esté correcta y al final muestra un reporte con los
problemas encontrados.

(Para crear cotizaciones de a una con una ventana, usar formulario.py.)

Uso:
    python generar.py                       -> usa datos/cotizaciones.xlsx
    python generar.py ruta/a/planilla.xlsx  -> usa otra planilla
"""

import sys
from pathlib import Path

from generador.config import CARPETA_SALIDA, preparar_planilla
from generador.lectura import leer_planilla
from generador.pdf import generar_pdf, nombre_archivo
from generador.validaciones import validar_cotizacion


def main():
    # Mostrar bien tildes y ñ en la consola de Windows.
    sys.stdout.reconfigure(encoding="utf-8")

    planilla = Path(sys.argv[1]) if len(sys.argv) > 1 else preparar_planilla()
    print(f"Leyendo planilla: {planilla}\n")

    try:
        empresa, cotizaciones = leer_planilla(planilla)
    except FileNotFoundError:
        print(f"ERROR: no se encontró la planilla {planilla}")
        return 1
    except ValueError as e:  # columnas u hojas faltantes
        print(f"ERROR en la planilla: {e}")
        return 1

    CARPETA_SALIDA.mkdir(exist_ok=True)
    generadas, con_problemas = [], []

    for cot in cotizaciones:
        problemas = validar_cotizacion(cot)
        if problemas:
            con_problemas.append((cot, problemas))
            continue

        ruta = CARPETA_SALIDA / nombre_archivo(cot)
        try:
            generar_pdf(empresa, cot, ruta)
            generadas.append(ruta)
            print(f"  [OK] Cotización N° {cot['n_cotizacion']} -> {ruta.name}")
        except PermissionError:
            # Típico en Windows: el PDF anterior está abierto en el lector.
            con_problemas.append((cot, [f"No se pudo guardar {ruta.name}: "
                                        "ciérrelo si lo tiene abierto y vuelva a intentar"]))

    # --- Reporte final ---
    print(f"\nResumen: {len(generadas)} PDF generados, "
          f"{len(con_problemas)} cotizaciones con problemas.")

    if con_problemas:
        print("\nRevise en la planilla y vuelva a ejecutar:")
        for cot, problemas in con_problemas:
            print(f"\n  Cotización N° {cot['n_cotizacion']} ({cot['razon_social'] or 'sin nombre'}):")
            for p in problemas:
                print(f"    - {p}")

    print(f"\nLos PDF quedaron en: {CARPETA_SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
