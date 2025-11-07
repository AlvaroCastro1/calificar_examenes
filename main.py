import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from imutils.perspective import four_point_transform
from imutils import contours
import numpy as np
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFont
import random
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile

# ==============================
# 📋 Funciones de calificación
# ==============================

def procesar_imagen(ruta_imagen, clave_respuestas):
    imagen = cv2.imread(ruta_imagen)
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    desenfocada = cv2.GaussianBlur(gris, (5, 5), 0)
    bordes = cv2.Canny(desenfocada, 75, 200)

    contornos, _ = cv2.findContours(bordes.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)
    contorno_documento = None

    for c in contornos:
        perimetro = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * perimetro, True)
        if len(aprox) == 4:
            contorno_documento = aprox
            break

    if contorno_documento is None:
        raise ValueError("No se detectó correctamente la hoja del examen.")

    hoja_color = four_point_transform(imagen, contorno_documento.reshape(4, 2))
    hoja_gris = four_point_transform(gris, contorno_documento.reshape(4, 2))
    umbral = cv2.threshold(hoja_gris, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    contornos_preguntas, _ = cv2.findContours(umbral.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    burbujas = []

    for c in contornos_preguntas:
        (x, y, w, h) = cv2.boundingRect(c)
        proporcion = w / float(h) if h != 0 else 0
        if w >= 20 and h >= 20 and 0.9 <= proporcion <= 1.1:
            burbujas.append(c)

    if len(burbujas) < 5:
        raise ValueError("No se detectaron suficientes burbujas en la hoja.")

    burbujas = contours.sort_contours(burbujas, method="top-to-bottom")[0]
    correctas = 0

    # Asumimos 5 opciones por pregunta y 5 preguntas (total 25 burbujas)
    for (pregunta, i) in enumerate(np.arange(0, len(burbujas), 5)):
        cnts = contours.sort_contours(burbujas[i:i + 5])[0]
        seleccionada = None

        for (j, c) in enumerate(cnts):
            mascara = np.zeros(umbral.shape, dtype="uint8")
            cv2.drawContours(mascara, [c], -1, 255, -1)
            mascara = cv2.bitwise_and(umbral, umbral, mask=mascara)
            total = cv2.countNonZero(mascara)
            if seleccionada is None or total > seleccionada[0]:
                seleccionada = (total, j)

        # protección si la clave no tiene la pregunta
        respuesta_correcta = clave_respuestas.get(pregunta, -1)
        if respuesta_correcta < 0 or respuesta_correcta >= len(cnts):
            # si no hay clave válida, marca en rojo la seleccionada
            color = (0, 0, 255)
        else:
            if respuesta_correcta == seleccionada[1]:
                color = (0, 255, 0)
                correctas += 1
            else:
                color = (0, 0, 255)

        # Dibujar contorno de la respuesta correcta (si existe)
        if 0 <= respuesta_correcta < len(cnts):
            cv2.drawContours(hoja_color, [cnts[respuesta_correcta]], -1, color, 2)
        else:
            # si no hay clave válida, dibujar la seleccionada en rojo
            cv2.drawContours(hoja_color, [cnts[seleccionada[1]]], -1, (0,0,255), 2)

    puntaje = (correctas / len(clave_respuestas)) * 100
    return puntaje, hoja_color

# ==============================
# 🆕 Funciones para generar hojas PDF
# ==============================

# Base de datos de preguntas por tema
BANCO_PREGUNTAS = {
    "Matemáticas Básicas": [
        {
            "enunciado": "¿Cuál es el resultado de 15 + 27?",
            "opciones": ["32", "42", "52", "37", "45"]
        },
        {
            "enunciado": "Si un triángulo tiene base 8 cm y altura 5 cm, ¿cuál es su área?",
            "opciones": ["13 cm²", "20 cm²", "40 cm²", "25 cm²", "30 cm²"]
        },
        {
            "enunciado": "¿Qué fracción es equivalente a 0.75?",
            "opciones": ["1/4", "2/3", "3/4", "4/5", "5/6"]
        },
        {
            "enunciado": "Resolver: 3x + 7 = 22",
            "opciones": ["x = 3", "x = 5", "x = 6", "x = 4", "x = 7"]
        },
        {
            "enunciado": "¿Cuál es el MCD de 24 y 36?",
            "opciones": ["6", "8", "12", "4", "18"]
        }
    ],
    "Historia Universal": [
        {
            "enunciado": "¿En qué año comenzó la Segunda Guerra Mundial?",
            "opciones": ["1914", "1939", "1945", "1918", "1929"]
        },
        {
            "enunciado": "¿Quién descubrió América?",
            "opciones": ["Vasco da Gama", "Cristóbal Colón", "Magallanes", "Marco Polo", "Hernán Cortés"]
        },
        {
            "enunciado": "¿Qué civilización construyó las pirámides de Egipto?",
            "opciones": ["Griegos", "Romanos", "Egipcios", "Mayas", "Persas"]
        },
        {
            "enunciado": "¿En qué siglo cayó el Imperio Romano de Occidente?",
            "opciones": ["Siglo III", "Siglo V", "Siglo VII", "Siglo IX", "Siglo XI"]
        },
        {
            "enunciado": "¿Qué revolucionó la industria textil en el siglo XVIII?",
            "opciones": ["Telar mecánico", "Motor de vapor", "Electricidad", "Computadora", "Radio"]
        }
    ],
    "Ciencias Naturales": [
        {
            "enunciado": "¿Qué planeta es conocido como el planeta rojo?",
            "opciones": ["Venus", "Marte", "Júpiter", "Saturno", "Mercurio"]
        },
        {
            "enunciado": "¿Qué gas necesitan las plantas para la fotosíntesis?",
            "opciones": ["Oxígeno", "Nitrógeno", "Dióxido de carbono", "Hidrógeno", "Argón"]
        },
        {
            "enunciado": "¿Cuál es el hueso más largo del cuerpo humano?",
            "opciones": ["Fémur", "Tibia", "Húmero", "Cráneo", "Columna"]
        },
        {
            "enunciado": "¿Qué partícula tiene carga positiva?",
            "opciones": ["Electrón", "Protón", "Neutrón", "Átomo", "Molécula"]
        },
        {
            "enunciado": "¿Qué proceso convierte el agua en vapor?",
            "opciones": ["Condensación", "Evaporación", "Solidificación", "Fusión", "Sublimación"]
        }
    ],
    "Geografía": [
        {
            "enunciado": "¿Cuál es el río más largo del mundo?",
            "opciones": ["Nilo", "Amazonas", "Misisipi", "Yangtsé", "Danubio"]
        },
        {
            "enunciado": "¿Qué montaña es la más alta del mundo?",
            "opciones": ["K2", "Everest", "Aconcagua", "Kilimanjaro", "Mont Blanc"]
        },
        {
            "enunciado": "¿Qué país tiene la mayor población del mundo?",
            "opciones": ["India", "China", "Estados Unidos", "Indonesia", "Brasil"]
        },
        {
            "enunciado": "¿Qué océano es el más grande?",
            "opciones": ["Atlántico", "Pacífico", "Índico", "Ártico", "Antártico"]
        },
        {
            "enunciado": "¿Qué desierto es el más grande del mundo?",
            "opciones": ["Sahara", "Gobi", "Kalahari", "Antártico", "Arábigo"]
        }
    ],
    "Literatura Española": [
        {
            "enunciado": "¿Quién escribió 'Don Quijote de la Mancha'?",
            "opciones": ["Miguel de Cervantes", "Federico García Lorca", "Lope de Vega", "Calderón de la Barca", "Francisco de Quevedo"]
        },
        {
            "enunciado": "¿Qué obra es de Federico García Lorca?",
            "opciones": ["La Celestina", "Bodas de Sangre", "Lazarillo de Tormes", "Rimas y Leyendas", "Los Pazos de Ulloa"]
        },
        {
            "enunciado": "¿En qué siglo vivió Lope de Vega?",
            "opciones": ["Siglo XV", "Siglo XVI", "Siglo XVII", "Siglo XVIII", "Siglo XIX"]
        },
        {
            "enunciado": "¿Qué movimiento literario pertenece al Romanticismo?",
            "opciones": ["Gustavo Adolfo Bécquer", "Miguel de Unamuno", "Antonio Machado", "Pío Baroja", "Benito Pérez Galdós"]
        },
        {
            "enunciado": "¿Qué generación literaria incluye a Antonio Machado?",
            "opciones": ["Generación del 27", "Generación del 98", "Generación del 14", "Generación del 36", "Generación del 50"]
        }
    ]
}

def generar_preguntas_aleatorias(tema, num_preguntas=5):
    """Genera preguntas aleatorias para un tema específico"""
    if tema in BANCO_PREGUNTAS:
        preguntas_tema = BANCO_PREGUNTAS[tema]
        if len(preguntas_tema) >= num_preguntas:
            return random.sample(preguntas_tema, num_preguntas)
        else:
            return preguntas_tema
    else:
        # Generar preguntas genéricas si el tema no está en la base
        preguntas_gen = []
        for i in range(num_preguntas):
            preguntas_gen.append({
                "enunciado": f"Pregunta {i+1} sobre {tema}",
                "opciones": [f"Opción A", f"Opción B", f"Opción C", f"Opción D", f"Opción E"]
            })
        return preguntas_gen

def generar_hoja_respuestas_pdf(tema, num_preguntas=5, num_opciones=5, incluir_clave=False):
    """
    Genera una hoja de respuestas en formato PDF optimizada para escaneo
    
    Args:
        tema (str): Nombre del tema
        num_preguntas (int): Número de preguntas
        num_opciones (int): Número de opciones por pregunta
        incluir_clave (bool): Si incluir la clave de respuestas
    
    Returns:
        tuple: (ruta_pdf, clave_respuestas)
    """
    # Crear archivo temporal para el PDF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf_path = temp_file.name
    temp_file.close()
    
    # Crear canvas PDF
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    # Configuración
    margen = 1 * inch
    ancho_util = width - 2 * margen
    espacio_pregunta = 0.7 * inch
    tamaño_burbuja = 0.2 * inch
    espacio_burbujas = 0.3 * inch
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margen, height - margen, f"HOJA DE RESPUESTAS - {tema.upper()}")
    
    # Información del estudiante
    c.setFont("Helvetica", 10)
    info_y = height - margen - 0.5 * inch
    c.rect(margen, info_y - 0.6 * inch, ancho_util, 0.6 * inch)
    c.drawString(margen + 0.1 * inch, info_y - 0.2 * inch, "Nombre: ___________________________________________________")
    c.drawString(margen + 0.1 * inch, info_y - 0.4 * inch, "Grupo: ___________   Fecha: ______________")
    
    # Generar clave de respuestas
    clave_respuestas = {}
    for i in range(num_preguntas):
        clave_respuestas[i] = random.randint(0, num_opciones-1)
    
    # Encabezado de las columnas de opciones
    letras_opciones = ['A', 'B', 'C', 'D', 'E', 'F', 'G'][:num_opciones]
    y_pos = info_y - 1.2 * inch
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margen, y_pos, "Pregunta")
    
    for j, letra in enumerate(letras_opciones):
        x_pos = margen + 1.5 * inch + j * espacio_burbujas
        c.drawString(x_pos, y_pos, letra)
    
    # Línea separadora
    c.line(margen, y_pos - 0.1 * inch, margen + ancho_util, y_pos - 0.1 * inch)
    
    # Preguntas y burbujas
    y_pos -= 0.3 * inch
    
    for i in range(num_preguntas):
        # Número de pregunta
        c.setFont("Helvetica", 10)
        c.drawString(margen, y_pos, f"{i+1}.")
        
        # Burbujas para cada opción
        for j in range(num_opciones):
            x_pos = margen + 1.5 * inch + j * espacio_burbujas
            
            # Dibujar burbuja (círculo)
            c.circle(x_pos, y_pos - 0.05 * inch, tamaño_burbuja / 2, stroke=1, fill=0)
            
            # Si es para la clave y esta es la respuesta correcta, marcar con X
            if incluir_clave and j == clave_respuestas[i]:
                c.setFont("Helvetica-Bold", 8)
                c.drawString(x_pos - 0.05 * inch, y_pos - 0.1 * inch, "X")
        
        y_pos -= espacio_pregunta
        
        # Verificar si necesita nueva página
        if y_pos < margen + 0.5 * inch and i < num_preguntas - 1:
            c.showPage()
            y_pos = height - margen - 0.5 * inch
    
    # Instrucciones
    c.setFont("Helvetica", 9)
    instrucciones = [
        "INSTRUCCIONES:",
        "1. Use solo LÁPIZ para marcar sus respuestas",
        "2. Rellene COMPLETAMENTE la burbuja de su elección",
        "3. Borre completamente cualquier marca incorrecta",
        "4. No doble, arrugue o maltrate esta hoja",
        "5. Escriba claramente su nombre y grupo"
    ]
    
    y_inst = margen + 0.8 * inch
    for instruccion in instrucciones:
        c.drawString(margen, y_inst, instruccion)
        y_inst -= 0.2 * inch
    
    # Pie de página
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(margen, margen - 0.3 * inch, 
                f"Generado automáticamente - {tema} - {num_preguntas} preguntas")
    
    c.save()
    return pdf_path, clave_respuestas

