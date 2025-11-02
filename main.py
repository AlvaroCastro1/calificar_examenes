import os
import tkinter as tk
from tkinter import filedialog, messagebox
from imutils.perspective import four_point_transform
from imutils import contours
import numpy as np
import cv2
from PIL import Image, ImageTk

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
# 🪟 Interfaz gráfica
# ==============================

root = tk.Tk()
root.title("🧾 Calificador Interactivo - Compacto")
# Tamaño moderado para caber en pantallas pequeñas; el usuario puede redimensionar
root.geometry("820x520")
root.minsize(760, 460)
root.configure(bg="#f7f7f7")

# Variables globales
ruta_imagen = None
imagen_tk = None

# Layout: izquierda = imagen, derecha = controles
frame_main = tk.Frame(root, bg="#f7f7f7")
frame_main.pack(fill="both", expand=True, padx=10, pady=10)

frame_left = tk.Frame(frame_main, bg="#ffffff", bd=1, relief="solid")
frame_left.pack(side="left", fill="both", expand=True)

frame_right = tk.Frame(frame_main, bg="#f7f7f7", width=260)
frame_right.pack(side="right", fill="y", padx=(10,0))

# ----- Panel izquierdo: imagen calificada -----
label_canvas = tk.Label(frame_left, bg="black")
label_canvas.pack(fill="both", expand=True, padx=8, pady=8)

# ----- Panel derecho: controles y clave -----
tk.Label(frame_right, text="Clave de Respuestas", font=("Arial", 11, "bold"), bg="#f7f7f7").pack(pady=(6,4))

letras = ['A', 'B', 'C', 'D', 'E']
respuestas_vars = []

# Cada pregunta con un grupo de radiobuttons (inicialmente vacío)
for i in range(5):
    cont = tk.Frame(frame_right, bg="#f7f7f7")
    cont.pack(fill="x", pady=4, padx=6)
    tk.Label(cont, text=f"P{i+1}:", width=4, anchor="w", bg="#f7f7f7").pack(side="left")
    var = tk.StringVar(value="")  # 🔹 vacío por defecto
    respuestas_vars.append(var)
    # Radiobuttons; al usar StringVar se asegura 1 por pregunta
    for letra in letras:
        rb = tk.Radiobutton(cont, text=letra, variable=var, value=letra.lower(), bg="#f7f7f7")
        rb.deselect()  # 🔹 asegúrate de que ninguno arranque seleccionado
        rb.pack(side="left", padx=2)

# Espacio
tk.Frame(frame_right, height=8, bg="#f7f7f7").pack()

# Botones y selección de imagen en la derecha
def seleccionar_imagen():
    global ruta_imagen
    ruta = filedialog.askopenfilename(
        title="Seleccionar examen a calificar",
        filetypes=[("Imágenes", "*.jpg *.jpeg *.png")]
    )
    if ruta:
        ruta_imagen = ruta
        lbl_imagen_sel.config(text=os.path.basename(ruta))
        # limpiar canvas previo
        limpiar_canvas()

def limpiar_canvas():
    global imagen_tk
    imagen_tk = None
    label_canvas.config(image="", text="")

btn_sel = tk.Button(frame_right, text="📂 Seleccionar Imagen", command=seleccionar_imagen)
btn_sel.pack(fill="x", padx=8, pady=(4,2))

lbl_imagen_sel = tk.Label(frame_right, text="Ninguna imagen seleccionada", bg="#f7f7f7", anchor="w")
lbl_imagen_sel.pack(fill="x", padx=8)

# Resultado
label_resultado = tk.Label(frame_right, text="", font=("Arial", 12, "bold"), bg="#f7f7f7")
label_resultado.pack(pady=(10,4))

# Validación: cada pregunta debe tener exactamente una seleccionada
def validar_clave():
    for i, var in enumerate(respuestas_vars):
        val = var.get()
        if val not in ['a','b','c','d','e']:
            return False, i+1
    return True, None

def ajustar_imagen_para_label(img_cv, max_w, max_h):
    # Convierte BGR->RGB y ajusta manteniendo aspect ratio
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

    # construir clave en índices 0..4
    clave = {i: ord(var.get()) - 97 for i, var in enumerate(respuestas_vars)}

    try:
        puntaje, hoja = procesar_imagen(ruta_imagen, clave)
    except Exception as e:
        messagebox.showerror("Error al procesar", str(e))
        return

    # Mostrar imagen calificada en el panel izquierdo (ajustada)
    # dejar un pequeño margen: calcular tamaño disponible del label
    label_canvas.update_idletasks()
    max_w = label_canvas.winfo_width() or 480
    max_h = label_canvas.winfo_height() or 420
    imagen_tk = ajustar_imagen_para_label(hoja, max_w-4, max_h-4)
    label_canvas.config(image=imagen_tk)

    label_resultado.config(text=f"Calificación: {puntaje:.2f}%")

# Botón Calificar
btn_calificar = tk.Button(frame_right, text="🚀 Calificar Examen", bg="#2e8b57", fg="white", command=calificar_examen)
btn_calificar.pack(fill="x", padx=8, pady=(8,2))

# 🔁 Botón para reiniciar todo
def reiniciar():
    global ruta_imagen, imagen_tk
    ruta_imagen = None
    imagen_tk = None
    label_canvas.config(image="", text="")
    lbl_imagen_sel.config(text="Ninguna imagen seleccionada")
    label_resultado.config(text="")
    for var in respuestas_vars:
        var.set("")  # limpia selección de radiobuttons

btn_reiniciar = tk.Button(frame_right, text="🔁 Reiniciar / Calificar otro", bg="#808080", fg="white", command=reiniciar)
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
    # Re-procesar para obtener la imagen en BGR y guardar (más fiable)
    clave = {i: ord(var.get()) - 97 for i, var in enumerate(respuestas_vars)}
    try:
        _, hoja = procesar_imagen(ruta_imagen, clave)
        cv2.imwrite(salida, hoja)
        messagebox.showinfo("Guardado", f"Imagen guardada en:\n{salida}")
    except Exception as e:
        messagebox.showerror("Error al guardar", str(e))

btn_guardar = tk.Button(frame_right, text="💾 Guardar imagen calificada", command=guardar_calificada)
btn_guardar.pack(fill="x", padx=8, pady=(4,6))

# Footer pequeño
tk.Label(frame_right, text="5 preguntas · opciones A–E", bg="#f7f7f7", fg="#555").pack(side="bottom", pady=6)

# Inicio
root.mainloop()
