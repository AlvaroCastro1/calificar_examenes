# ================================================
# 🧾 CALIFICADOR AUTOMÁTICO DE HOJAS DE RESPUESTA
# Procesa todas las imágenes de una carpeta, detecta
# las burbujas marcadas y calcula el puntaje obtenido.
# ================================================

from imutils.perspective import four_point_transform
from imutils import contours
import numpy as np
import imutils
import cv2
import os

# Clave de respuestas correctas (ejemplo: 5 preguntas, opción correcta por número)
CLAVE_RESPUESTAS = {0: 1, 1: 4, 2: 0, 3: 3, 4: 1}

# ------------------------------------------------
# 🧩 Función principal: procesa una imagen individual
# ------------------------------------------------
def procesar_imagen(ruta_imagen):
    # Cargar imagen
    imagen = cv2.imread(ruta_imagen)
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    desenfocada = cv2.GaussianBlur(gris, (5, 5), 0)
    bordes = cv2.Canny(desenfocada, 75, 200)

    # Buscar contornos (bordes externos)
    contornos, _ = cv2.findContours(bordes.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)
    contorno_documento = None

    # Buscar el contorno con 4 puntos (probablemente la hoja)
    for c in contornos:
        perimetro = cv2.arcLength(c, True)
        aprox = cv2.approxPolyDP(c, 0.02 * perimetro, True)
        if len(aprox) == 4:
            contorno_documento = aprox
            break

    # Aplicar transformación de perspectiva para "enderezar" la hoja
    hoja_color = four_point_transform(imagen, contorno_documento.reshape(4, 2))
    hoja_gris = four_point_transform(gris, contorno_documento.reshape(4, 2))

    # Umbral binario (blanco y negro) para resaltar burbujas
    umbral = cv2.threshold(hoja_gris, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Buscar contornos en la hoja umbralizada
    contornos_preguntas, _ = cv2.findContours(umbral.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    burbujas = []

    # Filtrar contornos que tengan forma y tamaño de burbuja
    for c in contornos_preguntas:
        (x, y, w, h) = cv2.boundingRect(c)
        proporcion = w / float(h)
        if w >= 20 and h >= 20 and 0.9 <= proporcion <= 1.1:
            burbujas.append(c)

    # Ordenar las burbujas de arriba a abajo
    burbujas = contours.sort_contours(burbujas, method="top-to-bottom")[0]
    correctas = 0

    # Procesar cada grupo de 5 burbujas (una pregunta)
    for (pregunta, i) in enumerate(np.arange(0, len(burbujas), 5)):
        cnts = contours.sort_contours(burbujas[i:i + 5])[0]
        seleccionada = None

        # Determinar cuál burbuja está marcada (más pixeles blancos)
        for (j, c) in enumerate(cnts):
            mascara = np.zeros(umbral.shape, dtype="uint8")
            cv2.drawContours(mascara, [c], -1, 255, -1)
            mascara = cv2.bitwise_and(umbral, umbral, mask=mascara)
            total = cv2.countNonZero(mascara)
            if seleccionada is None or total > seleccionada[0]:
                seleccionada = (total, j)

        # Comparar con la clave de respuestas
        color = (0, 0, 255)  # rojo por defecto (incorrecta)
        respuesta_correcta = CLAVE_RESPUESTAS.get(pregunta, -1)

        if respuesta_correcta == seleccionada[1]:
            color = (0, 255, 0)  # verde si es correcta
            correctas += 1

        # Dibujar el contorno de la respuesta correcta
        cv2.drawContours(hoja_color, [cnts[respuesta_correcta]], -1, color, 2)

    # Calcular el puntaje en porcentaje
    puntaje = (correctas / len(CLAVE_RESPUESTAS)) * 100
    return puntaje, hoja_color


# ------------------------------------------------
# 📁 Procesar todas las imágenes de una carpeta
# ------------------------------------------------
def procesar_todas_imagenes(carpeta_entrada, carpeta_salida, archivo_resultados):
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    archivos = [f for f in os.listdir(carpeta_entrada)
                if f.lower().endswith((".jpg", ".png", ".jpeg"))]

    with open(archivo_resultados, "w") as f:
        for nombre in archivos:
            ruta = os.path.join(carpeta_entrada, nombre)
            print(f"🧾 Procesando: {nombre}")
            puntaje, hoja_calificada = procesar_imagen(ruta)

            # Mostrar resultado en pantalla
            cv2.imshow(f"{nombre} - Puntaje: {puntaje:.2f}%", hoja_calificada)
            cv2.waitKey(0)  # Espera hasta que presiones una tecla
            cv2.destroyAllWindows()

            # Guardar imagen procesada
            salida = os.path.join(carpeta_salida, f"calificada_{nombre}")
            cv2.imwrite(salida, hoja_calificada)

            # Guardar resultado en archivo de texto
            f.write(f"{nombre}: {puntaje:.2f}%\n")

    print(f"✅ Resultados guardados en: {archivo_resultados}")


# ------------------------------------------------
# 🚀 Ejecutar todo
# ------------------------------------------------
carpeta_entrada = "imagenes_examenes"
carpeta_salida = "resultados_examenes"
archivo_resultados = "resultados.txt"

procesar_todas_imagenes(carpeta_entrada, carpeta_salida, archivo_resultados)