def generar_cuestionario_pdf(tema, preguntas, num_opciones=5):
    """
    Genera un PDF con el cuestionario completo (preguntas y opciones)
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf_path = temp_file.name
    temp_file.close()
    
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    margen = 1 * inch
    ancho_util = width - 2 * margen
    y_pos = height - margen
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margen, y_pos, f"CUESTIONARIO - {tema.upper()}")
    y_pos -= 0.4 * inch
    
    c.setFont("Helvetica", 10)
    c.drawString(margen, y_pos, "Instrucciones: Lea cuidadosamente cada pregunta y seleccione la respuesta correcta.")
    y_pos -= 0.6 * inch
    
    # Preguntas
    for i, pregunta_data in enumerate(preguntas):
        # Enunciado
        c.setFont("Helvetica-Bold", 11)
        enunciado = f"{i+1}. {pregunta_data['enunciado']}"
        
        # Manejar texto largo
        palabras = enunciado.split()
        lineas = []
        linea_actual = ""
        
        for palabra in palabras:
            prueba_linea = f"{linea_actual} {palabra}".strip()
            if c.stringWidth(prueba_linea, "Helvetica-Bold", 11) < ancho_util:
                linea_actual = prueba_linea
            else:
                lineas.append(linea_actual)
                linea_actual = palabra
        
        if linea_actual:
            lineas.append(linea_actual)
        
        for linea in lineas:
            if y_pos < margen + 0.8 * inch:
                c.showPage()
                y_pos = height - margen
            c.drawString(margen, y_pos, linea)
            y_pos -= 0.2 * inch
        
        # Opciones
        c.setFont("Helvetica", 10)
        opciones = pregunta_data['opciones'][:num_opciones]
        letras = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        
        for j, opcion in enumerate(opciones):
            if y_pos < margen + 0.6 * inch:
                c.showPage()
                y_pos = height - margen
            
            texto_opcion = f"   {letras[j]}) {opcion}"
            c.drawString(margen + 0.2 * inch, y_pos, texto_opcion)
            y_pos -= 0.18 * inch
        
        y_pos -= 0.2 * inch  # Espacio entre preguntas
    
    c.save()
    return pdf_path

def generar_examen_completo_pdf(tema, num_preguntas=5, num_opciones=5, carpeta_salida="examenes_pdf"):
    """
    Genera un examen completo en PDF (cuestionario + hoja de respuestas)
    """
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)
    
    # Generar preguntas
    preguntas = generar_preguntas_aleatorias(tema, num_preguntas)
    
    # Generar cuestionario PDF
    cuestionario_pdf = generar_cuestionario_pdf(tema, preguntas, num_opciones)
    
    # Generar hoja de respuestas para estudiantes
    hoja_estudiante_pdf, clave = generar_hoja_respuestas_pdf(
        tema, num_preguntas, num_opciones, incluir_clave=False
    )
    
    # Generar hoja de respuestas para profesor (con clave)
    hoja_profesor_pdf, _ = generar_hoja_respuestas_pdf(
        tema, num_preguntas, num_opciones, incluir_clave=True
    )
    
    # Mover archivos a la carpeta de salida
    nombre_base = tema.lower().replace(' ', '_')
    
    archivo_cuestionario = os.path.join(carpeta_salida, f"cuestionario_{nombre_base}.pdf")
    archivo_hoja_estudiante = os.path.join(carpeta_salida, f"hoja_respuestas_{nombre_base}.pdf")
    archivo_hoja_profesor = os.path.join(carpeta_salida, f"clave_correccion_{nombre_base}.pdf")
    
    os.rename(cuestionario_pdf, archivo_cuestionario)
    os.rename(hoja_estudiante_pdf, archivo_hoja_estudiante)
    os.rename(hoja_profesor_pdf, archivo_hoja_profesor)
    
    return archivo_cuestionario, archivo_hoja_estudiante, archivo_hoja_profesor, clave, preguntas

def generar_examenes_masivos_pdf(temas, num_preguntas=5, num_opciones=5, carpeta_salida="examenes_pdf"):
    """
    Genera exámenes completos en PDF para múltiples temas
    """
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)
    
    resultados = {}
    claves_totales = {}
    
    for tema in temas:
        try:
            cuestionario, hoja_estudiante, hoja_profesor, clave, preguntas = generar_examen_completo_pdf(
                tema, num_preguntas, num_opciones, carpeta_salida
            )
            
            resultados[tema] = {
                'cuestionario': cuestionario,
                'hoja_estudiante': hoja_estudiante,
                'hoja_profesor': hoja_profesor,
                'preguntas': preguntas
            }
            claves_totales[tema] = clave
            
            print(f"✅ PDF generado: {tema}")
            
        except Exception as e:
            print(f"❌ Error generando {tema}: {str(e)}")
    
    # Guardar claves en archivo de texto
    with open(os.path.join(carpeta_salida, "claves_respuestas.txt"), "w", encoding='utf-8') as f:
        for tema, clave in claves_totales.items():
            f.write(f"\n{tema}:\n")
            for pregunta, respuesta in clave.items():
                letra_respuesta = chr(65 + respuesta)
                f.write(f"  Pregunta {pregunta+1}: {letra_respuesta}\n")
    
    # Guardar preguntas en JSON
    preguntas_guardadas = {tema: datos['preguntas'] for tema, datos in resultados.items()}
    with open(os.path.join(carpeta_salida, "preguntas_completas.json"), "w", encoding='utf-8') as f:
        json.dump(preguntas_guardadas, f, ensure_ascii=False, indent=2)
    
    return resultados, claves_totales

# ==============================
# 🪟 Interfaz gráfica
# ==============================

root = tk.Tk()
root.title("🧾 Calificador Interactivo - Generador de PDFs")
root.geometry("1000x700")
root.minsize(900, 600)
root.configure(bg="#f7f7f7")

# Variables globales
ruta_imagen = None
imagen_tk = None

# Notebook para pestañas
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

# Pestaña 1: Calificación
frame_calificacion = ttk.Frame(notebook)
notebook.add(frame_calificacion, text="📊 Calificar Exámenes")

# Pestaña 2: Generar Exámenes PDF
frame_generar = ttk.Frame(notebook)
notebook.add(frame_generar, text="🆕 Generar PDFs")

# ==============================
# CONTENIDO PESTAÑA CALIFICACIÓN
# ==============================

frame_main_cal = tk.Frame(frame_calificacion, bg="#f7f7f7")
frame_main_cal.pack(fill="both", expand=True)

frame_left_cal = tk.Frame(frame_main_cal, bg="#ffffff", bd=1, relief="solid")
frame_left_cal.pack(side="left", fill="both", expand=True)

frame_right_cal = tk.Frame(frame_main_cal, bg="#f7f7f7", width=260)
frame_right_cal.pack(side="right", fill="y", padx=(10,0))

# Panel izquierdo: imagen calificada
label_canvas = tk.Label(frame_left_cal, bg="black")
label_canvas.pack(fill="both", expand=True, padx=8, pady=8)

# Panel derecho: controles y clave
tk.Label(frame_right_cal, text="Clave de Respuestas", font=("Arial", 11, "bold"), bg="#f7f7f7").pack(pady=(6,4))

letras = ['A', 'B', 'C', 'D', 'E']
respuestas_vars = []

for i in range(5):
    cont = tk.Frame(frame_right_cal, bg="#f7f7f7")
    cont.pack(fill="x", pady=4, padx=6)
    tk.Label(cont, text=f"P{i+1}:", width=4, anchor="w", bg="#f7f7f7").pack(side="left")
    var = tk.StringVar(value="")
    respuestas_vars.append(var)
    for letra in letras:
        rb = tk.Radiobutton(cont, text=letra, variable=var, value=letra.lower(), bg="#f7f7f7")
        rb.deselect()
        rb.pack(side="left", padx=2)

tk.Frame(frame_right_cal, height=8, bg="#f7f7f7").pack()

def seleccionar_imagen():
    global ruta_imagen
    ruta = filedialog.askopenfilename(
        title="Seleccionar examen a calificar",
        filetypes=[("Imágenes", "*.jpg *.jpeg *.png")]
    )
    if ruta:
        ruta_imagen = ruta
        lbl_imagen_sel.config(text=os.path.basename(ruta))
        limpiar_canvas()

def limpiar_canvas():
    global imagen_tk
    imagen_tk = None
    label_canvas.config(image="", text="")

btn_sel = tk.Button(frame_right_cal, text="📂 Seleccionar Imagen", command=seleccionar_imagen)
btn_sel.pack(fill="x", padx=8, pady=(4,2))

lbl_imagen_sel = tk.Label(frame_right_cal, text="Ninguna imagen seleccionada", bg="#f7f7f7", anchor="w")
lbl_imagen_sel.pack(fill="x", padx=8)

label_resultado = tk.Label(frame_right_cal, text="", font=("Arial", 12, "bold"), bg="#f7f7f7")
label_resultado.pack(pady=(10,4))

def validar_clave():
    for i, var in enumerate(respuestas_vars):
        val = var.get()
        if val not in ['a','b','c','d','e']:
            return False, i+1
    return True, None

def ajustar_imagen_para_label(img_cv, max_w, max_h):
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    h, w = img_rgb.shape[:2]
    scale = min(max_w / w, max_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    img_pil = Image.fromarray(img_rgb).resize((new_w, new_h))
    return ImageTk.PhotoImage(img_pil)

def calificar_examen():
    global imagen_tk
    if not ruta_imagen:
        messagebox.showerror("Error", "Selecciona primero una imagen.")
        return

    ok, falta = validar_clave()
    if not ok:
        messagebox.showerror("Clave incompleta", f"Selecciona una opción para la pregunta {falta}.")
        return

    clave = {i: ord(var.get()) - 97 for i, var in enumerate(respuestas_vars)}

    try:
        puntaje, hoja = procesar_imagen(ruta_imagen, clave)
    except Exception as e:
        messagebox.showerror("Error al procesar", str(e))
        return

    label_canvas.update_idletasks()
    max_w = label_canvas.winfo_width() or 480
    max_h = label_canvas.winfo_height() or 420
    imagen_tk = ajustar_imagen_para_label(hoja, max_w-4, max_h-4)
    label_canvas.config(image=imagen_tk)

    label_resultado.config(text=f"Calificación: {puntaje:.2f}%")

btn_calificar = tk.Button(frame_right_cal, text="🚀 Calificar Examen", bg="#2e8b57", fg="white", command=calificar_examen)
btn_calificar.pack(fill="x", padx=8, pady=(8,2))

def reiniciar():
    global ruta_imagen, imagen_tk
    ruta_imagen = None
    imagen_tk = None
    label_canvas.config(image="", text="")
    lbl_imagen_sel.config(text="Ninguna imagen seleccionada")
    label_resultado.config(text="")
    for var in respuestas_vars:
        var.set("")

btn_reiniciar = tk.Button(frame_right_cal, text="🔁 Reiniciar / Calificar otro", bg="#808080", fg="white", command=reiniciar)
btn_reiniciar.pack(fill="x", padx=8, pady=(4,6))

def guardar_calificada():
    if not ruta_imagen or imagen_tk is None:
        messagebox.showinfo("Nada que guardar", "Primero selecciona y califica una imagen.")
        return
    carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar")
    if not carpeta:
        return
    nombre_salida = os.path.splitext(os.path.basename(ruta_imagen))[0] + "_calificada.png"
    salida = os.path.join(carpeta, nombre_salida)
    clave = {i: ord(var.get()) - 97 for i, var in enumerate(respuestas_vars)}
    try:
        _, hoja = procesar_imagen(ruta_imagen, clave)
        cv2.imwrite(salida, hoja)
        messagebox.showinfo("Guardado", f"Imagen guardada en:\n{salida}")
    except Exception as e:
        messagebox.showerror("Error al guardar", str(e))

btn_guardar = tk.Button(frame_right_cal, text="💾 Guardar imagen calificada", command=guardar_calificada)
btn_guardar.pack(fill="x", padx=8, pady=(4,6))

tk.Label(frame_right_cal, text="5 preguntas · opciones A–E", bg="#f7f7f7", fg="#555").pack(side="bottom", pady=6)

# ==============================
# CONTENIDO PESTAÑA GENERAR PDFs
# ==============================

frame_main_gen = tk.Frame(frame_generar, bg="#f7f7f7")
frame_main_gen.pack(fill="both", expand=True, padx=20, pady=20)

# Configuración de exámenes PDF
tk.Label(frame_main_gen, text="Generador de Exámenes en PDF", 
         font=("Arial", 16, "bold"), bg="#f7f7f7").pack(pady=(0,15))

frame_config = tk.Frame(frame_main_gen, bg="#f7f7f7")
frame_config.pack(fill="x", pady=10)

# Número de preguntas
tk.Label(frame_config, text="Número de preguntas:", bg="#f7f7f7").grid(row=0, column=0, sticky="w", padx=(0,10))
var_num_preguntas = tk.IntVar(value=5)
spin_preguntas = tk.Spinbox(frame_config, from_=1, to=20, textvariable=var_num_preguntas, width=5)
spin_preguntas.grid(row=0, column=1, sticky="w")

# Número de opciones
tk.Label(frame_config, text="Opciones por pregunta:", bg="#f7f7f7").grid(row=0, column=2, sticky="w", padx=(20,10))
var_num_opciones = tk.IntVar(value=5)
spin_opciones = tk.Spinbox(frame_config, from_=2, to=7, textvariable=var_num_opciones, width=5)
spin_opciones.grid(row=0, column=3, sticky="w")

# Temas disponibles
tk.Label(frame_main_gen, text="Temas disponibles:", font=("Arial", 11, "bold"), 
         bg="#f7f7f7").pack(anchor="w", pady=(15,5))

# Frame para temas predefinidos
frame_temas = tk.Frame(frame_main_gen, bg="#f7f7f7")
frame_temas.pack(fill="x", pady=5)

temas_predefinidos = list(BANCO_PREGUNTAS.keys())
var_temas_seleccionados = {}

for i, tema in enumerate(temas_predefinidos):
    var = tk.BooleanVar(value=True)
    var_temas_seleccionados[tema] = var
    cb = tk.Checkbutton(frame_temas, text=tema, variable=var, bg="#f7f7f7")
    cb.grid(row=i//2, column=i%2, sticky="w", padx=10, pady=2)

# Temas personalizados
tk.Label(frame_main_gen, text="Temas personalizados (uno por línea):", 
         font=("Arial", 11, "bold"), bg="#f7f7f7").pack(anchor="w", pady=(15,5))

text_temas_personalizados = tk.Text(frame_main_gen, height=3, width=50)
text_temas_personalizados.pack(fill="x", pady=(0,10))

def generar_pdfs_desde_interfaz():
    # Obtener temas seleccionados
    temas_seleccionados = []
    
    # Temas predefinidos seleccionados
    for tema, var in var_temas_seleccionados.items():
        if var.get():
            temas_seleccionados.append(tema)
    
    # Temas personalizados
    temas_personalizados_texto = text_temas_personalizados.get("1.0", "end-1c").strip()
    if temas_personalizados_texto:
        temas_personalizados = [tema.strip() for tema in temas_personalizados_texto.split('\n') if tema.strip()]
        temas_seleccionados.extend(temas_personalizados)
    
    if not temas_seleccionados:
        messagebox.showerror("Error", "Selecciona al menos un tema.")
        return
    
    num_preguntas = var_num_preguntas.get()
    num_opciones = var_num_opciones.get()
    
    carpeta = filedialog.askdirectory(title="Seleccionar carpeta para guardar los PDFs")
    if not carpeta:
        return
    
    try:
        resultados, claves = generar_examenes_masivos_pdf(
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

btn_generar = tk.Button(frame_main_gen, text="📄 Generar Exámenes PDF", 
                       bg="#dc3545", fg="white", font=("Arial", 12, "bold"),
                       command=generar_pdfs_desde_interfaz)
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

# Inicio
root.mainloop()