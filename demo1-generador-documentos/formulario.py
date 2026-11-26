"""
formulario.py
-------------
Ventana para crear cotizaciones de a una, pensada para el vendedor:

  - El RUT se valida MIENTRAS se escribe (verde = válido, rojo = inválido).
  - Si el cliente ya cotizó antes, sus datos se completan solos.
  - Los productos se eligen del catálogo (hoja Productos): solo se escribe
    la cantidad. Se puede buscar escribiendo parte del nombre o del código.
  - Al guardar: se genera el PDF y la cotización queda registrada en el Excel
    (hojas Cotizaciones y Detalle), con número correlativo automático.

Uso:  python formulario.py   (o doble clic en Formulario_cotizaciones.bat)

Se usa tkinter, que viene incluido con Python: no hay que instalar nada y
se puede empaquetar como .exe.
"""

import os
import tkinter as tk
import traceback
from datetime import date
from tkinter import messagebox, ttk

from generador.calculos import calcular_totales, formato_cantidad, formato_pesos, total_linea
from generador.config import CARPETA_SALIDA, preparar_planilla
from generador.escritura import guardar_cotizacion, siguiente_numero
from generador.lectura import leer_planilla, leer_productos
from generador.pdf import generar_pdf, nombre_archivo
from generador.validaciones import formatear_rut, rut_es_valido, validar_cotizacion

VERDE = "#1E7B34"
ROJO = "#B3261E"
AZUL = "#1F4E78"
SEPARADOR = " — "   # separa código y descripción en la lista de productos


