# Demo 1 · Generador de cotizaciones (Excel → PDF)

Crea cotizaciones en **PDF listas para enviar o imprimir** a partir de una planilla Excel con el inventario y los datos de la empresa. El vendedor solo ingresa **al cliente y los productos (código + cantidad)**; los precios, las descripciones, el logo y las condiciones salen solos. Cuando una cotización se acepta, **descuenta el stock** automáticamente.

Es un solo programa (doble clic en **`Abrir_cotizaciones.bat`**) con dos pestañas:

| Pestaña | Para qué |
|---|---|
| **Nueva cotización** | El vendedor elige al cliente y los productos; se genera el PDF y la cotización queda registrada en el Excel |
| **Procesar planilla** | Genera los PDF nuevos, mueve el stock y muestra en una tabla **cada error con su hoja, su celda y cómo corregirlo** |

Pensado para pymes que hoy arman cada cotización a mano copiando precios y datos de un lado a otro.

![Pestaña Nueva cotización](docs/formulario.png)

![Pestaña Procesar planilla](docs/procesar.png)

![Ejemplo de cotización generada](docs/ejemplo_cotizacion.png)

> Datos 100 % ficticios: "Ferretería El Martillo SpA" no existe.

---

## ¿Qué problema resuelve?

| Antes | Con el generador |
|---|---|
| Copiar a mano los precios y las descripciones de cada producto | Se escribe el código (o se elige de una lista) y el resto sale del Inventario |
| Calcular neto e IVA a mano, con errores de redondeo | Neto, IVA y total siempre cuadran |
| Errores de digitación (RUT, códigos) que se descubren tarde | Se detectan todos juntos, indicando la celda exacta |
| Actualizar el stock a mano después de cada venta | Al marcar una cotización como `aceptada`, el stock se descuenta solo |

---

## Uso

Doble clic en **`Abrir_cotizaciones.bat`** (o `python app.py`).

La primera vez se crea `datos/cotizaciones.xlsx` (y `datos/assets/` con el logo) como copia de la planilla de ejemplo. **Esa es la planilla de trabajo**; la de `datos_ejemplo/` nunca se modifica. El botón **Abrir planilla** siempre abre la correcta. La carpeta `datos/` **nunca se sube al repositorio**.

### Pestaña "Nueva cotización"

- **RUT validado mientras se escribe**: verde si es válido, rojo si no lo es.
- **Clientes recordados**: si el RUT ya cotizó antes, se completan nombre, contacto y email.
- **Productos desde el Inventario**: se busca escribiendo parte del código o del nombre y se ve el stock. Si se cotiza más de lo que hay, aparece un aviso en naranjo, pero se puede cotizar igual.
- **Guardar y generar PDF**: crea el PDF y agrega la cotización al Excel como `pendiente`, con número correlativo.
- Si alguien cambia precios o stock en el Excel, el formulario se actualiza solo al volver a esta pestaña.

### Pestaña "Procesar planilla"

Botón **▶ Procesar planilla**. Hace, en orden:
1. **Revisa la hoja Empresa.** Si falta un dato obligatorio, se detiene **sin generar nada** (y el formulario queda bloqueado hasta corregirla).
2. **Valida cada cotización** contra el Inventario.
3. **Genera los PDF nuevos.** Los que ya existen **no se sobrescriben**, porque son lo que se le envió al cliente con los precios de ese día. Para regenerar uno, hay que borrar el PDF.
4. **Mueve el stock** según el estado de cada cotización (ver más abajo).
5. **Muestra el resultado**:
   - tarjetas con el resumen (PDF nuevos, cotizaciones con errores, advertencias, movimientos de stock);
   - una tabla de **errores y advertencias** con el N° de cotización, el cliente, **dónde** está el problema (por ejemplo `Detalle B16`) y el problema. Al seleccionar una fila se muestra **cómo corregirlo**;
   - una tabla de **PDF y stock**: doble clic en un PDF para abrirlo.

Con la planilla de ejemplo (que trae errores a propósito):

| Tipo | N° | Dónde | Problema | Cómo corregir |
|---|---|---|---|---|
| ✗ Error | 1003 | Cotizaciones C4 | RUT del cliente inválido: 76.555.444-1 | Revise los números y el dígito verificador |
| ✗ Error | 1005 | Detalle | No tiene productos | Agregue filas en Detalle con n_cotizacion 1005 |
| ✗ Error | 1006 | Detalle B16 | El código XYZ-99 no existe en Inventario | Elija un código de la lista desplegable |
| ✗ Error | 1006 | Detalle C17 | Producto CLA-4: la cantidad debe ser mayor que 0 | Escriba un número mayor que 0 |
| ⚠ Advertencia | 1004 | Detalle C15 | Producto ESM-01: se cotizan 3 y hay 2 en stock | Se puede cotizar igual |

