# [file name]: test_grader.py
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

# Importar la lógica del programa
from logica import procesar_imagen

# Clave de respuestas correctas (ejemplo: 5 preguntas, opción correcta por número)
CLAVE_RESPUESTAS = {0: 1, 1: 4, 2: 0, 3: 3, 4: 1}

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
            puntaje, hoja_calificada = procesar_imagen(ruta, CLAVE_RESPUESTAS)

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
if __name__ == "__main__":
    carpeta_entrada = "imagenes_examenes"
    carpeta_salida = "resultados_examenes"
    archivo_resultados = "resultados.txt"

    procesar_todas_imagenes(carpeta_entrada, carpeta_salida, archivo_resultados)
