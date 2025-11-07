# [file name]: logica.py
import os
import random
import json
import tempfile
import cv2
import numpy as np
from imutils.perspective import four_point_transform
from imutils import contours
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

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

class GestorCuestionarios:
    """Clase para gestionar el guardado y carga de cuestionarios personalizados"""
    
    @staticmethod
    def guardar_cuestionario(preguntas, nombre_archivo, titulo="Cuestionario Personalizado", tema="Personalizado"):
        """
        Guarda un cuestionario personalizado en formato JSON
        
        Args:
            preguntas (list): Lista de preguntas
            nombre_archivo (str): Nombre del archivo (sin extensión)
            titulo (str): Título del cuestionario
            tema (str): Tema del cuestionario
        """
        datos = {
            "titulo": titulo,
            "tema": tema,
            "fecha_creacion": str(np.datetime64('now')),
            "total_preguntas": len(preguntas),
            "preguntas": preguntas
        }
        
        # Asegurar que el archivo tenga extensión .json
        if not nombre_archivo.endswith('.json'):
            nombre_archivo += '.json'
        
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        return nombre_archivo
    
    @staticmethod
    def cargar_cuestionario(nombre_archivo):
        """
        Carga un cuestionario personalizado desde archivo JSON
        
        Args:
            nombre_archivo (str): Ruta del archivo JSON
            
        Returns:
            dict: Datos del cuestionario
        """
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        return datos
    
    @staticmethod
    def listar_cuestionarios_guardados(carpeta="."):
        """
        Lista todos los cuestionarios guardados en una carpeta
        
        Returns:
            list: Lista de archivos JSON de cuestionarios
        """
        archivos = [f for f in os.listdir(carpeta) if f.endswith('.json')]
        cuestionarios = []
        
        for archivo in archivos:
            try:
                with open(os.path.join(carpeta, archivo), 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    if all(key in datos for key in ['titulo', 'tema', 'preguntas']):
                        cuestionarios.append({
                            'archivo': archivo,
                            'titulo': datos['titulo'],
                            'tema': datos['tema'],
                            'total_preguntas': datos['total_preguntas'],
                            'fecha_creacion': datos.get('fecha_creacion', 'Desconocida')
                        })
            except:
                continue
        
        return cuestionarios

class GeneradorPDF:
    """Clase para generar todos los tipos de PDFs necesarios"""
    
    @staticmethod
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

    @staticmethod
    def generar_hoja_respuestas_pdf(tema, num_preguntas=5, num_opciones=5, incluir_clave=False):
        """
        Genera una hoja de respuestas en formato PDF optimizada para escaneo
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

    @staticmethod
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

    @staticmethod
    def generar_examen_completo(tema, preguntas=None, num_preguntas=5, num_opciones=5, carpeta_salida="examenes_pdf"):
        """
        Genera un examen completo en PDF (cuestionario + hoja de respuestas)
        Si no se proporcionan preguntas, genera preguntas aleatorias
        """
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
        
        # Generar preguntas si no se proporcionan
        if preguntas is None:
            preguntas = GeneradorPDF.generar_preguntas_aleatorias(tema, num_preguntas)
        
        # Generar cuestionario PDF
        cuestionario_pdf = GeneradorPDF.generar_cuestionario_pdf(tema, preguntas, num_opciones)
        
        # Generar hoja de respuestas para estudiantes
        hoja_estudiante_pdf, clave = GeneradorPDF.generar_hoja_respuestas_pdf(
            tema, len(preguntas), num_opciones, incluir_clave=False
        )
        
        # Generar hoja de respuestas para profesor (con clave)
        hoja_profesor_pdf, _ = GeneradorPDF.generar_hoja_respuestas_pdf(
            tema, len(preguntas), num_opciones, incluir_clave=True
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

    @staticmethod
    def generar_examenes_masivos(temas, num_preguntas=5, num_opciones=5, carpeta_salida="examenes_pdf"):
        """
        Genera exámenes completos en PDF para múltiples temas
        """
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
        
        resultados = {}
        claves_totales = {}
        
        for tema in temas:
            try:
                cuestionario, hoja_estudiante, hoja_profesor, clave, preguntas = GeneradorPDF.generar_examen_completo(
                    tema, None, num_preguntas, num_opciones, carpeta_salida
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

    @staticmethod
    def generar_cuestionario_personalizado(preguntas_personalizadas, tema="Personalizado", num_opciones=5, carpeta_salida="examenes_pdf"):
        """
        Genera un PDF con preguntas personalizadas ingresadas por el usuario
        """
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
        
        # Generar clave de respuestas aleatoria
        clave_respuestas = {}
        for i in range(len(preguntas_personalizadas)):
            clave_respuestas[i] = random.randint(0, num_opciones-1)
        
        # Generar cuestionario PDF
        cuestionario_pdf = GeneradorPDF.generar_cuestionario_pdf(tema, preguntas_personalizadas, num_opciones)
        
        # Generar hojas de respuestas
        hoja_estudiante_pdf, _ = GeneradorPDF.generar_hoja_respuestas_pdf(
            tema, len(preguntas_personalizadas), num_opciones, incluir_clave=False
        )
        
        hoja_profesor_pdf, _ = GeneradorPDF.generar_hoja_respuestas_pdf(
            tema, len(preguntas_personalizadas), num_opciones, incluir_clave=True
        )
        
        # Mover archivos a carpeta de salida
        nombre_base = tema.lower().replace(' ', '_')
        
        archivo_cuestionario = os.path.join(carpeta_salida, f"cuestionario_{nombre_base}.pdf")
        archivo_hoja_estudiante = os.path.join(carpeta_salida, f"hoja_respuestas_{nombre_base}.pdf")
        archivo_hoja_profesor = os.path.join(carpeta_salida, f"clave_correccion_{nombre_base}.pdf")
        
        os.rename(cuestionario_pdf, archivo_cuestionario)
        os.rename(hoja_estudiante_pdf, archivo_hoja_estudiante)
        os.rename(hoja_profesor_pdf, archivo_hoja_profesor)
        
        # Guardar clave en archivo de texto
        with open(os.path.join(carpeta_salida, f"clave_{nombre_base}.txt"), "w", encoding='utf-8') as f:
            f.write(f"CLAVE DE RESPUESTAS - {tema}\n")
            f.write("=" * 40 + "\n")
            for pregunta, respuesta in clave_respuestas.items():
                letra_respuesta = chr(65 + respuesta)
                f.write(f"Pregunta {pregunta+1}: {letra_respuesta}\n")
        
        # Guardar preguntas en JSON
        with open(os.path.join(carpeta_salida, f"preguntas_{nombre_base}.json"), "w", encoding='utf-8') as f:
            json.dump(preguntas_personalizadas, f, ensure_ascii=False, indent=2)
        
        return archivo_cuestionario, archivo_hoja_estudiante, archivo_hoja_profesor, clave_respuestas

    @staticmethod
    def generar_desde_json(archivo_json, carpeta_salida="examenes_pdf"):
        """
        Genera PDFs a partir de un cuestionario guardado en JSON
        """
        datos = GestorCuestionarios.cargar_cuestionario(archivo_json)
        
        tema = datos.get('tema', 'Personalizado')
        titulo = datos.get('titulo', tema)
        preguntas = datos.get('preguntas', [])
        
        if not preguntas:
            raise ValueError("El archivo JSON no contiene preguntas válidas")
        
        # Determinar número de opciones
        num_opciones = 5
        if preguntas:
            num_opciones = max(len(pregunta.get('opciones', [])) for pregunta in preguntas)
        
        return GeneradorPDF.generar_cuestionario_personalizado(
            preguntas, titulo, num_opciones, carpeta_salida
        )