### Versión de consola (opcional)

`python generar.py` hace exactamente lo mismo que "Procesar planilla", pero imprime el resultado como texto. Sirve para automatizarlo, por ejemplo para que corra solo cada mañana.

---

## Cómo llenar la planilla

La planilla tiene 4 hojas. Las columnas con **encabezado azul** las llena el usuario; las de **encabezado gris** las llena una fórmula o el programa, así que no se escriben.

### 1. `Empresa`: se llena una sola vez

| campo | Obligatorio | Ejemplo |
|---|---|---|
| `razon_social` | ✅ | Ferretería El Martillo SpA |
| `rut` | ✅ | 77.654.321-7 (se valida el dígito verificador) |
| `giro` | | Venta al por menor de artículos de ferretería |
| `direccion` | ✅ | Av. Ejemplo 1234, Santiago |
| `telefono` | ✅ | +56 9 1234 5678 |
| `email` | ✅ | ventas@gmail.com |
| `sitio_web` | | www.miferreteria.cl (si está vacío, no aparece) |
| `logo` | | `assets/logo.png`: ruta **relativa a la carpeta de la planilla**. PNG o JPG |
| `validez_dias` | ✅ | 15 |
| `condiciones_pago` | ✅ | 50% al confirmar y 50% contra entrega |

- Si falta un dato obligatorio o está mal, **no se genera ningún PDF** y el reporte dice qué corregir.
- **Logo:** si la celda está vacía, el PDF sale sin logo. Si tiene una ruta pero el archivo no existe, el PDF también sale sin logo y el reporte muestra una advertencia. Basta con copiar el archivo a la carpeta `assets/` para que aparezca.

### 2. `Inventario`: la empresa lo mantiene al día

| codigo | descripcion | unidad | precio_unitario_iva | stock |
|---|---|---|---|---|
| CEM-25 | Cemento saco 25 kg | saco | 5490 | 120 |

- **Los precios van con IVA incluido.** Al cambiar un precio aquí, las cotizaciones **nuevas** usan el precio nuevo.
- El código debe ser único. El `stock` lo actualiza el programa al aceptar o rechazar cotizaciones; también se puede corregir a mano (por ejemplo, cuando llega mercadería).

### 3. `Cotizaciones`: una fila por cotización

| n_cotizacion | fecha | rut_cliente | razon_social | contacto | email | observaciones | estado ▼ | stock_descontado |
|---|---|---|---|---|---|---|---|---|
| 1001 | 20-11-2026 | 76.123.456-0 | Constructora Los Robles SpA | Ana Pérez | ana@ejemplo.cl | Despacho incluido | aceptada | *(lo llena el programa)* |

- `estado` tiene una lista desplegable: `pendiente` (el valor si se deja vacío), `aceptada` o `rechazada`.
- `stock_descontado` **no se escribe a mano**: el programa anota ahí la fecha en que descontó el stock.

### 4. `Detalle`: los productos de cada cotización

| n_cotizacion ✏️ | codigo ▼ ✏️ | cantidad ✏️ | descripcion | unidad | precio_unitario_iva | total |
|---|---|---|---|---|---|---|
| 1001 | CEM-25 | 40 | *Cemento saco 25 kg* | *saco* | *$5.490* | *$219.600* |

- **Solo se escriben las 3 primeras columnas.** `codigo` tiene una lista desplegable con los códigos del Inventario, y Excel rechaza cantidades de 0 o menos.
- Las columnas grises son **fórmulas** (BUSCARV) que muestran la descripción y el precio mientras se escribe. Si un código no existe, aparece *¡Código no existe!*.
- El programa **no usa esas fórmulas**: vuelve a buscar todo en el Inventario. Así, aunque alguien escriba encima de una fórmula, el PDF sale correcto.

### Stock: qué pasa según el estado

| estado | stock_descontado | El programa... |
|---|---|---|
| `aceptada` | vacío | **Descuenta** el stock y anota la fecha |
| `aceptada` | con fecha | Nada (ya lo hizo; nunca descuenta dos veces) |
| `pendiente` / `rechazada` | con fecha | **Devuelve** el stock y borra la fecha |
| `pendiente` / `rechazada` | vacío | Nada |

Una **cotización no es una venta**: el stock solo baja cuando el cliente acepta. Si no hay stock suficiente para aceptar, **no se descuenta nada** de esa cotización y se informa como error, así el inventario nunca queda negativo.

---

## Decisiones de diseño

