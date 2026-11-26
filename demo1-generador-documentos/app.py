"""
app.py
------
Programa de cotizaciones con dos pestañas:

  1. "Nueva cotización": formulario para el vendedor.
       - El RUT se valida MIENTRAS se escribe (verde = válido, rojo = inválido).
       - Si el cliente ya cotizó antes, sus datos se completan solos.
       - Los productos se eligen del Inventario (se ve el stock); solo se
         escribe la cantidad.
       - Al guardar: genera el PDF y registra la cotización en el Excel como
         "pendiente", con número correlativo.

  2. "Procesar planilla": lo que hace generar.py, pero con una tabla ordenada
     de errores y advertencias que dice DÓNDE está cada problema (hoja y
     celda) y CÓMO corregirlo.

Uso:  python app.py   (o doble clic en Abrir_cotizaciones.bat)

Se usa tkinter, que viene incluido con Python: no hay que instalar nada y
se puede empaquetar como .exe.
"""

import os
import tkinter as tk
import traceback
from datetime import date, datetime
from tkinter import messagebox, ttk

from generador.calculos import calcular_totales, formato_cantidad, formato_pesos, total_linea
from generador.config import CARPETA_SALIDA, preparar_planilla
from generador.escritura import guardar_cotizacion, siguiente_numero
from generador.inventario import completar_items
from generador.lectura import leer_planilla
from generador.pdf import generar_pdf, nombre_archivo
from generador.proceso import ERROR, procesar_planilla
from generador.validaciones import (formatear_rut, rut_es_valido, validar_cotizacion,
                                    validar_empresa)

VERDE = "#1E7B34"
ROJO = "#B3261E"
NARANJO = "#B45F06"
AZUL = "#1F4E78"
GRIS = "#666666"
SEPARADOR = " — "   # separa código y descripción en la lista de productos


def _abrir(ruta):
    """Abre un archivo o carpeta con el programa predeterminado de Windows."""
    try:
        os.startfile(ruta)
    except OSError as e:
        messagebox.showerror("No se pudo abrir", f"{ruta}\n\n{e}")