class Formulario(tk.Tk):
    """Ventana principal. Hereda de tk.Tk, así 'self' ES la ventana."""

    def __init__(self, planilla):
        super().__init__()
        self.planilla = planilla
        self.items = []            # productos agregados a la cotización actual
        self.n_cotizacion = None

        self._cargar_datos()
        self._construir_ventana()
        self._nueva_cotizacion()

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def _cargar_datos(self):
        """Lee empresa, clientes anteriores y catálogo desde el Excel."""
        self.empresa, cotizaciones = leer_planilla(self.planilla)

        # Catálogo: {"CEM-25": {...}, ...} y el texto que se ve en la lista.
        productos = leer_productos(self.planilla)
        self.catalogo = {p["codigo"].upper(): p for p in productos}
        self.opciones = [
            f"{p['codigo']}{SEPARADOR}{p['descripcion']} ({formato_pesos(p['precio_unitario_iva'])})"
            for p in productos
        ]

        # Clientes conocidos, por RUT. Si un cliente aparece varias veces,
        # queda la cotización más reciente (la última de la planilla).
        self.clientes = {}
        for c in cotizaciones:
            rut = formatear_rut(c["rut_cliente"])
            if rut:
                self.clientes[rut] = c

    # ------------------------------------------------------------------
    # Construcción de la ventana
    # ------------------------------------------------------------------
    def _construir_ventana(self):
        self.title(f"Nueva cotización · {self.empresa.get('nombre', '')}")
        self.minsize(860, 640)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)   # la sección de productos crece con la ventana

        estilo = ttk.Style(self)
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 14, "bold"), foreground=AZUL)
        estilo.configure("Total.TLabel", font=("Segoe UI", 13, "bold"), foreground=AZUL)
        estilo.configure("Principal.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 6))

        self._construir_encabezado().grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        self._construir_cliente().grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        self._construir_productos().grid(row=2, column=0, sticky="nsew", padx=14, pady=6)
        self._construir_pie().grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 12))

    def _construir_encabezado(self):
        marco = ttk.Frame(self)
        ttk.Label(marco, text=self.empresa.get("nombre", ""), style="Titulo.TLabel").pack(side="left")
        self.lbl_numero = ttk.Label(marco, font=("Segoe UI", 10))
        self.lbl_numero.pack(side="right")
        return marco

    def _construir_cliente(self):
        marco = ttk.LabelFrame(self, text=" Cliente ", padding=10)
        marco.columnconfigure(1, weight=1)
        marco.columnconfigure(3, weight=1)

        # Fila 0: RUT + mensaje de validación en vivo
        # Campo y mensaje van en un mismo sub-marco para que el mensaje quede
        # justo al lado del RUT.
        ttk.Label(marco, text="RUT *").grid(row=0, column=0, sticky="w")
        fila_rut = ttk.Frame(marco)
        fila_rut.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(6, 0))
        self.var_rut = tk.StringVar()
        entrada_rut = ttk.Entry(fila_rut, textvariable=self.var_rut, width=18)
        entrada_rut.pack(side="left")
        entrada_rut.bind("<KeyRelease>", self._al_escribir_rut)
        entrada_rut.bind("<FocusOut>", self._al_salir_rut)
        self.entrada_rut = entrada_rut
        self.lbl_estado_rut = tk.Label(fila_rut, text="", anchor="w")
        self.lbl_estado_rut.pack(side="left", padx=(10, 0))

        # Resto de los campos: (etiqueta, variable, fila, columna)
        self.var_razon = tk.StringVar()
        self.var_contacto = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_validez = tk.StringVar()
        self.var_obs = tk.StringVar()

        def campo(texto, var, fila, col, columnspan=1):
            ttk.Label(marco, text=texto).grid(row=fila, column=col, sticky="w", pady=(8, 0))
            e = ttk.Entry(marco, textvariable=var)
            e.grid(row=fila, column=col + 1, columnspan=columnspan, sticky="ew",
                   padx=(6, 12), pady=(8, 0))
            return e

        campo("Razón social *", self.var_razon, 1, 0, columnspan=3)
        campo("Contacto", self.var_contacto, 2, 0)
        campo("Email", self.var_email, 2, 2)
        campo("Observaciones", self.var_obs, 3, 0)

        ttk.Label(marco, text="Validez (días)").grid(row=3, column=2, sticky="w", pady=(8, 0))
        ttk.Spinbox(marco, from_=1, to=90, textvariable=self.var_validez, width=6).grid(
            row=3, column=3, sticky="w", padx=(6, 0), pady=(8, 0))
        return marco

    def _construir_productos(self):
        marco = ttk.LabelFrame(self, text=" Productos ", padding=10)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(2, weight=1)

        # Fila de ingreso: buscador del catálogo + cantidad + botón
        fila = ttk.Frame(marco)
        fila.grid(row=0, column=0, sticky="ew")
        fila.columnconfigure(1, weight=1)

        ttk.Label(fila, text="Producto").grid(row=0, column=0, sticky="w")
        self.var_producto = tk.StringVar()
        self.combo = ttk.Combobox(fila, textvariable=self.var_producto, values=self.opciones)
        self.combo.grid(row=0, column=1, sticky="ew", padx=6)
        self.combo.bind("<KeyRelease>", self._filtrar_catalogo)
        self.combo.bind("<Return>", lambda e: self.entrada_cantidad.focus_set())

        ttk.Label(fila, text="Cantidad").grid(row=0, column=2, padx=(8, 0))
        self.var_cantidad = tk.StringVar()
        self.entrada_cantidad = ttk.Entry(fila, textvariable=self.var_cantidad, width=8)
        self.entrada_cantidad.grid(row=0, column=3, padx=6)
        self.entrada_cantidad.bind("<Return>", lambda e: self._agregar_producto())

        ttk.Button(fila, text="Agregar", command=self._agregar_producto).grid(row=0, column=4)

        self.lbl_error_producto = tk.Label(marco, text="", fg=ROJO, anchor="w")
        self.lbl_error_producto.grid(row=1, column=0, sticky="ew", pady=(4, 2))

        # Tabla de productos agregados
        columnas = {
            "codigo": ("Código", 80, "w"),
            "descripcion": ("Descripción", 300, "w"),
            "unidad": ("Unidad", 70, "w"),
            "cantidad": ("Cant.", 60, "e"),
            "precio": ("Precio unit.", 100, "e"),
            "total": ("Total", 110, "e"),
        }
        self.tabla = ttk.Treeview(marco, columns=list(columnas), show="headings", height=8)
        for clave, (titulo, ancho, alineacion) in columnas.items():
            self.tabla.heading(clave, text=titulo, anchor=alineacion)
            self.tabla.column(clave, width=ancho, anchor=alineacion,
                              stretch=(clave == "descripcion"))
        self.tabla.grid(row=2, column=0, sticky="nsew")
        self.tabla.bind("<Delete>", lambda e: self._quitar_producto())

        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        barra.grid(row=2, column=1, sticky="ns")
        self.tabla.configure(yscrollcommand=barra.set)

        # Quitar + totales
        abajo = ttk.Frame(marco)
        abajo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(abajo, text="Quitar seleccionado", command=self._quitar_producto).pack(side="left")

        # Totales: grilla de 2 columnas (etiqueta | monto), alineadas a la derecha
        totales = ttk.Frame(abajo)
        totales.pack(side="right")
        self.lbl_neto = ttk.Label(totales, anchor="e", width=12)
        self.lbl_iva = ttk.Label(totales, anchor="e", width=12)
        self.lbl_total = ttk.Label(totales, anchor="e", width=12, style="Total.TLabel")
        for fila_t, (texto, lbl) in enumerate((("Subtotal neto", self.lbl_neto),
                                               ("IVA (19%)", self.lbl_iva),
                                               ("TOTAL", self.lbl_total))):
            estilo_etiqueta = "Total.TLabel" if texto == "TOTAL" else "TLabel"
            ttk.Label(totales, text=texto, style=estilo_etiqueta).grid(
                row=fila_t, column=0, sticky="e", padx=(0, 12))
            lbl.grid(row=fila_t, column=1, sticky="e")
        return marco

    def _construir_pie(self):
        marco = ttk.Frame(self)
        ttk.Label(marco, text="* obligatorio", foreground="#666").pack(side="left")
        ttk.Button(marco, text="Guardar y generar PDF", style="Principal.TButton",
                   command=self._guardar).pack(side="right")
        ttk.Button(marco, text="Limpiar", command=self._limpiar).pack(side="right", padx=8)
        return marco

    # ------------------------------------------------------------------
    # Cliente: validación del RUT en vivo y autocompletado
    # ------------------------------------------------------------------
    def _al_escribir_rut(self, _evento=None):
        rut = self.var_rut.get().strip()
        if not rut:
            self.lbl_estado_rut.config(text="")
            return

        if not rut_es_valido(rut):
            # Mientras no haya guion, probablemente todavía está escribiendo.
            if "-" not in rut:
                self.lbl_estado_rut.config(text="Escriba el RUT con guion: 12.345.678-9",
                                           fg="#666")
            else:
                self.lbl_estado_rut.config(text="✗ RUT inválido. Revise los números y el "
                                                "dígito verificador e intente nuevamente.",
                                           fg=ROJO)
            return

        cliente = self.clientes.get(formatear_rut(rut))
        if cliente:
            # Completar solo los campos vacíos, para no borrar lo que ya escribió.
            for var, clave in ((self.var_razon, "razon_social"),
                               (self.var_contacto, "contacto"),
                               (self.var_email, "email")):
                if not var.get().strip():
                    var.set(cliente.get(clave, ""))
            self.lbl_estado_rut.config(text="✓ Cliente registrado: datos completados", fg=VERDE)
        else:
            self.lbl_estado_rut.config(text="✓ RUT válido (cliente nuevo)", fg=VERDE)

    def _al_salir_rut(self, _evento=None):
        """Al salir del campo, dejar el RUT en formato estándar 12.345.678-9."""
        formateado = formatear_rut(self.var_rut.get())
        if formateado:
            self.var_rut.set(formateado)

    # ------------------------------------------------------------------
    # Productos
    # ------------------------------------------------------------------
    def _filtrar_catalogo(self, evento=None):
        """Mientras se escribe, la lista muestra solo lo que coincide."""
        if evento is not None and evento.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        texto = self.var_producto.get().strip().lower()
        self.combo["values"] = [o for o in self.opciones if texto in o.lower()] or self.opciones

    def _producto_elegido(self):
        """Interpreta lo escrito en el buscador. Retorna el producto o None."""
        texto = self.var_producto.get().strip()
        if not texto:
            return None
        codigo = texto.split(SEPARADOR)[0].strip().upper()
        if codigo in self.catalogo:
            return self.catalogo[codigo]
        # Si escribió parte del nombre y hay UNA sola coincidencia, usar esa.
        coincidencias = [o for o in self.opciones if texto.lower() in o.lower()]
        if len(coincidencias) == 1:
            return self.catalogo[coincidencias[0].split(SEPARADOR)[0].upper()]
        return None

    def _agregar_producto(self):
        producto = self._producto_elegido()
        if producto is None:
            texto = self.var_producto.get().strip().lower()
            n = sum(texto in o.lower() for o in self.opciones) if texto else 0
            if n > 1:
                mensaje = f"Hay {n} productos que coinciden con «{texto}». Elija uno de la lista."
            else:
                mensaje = "Elija un producto de la lista (puede buscar escribiendo parte del nombre)."
            self.lbl_error_producto.config(text=mensaje)
            self._filtrar_catalogo()
            self.combo.focus_set()
            return

        try:
            cantidad = float(self.var_cantidad.get().replace(",", "."))
        except ValueError:
            cantidad = 0
        if cantidad <= 0:
            self.lbl_error_producto.config(text="La cantidad debe ser un número mayor que 0.")
            self.entrada_cantidad.focus_set()
            return
        if cantidad.is_integer():
            cantidad = int(cantidad)

        # Si el producto ya está en la lista, se suma la cantidad.
        for item in self.items:
            if item["codigo"] == producto["codigo"]:
                item["cantidad"] += cantidad
                break
        else:
            self.items.append({
                "codigo": producto["codigo"],
                "descripcion": producto["descripcion"],
                "unidad": producto["unidad"],
                "cantidad": cantidad,
                "precio_unitario_iva": producto["precio_unitario_iva"],
            })

        self.lbl_error_producto.config(text="")
        self.var_producto.set("")
        self.var_cantidad.set("")
        self.combo["values"] = self.opciones
        self._refrescar_tabla()
        self.combo.focus_set()

    def _quitar_producto(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        codigos = {self.tabla.item(s, "values")[0] for s in seleccion}
        self.items = [i for i in self.items if i["codigo"] not in codigos]
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        """Redibuja la tabla y los totales a partir de self.items."""
        self.tabla.delete(*self.tabla.get_children())
        for item in self.items:
            self.tabla.insert("", "end", values=(
                item["codigo"], item["descripcion"], item["unidad"],
                formato_cantidad(item["cantidad"]),
                formato_pesos(item["precio_unitario_iva"]),
                formato_pesos(total_linea(item)),
            ))
        t = calcular_totales(self.items)
        self.lbl_neto.config(text=formato_pesos(t["neto"]))
        self.lbl_iva.config(text=formato_pesos(t["iva"]))
        self.lbl_total.config(text=formato_pesos(t["total"]))

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------
    def _armar_cotizacion(self):
        """Junta lo que hay en pantalla en el mismo formato que lee lectura.py."""
        try:
            validez = int(self.var_validez.get())
        except ValueError:
            validez = 0
        return {
            "n_cotizacion": self.n_cotizacion,
            "fecha": date.today(),
            "rut_cliente": formatear_rut(self.var_rut.get()) or self.var_rut.get().strip(),
            "razon_social": self.var_razon.get().strip(),
            "contacto": self.var_contacto.get().strip(),
            "email": self.var_email.get().strip(),
            "validez_dias": validez,
            "observaciones": self.var_obs.get().strip(),
            "items": [dict(i) for i in self.items],
        }

    def _guardar(self):
        cot = self._armar_cotizacion()

        # Las mismas reglas que la generación masiva: todos los problemas juntos.
        problemas = validar_cotizacion(cot)
        if problemas:
            messagebox.showwarning("Revise la cotización",
                                   "Antes de guardar, corrija lo siguiente:\n\n• "
                                   + "\n• ".join(problemas))
            return

        # Primero el PDF y después el Excel: si el Excel falla (por estar
        # abierto), basta con cerrarlo y volver a guardar; el PDF se reemplaza.
        CARPETA_SALIDA.mkdir(exist_ok=True)
        ruta_pdf = CARPETA_SALIDA / nombre_archivo(cot)
        try:
            generar_pdf(self.empresa, cot, ruta_pdf)
        except PermissionError:
            messagebox.showerror("No se pudo crear el PDF",
                                 f"El archivo {ruta_pdf.name} está abierto.\n"
                                 "Ciérrelo y vuelva a presionar Guardar.")
            return
        try:
            guardar_cotizacion(self.planilla, cot)
        except PermissionError:
            messagebox.showerror("No se pudo guardar en Excel",
                                 "La planilla está abierta en Excel.\n"
                                 "Ciérrela y vuelva a presionar Guardar.")
            return

        self.clientes[cot["rut_cliente"]] = cot
        if messagebox.askyesno("Cotización guardada",
                               f"Cotización N° {cot['n_cotizacion']} guardada.\n\n"
                               f"PDF: {ruta_pdf.name}\n\n¿Desea abrir el PDF?"):
            os.startfile(ruta_pdf)  # abre con el lector de PDF de Windows
        self._nueva_cotizacion()

    def _limpiar(self):
        if self.items and not messagebox.askyesno(
                "Limpiar", "¿Borrar los datos de esta cotización sin guardar?"):
            return
        self._nueva_cotizacion()

    def _nueva_cotizacion(self):
        """Deja el formulario en blanco con el siguiente número correlativo."""
        self.n_cotizacion = siguiente_numero(self.planilla)
        self.lbl_numero.config(
            text=f"Cotización N° {self.n_cotizacion}   ·   {date.today():%d-%m-%Y}")
        for var in (self.var_rut, self.var_razon, self.var_contacto, self.var_email,
                    self.var_obs, self.var_producto, self.var_cantidad):
            var.set("")
        self.var_validez.set("15")
        self.lbl_estado_rut.config(text="")
        self.lbl_error_producto.config(text="")
        self.items = []
        self._refrescar_tabla()
        self.entrada_rut.focus_set()


def main():
    # Texto nítido en pantallas con escalado de Windows (125 %, 150 %...).
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    try:
        app = Formulario(preparar_planilla())
    except Exception:
        # Sin consola (doble clic), un error solo se vería así.
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("No se pudo abrir el formulario",
                             "Error al leer la planilla:\n\n" + traceback.format_exc(limit=1))
        return
    app.mainloop()


if __name__ == "__main__":
    main()