- **Python no confía en las fórmulas de Excel.** openpyxl escribe fórmulas pero no las calcula (eso lo hace Excel al abrir el archivo), así que su valor puede no existir. Las fórmulas son solo para que el usuario vea los datos; el programa busca todo en `Inventario`.
- **BUSCARV y no BUSCARX.** BUSCARX solo existe en Excel 2021/365; en versiones anteriores la celda muestra `#¿NOMBRE?`.
- **Lista desplegable vinculada a un nombre** (`CodigosInventario`), no directamente a otra hoja: es lo más compatible entre versiones de Excel, y el programa la vuelve a crear cada vez que guarda.
- **Precios con IVA.** `neto = total / 1,19` e `IVA = total − neto`: como el IVA se obtiene **restando**, siempre cuadra. Para redondear se usa `Decimal` ("0,5 sube"), porque el `round()` de Python usa redondeo bancario.
- **Errores y advertencias.** Un error impide generar el PDF; una advertencia (por ejemplo, poco stock) se informa pero no lo impide. Cada cotización lista **todos** sus problemas a la vez.
- **Los PDF no se sobrescriben.** Los precios cambian, pero el PDF enviado es un compromiso con el cliente.
- **Movimientos de stock idempotentes.** La columna `stock_descontado` permite ejecutar el programa muchas veces sin descontar dos veces.
- **Un módulo por responsabilidad.** `inventario.py` calcula los movimientos **sin tocar archivos** (por eso es fácil de testear) y `escritura.py` los aplica.
- **Lógica separada de la pantalla.** `proceso.py` no imprime ni dibuja nada: retorna un `Resultado`. La pestaña "Procesar planilla" y `generar.py` (consola) lo muestran cada una a su manera, así que se comportan igual y la lógica se testea sin abrir ventanas.
- **Cada problema sabe dónde está.** `lectura.py` recuerda la fila de Excel de cada dato, y cada problema guarda su columna y una sugerencia (`Problema` hereda de `str`, así el resto del código lo sigue tratando como texto). `proceso.py` lo traduce a una celda, por ejemplo `Detalle B16`.

## Estructura del código

```
demo1-generador-documentos/
├── app.py                     ← programa con pestañas (tkinter): formulario + procesar
├── generar.py                 ← versión de consola de "Procesar planilla"
├── Abrir_cotizaciones.bat     ← doble clic para abrir app.py
├── generador/
│   ├── config.py              ← rutas compartidas
│   ├── plantilla.py           ← hojas, columnas, fórmulas BUSCARV y listas desplegables
│   ├── lectura.py             ← Excel → datos de Python (recuerda la fila de cada dato)
│   ├── validaciones.py        ← RUT (módulo 11), hoja Empresa, cotizaciones vs Inventario
│   ├── proceso.py             ← "Procesar planilla" sin pantalla: retorna un Resultado
│   ├── inventario.py          ← completar productos y calcular movimientos de stock
│   ├── escritura.py           ← guardar cotizaciones y aplicar movimientos en el Excel
│   ├── calculos.py            ← neto, IVA, total, formato $1.234.567
│   └── pdf.py                 ← diseño del documento (reportlab)
├── herramientas/
│   └── crear_planilla_ejemplo.py  ← crea la planilla y el logo de ejemplo
├── tests/                     ← 108 tests con pytest
├── datos_ejemplo/             ← planilla y logo ficticios (no se modifican)
├── datos/                     ← planilla de trabajo (no se sube al repo)
└── salida/                    ← PDF generados (no se suben al repo)
```

## Instalación (desarrollo)

Requiere Python 3.12 o superior.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest                                       # ejecutar los tests
python -m herramientas.crear_planilla_ejemplo  # regenerar la planilla de ejemplo
```

## Limitaciones conocidas

- Si se modifica el `Detalle` de una cotización **después** de descontar su stock, la devolución usa las cantidades nuevas. Lo correcto es rechazar la cotización y crear una nueva.
- El programa guarda la planilla con openpyxl: se conservan los formatos, las fórmulas y las listas, pero no gráficos ni imágenes que alguien agregue al Excel.
- Si el Excel está abierto, Windows no deja guardar: el programa lo avisa y no modifica nada.

## Próximos pasos

- [x] Formulario para el vendedor (tkinter)
- [x] Hoja Empresa con logo y condiciones
- [x] Inventario con stock y descuento al aceptar
- [x] Una sola app con pestañas y reporte de errores con hoja, celda y cómo corregir
- [ ] Buscar y reimprimir cotizaciones anteriores desde el formulario
- [ ] Cambiar el estado de una cotización desde el formulario
- [ ] Empaquetar como `.exe` con PyInstaller (sin instalar Python)

## Tecnologías

Python · tkinter · pandas · openpyxl · reportlab · Pillow · pytest