# ======================================================================
# Pestaña 1: Nueva cotización
# ======================================================================
class PestanaCotizacion(ttk.Frame):
    """Formulario de cotización. Hereda de ttk.Frame: 'self' ES la pestaña."""

    def __init__(self, master, planilla):
        super().__init__(master)
        self.items = []            # productos agregados: [{codigo, cantidad}]
        self.n_cotizacion = None
        self._cargar_datos(planilla)
        self._construir()
        self._nueva_cotizacion()

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------
    def _cargar_datos(self, planilla):
        """Prepara el catálogo y los clientes conocidos a partir de la planilla."""
        self.planilla = planilla
        self.empresa = planilla.empresa
        self.inventario = planilla.inventario
        self.opciones = [
            f"{p['codigo']}{SEPARADOR}{p['descripcion']} "
            f"({formato_pesos(p['precio_unitario_iva'])} · stock {formato_cantidad(p['stock'])})"
            for p in self.inventario.values()
            if isinstance(p.get("precio_unitario_iva"), (int, float))
            and isinstance(p.get("stock"), (int, float)) and p["stock"] == p["stock"]
        ]
        # Clientes conocidos, por RUT (queda la cotización más reciente).
        self.clientes = {}
        for c in planilla.cotizaciones:
            rut = formatear_rut(c["rut_cliente"])
            if rut:
                self.clientes[rut] = c

    def recargar(self, planilla):
        """
        Vuelve a leer la planilla (por ejemplo, si alguien cambió precios o
        stock en Excel, o si "Procesar planilla" movió el stock). Conserva los
        productos que el vendedor ya agregó, si siguen existiendo.
        """
        self._cargar_datos(planilla)
        self.combo["values"] = self.opciones
        self.lbl_empresa.config(text=self.empresa.get("razon_social", ""))
        self.lbl_validez.config(text=self._texto_validez())
        self.items = [i for i in self.items if i["codigo"] in self.inventario]
        if not self.items:
            self.n_cotizacion = siguiente_numero(self.planilla.ruta)
            self._actualizar_numero()
        self._refrescar_tabla()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _construir(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)   # la sección de productos crece con la ventana
        self._construir_encabezado().grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        self._construir_cliente().grid(row=1, column=0, sticky="ew", padx=14, pady=6)
        self._construir_productos().grid(row=2, column=0, sticky="nsew", padx=14, pady=6)
        self._construir_pie().grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 12))

    def _construir_encabezado(self):
        marco = ttk.Frame(self)
        self.lbl_empresa = ttk.Label(marco, text=self.empresa.get("razon_social", ""),
                                     style="Titulo.TLabel")
        self.lbl_empresa.pack(side="left")
        self.lbl_numero = ttk.Label(marco, font=("Segoe UI", 10))
        self.lbl_numero.pack(side="right")
        return marco

    def _construir_cliente(self):
        marco = ttk.LabelFrame(self, text=" Cliente ", padding=10)
        marco.columnconfigure(1, weight=1)
        marco.columnconfigure(3, weight=1)

        # RUT + mensaje de validación en vivo, en un mismo sub-marco para que
        # el mensaje quede justo al lado del campo.
        ttk.Label(marco, text="RUT *").grid(row=0, column=0, sticky="w")
        fila_rut = ttk.Frame(marco)
        fila_rut.grid(row=0, column=1, columnspan=3, sticky="ew", padx=(6, 0))
        self.var_rut = tk.StringVar()
        self.entrada_rut = ttk.Entry(fila_rut, textvariable=self.var_rut, width=18)
        self.entrada_rut.pack(side="left")
        self.entrada_rut.bind("<KeyRelease>", self._al_escribir_rut)
        self.entrada_rut.bind("<FocusOut>", self._al_salir_rut)
        self.lbl_estado_rut = tk.Label(fila_rut, text="", anchor="w")
        self.lbl_estado_rut.pack(side="left", padx=(10, 0))

        self.var_razon = tk.StringVar()
        self.var_contacto = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_obs = tk.StringVar()

        def campo(texto, var, fila, col, columnspan=1):
            ttk.Label(marco, text=texto).grid(row=fila, column=col, sticky="w", pady=(8, 0))
            ttk.Entry(marco, textvariable=var).grid(
                row=fila, column=col + 1, columnspan=columnspan, sticky="ew",
                padx=(6, 12), pady=(8, 0))

        campo("Razón social *", self.var_razon, 1, 0, columnspan=3)
        campo("Contacto", self.var_contacto, 2, 0)
        campo("Email", self.var_email, 2, 2)
        campo("Observaciones", self.var_obs, 3, 0, columnspan=3)
        return marco

    def _construir_productos(self):
        marco = ttk.LabelFrame(self, text=" Productos ", padding=10)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(2, weight=1)

        # Fila de ingreso: buscador del Inventario + cantidad + botón
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

        # Mensajes: errores en rojo, advertencias de stock en naranjo
        self.lbl_mensaje = tk.Label(marco, text="", anchor="w")
        self.lbl_mensaje.grid(row=1, column=0, sticky="ew", pady=(4, 2))

        columnas = {
            "codigo": ("Código", 80, "w"),
            "descripcion": ("Descripción", 290, "w"),
            "unidad": ("Unidad", 65, "w"),
            "cantidad": ("Cant.", 55, "e"),
            "stock": ("Stock", 55, "e"),
            "precio": ("Precio unit.", 95, "e"),
            "total": ("Total", 105, "e"),
        }
        self.tabla = ttk.Treeview(marco, columns=list(columnas), show="headings", height=8)
        for clave, (titulo, ancho, alineacion) in columnas.items():
            self.tabla.heading(clave, text=titulo, anchor=alineacion)
            self.tabla.column(clave, width=ancho, anchor=alineacion,
                              stretch=(clave == "descripcion"))
        self.tabla.tag_configure("sin_stock", foreground=NARANJO)
        self.tabla.grid(row=2, column=0, sticky="nsew")
        self.tabla.bind("<Delete>", lambda e: self._quitar_producto())

        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        barra.grid(row=2, column=1, sticky="ns")
        self.tabla.configure(yscrollcommand=barra.set)

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

    def _texto_validez(self):
        return (f"* obligatorio   ·   Validez: {self.empresa.get('validez_dias', '')} días "
                "(hoja Empresa)")

    def _construir_pie(self):
        marco = ttk.Frame(self)
        self.lbl_validez = ttk.Label(marco, text=self._texto_validez(), foreground=GRIS)
        self.lbl_validez.pack(side="left")
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
                self.lbl_estado_rut.config(text="Escriba el RUT con guion: 12.345.678-9", fg=GRIS)
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
        if codigo in self.inventario:
            return self.inventario[codigo]
        # Si escribió parte del nombre y hay UNA sola coincidencia, usar esa.
        coincidencias = [o for o in self.opciones if texto.lower() in o.lower()]
        if len(coincidencias) == 1:
            return self.inventario[coincidencias[0].split(SEPARADOR)[0].upper()]
        return None

    def _mensaje(self, texto, color=ROJO):
        self.lbl_mensaje.config(text=texto, fg=color)

    def _agregar_producto(self):
        producto = self._producto_elegido()
        if producto is None:
            texto = self.var_producto.get().strip().lower()
            n = sum(texto in o.lower() for o in self.opciones) if texto else 0
            if n > 1:
                self._mensaje(f"Hay {n} productos que coinciden con «{texto}». Elija uno de la lista.")
            else:
                self._mensaje("Elija un producto de la lista "
                              "(puede buscar escribiendo parte del nombre).")
            self._filtrar_catalogo()
            self.combo.focus_set()
            return

        try:
            cantidad = float(self.var_cantidad.get().replace(",", "."))
        except ValueError:
            cantidad = 0
        if cantidad <= 0:
            self._mensaje("La cantidad debe ser un número mayor que 0.")
            self.entrada_cantidad.focus_set()
            return
        if cantidad.is_integer():
            cantidad = int(cantidad)

        # Si el producto ya está en la lista, se suma la cantidad.
        for item in self.items:
            if item["codigo"] == producto["codigo"]:
                item["cantidad"] += cantidad
                total_pedido = item["cantidad"]
                break
        else:
            self.items.append({"codigo": producto["codigo"], "cantidad": cantidad})
            total_pedido = cantidad

        # Advertencia (no error) si se cotiza más que el stock.
        stock = producto["stock"]
        if total_pedido > stock:
            self._mensaje(f"⚠ {producto['codigo']}: se cotizan {formato_cantidad(total_pedido)} "
                          f"y hay {formato_cantidad(stock)} en stock. Se puede cotizar igual.",
                          NARANJO)
        else:
            self._mensaje("")

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

    def _items_completos(self):
        """Productos con descripción y precio tomados del Inventario."""
        return completar_items({"items": self.items}, self.inventario)

    def _refrescar_tabla(self):
        """Redibuja la tabla y los totales a partir de self.items."""
        self.tabla.delete(*self.tabla.get_children())
        completos = self._items_completos()
        for item in completos:
            stock = self.inventario[item["codigo"]]["stock"]
            self.tabla.insert("", "end", values=(
                item["codigo"], item["descripcion"], item["unidad"],
                formato_cantidad(item["cantidad"]), formato_cantidad(stock),
                formato_pesos(item["precio_unitario_iva"]),
                formato_pesos(total_linea(item)),
            ), tags=("sin_stock",) if item["cantidad"] > stock else ())
        t = calcular_totales(completos)
        self.lbl_neto.config(text=formato_pesos(t["neto"]))
        self.lbl_iva.config(text=formato_pesos(t["iva"]))
        self.lbl_total.config(text=formato_pesos(t["total"]))

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------
    def _armar_cotizacion(self):
        """Junta lo que hay en pantalla en el mismo formato que lee lectura.py."""
        return {
            "n_cotizacion": self.n_cotizacion,
            "fecha": date.today(),
            "rut_cliente": formatear_rut(self.var_rut.get()) or self.var_rut.get().strip(),
            "razon_social": self.var_razon.get().strip(),
            "contacto": self.var_contacto.get().strip(),
            "email": self.var_email.get().strip(),
            "observaciones": self.var_obs.get().strip(),
            "estado": "pendiente",
            "items": [dict(i) for i in self.items],   # solo código y cantidad
        }

    def _guardar(self):
        errores_empresa, _ = validar_empresa(self.empresa, self.planilla.carpeta)
        if errores_empresa:
            messagebox.showwarning(
                "Revise la hoja Empresa",
                "No se pueden generar cotizaciones hasta completar la hoja Empresa:\n\n• "
                + "\n• ".join(errores_empresa)
                + "\n\nVea el detalle en la pestaña «Procesar planilla».")
            return

        cot = self._armar_cotizacion()
        errores, advertencias = validar_cotizacion(cot, self.inventario)
        if errores:
            messagebox.showwarning("Revise la cotización",
                                   "Antes de guardar, corrija lo siguiente:\n\n• "
                                   + "\n• ".join(errores))
            return

        # Primero el PDF y después el Excel: si el Excel falla (por estar
        # abierto), basta con cerrarlo y volver a guardar; el PDF se reemplaza.
        CARPETA_SALIDA.mkdir(exist_ok=True)
        ruta_pdf = CARPETA_SALIDA / nombre_archivo(cot)
        try:
            generar_pdf(self.empresa, cot, self._items_completos(), ruta_pdf,
                        self.planilla.ruta_logo())
        except PermissionError:
            messagebox.showerror("No se pudo crear el PDF",
                                 f"El archivo {ruta_pdf.name} está abierto.\n"
                                 "Ciérrelo y vuelva a presionar Guardar.")
            return
        try:
            guardar_cotizacion(self.planilla.ruta, cot)
        except PermissionError:
            messagebox.showerror("No se pudo guardar en Excel",
                                 "La planilla está abierta en Excel.\n"
                                 "Ciérrela y vuelva a presionar Guardar.")
            return

        self.clientes[cot["rut_cliente"]] = cot
        aviso = ("\n\nAdvertencias:\n• " + "\n• ".join(advertencias)) if advertencias else ""
        if messagebox.askyesno("Cotización guardada",
                               f"Cotización N° {cot['n_cotizacion']} guardada como pendiente.\n\n"
                               f"PDF: {ruta_pdf.name}{aviso}\n\n¿Desea abrir el PDF?"):
            _abrir(ruta_pdf)
        self._nueva_cotizacion()

    def _limpiar(self):
        if self.items and not messagebox.askyesno(
                "Limpiar", "¿Borrar los datos de esta cotización sin guardar?"):
            return
        self._nueva_cotizacion()

    def _actualizar_numero(self):
        self.lbl_numero.config(
            text=f"Cotización N° {self.n_cotizacion}   ·   {date.today():%d-%m-%Y}")

    def _nueva_cotizacion(self):
        """Deja el formulario en blanco con el siguiente número correlativo."""
        self.n_cotizacion = siguiente_numero(self.planilla.ruta)
        self._actualizar_numero()
        for var in (self.var_rut, self.var_razon, self.var_contacto, self.var_email,
                    self.var_obs, self.var_producto, self.var_cantidad):
            var.set("")
        self.lbl_estado_rut.config(text="")
        self._mensaje("")
        self.items = []
        self._refrescar_tabla()
        self.entrada_rut.focus_set()


