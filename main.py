# [file name]: main.py

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2

# Importar la lógica del programa
from logica import procesar_imagen, GeneradorPDF, GestorCuestionarios, BANCO_PREGUNTAS

# ==============================
# 🪟 Interfaz gráfica
# ==============================

class AplicacionCalificador:
    def __init__(self, root):
        self.root = root
        self.root.title("🧾 Calificador Interactivo - Generador de PDFs")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        self.root.configure(bg="#f7f7f7")
        
        # Variables globales
        self.ruta_imagen = None
        self.imagen_tk = None
        self.preguntas_personalizadas = []
        
        self.crear_interfaz()
    
    def crear_interfaz(self):
        # Notebook para pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Crear pestañas
        self.crear_pestana_calificacion()
        self.crear_pestana_generador()
        self.crear_pestana_personalizado()
        self.crear_pestana_cargar_json()
    
    def crear_pestana_calificacion(self):
        # Pestaña 1: Calificación
        frame_calificacion = ttk.Frame(self.notebook)
        self.notebook.add(frame_calificacion, text="📊 Calificar Exámenes")
        
        frame_main_cal = tk.Frame(frame_calificacion, bg="#f7f7f7")
        frame_main_cal.pack(fill="both", expand=True)
        
        frame_left_cal = tk.Frame(frame_main_cal, bg="#ffffff", bd=1, relief="solid")
        frame_left_cal.pack(side="left", fill="both", expand=True)
        
        frame_right_cal = tk.Frame(frame_main_cal, bg="#f7f7f7", width=260)
        frame_right_cal.pack(side="right", fill="y", padx=(10,0))
        
        # Panel izquierdo: imagen calificada
        self.label_canvas = tk.Label(frame_left_cal, bg="black")
        self.label_canvas.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Panel derecho: controles y clave
        tk.Label(frame_right_cal, text="Clave de Respuestas", font=("Arial", 11, "bold"), bg="#f7f7f7").pack(pady=(6,4))
        
        letras = ['A', 'B', 'C', 'D', 'E']
        self.respuestas_vars = []
        
        for i in range(5):
            cont = tk.Frame(frame_right_cal, bg="#f7f7f7")
            cont.pack(fill="x", pady=4, padx=6)
            tk.Label(cont, text=f"P{i+1}:", width=4, anchor="w", bg="#f7f7f7").pack(side="left")
            var = tk.StringVar(value="")
            self.respuestas_vars.append(var)
            for letra in letras:
                rb = tk.Radiobutton(cont, text=letra, variable=var, value=letra.lower(), bg="#f7f7f7")
                rb.deselect()
                rb.pack(side="left", padx=2)
        
        tk.Frame(frame_right_cal, height=8, bg="#f7f7f7").pack()
        
        # Botones y controles
        btn_sel = tk.Button(frame_right_cal, text="📂 Seleccionar Imagen", command=self.seleccionar_imagen)
        btn_sel.pack(fill="x", padx=8, pady=(4,2))
        
        self.lbl_imagen_sel = tk.Label(frame_right_cal, text="Ninguna imagen seleccionada", bg="#f7f7f7", anchor="w")
        self.lbl_imagen_sel.pack(fill="x", padx=8)
        
        self.label_resultado = tk.Label(frame_right_cal, text="", font=("Arial", 12, "bold"), bg="#f7f7f7")
        self.label_resultado.pack(pady=(10,4))
        
        btn_calificar = tk.Button(frame_right_cal, text="🚀 Calificar Examen", bg="#2e8b57", fg="white", command=self.calificar_examen)
        btn_calificar.pack(fill="x", padx=8, pady=(8,2))
        
        btn_reiniciar = tk.Button(frame_right_cal, text="🔁 Reiniciar / Calificar otro", bg="#808080", fg="white", command=self.reiniciar)
        btn_reiniciar.pack(fill="x", padx=8, pady=(4,6))
        
        btn_guardar = tk.Button(frame_right_cal, text="💾 Guardar imagen calificada", command=self.guardar_calificada)
        btn_guardar.pack(fill="x", padx=8, pady=(4,6))
        
        tk.Label(frame_right_cal, text="5 preguntas · opciones A–E", bg="#f7f7f7", fg="#555").pack(side="bottom", pady=6)
    
    def crear_pestana_generador(self):
        # Pestaña 2: Generar Exámenes PDF
        frame_generar = ttk.Frame(self.notebook)
        self.notebook.add(frame_generar, text="🆕 Generar PDFs")
        
        frame_main_gen = tk.Frame(frame_generar, bg="#f7f7f7")
        frame_main_gen.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configuración de exámenes PDF
        tk.Label(frame_main_gen, text="Generador de Exámenes en PDF", 
                font=("Arial", 16, "bold"), bg="#f7f7f7").pack(pady=(0,15))
        
        frame_config = tk.Frame(frame_main_gen, bg="#f7f7f7")
        frame_config.pack(fill="x", pady=10)
        
        # Número de preguntas
        tk.Label(frame_config, text="Número de preguntas:", bg="#f7f7f7").grid(row=0, column=0, sticky="w", padx=(0,10))
        self.var_num_preguntas = tk.IntVar(value=5)
        spin_preguntas = tk.Spinbox(frame_config, from_=1, to=20, textvariable=self.var_num_preguntas, width=5)
        spin_preguntas.grid(row=0, column=1, sticky="w")
        
        # Número de opciones
        tk.Label(frame_config, text="Opciones por pregunta:", bg="#f7f7f7").grid(row=0, column=2, sticky="w", padx=(20,10))
        self.var_num_opciones = tk.IntVar(value=5)
        spin_opciones = tk.Spinbox(frame_config, from_=2, to=7, textvariable=self.var_num_opciones, width=5)
        spin_opciones.grid(row=0, column=3, sticky="w")
        
        # Temas disponibles
        tk.Label(frame_main_gen, text="Temas disponibles:", font=("Arial", 11, "bold"), 
                bg="#f7f7f7").pack(anchor="w", pady=(15,5))
        
        # Frame para temas predefinidos
        frame_temas = tk.Frame(frame_main_gen, bg="#f7f7f7")
        frame_temas.pack(fill="x", pady=5)
        
        temas_predefinidos = list(BANCO_PREGUNTAS.keys())
        self.var_temas_seleccionados = {}
        
        for i, tema in enumerate(temas_predefinidos):
            var = tk.BooleanVar(value=True)
            self.var_temas_seleccionados[tema] = var
            cb = tk.Checkbutton(frame_temas, text=tema, variable=var, bg="#f7f7f7")
            cb.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=2)
        
        # Temas personalizados
        tk.Label(frame_main_gen, text="Temas personalizados (uno por línea):", 
                font=("Arial", 11, "bold"), bg="#f7f7f7").pack(anchor="w", pady=(15,5))
        
        self.text_temas_personalizados = tk.Text(frame_main_gen, height=3, width=50)
        self.text_temas_personalizados.pack(fill="x", pady=(0,10))
        
        btn_generar = tk.Button(frame_main_gen, text="📄 Generar Exámenes PDF", 
                            bg="#dc3545", fg="white", font=("Arial", 12, "bold"),
                            command=self.generar_pdfs_desde_interfaz)
        btn_generar.pack(fill="x", pady=20)
        
        # Información
        frame_info = tk.Frame(frame_main_gen, bg="#e8f4f8", bd=1, relief="solid")
        frame_info.pack(fill="x", pady=10)
        tk.Label(frame_info, text="💡 Ventajas de los PDFs generados:", 
                font=("Arial", 10, "bold"), bg="#e8f4f8").pack(anchor="w", padx=10, pady=(10,5))
        tk.Label(frame_info, text="• Formato PDF estándar listo para imprimir y escanear", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info, text="• Burbujas de tamaño óptimo para detección automática", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info, text="• Diseño limpio y profesional", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info, text="• Separación entre cuestionario y hoja de respuestas", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info, text="• Compatible con cualquier impresora y escáner", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=(2,10))
    
    def crear_pestana_personalizado(self):
        # Pestaña 3: Cuestionarios Personalizados
        frame_personalizado = ttk.Frame(self.notebook)
        self.notebook.add(frame_personalizado, text="✏️ Cuestionarios Personalizados")
        
        # Crear frame principal con scrollbar
        frame_main_container = tk.Frame(frame_personalizado, bg="#f7f7f7")
        frame_main_container.pack(fill="both", expand=True)
        
        # Crear canvas y scrollbar
        canvas = tk.Canvas(frame_main_container, bg="#f7f7f7", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame_main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f7f7f7")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y")
        
        # Configurar scroll con mouse wheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Ahora usamos scrollable_frame en lugar de frame_main_pers
        frame_main_pers = scrollable_frame
        
        tk.Label(frame_main_pers, text="Generador de Cuestionarios Personalizados", 
                font=("Arial", 16, "bold"), bg="#f7f7f7").pack(pady=(0,15))
        
        # Frame para configuración
        frame_config_pers = tk.Frame(frame_main_pers, bg="#f7f7f7")
        frame_config_pers.pack(fill="x", pady=10)
        
        tk.Label(frame_config_pers, text="Título del cuestionario:", bg="#f7f7f7").grid(row=0, column=0, sticky="w", padx=(0,10))
        self.var_titulo_personalizado = tk.StringVar(value="Examen Personalizado")
        self.entry_titulo = tk.Entry(frame_config_pers, textvariable=self.var_titulo_personalizado, width=30)
        self.entry_titulo.grid(row=0, column=1, sticky="w")
        
        tk.Label(frame_config_pers, text="Número de opciones:", bg="#f7f7f7").grid(row=0, column=2, sticky="w", padx=(20,10))
        self.var_opciones_pers = tk.IntVar(value=5)
        self.spin_opciones_pers = tk.Spinbox(frame_config_pers, from_=2, to=7, textvariable=self.var_opciones_pers, width=5)
        self.spin_opciones_pers.grid(row=0, column=3, sticky="w")
        
        # Frame para ingresar preguntas
        frame_preguntas_pers = tk.Frame(frame_main_pers, bg="#f7f7f7")
        frame_preguntas_pers.pack(fill="both", expand=True, pady=10)
        
        # Widget para ingresar nueva pregunta
        frame_nueva_pregunta = tk.LabelFrame(frame_preguntas_pers, text="Agregar Nueva Pregunta", 
                                            bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_nueva_pregunta.pack(fill="x", pady=(0,10))
        
        tk.Label(frame_nueva_pregunta, text="Enunciado:", bg="#f7f7f7").pack(anchor="w", padx=10, pady=(10,5))
        self.text_enunciado = tk.Text(frame_nueva_pregunta, height=3, width=80)
        self.text_enunciado.pack(fill="x", padx=10, pady=(0,10))
        
        self.frame_opciones_pers = tk.Frame(frame_nueva_pregunta, bg="#f7f7f7")
        self.frame_opciones_pers.pack(fill="x", padx=10, pady=5)
        
        self.labels_opciones = []
        self.entries_opciones = []
        
        self.actualizar_campos_opciones()
        
        # Botón para agregar pregunta
        btn_agregar_pregunta = tk.Button(frame_nueva_pregunta, text="➕ Agregar Pregunta", 
                                        bg="#28a745", fg="white", command=self.agregar_pregunta)
        btn_agregar_pregunta.pack(pady=10)
        
        # Lista de preguntas agregadas
        frame_lista_preguntas = tk.LabelFrame(frame_preguntas_pers, text="Preguntas Agregadas", 
                                            bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_lista_preguntas.pack(fill="both", expand=True, pady=(10,0))
        
        # Treeview para mostrar preguntas
        tree_columns = ("#", "Enunciado", "Opciones")
        self.tree_preguntas = ttk.Treeview(frame_lista_preguntas, columns=tree_columns, show="headings", height=8)
        self.tree_preguntas.heading("#", text="#")
        self.tree_preguntas.heading("Enunciado", text="Enunciado")
        self.tree_preguntas.heading("Opciones", text="Opciones")
        
        self.tree_preguntas.column("#", width=50)
        self.tree_preguntas.column("Enunciado", width=400)
        self.tree_preguntas.column("Opciones", width=200)
        
        scroll_tree = ttk.Scrollbar(frame_lista_preguntas, orient="vertical", command=self.tree_preguntas.yview)
        self.tree_preguntas.configure(yscrollcommand=scroll_tree.set)
        
        self.tree_preguntas.pack(side="left", fill="both", expand=True)
        scroll_tree.pack(side="right", fill="y")
        
        # Botones para gestionar preguntas
        frame_botones_preguntas = tk.Frame(frame_lista_preguntas, bg="#f7f7f7")
        frame_botones_preguntas.pack(fill="x", pady=5)
        
        btn_editar = tk.Button(frame_botones_preguntas, text="✏️ Editar Seleccionada", 
                            command=self.editar_pregunta)
        btn_editar.pack(side="left", padx=5)
        
        btn_eliminar = tk.Button(frame_botones_preguntas, text="🗑️ Eliminar Seleccionada", 
                                command=self.eliminar_pregunta)
        btn_eliminar.pack(side="left", padx=5)
        
        btn_limpiar = tk.Button(frame_botones_preguntas, text="🔁 Limpiar Todo", 
                            command=self.limpiar_todo)
        btn_limpiar.pack(side="left", padx=5)
        
        # Botones para guardar y generar
        frame_botones_guardar = tk.Frame(frame_main_pers, bg="#f7f7f7")
        frame_botones_guardar.pack(fill="x", pady=10)
        
        btn_guardar_json = tk.Button(frame_botones_guardar, text="💾 Guardar como JSON", 
                                   bg="#17a2b8", fg="white", command=self.guardar_cuestionario_json)
        btn_guardar_json.pack(side="left", padx=5, pady=5)
        
        btn_generar_personalizado = tk.Button(frame_botones_guardar, text="📄 Generar Cuestionario PDF", 
                                            bg="#dc3545", fg="white", command=self.generar_pdf_personalizado)
        btn_generar_personalizado.pack(side="left", padx=5, pady=5)
        
        # Actualizar campos cuando cambie el número de opciones
        self.var_opciones_pers.trace('w', lambda *args: self.actualizar_campos_opciones())
        
        # Información
        frame_info_pers = tk.Frame(frame_main_pers, bg="#e8f4f8", bd=1, relief="solid")
        frame_info_pers.pack(fill="x", pady=10)
        
        tk.Label(frame_info_pers, text="💡 Cómo usar el generador personalizado:", 
                font=("Arial", 10, "bold"), bg="#e8f4f8").pack(anchor="w", padx=10, pady=(10,5))
        tk.Label(frame_info_pers, text="1. Ingresa el enunciado de la pregunta", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info_pers, text="2. Completa todas las opciones de respuesta", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info_pers, text="3. Haz clic en 'Agregar Pregunta' para añadirla a la lista", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info_pers, text="4. Repite hasta tener todas las preguntas deseadas", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info_pers, text="5. Guarda como JSON o genera PDF directamente", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=(2,10))
            
    def crear_pestana_cargar_json(self):
        # Pestaña 4: Cargar desde JSON
        frame_cargar = ttk.Frame(self.notebook)
        self.notebook.add(frame_cargar, text="📁 Cargar JSON")
        
        # Crear frame principal con scrollbar
        frame_main_container = tk.Frame(frame_cargar, bg="#f7f7f7")
        frame_main_container.pack(fill="both", expand=True)
        
        # Crear canvas y scrollbar
        canvas = tk.Canvas(frame_main_container, bg="#f7f7f7", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame_main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f7f7f7")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        scrollbar.pack(side="right", fill="y")
        
        # Configurar scroll con mouse wheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Ahora usamos scrollable_frame en lugar de frame_main_cargar
        frame_main_cargar = scrollable_frame
        
        tk.Label(frame_main_cargar, text="Cargar Cuestionarios desde JSON", 
                font=("Arial", 16, "bold"), bg="#f7f7f7").pack(pady=(0,15))
        
        # Frame para cargar archivo
        frame_cargar_archivo = tk.LabelFrame(frame_main_cargar, text="Cargar Archivo JSON", 
                                           bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_cargar_archivo.pack(fill="x", pady=10)
        
        btn_seleccionar_json = tk.Button(frame_cargar_archivo, text="📂 Seleccionar Archivo JSON", 
                                       command=self.seleccionar_archivo_json)
        btn_seleccionar_json.pack(pady=10)
        
        self.lbl_archivo_json = tk.Label(frame_cargar_archivo, text="Ningún archivo seleccionado", 
                                       bg="#f7f7f7", wraplength=600)
        self.lbl_archivo_json.pack(pady=5)
        
        # Información del cuestionario cargado
        frame_info_cuestionario = tk.LabelFrame(frame_main_cargar, text="Información del Cuestionario", 
                                              bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_info_cuestionario.pack(fill="x", pady=10)
        
        self.lbl_titulo_cargado = tk.Label(frame_info_cuestionario, text="Título: No cargado", 
                                         bg="#f7f7f7", anchor="w")
        self.lbl_titulo_cargado.pack(fill="x", padx=10, pady=2)
        
        self.lbl_tema_cargado = tk.Label(frame_info_cuestionario, text="Tema: No cargado", 
                                       bg="#f7f7f7", anchor="w")
        self.lbl_tema_cargado.pack(fill="x", padx=10, pady=2)
        
        self.lbl_preguntas_cargado = tk.Label(frame_info_cuestionario, text="Preguntas: 0", 
                                            bg="#f7f7f7", anchor="w")
        self.lbl_preguntas_cargado.pack(fill="x", padx=10, pady=2)
        
        self.lbl_fecha_cargado = tk.Label(frame_info_cuestionario, text="Fecha: No disponible", 
                                        bg="#f7f7f7", anchor="w")
        self.lbl_fecha_cargado.pack(fill="x", padx=10, pady=2)
        
        # Botón para generar PDF desde JSON
        btn_generar_desde_json = tk.Button(frame_main_cargar, text="📄 Generar PDF desde JSON", 
                                         bg="#28a745", fg="white", font=("Arial", 12, "bold"),
                                         command=self.generar_desde_json)
        btn_generar_desde_json.pack(fill="x", pady=20)
        
        # Lista de cuestionarios guardados
        frame_lista_guardados = tk.LabelFrame(frame_main_cargar, text="Cuestionarios Guardados", 
                                            bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_lista_guardados.pack(fill="both", expand=True, pady=10)
        
        # Treeview para cuestionarios guardados
        tree_columns_guardados = ("Título", "Tema", "Preguntas", "Archivo", "Fecha")
        self.tree_guardados = ttk.Treeview(frame_lista_guardados, columns=tree_columns_guardados, show="headings", height=8)
        
        for col in tree_columns_guardados:
            self.tree_guardados.heading(col, text=col)
            self.tree_guardados.column(col, width=120)
        
        scroll_tree_guardados = ttk.Scrollbar(frame_lista_guardados, orient="vertical", command=self.tree_guardados.yview)
        self.tree_guardados.configure(yscrollcommand=scroll_tree_guardados.set)
        
        self.tree_guardados.pack(side="left", fill="both", expand=True)
        scroll_tree_guardados.pack(side="right", fill="y")
        
        # Botones para la lista de guardados
        frame_botones_guardados = tk.Frame(frame_lista_guardados, bg="#f7f7f7")
        frame_botones_guardados.pack(fill="x", pady=5)
        
        btn_actualizar_lista = tk.Button(frame_botones_guardados, text="🔄 Actualizar Lista", 
                                       command=self.actualizar_lista_guardados)
        btn_actualizar_lista.pack(side="left", padx=5)
        
        btn_cargar_desde_lista = tk.Button(frame_botones_guardados, text="📂 Cargar Seleccionado", 
                                         command=self.cargar_desde_lista)
        btn_cargar_desde_lista.pack(side="left", padx=5)
        
        btn_generar_desde_lista = tk.Button(frame_botones_guardados, text="📄 Generar PDF", 
                                          command=self.generar_desde_lista)
        btn_generar_desde_lista.pack(side="left", padx=5)
        
        # Cargar lista inicial
        self.actualizar_lista_guardados()

    # ==============================
    # Métodos de la pestaña Calificación
    # ==============================
    
    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar examen a calificar",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png")]
        )
        if ruta:
            self.ruta_imagen = ruta
            self.lbl_imagen_sel.config(text=os.path.basename(ruta))
            self.limpiar_canvas()
    
    def limpiar_canvas(self):
        self.imagen_tk = None
        self.label_canvas.config(image="", text="")
    
    def validar_clave(self):
        for i, var in enumerate(self.respuestas_vars):
            val = var.get()
            if val not in ['a','b','c','d','e']:
                return False, i+1
        return True, None
    
    def ajustar_imagen_para_label(self, img_cv, max_w, max_h):
        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]
        scale = min(max_w / w, max_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        img_pil = Image.fromarray(img_rgb).resize((new_w, new_h))
        return ImageTk.PhotoImage(img_pil)
    
    def calificar_examen(self):
        if not self.ruta_imagen:
            messagebox.showerror("Error", "Selecciona primero una imagen.")
            return
        
        ok, falta = self.validar_clave()
        if not ok:
            messagebox.showerror("Clave incompleta", f"Selecciona una opción para la pregunta {falta}.")
            return
        
        clave = {i: ord(var.get()) - 97 for i, var in enumerate(self.respuestas_vars)}
        
        try:
            puntaje, hoja = procesar_imagen(self.ruta_imagen, clave)
        except Exception as e:
            messagebox.showerror("Error al procesar", str(e))
            return
        
        self.label_canvas.update_idletasks()
        max_w = self.label_canvas.winfo_width() or 480
        max_h = self.label_canvas.winfo_height() or 420
        self.imagen_tk = self.ajustar_imagen_para_label(hoja, max_w-4, max_h-4)
        self.label_canvas.config(image=self.imagen_tk)
        
        self.label_resultado.config(text=f"Calificación: {puntaje:.2f}%")
    
    def reiniciar(self):
        self.ruta_imagen = None
        self.imagen_tk = None
        self.label_canvas.config(image="", text="")
        self.lbl_imagen_sel.config(text="Ninguna imagen seleccionada")
        self.label_resultado.config(text="")
        for var in self.respuestas_vars:
            var.set("")
    
    def guardar_calificada(self):
        if not self.ruta_imagen or self.imagen_tk is None:
            messagebox.showinfo("Nada que guardar", "Primero selecciona y califica una imagen.")
            return
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar")
        if not carpeta:
            return
        nombre_salida = os.path.splitext(os.path.basename(self.ruta_imagen))[0] + "_calificada.png"
        salida = os.path.join(carpeta, nombre_salida)
        clave = {i: ord(var.get()) - 97 for i, var in enumerate(self.respuestas_vars)}
        try:
            _, hoja = procesar_imagen(self.ruta_imagen, clave)
            cv2.imwrite(salida, hoja)
            messagebox.showinfo("Guardado", f"Imagen guardada en:\n{salida}")
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))
    
    # ==============================
    # Métodos de la pestaña Generador PDF
    # ==============================
    
    def generar_pdfs_desde_interfaz(self):
        # Obtener temas seleccionados
        temas_seleccionados = []
        
        # Temas predefinidos seleccionados
        for tema, var in self.var_temas_seleccionados.items():
            if var.get():
                temas_seleccionados.append(tema)
        
        # Temas personalizados
        temas_personalizados_texto = self.text_temas_personalizados.get("1.0", "end-1c").strip()
        if temas_personalizados_texto:
            temas_personalizados = [tema.strip() for tema in temas_personalizados_texto.split('\n') if tema.strip()]
            temas_seleccionados.extend(temas_personalizados)
        
        if not temas_seleccionados:
            messagebox.showerror("Error", "Selecciona al menos un tema.")
            return
        
        num_preguntas = self.var_num_preguntas.get()
        num_opciones = self.var_num_opciones.get()
        
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar los PDFs")
        if not carpeta:
            return
        
        try:
            resultados, claves = GeneradorPDF.generar_examenes_masivos(
                temas=temas_seleccionados,
                num_preguntas=num_preguntas,
                num_opciones=num_opciones,
                carpeta_salida=carpeta
            )
            
            archivos_generados = len(temas_seleccionados) * 3  # cuestionario + hoja estudiante + hoja profesor
            
            messagebox.showinfo("Éxito", 
                            f"✅ Se generaron {archivos_generados} archivos PDF en:\n{carpeta}\n\n"
                            f"• {len(temas_seleccionados)} cuestionarios con preguntas\n"
                            f"• {len(temas_seleccionados)} hojas de respuestas para estudiantes\n"
                            f"• {len(temas_seleccionados)} hojas de corrección para profesores\n"
                            f"• Archivo de claves: claves_respuestas.txt\n"
                            f"• Banco de preguntas: preguntas_completas.json")
            
            # Preguntar si abrir la carpeta
            abrir = messagebox.askyesno("Abrir carpeta", "¿Deseas abrir la carpeta con los archivos generados?")
            if abrir:
                if os.name == 'nt':  # Windows
                    os.startfile(carpeta)
                elif os.name == 'posix':  # macOS, Linux
                    os.system(f'open "{carpeta}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{carpeta}"')
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron generar los PDFs:\n{str(e)}")
    
    # ==============================
    # Métodos de la pestaña Personalizado
    # ==============================
    
    def actualizar_campos_opciones(self):
        """Actualiza los campos de opciones según el número seleccionado"""
        # Limpiar frame existente
        for widget in self.frame_opciones_pers.winfo_children():
            widget.destroy()
        
        self.labels_opciones.clear()
        self.entries_opciones.clear()
        
        num_opciones = self.var_opciones_pers.get()
        letras = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        
        tk.Label(self.frame_opciones_pers, text="Opciones de respuesta:", 
                bg="#f7f7f7", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", columnspan=2)
        
        for i in range(num_opciones):
            lbl = tk.Label(self.frame_opciones_pers, text=f"{letras[i]}:", bg="#f7f7f7")
            lbl.grid(row=i+1, column=0, sticky="w", padx=(0,5), pady=2)
            self.labels_opciones.append(lbl)
            
            entry = tk.Entry(self.frame_opciones_pers, width=60)
            entry.grid(row=i+1, column=1, sticky="w", padx=(0,10), pady=2)
            self.entries_opciones.append(entry)
    
    def agregar_pregunta(self):
        enunciado = self.text_enunciado.get("1.0", "end-1c").strip()
        if not enunciado:
            messagebox.showerror("Error", "El enunciado no puede estar vacío.")
            return
        
        opciones = []
        for i, entry in enumerate(self.entries_opciones):
            texto_opcion = entry.get().strip()
            if not texto_opcion:
                messagebox.showerror("Error", f"La opción {chr(65+i)} no puede estar vacía.")
                return
            opciones.append(texto_opcion)
        
        # Agregar a la lista
        nueva_pregunta = {
            "enunciado": enunciado,
            "opciones": opciones
        }
        self.preguntas_personalizadas.append(nueva_pregunta)
        
        # Actualizar lista visual
        self.actualizar_lista_preguntas()
        
        # Limpiar campos
        self.text_enunciado.delete("1.0", "end")
        for entry in self.entries_opciones:
            entry.delete(0, "end")
        
        messagebox.showinfo("Éxito", f"Pregunta {len(self.preguntas_personalizadas)} agregada correctamente.")
    
    def actualizar_lista_preguntas(self):
        """Actualiza la lista visual de preguntas"""
        self.tree_preguntas.delete(*self.tree_preguntas.get_children())
        
        for i, pregunta in enumerate(self.preguntas_personalizadas, 1):
            # Acortar texto para visualización
            enunciado_corto = (pregunta['enunciado'][:60] + '...') if len(pregunta['enunciado']) > 60 else pregunta['enunciado']
            opciones_texto = ", ".join(pregunta['opciones'][:3]) + ("..." if len(pregunta['opciones']) > 3 else "")
            
            self.tree_preguntas.insert("", "end", values=(i, enunciado_corto, opciones_texto))
    
    def eliminar_pregunta(self):
        seleccion = self.tree_preguntas.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Selecciona una pregunta para eliminar.")
            return
        
        indice = self.tree_preguntas.index(seleccion[0])
        self.preguntas_personalizadas.pop(indice)
        self.actualizar_lista_preguntas()
    
    def editar_pregunta(self):
        seleccion = self.tree_preguntas.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Selecciona una pregunta para editar.")
            return
        
        indice = self.tree_preguntas.index(seleccion[0])
        pregunta = self.preguntas_personalizadas[indice]
        
        # Cargar datos en los campos
        self.text_enunciado.delete("1.0", "end")
        self.text_enunciado.insert("1.0", pregunta['enunciado'])
        
        for i, entry in enumerate(self.entries_opciones):
            if i < len(pregunta['opciones']):
                entry.delete(0, "end")
                entry.insert(0, pregunta['opciones'][i])
            else:
                entry.delete(0, "end")
        
        # Eliminar la pregunta actual (se reinsertará al guardar)
        self.preguntas_personalizadas.pop(indice)
        self.actualizar_lista_preguntas()
    
    def limpiar_todo(self):
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar todas las preguntas?"):
            self.preguntas_personalizadas.clear()
            self.actualizar_lista_preguntas()
    
    def guardar_cuestionario_json(self):
        if not self.preguntas_personalizadas:
            messagebox.showerror("Error", "No hay preguntas agregadas. Agrega al menos una pregunta.")
            return
        
        titulo = self.var_titulo_personalizado.get().strip()
        if not titulo:
            messagebox.showerror("Error", "El título del cuestionario no puede estar vacío.")
            return
        
        archivo = filedialog.asksaveasfilename(
            title="Guardar cuestionario como JSON",
            defaultextension=".json",
            filetypes=[("Archivos JSON", "*.json")]
        )
        
        if archivo:
            try:
                archivo_guardado = GestorCuestionarios.guardar_cuestionario(
                    self.preguntas_personalizadas, 
                    archivo, 
                    titulo,
                    self.var_titulo_personalizado.get()
                )
                
                messagebox.showinfo("Éxito", f"Cuestionario guardado en:\n{archivo_guardado}")
                self.actualizar_lista_guardados()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el cuestionario:\n{str(e)}")
    
    def generar_pdf_personalizado(self):
        if not self.preguntas_personalizadas:
            messagebox.showerror("Error", "No hay preguntas agregadas. Agrega al menos una pregunta.")
            return
        
        titulo = self.var_titulo_personalizado.get().strip()
        if not titulo:
            messagebox.showerror("Error", "El título del cuestionario no puede estar vacío.")
            return
        
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar los PDFs")
        if not carpeta:
            return
        
        try:
            cuestionario_pdf, hoja_estudiante_pdf, hoja_profesor_pdf, clave = GeneradorPDF.generar_cuestionario_personalizado(
                self.preguntas_personalizadas, titulo, self.var_opciones_pers.get(), carpeta
            )
            
            messagebox.showinfo("Éxito", 
                            f"✅ Cuestionario personalizado generado:\n\n"
                            f"• Cuestionario: {os.path.basename(cuestionario_pdf)}\n"
                            f"• Hoja de respuestas: {os.path.basename(hoja_estudiante_pdf)}\n"
                            f"• Clave de corrección: {os.path.basename(hoja_profesor_pdf)}\n"
                            f"• Archivo de claves: clave_{titulo.lower().replace(' ', '_')}.txt\n"
                            f"• Banco de preguntas: preguntas_{titulo.lower().replace(' ', '_')}.json")
            
            # Preguntar si abrir la carpeta
            abrir = messagebox.askyesno("Abrir carpeta", "¿Deseas abrir la carpeta con los archivos generados?")
            if abrir:
                if os.name == 'nt':  # Windows
                    os.startfile(carpeta)
                elif os.name == 'posix':  # macOS, Linux
                    os.system(f'open "{carpeta}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{carpeta}"')
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el cuestionario:\n{str(e)}")
    
    # ==============================
    # Métodos de la pestaña Cargar JSON
    # ==============================
    
    def seleccionar_archivo_json(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo JSON",
            filetypes=[("Archivos JSON", "*.json")]
        )
        
        if archivo:
            try:
                self.archivo_json_cargado = archivo
                self.lbl_archivo_json.config(text=os.path.basename(archivo))
                
                # Cargar y mostrar información del cuestionario
                datos = GestorCuestionarios.cargar_cuestionario(archivo)
                
                self.lbl_titulo_cargado.config(text=f"Título: {datos.get('titulo', 'No disponible')}")
                self.lbl_tema_cargado.config(text=f"Tema: {datos.get('tema', 'No disponible')}")
                self.lbl_preguntas_cargado.config(text=f"Preguntas: {datos.get('total_preguntas', 0)}")
                self.lbl_fecha_cargado.config(text=f"Fecha: {datos.get('fecha_creacion', 'No disponible')}")
                
                messagebox.showinfo("Éxito", "Cuestionario cargado correctamente.")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el archivo JSON:\n{str(e)}")
    
    def actualizar_lista_guardados(self):
        """Actualiza la lista de cuestionarios guardados"""
        self.tree_guardados.delete(*self.tree_guardados.get_children())
        
        cuestionarios = GestorCuestionarios.listar_cuestionarios_guardados()
        
        for cuestionario in cuestionarios:
            self.tree_guardados.insert("", "end", values=(
                cuestionario['titulo'],
                cuestionario['tema'],
                cuestionario['total_preguntas'],
                cuestionario['archivo'],
                cuestionario['fecha_creacion']
            ))
    
    def cargar_desde_lista(self):
        """Carga un cuestionario desde la lista de guardados"""
        seleccion = self.tree_guardados.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Selecciona un cuestionario de la lista.")
            return
        
        item = self.tree_guardados.item(seleccion[0])
        archivo = item['values'][3]  # Nombre del archivo
        
        try:
            self.archivo_json_cargado = archivo
            self.lbl_archivo_json.config(text=archivo)
            
            # Cargar y mostrar información del cuestionario
            datos = GestorCuestionarios.cargar_cuestionario(archivo)
            
            self.lbl_titulo_cargado.config(text=f"Título: {datos.get('titulo', 'No disponible')}")
            self.lbl_tema_cargado.config(text=f"Tema: {datos.get('tema', 'No disponible')}")
            self.lbl_preguntas_cargado.config(text=f"Preguntas: {datos.get('total_preguntas', 0)}")
            self.lbl_fecha_cargado.config(text=f"Fecha: {datos.get('fecha_creacion', 'No disponible')}")
            
            messagebox.showinfo("Éxito", "Cuestionario cargado correctamente.")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el cuestionario:\n{str(e)}")
    
    def generar_desde_json(self):
        """Genera PDFs desde un archivo JSON cargado"""
        if not hasattr(self, 'archivo_json_cargado') or not self.archivo_json_cargado:
            messagebox.showerror("Error", "Primero carga un archivo JSON.")
            return
        
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar los PDFs")
        if not carpeta:
            return
        
        try:
            cuestionario_pdf, hoja_estudiante_pdf, hoja_profesor_pdf, clave = GeneradorPDF.generar_desde_json(
                self.archivo_json_cargado, carpeta
            )
            
            messagebox.showinfo("Éxito", 
                            f"✅ Cuestionario generado desde JSON:\n\n"
                            f"• Cuestionario: {os.path.basename(cuestionario_pdf)}\n"
                            f"• Hoja de respuestas: {os.path.basename(hoja_estudiante_pdf)}\n"
                            f"• Clave de corrección: {os.path.basename(hoja_profesor_pdf)}\n"
                            f"• Archivos adicionales generados en la carpeta")
            
            # Preguntar si abrir la carpeta
            abrir = messagebox.askyesno("Abrir carpeta", "¿Deseas abrir la carpeta con los archivos generados?")
            if abrir:
                if os.name == 'nt':  # Windows
                    os.startfile(carpeta)
                elif os.name == 'posix':  # macOS, Linux
                    os.system(f'open "{carpeta}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{carpeta}"')
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el cuestionario:\n{str(e)}")
    
    def generar_desde_lista(self):
        """Genera PDFs directamente desde un cuestionario de la lista"""
        seleccion = self.tree_guardados.selection()
        if not seleccion:
            messagebox.showinfo("Información", "Selecciona un cuestionario de la lista.")
            return
        
        item = self.tree_guardados.item(seleccion[0])
        archivo = item['values'][3]  # Nombre del archivo
        
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar los PDFs")
        if not carpeta:
            return
        
        try:
            cuestionario_pdf, hoja_estudiante_pdf, hoja_profesor_pdf, clave = GeneradorPDF.generar_desde_json(
                archivo, carpeta
            )
            
            messagebox.showinfo("Éxito", 
                            f"✅ Cuestionario generado desde JSON:\n\n"
                            f"• Cuestionario: {os.path.basename(cuestionario_pdf)}\n"
                            f"• Hoja de respuestas: {os.path.basename(hoja_estudiante_pdf)}\n"
                            f"• Clave de corrección: {os.path.basename(hoja_profesor_pdf)}\n"
                            f"• Archivos adicionales generados en la carpeta")
            
            # Preguntar si abrir la carpeta
            abrir = messagebox.askyesno("Abrir carpeta", "¿Deseas abrir la carpeta con los archivos generados?")
            if abrir:
                if os.name == 'nt':  # Windows
                    os.startfile(carpeta)
                elif os.name == 'posix':  # macOS, Linux
                    os.system(f'open "{carpeta}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{carpeta}"')
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el cuestionario:\n{str(e)}")

# Inicio de la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = AplicacionCalificador(root)
    root.mainloop()
