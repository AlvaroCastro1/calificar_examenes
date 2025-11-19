# [file name]: main.py

import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import json
import numpy as np

# Importar la lógica del programa
from logica import GeneradorPDF, GestorCuestionarios, BANCO_PREGUNTAS
from calificador_automatico import CalificadorAutomatico

# ==============================
# 🪟 Interfaz gráfica
# ==============================

class AplicacionCalificador:
    def __init__(self, root):
        self.root = root
        self.root.title("🧾 Generador de Cuestionarios PDF - Calificador Automático")
        self.root.geometry("1100x750")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#f7f7f7")
        
        # Variables globales
        self.preguntas_personalizadas = []
        self.calificador = CalificadorAutomatico()
        
        self.crear_interfaz()
    
    def crear_interfaz(self):
        # Notebook para pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Crear pestañas
        self.crear_pestana_calificacion_automatica()
        self.crear_pestana_personalizado()
        self.crear_pestana_cargar_json()
    
    def crear_pestana_calificacion_automatica(self):
        """Crea la pestaña para calificación automática de exámenes"""
        frame_calificacion = ttk.Frame(self.notebook)
        self.notebook.add(frame_calificacion, text="🎯 Calificar Exámenes")
        
        # Frame principal dividido en izquierda y derecha
        frame_main = tk.Frame(frame_calificacion, bg="#f7f7f7")
        frame_main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Panel izquierdo: imagen del examen
        frame_imagen = tk.LabelFrame(frame_main, text="Vista del Examen", bg="#ffffff", font=("Arial", 10, "bold"))
        frame_imagen.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.label_imagen_examen = tk.Label(frame_imagen, bg="black", text="Imagen del examen aparecerá aquí", 
                                           fg="white", font=("Arial", 12))
        self.label_imagen_examen.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Panel derecho: controles
        frame_controles = tk.Frame(frame_main, bg="#f7f7f7", width=350)
        frame_controles.pack(side="right", fill="y")
        frame_controles.pack_propagate(False)
        
        # Título
        tk.Label(frame_controles, text="Calificación Automática", 
                font=("Arial", 14, "bold"), bg="#f7f7f7").pack(pady=(0, 15))
        
        # Sección: Cargar clave de respuestas
        frame_clave = tk.LabelFrame(frame_controles, text="1. Cargar Clave de Respuestas", 
                                  bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_clave.pack(fill="x", pady=(0, 10))
        
        btn_cargar_clave = tk.Button(frame_clave, text="📁 Cargar Clave JSON", 
                                   command=self.cargar_clave_json, bg="#4CAF50", fg="white")
        btn_cargar_clave.pack(fill="x", padx=10, pady=5)
        
        self.label_info_clave = tk.Label(frame_clave, text="No se ha cargado ninguna clave", 
                                       bg="#f7f7f7", wraplength=320, justify="left")
        self.label_info_clave.pack(fill="x", padx=10, pady=(0, 5))
        
        # Sección: Seleccionar examen
        frame_examen = tk.LabelFrame(frame_controles, text="2. Seleccionar Examen", 
                                   bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_examen.pack(fill="x", pady=(0, 10))
        
        btn_seleccionar_examen = tk.Button(frame_examen, text="📷 Seleccionar Imagen", 
                                         command=self.seleccionar_imagen_examen)
        btn_seleccionar_examen.pack(fill="x", padx=10, pady=5)
        
        self.label_info_examen = tk.Label(frame_examen, text="No se ha seleccionado ningún examen", 
                                        bg="#f7f7f7", wraplength=320)
        self.label_info_examen.pack(fill="x", padx=10, pady=(0, 5))
        
        # Sección: Calificar
        frame_accion = tk.LabelFrame(frame_controles, text="3. Calificar Examen", 
                                   bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_accion.pack(fill="x", pady=(0, 10))
        
        btn_calificar = tk.Button(frame_accion, text="🚀 Calificar Automáticamente", 
                                command=self.calificar_examen_automatico, 
                                bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
        btn_calificar.pack(fill="x", padx=10, pady=8)
        
        # Resultados
        frame_resultados = tk.LabelFrame(frame_controles, text="Resultados", 
                                       bg="#f7f7f7", font=("Arial", 10, "bold"))
        frame_resultados.pack(fill="x", pady=(0, 10))
        
        self.label_puntaje = tk.Label(frame_resultados, text="Puntaje: --", 
                                    font=("Arial", 16, "bold"), bg="#f7f7f7")
        self.label_puntaje.pack(pady=5)
        
        self.label_detalle = tk.Label(frame_resultados, text="Correctas: 0/0", 
                                    bg="#f7f7f7")
        self.label_detalle.pack(pady=2)
        
        # Detalles por pregunta
        self.tree_resultados = ttk.Treeview(frame_resultados, 
                                          columns=("Pregunta", "Seleccionada", "Correcta", "Estado"), 
                                          show="headings", height=8)
        self.tree_resultados.heading("Pregunta", text="Pregunta")
        self.tree_resultados.heading("Seleccionada", text="Seleccionada")
        self.tree_resultados.heading("Correcta", text="Correcta")
        self.tree_resultados.heading("Estado", text="Estado")
        
        self.tree_resultados.column("Pregunta", width=60)
        self.tree_resultados.column("Seleccionada", width=70)
        self.tree_resultados.column("Correcta", width=70)
        self.tree_resultados.column("Estado", width=70)
        
        scroll_tree = ttk.Scrollbar(frame_resultados, orient="vertical", 
                                  command=self.tree_resultados.yview)
        self.tree_resultados.configure(yscrollcommand=scroll_tree.set)
        
        self.tree_resultados.pack(side="left", fill="both", expand=True, padx=(0, 5))
        scroll_tree.pack(side="right", fill="y")
        
        # Botones de acción
        frame_botones = tk.Frame(frame_controles, bg="#f7f7f7")
        frame_botones.pack(fill="x", pady=10)
        
        btn_guardar_resultados = tk.Button(frame_botones, text="💾 Guardar Resultados", 
                                         command=self.guardar_resultados_calificacion)
        btn_guardar_resultados.pack(fill="x", pady=2)
        
        btn_convertir_txt_json = tk.Button(frame_botones, text="🔄 Convertir TXT a JSON", 
                                         command=self.convertir_txt_a_json)
        btn_convertir_txt_json.pack(fill="x", pady=2)
        
        btn_reiniciar = tk.Button(frame_botones, text="🔁 Reiniciar", 
                                command=self.reiniciar_calificacion, bg="#f44336", fg="white")
        btn_reiniciar.pack(fill="x", pady=2)
        
        # Información
        frame_info = tk.Frame(frame_controles, bg="#e8f4f8", bd=1, relief="solid")
        frame_info.pack(fill="x", pady=10)
        
        tk.Label(frame_info, text="💡 Instrucciones:", 
                font=("Arial", 10, "bold"), bg="#e8f4f8").pack(anchor="w", padx=10, pady=(10,5))
        tk.Label(frame_info, text="1. Carga un archivo JSON con las respuestas correctas", 
                bg="#e8f4f8", wraplength=320, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info, text="2. Selecciona la imagen del examen escaneado", 
                bg="#e8f4f8", wraplength=320, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info, text="3. Haz clic en 'Calificar Automáticamente'", 
                bg="#e8f4f8", wraplength=320, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info, text="4. Revisa los resultados y guárdalos si es necesario", 
                bg="#e8f4f8", wraplength=320, justify="left").pack(anchor="w", padx=20, pady=(2,10))
    
    def crear_pestana_personalizado(self):
        # Pestaña 2: Cuestionarios Personalizados
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
        # Frame para el enunciado con scrollbar
        frame_enunciado = tk.Frame(frame_nueva_pregunta)
        frame_enunciado.pack(fill="x", padx=10, pady=(0,10))

        self.text_enunciado = tk.Text(frame_enunciado, height=3, width=80, wrap="word")
        scroll_enunciado = tk.Scrollbar(frame_enunciado, orient="vertical", command=self.text_enunciado.yview)
        self.text_enunciado.configure(yscrollcommand=scroll_enunciado.set)

        self.text_enunciado.pack(side="left", fill="both", expand=True)
        scroll_enunciado.pack(side="right", fill="y")
        
        self.frame_opciones_pers = tk.Frame(frame_nueva_pregunta, bg="#f7f7f7")
        self.frame_opciones_pers.pack(fill="x", padx=10, pady=5)
        
        self.labels_opciones = []
        self.entries_opciones = []
        self.radio_buttons = []
        self.respuesta_correcta_var = tk.StringVar(value="")  # Variable para la respuesta correcta
        
        # Frame para seleccionar respuesta correcta - CREAR PRIMERO ESTE FRAME
        frame_respuesta_correcta = tk.Frame(frame_nueva_pregunta, bg="#f7f7f7")
        frame_respuesta_correcta.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame_respuesta_correcta, text="Respuesta correcta:", 
                bg="#f7f7f7", font=("Arial", 9, "bold")).pack(side="left")
        
        # Este frame contendrá los radio buttons para la respuesta correcta
        self.frame_radios_correcta = tk.Frame(frame_respuesta_correcta, bg="#f7f7f7")
        self.frame_radios_correcta.pack(side="left", padx=(10,0))
        
        # AHORA inicializar los campos de opciones
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
        tree_columns = ("#", "Enunciado", "Opciones", "Correcta")
        self.tree_preguntas = ttk.Treeview(frame_lista_preguntas, columns=tree_columns, show="headings", height=8)
        self.tree_preguntas.heading("#", text="#")
        self.tree_preguntas.heading("Enunciado", text="Enunciado")
        self.tree_preguntas.heading("Opciones", text="Opciones")
        self.tree_preguntas.heading("Correcta", text="Respuesta Correcta")
        
        self.tree_preguntas.column("#", width=50)
        self.tree_preguntas.column("Enunciado", width=300)
        self.tree_preguntas.column("Opciones", width=200)
        self.tree_preguntas.column("Correcta", width=100)
        
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
        tk.Label(frame_info_pers, text="3. Selecciona la respuesta correcta", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info_pers, text="4. Haz clic en 'Agregar Pregunta' para añadirla a la lista", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info_pers, text="5. Repite hasta tener todas las preguntas deseadas", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=2)
        tk.Label(frame_info_pers, text="6. Guarda como JSON o genera PDF directamente", 
                bg="#e8f4f8", wraplength=800, justify="left").pack(anchor="w", padx=20, pady=(2,10))
        
    def crear_pestana_cargar_json(self):
        # Pestaña 3: Cargar desde JSON
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
    # Métodos de la pestaña Calificación Automática
    # ==============================
    
    def cargar_clave_json(self):
        """Carga un archivo JSON con las respuestas correctas"""
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo JSON de claves",
            filetypes=[("Archivos JSON", "*.json")]
        )
        
        if ruta:
            try:
                if self.calificador.cargar_clave_desde_json(ruta):
                    self.ruta_clave_json = ruta
                    info = f"✅ Clave cargada: {self.calificador.num_preguntas} preguntas\n{os.path.basename(ruta)}"
                    self.label_info_clave.config(text=info, fg="green")
                else:
                    self.label_info_clave.config(text="❌ Error al cargar la clave", fg="red")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el archivo JSON:\n{str(e)}")
    
    def seleccionar_imagen_examen(self):
        """Selecciona una imagen de examen para calificar"""
        ruta = filedialog.askopenfilename(
            title="Seleccionar imagen del examen",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp")]
        )
        
        if ruta:
            self.ruta_imagen_examen = ruta
            self.label_info_examen.config(text=f"📷 {os.path.basename(ruta)}")
            
            # Mostrar vista previa de la imagen
            self.mostrar_vista_previa_imagen(ruta)
    
    def mostrar_vista_previa_imagen(self, ruta_imagen):
        """Muestra una vista previa de la imagen del examen"""
        try:
            imagen = cv2.imread(ruta_imagen)
            if imagen is not None:
                # Redimensionar para vista previa
                imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
                h, w = imagen_rgb.shape[:2]
                
                # Calcular tamaño máximo para el label
                max_w = self.label_imagen_examen.winfo_width() or 600
                max_h = self.label_imagen_examen.winfo_height() or 400
                
                scale = min(max_w / w, max_h / h, 1.0)  # No escalar más allá del 100%
                new_w, new_h = int(w * scale), int(h * scale)
                
                imagen_redimensionada = cv2.resize(imagen_rgb, (new_w, new_h))
                imagen_pil = Image.fromarray(imagen_redimensionada)
                imagen_tk = ImageTk.PhotoImage(imagen_pil)
                
                self.label_imagen_examen.config(image=imagen_tk, text="")
                self.label_imagen_examen.image = imagen_tk  # Mantener referencia
            else:
                self.label_imagen_examen.config(image="", text="❌ No se pudo cargar la imagen")
        except Exception as e:
            self.label_imagen_examen.config(image="", text=f"❌ Error: {str(e)}")
    
    def calificar_examen_automatico(self):
        """Ejecuta la calificación automática del examen"""
        # Validaciones
        if not hasattr(self, 'ruta_clave_json') or not self.ruta_clave_json:
            messagebox.showerror("Error", "Primero carga un archivo JSON con las respuestas correctas.")
            return
        
        if not hasattr(self, 'ruta_imagen_examen') or not self.ruta_imagen_examen:
            messagebox.showerror("Error", "Primero selecciona una imagen del examen.")
            return
        
        # Mostrar mensaje de procesamiento
        self.label_imagen_examen.config(text="🔄 Procesando imagen...", image="")
        self.root.update()
        
        try:
            # Calificar examen
            puntaje, imagen_procesada, resultados, error = self.calificador.procesar_hoja_respuestas(self.ruta_imagen_examen)
            
            if error:
                messagebox.showerror("Error", f"No se pudo calificar el examen:\n{error}")
                self.label_imagen_examen.config(text="❌ Error en el procesamiento", image="")
                return
            
            # Mostrar resultados
            self.mostrar_resultados_calificacion(puntaje, imagen_procesada, resultados)
            
            # Guardar referencia a los resultados actuales
            self.resultados_actuales = resultados
            self.puntaje_actual = puntaje
            self.imagen_procesada_actual = imagen_procesada
            
            messagebox.showinfo("Calificación completada", 
                              f"✅ Examen calificado correctamente\n\nPuntaje: {puntaje:.2f}%")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado:\n{str(e)}")
            self.label_imagen_examen.config(text="❌ Error inesperado", image="")
    
    def mostrar_resultados_calificacion(self, puntaje, imagen_procesada, resultados):
        """Muestra los resultados de la calificación en la interfaz"""
        # Mostrar imagen procesada
        if imagen_procesada is not None:
            imagen_rgb = cv2.cvtColor(imagen_procesada, cv2.COLOR_BGR2RGB)
            h, w = imagen_rgb.shape[:2]
            
            max_w = self.label_imagen_examen.winfo_width() or 600
            max_h = self.label_imagen_examen.winfo_height() or 400
            
            scale = min(max_w / w, max_h / h, 1.0)
            new_w, new_h = int(w * scale), int(h * scale)
            
            imagen_redimensionada = cv2.resize(imagen_rgb, (new_w, new_h))
            imagen_pil = Image.fromarray(imagen_redimensionada)
            imagen_tk = ImageTk.PhotoImage(imagen_pil)
            
            self.label_imagen_examen.config(image=imagen_tk, text="")
            self.label_imagen_examen.image = imagen_tk
        
        # Actualizar estadísticas
        correctas = sum(1 for r in resultados if r['es_correcta'])
        total = len(resultados)
        
        self.label_puntaje.config(text=f"Puntaje: {puntaje:.2f}%")
        self.label_detalle.config(text=f"Correctas: {correctas}/{total}")
        
        # Colorear según puntaje
        if puntaje >= 80:
            self.label_puntaje.config(fg="green")
        elif puntaje >= 60:
            self.label_puntaje.config(fg="orange")
        else:
            self.label_puntaje.config(fg="red")
        
        # Mostrar detalles por pregunta
        self.tree_resultados.delete(*self.tree_resultados.get_children())
        
        for resultado in resultados:
            preg = resultado['pregunta']
            selec = resultado['letra_seleccionada']
            correcta = resultado['letra_correcta']
            estado = "✅" if resultado['es_correcta'] else "❌"
            
            self.tree_resultados.insert("", "end", values=(preg, selec, correcta, estado))
    
    def guardar_resultados_calificacion(self):
        """Guarda los resultados de la calificación actual"""
        if not hasattr(self, 'resultados_actuales') or not self.resultados_actuales:
            messagebox.showinfo("Información", "Primero califica un examen para poder guardar los resultados.")
            return
        
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar resultados")
        if not carpeta:
            return
        
        try:
            ruta_imagen, ruta_reporte = self.calificador.guardar_resultados(
                self.ruta_imagen_examen,
                self.imagen_procesada_actual,
                self.resultados_actuales,
                self.puntaje_actual,
                carpeta
            )
            
            messagebox.showinfo("Éxito", 
                              f"✅ Resultados guardados en:\n{carpeta}\n\n"
                              f"• Imagen calificada: {os.path.basename(ruta_imagen)}\n"
                              f"• Reporte: {os.path.basename(ruta_reporte)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron guardar los resultados:\n{str(e)}")
    
    def convertir_txt_a_json(self):
        """Convierte un archivo TXT de claves a formato JSON"""
        from calificador_automatico import generar_json_clave_desde_txt
        
        ruta_txt = filedialog.askopenfilename(
            title="Seleccionar archivo TXT de claves",
            filetypes=[("Archivos TXT", "*.txt")]
        )
        
        if ruta_txt:
            ruta_json = filedialog.asksaveasfilename(
                title="Guardar JSON como",
                defaultextension=".json",
                filetypes=[("Archivos JSON", "*.json")]
            )
            
            if ruta_json:
                try:
                    generar_json_clave_desde_txt(ruta_txt, ruta_json)
                    messagebox.showinfo("Éxito", f"Archivo JSON generado:\n{ruta_json}")
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo convertir el archivo:\n{str(e)}")
    
    def reiniciar_calificacion(self):
        """Reinicia la interfaz de calificación"""
        if hasattr(self, 'ruta_clave_json'):
            del self.ruta_clave_json
        if hasattr(self, 'ruta_imagen_examen'):
            del self.ruta_imagen_examen
        if hasattr(self, 'resultados_actuales'):
            del self.resultados_actuales
        if hasattr(self, 'puntaje_actual'):
            del self.puntaje_actual
        if hasattr(self, 'imagen_procesada_actual'):
            del self.imagen_procesada_actual
        
        self.label_info_clave.config(text="No se ha cargado ninguna clave", fg="black")
        self.label_info_examen.config(text="No se ha seleccionado ningún examen")
        self.label_imagen_examen.config(image="", text="Imagen del examen aparecerá aquí")
        self.label_puntaje.config(text="Puntaje: --", fg="black")
        self.label_detalle.config(text="Correctas: 0/0")
        self.tree_resultados.delete(*self.tree_resultados.get_children())

    # ==============================
    # Métodos de la pestaña Personalizado (se mantienen igual)
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
        
        # Actualizar también los radio buttons para respuesta correcta
        self.actualizar_radios_correcta()

    def actualizar_radios_correcta(self):
        """Actualiza los radio buttons para seleccionar respuesta correcta"""
        # Limpiar frame existente
        for widget in self.frame_radios_correcta.winfo_children():
            widget.destroy()
        
        self.radio_buttons.clear()
        num_opciones = self.var_opciones_pers.get()
        letras = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        
        # Crear radio buttons para cada opción
        for i in range(num_opciones):
            rb = tk.Radiobutton(self.frame_radios_correcta, 
                              text=letras[i],
                              variable=self.respuesta_correcta_var,
                              value=letras[i],
                              bg="#f7f7f7")
            rb.pack(side="left", padx=5)
            self.radio_buttons.append(rb)
    
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
        
        # Validar que se haya seleccionado una respuesta correcta
        respuesta_correcta = self.respuesta_correcta_var.get()
        if not respuesta_correcta:
            messagebox.showerror("Error", "Debes seleccionar la respuesta correcta.")
            return
        
        # Convertir letra de respuesta correcta a índice numérico (A=0, B=1, etc.)
        indice_correcto = ord(respuesta_correcta) - 65
        
        # Agregar a la lista
        nueva_pregunta = {
            "enunciado": enunciado,
            "opciones": opciones,
            "respuesta_correcta": indice_correcto,
            "letra_correcta": respuesta_correcta
        }
        self.preguntas_personalizadas.append(nueva_pregunta)
        
        # Actualizar lista visual
        self.actualizar_lista_preguntas()
        
        # Limpiar campos
        self.text_enunciado.delete("1.0", "end")
        for entry in self.entries_opciones:
            entry.delete(0, "end")
        self.respuesta_correcta_var.set("")  # Reiniciar selección
        
        messagebox.showinfo("Éxito", f"Pregunta {len(self.preguntas_personalizadas)} agregada correctamente.\nRespuesta correcta: {respuesta_correcta}")
    
    def actualizar_lista_preguntas(self):
        """Actualiza la lista visual de preguntas"""
        self.tree_preguntas.delete(*self.tree_preguntas.get_children())
        
        for i, pregunta in enumerate(self.preguntas_personalizadas, 1):
            # Acortar texto para visualización
            enunciado_corto = (pregunta['enunciado'][:40] + '...') if len(pregunta['enunciado']) > 40 else pregunta['enunciado']
            opciones_texto = ", ".join(pregunta['opciones'][:2]) + ("..." if len(pregunta['opciones']) > 2 else "")
            respuesta_correcta = pregunta.get('letra_correcta', 'N/A')
            
            self.tree_preguntas.insert("", "end", values=(i, enunciado_corto, opciones_texto, respuesta_correcta))

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
        
        # Cargar respuesta correcta
        letra_correcta = pregunta.get('letra_correcta', '')
        if letra_correcta:
            self.respuesta_correcta_var.set(letra_correcta)
        
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
    # Métodos de la pestaña Cargar JSON (se mantienen igual)
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