# ======================================================================
# Pestaña 2: Procesar planilla
# ======================================================================
class PestanaProcesar(ttk.Frame):
    """Procesa la planilla y muestra el resultado ordenado en tablas."""

    def __init__(self, master, ruta_planilla, al_terminar=None):
        super().__init__(master)
        self.ruta = ruta_planilla
        self.al_terminar = al_terminar      # función a llamar después de procesar
        self.avisos_por_fila = {}           # id de fila de la tabla -> Aviso
        self.pdf_por_fila = {}              # id de fila de la tabla -> ruta del PDF
        self._construir()

    def _construir(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=3)      # tabla de problemas
        self.rowconfigure(6, weight=1)      # tabla de PDF y stock

        # --- Barra de botones ---
        barra = ttk.Frame(self)
        barra.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        ttk.Button(barra, text="▶  Procesar planilla", style="Principal.TButton",
                   command=self.procesar).pack(side="left")
        ttk.Button(barra, text="Abrir planilla", command=lambda: _abrir(self.ruta)).pack(
            side="left", padx=(10, 0))
        ttk.Button(barra, text="Abrir carpeta de PDF",
                   command=lambda: _abrir(CARPETA_SALIDA)).pack(side="left", padx=(6, 0))
        # Solo carpeta\archivo: la ruta completa no cabe (está en el botón "Abrir planilla").
        ttk.Label(barra, text=f"Planilla: {self.ruta.parent.name}\\{self.ruta.name}",
                  foreground=GRIS).pack(side="right")

        # --- Tarjetas de resumen ---
        tarjetas = ttk.Frame(self)
        tarjetas.grid(row=1, column=0, sticky="ew", padx=14, pady=4)
        self.tarjetas = {}
        for i, (clave, titulo, color) in enumerate((
                ("pdf", "PDF nuevos", VERDE), ("errores", "Cotizaciones con errores", ROJO),
                ("advertencias", "Advertencias", NARANJO), ("stock", "Movimientos de stock", AZUL))):
            tarjetas.columnconfigure(i, weight=1)
            marco = tk.Frame(tarjetas, bg="white", highlightthickness=1,
                             highlightbackground="#D0D7DE")
            marco.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            numero = tk.Label(marco, text="–", font=("Segoe UI", 20, "bold"), fg=color, bg="white")
            numero.pack(anchor="w", padx=12, pady=(6, 0))
            tk.Label(marco, text=titulo, fg=GRIS, bg="white").pack(anchor="w", padx=12, pady=(0, 8))
            self.tarjetas[clave] = numero

        # --- Mensaje general ---
        self.lbl_estado = tk.Label(self, text="Presione «Procesar planilla» para generar los PDF "
                                              "nuevos, mover el stock y revisar errores.",
                                   anchor="w", fg=GRIS, font=("Segoe UI", 10))
        self.lbl_estado.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 2))

        # --- Tabla de problemas ---
        marco = ttk.LabelFrame(self, text=" Errores y advertencias ", padding=8)
        marco.grid(row=3, column=0, sticky="nsew", padx=14, pady=4)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)
        columnas = {
            "tipo": ("Tipo", 95, "w"), "n": ("N°", 55, "center"),
            "cliente": ("Cliente", 190, "w"), "donde": ("Dónde", 120, "w"),
            "problema": ("Problema", 420, "w"),
        }
        self.tabla_avisos = ttk.Treeview(marco, columns=list(columnas), show="headings", height=8)
        for clave, (titulo, ancho, alin) in columnas.items():
            self.tabla_avisos.heading(clave, text=titulo, anchor=alin)
            self.tabla_avisos.column(clave, width=ancho, anchor=alin,
                                     stretch=(clave == "problema"))
        self.tabla_avisos.tag_configure(ERROR, foreground=ROJO)
        self.tabla_avisos.tag_configure("advertencia", foreground=NARANJO)
        self.tabla_avisos.grid(row=0, column=0, sticky="nsew")
        self.tabla_avisos.bind("<<TreeviewSelect>>", self._mostrar_detalle)
        barra_y = ttk.Scrollbar(marco, orient="vertical", command=self.tabla_avisos.yview)
        barra_y.grid(row=0, column=1, sticky="ns")
        self.tabla_avisos.configure(yscrollcommand=barra_y.set)

        # --- Detalle del problema seleccionado ---
        self.lbl_detalle = tk.Label(self, text="Seleccione un problema para ver cómo corregirlo.",
                                    anchor="w", justify="left", fg=GRIS, wraplength=900,
                                    bg="#F6F8FA", padx=10, pady=8)
        self.lbl_detalle.grid(row=4, column=0, sticky="ew", padx=14, pady=(2, 6))
        self.bind("<Configure>", lambda e: self.lbl_detalle.config(wraplength=max(300, e.width - 60)))

        # --- Tabla de PDF y stock ---
        ttk.Label(self, text="PDF y stock   (doble clic en un PDF para abrirlo)",
                  foreground=GRIS).grid(row=5, column=0, sticky="w", padx=16)
        marco2 = ttk.Frame(self)
        marco2.grid(row=6, column=0, sticky="nsew", padx=14, pady=(2, 12))
        marco2.columnconfigure(0, weight=1)
        marco2.rowconfigure(0, weight=1)
        self.tabla_hechos = ttk.Treeview(marco2, columns=("que", "n", "detalle"),
                                         show="headings", height=5)
        for clave, titulo, ancho in (("que", "Acción", 150), ("n", "N°", 55),
                                     ("detalle", "Detalle", 600)):
            self.tabla_hechos.heading(clave, text=titulo, anchor="w")
            self.tabla_hechos.column(clave, width=ancho, anchor="w", stretch=(clave == "detalle"))
        self.tabla_hechos.tag_configure("nuevo", foreground=VERDE)
        self.tabla_hechos.tag_configure("existente", foreground=GRIS)
        self.tabla_hechos.tag_configure("stock", foreground=AZUL)
        self.tabla_hechos.grid(row=0, column=0, sticky="nsew")
        self.tabla_hechos.bind("<Double-1>", self._abrir_pdf)
        barra_y2 = ttk.Scrollbar(marco2, orient="vertical", command=self.tabla_hechos.yview)
        barra_y2.grid(row=0, column=1, sticky="ns")
        self.tabla_hechos.configure(yscrollcommand=barra_y2.set)

    # ------------------------------------------------------------------
    def procesar(self):
        """Ejecuta proceso.procesar_planilla() y muestra el resultado."""
        self.winfo_toplevel().config(cursor="watch")
        self.update_idletasks()
        try:
            resultado = procesar_planilla(self.ruta)
        except (FileNotFoundError, ValueError) as e:
            messagebox.showerror("No se pudo leer la planilla", str(e))
            return
        finally:
            self.winfo_toplevel().config(cursor="")
        self.mostrar(resultado)
        if self.al_terminar:
            self.al_terminar(resultado)

    def mostrar(self, res):
        """Llena las tarjetas y las tablas con un Resultado."""
        self.tarjetas["pdf"].config(text=len(res.pdfs_nuevos))
        self.tarjetas["errores"].config(text=len(res.cotizaciones_con_errores)
                                        if not res.empresa_bloqueada else "–")
        self.tarjetas["advertencias"].config(text=len(res.advertencias))
        self.tarjetas["stock"].config(text=len(res.descontadas) + len(res.devueltas))

        hora = datetime.now().strftime("%d-%m-%Y a las %H:%M")
        if res.empresa_bloqueada:
            self.lbl_estado.config(fg=ROJO, text="✗ La hoja Empresa tiene errores: no se generó "
                                                 "ningún PDF ni se movió stock. Corrija lo "
                                                 "indicado abajo y vuelva a procesar.")
        elif res.errores:
            self.lbl_estado.config(fg=ROJO, text=f"Procesado el {hora}. Hay errores: esas "
                                                 "cotizaciones no generaron PDF. Corríjalos en "
                                                 "la planilla y vuelva a procesar.")
        elif res.advertencias:
            self.lbl_estado.config(fg=NARANJO, text=f"✓ Procesado el {hora}, con advertencias "
                                                    "(no impiden generar).")
        else:
            self.lbl_estado.config(fg=VERDE, text=f"✓ Procesado el {hora}. Todo en orden.")

        # Tabla de problemas
        self.tabla_avisos.delete(*self.tabla_avisos.get_children())
        self.avisos_por_fila = {}
        for a in res.avisos:
            tipo = "✗ Error" if a.nivel == ERROR else "⚠ Advertencia"
            cliente = a.cliente or ("Datos de la empresa" if a.donde.startswith("Empresa") else "")
            fila = self.tabla_avisos.insert("", "end", tags=(a.nivel,), values=(
                tipo, a.n_cotizacion or "", cliente, a.donde, a.mensaje))
            self.avisos_por_fila[fila] = a
        if not res.avisos:
            self.tabla_avisos.insert("", "end", values=("✓", "", "", "", "Sin problemas"))
        self.lbl_detalle.config(text="Seleccione un problema para ver cómo corregirlo.", fg=GRIS)

        # Tabla de PDF y stock
        self.tabla_hechos.delete(*self.tabla_hechos.get_children())
        self.pdf_por_fila = {}
        for n, ruta in res.pdfs_nuevos:
            fila = self.tabla_hechos.insert("", "end", tags=("nuevo",),
                                            values=("PDF nuevo", n, ruta.name))
            self.pdf_por_fila[fila] = ruta
        for n in res.descontadas:
            self.tabla_hechos.insert("", "end", tags=("stock",),
                                     values=("Stock descontado", n, "Cotización aceptada"))
        for n in res.devueltas:
            self.tabla_hechos.insert("", "end", tags=("stock",),
                                     values=("Stock devuelto", n, "Ya no está aceptada"))
        for n, ruta in res.pdfs_existentes:
            fila = self.tabla_hechos.insert("", "end", tags=("existente",), values=(
                "PDF ya existía", n, f"{ruta.name} (se mantiene el original)"))
            self.pdf_por_fila[fila] = ruta

    def _mostrar_detalle(self, _evento=None):
        seleccion = self.tabla_avisos.selection()
        aviso = self.avisos_por_fila.get(seleccion[0]) if seleccion else None
        if aviso is None:
            return
        partes = [aviso.mensaje]
        if aviso.donde:
            partes.append(f"Dónde: hoja {aviso.donde.replace(' ', ', celda ', 1)}"
                          if " " in aviso.donde and aviso.donde[-1].isdigit()
                          else f"Dónde: {aviso.donde}")
        if aviso.ayuda:
            partes.append(f"Cómo corregir: {aviso.ayuda}")
        color = ROJO if aviso.nivel == ERROR else NARANJO
        self.lbl_detalle.config(text="\n".join(partes), fg=color)

    def _abrir_pdf(self, _evento=None):
        seleccion = self.tabla_hechos.selection()
        ruta = self.pdf_por_fila.get(seleccion[0]) if seleccion else None
        if ruta:
            _abrir(ruta)


