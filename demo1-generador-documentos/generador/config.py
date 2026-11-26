"""
config.py
---------
Rutas que comparten todos los programas de la demo.

La planilla de TRABAJO (datos/cotizaciones.xlsx) es distinta de la de EJEMPLO:
  - La primera vez se crea copiando la de ejemplo.
  - El formulario escribe en la de trabajo, así la de ejemplo queda intacta.
  - La carpeta datos/ está en .gitignore: los datos reales nunca se suben.
"""

import shutil
from pathlib import Path

CARPETA_DEMO = Path(__file__).resolve().parent.parent
PLANILLA_EJEMPLO = CARPETA_DEMO / "datos_ejemplo" / "cotizaciones_ejemplo.xlsx"
PLANILLA_TRABAJO = CARPETA_DEMO / "datos" / "cotizaciones.xlsx"
CARPETA_SALIDA = CARPETA_DEMO / "salida"


def preparar_planilla():
    """Retorna la ruta de la planilla de trabajo, creándola si no existe."""
    if not PLANILLA_TRABAJO.exists():
        PLANILLA_TRABAJO.parent.mkdir(exist_ok=True)
        shutil.copy(PLANILLA_EJEMPLO, PLANILLA_TRABAJO)
    return PLANILLA_TRABAJO