# ======================================================================
# Ventana principal
# ======================================================================
class App(tk.Tk):
    """Ventana con las dos pestañas."""

    def __init__(self, planilla):
        super().__init__()
        self.ruta = planilla.ruta
        self.title(f"Cotizaciones · {planilla.empresa.get('razon_social', '')}")
        self.minsize(980, 720)
        self.geometry("1040x760")

        estilo = ttk.Style(self)
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 14, "bold"), foreground=AZUL)
        estilo.configure("Total.TLabel", font=("Segoe UI", 13, "bold"), foreground=AZUL)
        estilo.configure("Principal.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 6))
        estilo.configure("TNotebook.Tab", padding=(16, 6), font=("Segoe UI", 10))

        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill="both", expand=True, padx=6, pady=6)
        self.cotizacion = PestanaCotizacion(self.pestanas, planilla)
        self.procesar = PestanaProcesar(self.pestanas, self.ruta, al_terminar=self._al_procesar)
        self.pestanas.add(self.cotizacion, text="  Nueva cotización  ")
        self.pestanas.add(self.procesar, text="  Procesar planilla  ")

        # Si alguien modificó el Excel (precios, stock), recargar al volver al formulario.
        self._ultima_modificacion = self._fecha_archivo()
        self.pestanas.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

        # Si la hoja Empresa tiene errores, se muestra el detalle de inmediato
        # (sin efectos: con Empresa mal, el proceso se detiene antes de generar
        # o mover nada) y se bloquea el formulario hasta corregirla.
        errores, _ = validar_empresa(planilla.empresa, planilla.carpeta)
        if errores:
            self.pestanas.tab(self.cotizacion, state="disabled")
            self.pestanas.select(self.procesar)
            self.after(100, self.procesar.procesar)

    def _fecha_archivo(self):
        try:
            return self.ruta.stat().st_mtime
        except OSError:
            return None

    def _recargar_formulario(self):
        try:
            planilla = leer_planilla(self.ruta)
        except Exception:
            return
        self.cotizacion.recargar(planilla)
        self._ultima_modificacion = self._fecha_archivo()
        errores, _ = validar_empresa(planilla.empresa, planilla.carpeta)
        self.pestanas.tab(self.cotizacion, state="disabled" if errores else "normal")
        self.title(f"Cotizaciones · {planilla.empresa.get('razon_social', '')}")

    def _al_cambiar_pestana(self, _evento=None):
        if (self.pestanas.select() == str(self.cotizacion)
                and self._fecha_archivo() != self._ultima_modificacion):
            self._recargar_formulario()

    def _al_procesar(self, _resultado):
        """Procesar pudo mover stock o corregirse la hoja Empresa: recargar el formulario."""
        self._recargar_formulario()


def main():
    # Texto nítido en pantallas con escalado de Windows (125 %, 150 %...).
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    try:
        planilla = leer_planilla(preparar_planilla())
    except Exception:
        # Sin consola (doble clic), un error solo se vería así.
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror("No se pudo abrir el programa",
                             "Error al leer la planilla:\n\n" + traceback.format_exc(limit=1))
        raiz.destroy()
        return

    App(planilla).mainloop()


if __name__ == "__main__":
    main()
