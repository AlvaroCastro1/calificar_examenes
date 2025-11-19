import os
import cv2
import numpy as np
import json
from imutils.perspective import four_point_transform
from imutils import contours

class CalificadorAutomatico:
    """Clase para calificar exámenes automáticamente mediante procesamiento de imágenes"""
    
    def __init__(self, modo_depuracion=False):
        self.clave_respuestas = {}
        self.num_preguntas = 0
        self.num_opciones = 5  # Por defecto, 5 opciones (A-E)
        self.modo_depuracion = modo_depuracion
        self.umbral_relleno_minimo = 500  # Mínimo de píxeles para considerar una burbuja marcada
        self.umbral_ratio_relleno = 0.3   # Mínimo ratio de relleno (área marcada / área total)
    
    def cargar_clave_desde_json(self, ruta_json):
        """
        Carga la clave de respuestas desde un archivo JSON
        """
        try:
            with open(ruta_json, 'r', encoding='utf-8') as f:
                datos_clave = json.load(f)
            
            if isinstance(datos_clave, dict) and 'respuestas' in datos_clave:
                self.clave_respuestas = datos_clave['respuestas']
            elif isinstance(datos_clave, list):
                self.clave_respuestas = {i: resp for i, resp in enumerate(datos_clave)}
            else:
                self.clave_respuestas = {}
                for key, value in datos_clave.items():
                    if 'pregunta' in key.lower() or key.isdigit():
                        if isinstance(value, dict) and 'correcta' in value:
                            idx = int(key.replace('pregunta', '')) if 'pregunta' in key.lower() else int(key)
                            self.clave_respuestas[idx] = value['correcta']
                        elif isinstance(value, (int, str)):
                            idx = int(key.replace('pregunta', '')) if 'pregunta' in key.lower() else int(key)
                            if isinstance(value, str) and value.isalpha():
                                self.clave_respuestas[idx] = ord(value.upper()) - 65
                            else:
                                self.clave_respuestas[idx] = int(value)
            
            self.num_preguntas = len(self.clave_respuestas)
            print(f"✅ Clave cargada: {self.num_preguntas} preguntas")
            return True
            
        except Exception as e:
            print(f"❌ Error al cargar clave JSON: {str(e)}")
            return False
    
    def mostrar_imagen(self, titulo, imagen, escala=0.7):
        """Muestra una imagen en una ventana OpenCV (solo en modo depuración)"""
        if self.modo_depuracion:
            h, w = imagen.shape[:2]
            nueva_w = int(w * escala)
            nueva_h = int(h * escala)
            imagen_redimensionada = cv2.resize(imagen, (nueva_w, nueva_h))
            cv2.imshow(titulo, imagen_redimensionada)
            cv2.waitKey(1)
    
    def detectar_circulos_hough(self, imagen_gris):
        """
        Detecta círculos usando la transformada de Hough
        """
        # Aplicar desenfoque para reducir ruido
        suavizada = cv2.medianBlur(imagen_gris, 5)
        
        # Detectar círculos
        circulos = cv2.HoughCircles(
            suavizada,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=10,
            maxRadius=30
        )
        
        return circulos
    
    def mejorar_deteccion_burbujas(self, umbral):
        """
        Mejora la detección de burbujas usando operaciones morfológicas
        """
        # Operaciones morfológicas para mejorar la detección
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        umbral_mejorado = cv2.morphologyEx(umbral, cv2.MORPH_CLOSE, kernel)
        umbral_mejorado = cv2.morphologyEx(umbral_mejorado, cv2.MORPH_OPEN, kernel)
        
        return umbral_mejorado
    
    def analizar_relleno_burbuja(self, contorno, umbral):
        """
        Analiza el nivel de relleno de una burbuja
        """
        # Crear máscara para el contorno
        mascara = np.zeros(umbral.shape, dtype="uint8")
        cv2.drawContours(mascara, [contorno], -1, 255, -1)
        
        # Aplicar máscara
        mascara_aplicada = cv2.bitwise_and(umbral, umbral, mask=mascara)
        
        # Calcular métricas
        total_pixels = cv2.countNonZero(mascara_aplicada)
        area_contorno = cv2.contourArea(contorno)
        
        # Calcular ratio de relleno
        ratio_relleno = total_pixels / area_contorno if area_contorno > 0 else 0
        
        # Calcular densidad de píxeles (píxeles por área)
        densidad = total_pixels / area_contorno if area_contorno > 0 else 0
        
        # Obtener bounding rect para análisis adicional
        (x, y, w, h) = cv2.boundingRect(contorno)
        
        return {
            'total_pixels': total_pixels,
            'area_contorno': area_contorno,
            'ratio_relleno': ratio_relleno,
            'densidad': densidad,
            'mascara': mascara_aplicada,
            'bbox': (x, y, w, h)
        }
    
    def filtrar_burbujas_validas(self, contornos, umbral, ancho_hoja, alto_hoja):
        """
        Filtra contornos para identificar solo burbujas válidas
        """
        burbujas_validas = []
        metricas_burbujas = []
        
        area_minima = (ancho_hoja * alto_hoja) * 0.0001  # 0.01% del área total
        area_maxima = (ancho_hoja * alto_hoja) * 0.01   # 1% del área total
        
        for c in contornos:
            (x, y, w, h) = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            proporcion = w / float(h) if h != 0 else 0
            
            # Filtrar por tamaño y forma
            if (area_minima <= area <= area_maxima and 
                0.6 <= proporcion <= 1.4 and
                w >= 12 and h >= 12):
                
                # Analizar relleno
                analisis = self.analizar_relleno_burbuja(c, umbral)
                
                # Verificar si tiene características de burbuja
                if self.es_burbuja_valida(analisis, c):
                    burbujas_validas.append(c)
                    metricas_burbujas.append(analisis)
        
        return burbujas_validas, metricas_burbujas
    
    def es_burbuja_valida(self, analisis, contorno):
        """
        Determina si un contorno es una burbuja válida basándose en sus características
        """
        # Verificar circularidad
        perimetro = cv2.arcLength(contorno, True)
        circularidad = (4 * np.pi * analisis['area_contorno']) / (perimetro * perimetro) if perimetro > 0 else 0
        
        # Una burbuja válida debe ser relativamente circular
        es_circular = circularidad > 0.6
        
        # Tamaño razonable
        tamaño_ok = analisis['area_contorno'] > 100
        
        return es_circular and tamaño_ok
    
    def detectar_burbujas_marcadas(self, burbujas, umbral):
        """
        Detecta qué burbujas están marcadas basándose en múltiples criterios
        """
        burbujas_marcadas = []
        confianzas = []
        
        for burbuja in burbujas:
            analisis = self.analizar_relleno_burbuja(burbuja, umbral)
            
            # Múltiples criterios para determinar si está marcada
            criterio_pixels = analisis['total_pixels'] > self.umbral_relleno_minimo
            criterio_ratio = analisis['ratio_relleno'] > self.umbral_ratio_relleno
            criterio_densidad = analisis['densidad'] > 0.4
            
            # Combinar criterios (al menos 2 de 3)
            criterios_cumplidos = sum([criterio_pixels, criterio_ratio, criterio_densidad])
            esta_marcada = criterios_cumplidos >= 2
            
            # Calcular confianza
            confianza = min(100, (analisis['ratio_relleno'] * 100))
            
            burbujas_marcadas.append(esta_marcada)
            confianzas.append(confianza)
        
        return burbujas_marcadas, confianzas
    
    def organizar_burbujas_por_preguntas(self, burbujas, num_preguntas, num_opciones):
        """
        Organiza las burbujas en preguntas y opciones
        """
        if len(burbujas) != num_preguntas * num_opciones:
            print(f"⚠️ Advertencia: Se esperaban {num_preguntas * num_opciones} burbujas, pero se encontraron {len(burbujas)}")
        
        # Ordenar burbujas por posición Y (filas)
        burbujas_ordenadas = contours.sort_contours(burbujas, method="top-to-bottom")[0]
        
        # Agrupar por preguntas
        preguntas = []
        for i in range(num_preguntas):
            inicio = i * num_opciones
            fin = inicio + num_opciones
            
            if fin <= len(burbujas_ordenadas):
                burbujas_pregunta = burbujas_ordenadas[inicio:fin]
                # Ordenar cada grupo de izquierda a derecha
                burbujas_pregunta_ordenadas = contours.sort_contours(burbujas_pregunta)[0]
                preguntas.append(burbujas_pregunta_ordenadas)
            else:
                # Si no hay suficientes burbujas, completar con None
                preguntas.append([None] * num_opciones)
        
        return preguntas
    
    def procesar_hoja_respuestas(self, ruta_imagen):
        """
        Procesa una imagen de hoja de respuestas y la califica automáticamente
        """
        try:
            # Cargar imagen
            imagen = cv2.imread(ruta_imagen)
            if imagen is None:
                return 0, None, [], "No se pudo cargar la imagen"
            
            # Mostrar imagen original
            self.mostrar_imagen("1. Imagen Original", imagen)
            
            # Preprocesamiento mejorado
            gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
            self.mostrar_imagen("2. Escala de Grises", gris)
            
            # Mejorar contraste
            gris_ecualizado = cv2.equalizeHist(gris)
            self.mostrar_imagen("3. Ecualizado", gris_ecualizado)
            
            desenfocada = cv2.GaussianBlur(gris_ecualizado, (5, 5), 0)
            self.mostrar_imagen("4. Desenfoque Gaussiano", desenfocada)
            
            bordes = cv2.Canny(desenfocada, 50, 150)
            self.mostrar_imagen("5. Detección de Bordes (Canny)", bordes)

            # Detectar contornos
            contornos, _ = cv2.findContours(bordes.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Buscar contorno del documento
            contorno_documento = None
            for c in contornos:
                perimetro = cv2.arcLength(c, True)
                aprox = cv2.approxPolyDP(c, 0.02 * perimetro, True)
                if len(aprox) == 4:
                    area = cv2.contourArea(c)
                    # Verificar que sea lo suficientemente grande
                    if area > (imagen.shape[0] * imagen.shape[1] * 0.5):
                        contorno_documento = aprox
                        break

            if contorno_documento is None:
                return 0, None, [], "No se detectó correctamente la hoja del examen"

            # Transformar perspectiva
            hoja_color = four_point_transform(imagen, contorno_documento.reshape(4, 2))
            hoja_gris = four_point_transform(gris, contorno_documento.reshape(4, 2))
            
            self.mostrar_imagen("6. Vista Frontal (Color)", hoja_color)
            self.mostrar_imagen("7. Vista Frontal (Grises)", hoja_gris)
            
            # Umbralización adaptativa para mejor detección
            umbral_adaptativo = cv2.adaptiveThreshold(
                hoja_gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            self.mostrar_imagen("8. Umbralización Adaptativa", umbral_adaptativo)
            
            # Mejorar detección de burbujas
            umbral_mejorado = self.mejorar_deteccion_burbujas(umbral_adaptativo)
            self.mostrar_imagen("9. Umbral Mejorado", umbral_mejorado)
            
            # Detectar contornos en la imagen mejorada
            contornos_burbujas, _ = cv2.findContours(
                umbral_mejorado.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Filtrar burbujas válidas
            h, w = umbral_mejorado.shape
            burbujas_validas, metricas = self.filtrar_burbujas_validas(
                contornos_burbujas, umbral_mejorado, w, h
            )
            
            # Mostrar burbujas detectadas
            imagen_burbujas = hoja_color.copy()
            for i, burbuja in enumerate(burbujas_validas):
                (x, y, w, h) = cv2.boundingRect(burbuja)
                cv2.rectangle(imagen_burbujas, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(imagen_burbujas, str(i+1), (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            self.mostrar_imagen("10. Burbujas Detectadas", imagen_burbujas)
            
            # Organizar burbujas por preguntas
            preguntas_burbujas = self.organizar_burbujas_por_preguntas(
                burbujas_validas, self.num_preguntas, self.num_opciones
            )
            
            # Procesar cada pregunta
            correctas = 0
            resultados_detallados = []
            imagen_resultado = hoja_color.copy()
            
            for pregunta_idx, burbujas_pregunta in enumerate(preguntas_burbujas):
                if None in burbujas_pregunta:
                    # Pregunta incompleta
                    resultados_detallados.append({
                        'pregunta': pregunta_idx + 1,
                        'seleccionada': None,
                        'correcta': self.clave_respuestas.get(pregunta_idx, -1),
                        'es_correcta': False,
                        'confianza': 0,
                        'letra_seleccionada': 'N/A',
                        'letra_correcta': chr(65 + self.clave_respuestas.get(pregunta_idx, -1)) 
                                       if self.clave_respuestas.get(pregunta_idx, -1) >= 0 else 'N/A',
                        'error': 'Burbujas incompletas'
                    })
                    continue
                
                # Detectar burbuja marcada en esta pregunta
                burbujas_marcadas, confianzas = self.detectar_burbujas_marcadas(
                    burbujas_pregunta, umbral_mejorado
                )
                
                # Encontrar la burbuja con mayor confianza de estar marcada
                seleccionada = None
                max_confianza = 0
                
                for opcion_idx, (marcada, confianza) in enumerate(zip(burbujas_marcadas, confianzas)):
                    if marcada and confianza > max_confianza:
                        max_confianza = confianza
                        seleccionada = opcion_idx
                
                # Obtener respuesta correcta
                respuesta_correcta = self.clave_respuestas.get(pregunta_idx, -1)
                if isinstance(respuesta_correcta, str) and respuesta_correcta.isalpha():
                    respuesta_correcta = ord(respuesta_correcta.upper()) - 65
                
                # Determinar si es correcta
                es_correcta = (respuesta_correcta == seleccionada) if seleccionada is not None else False
                
                if es_correcta:
                    correctas += 1
                    color = (0, 255, 0)  # Verde
                else:
                    color = (0, 0, 255)  # Rojo
                
                # Guardar resultado detallado
                resultados_detallados.append({
                    'pregunta': pregunta_idx + 1,
                    'seleccionada': seleccionada,
                    'correcta': respuesta_correcta,
                    'es_correcta': es_correcta,
                    'confianza': max_confianza,
                    'letra_seleccionada': chr(65 + seleccionada) if seleccionada is not None else 'N/A',
                    'letra_correcta': chr(65 + respuesta_correcta) if respuesta_correcta >= 0 else 'N/A'
                })
                
                # Dibujar en imagen de resultado
                if seleccionada is not None:
                    cv2.drawContours(imagen_resultado, [burbujas_pregunta[seleccionada]], -1, color, 3)
                    
                    # Marcar respuesta correcta si es incorrecta
                    if not es_correcta and 0 <= respuesta_correcta < len(burbujas_pregunta):
                        cv2.drawContours(imagen_resultado, [burbujas_pregunta[respuesta_correcta]], -1, (255, 255, 0), 2)
            
            # Mostrar imagen final
            self.mostrar_imagen("11. Resultado Final", imagen_resultado)
            
            # Calcular puntaje
            puntaje = (correctas / self.num_preguntas) * 100 if self.num_preguntas > 0 else 0
            
            if self.modo_depuracion:
                print("Presiona cualquier tecla en una ventana de OpenCV para continuar...")
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            return puntaje, imagen_resultado, resultados_detallados, None
            
        except Exception as e:
            if self.modo_depuracion:
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            return 0, None, [], f"Error en el procesamiento: {str(e)}"
    
    # Los métodos restantes (generar_reporte_calificacion, guardar_resultados) se mantienen igual
    def generar_reporte_calificacion(self, resultados_detallados, puntaje, nombre_archivo):
        """Genera un reporte de calificación en formato de texto"""
        reporte = f"REPORTE DE CALIFICACIÓN AUTOMÁTICA\n"
        reporte += f"================================\n"
        reporte += f"Archivo: {nombre_archivo}\n"
        reporte += f"Total preguntas: {len(resultados_detallados)}\n"
        reporte += f"Puntaje: {puntaje:.2f}%\n\n"
        
        correctas = sum(1 for r in resultados_detallados if r['es_correcta'])
        reporte += f"RESUMEN: {correctas}/{len(resultados_detallados)} correctas\n\n"
        
        reporte += "DETALLE POR PREGUNTA:\n"
        reporte += "-------------------\n"
        
        for resultado in resultados_detallados:
            estado = "✅ CORRECTA" if resultado['es_correcta'] else "❌ INCORRECTA"
            reporte += (f"P{resultado['pregunta']}: Seleccionada {resultado['letra_seleccionada']}, "
                       f"Correcta {resultado['letra_correcta']} - {estado} (confianza: {resultado['confianza']:.1f}%)\n")
        
        return reporte
    
    def guardar_resultados(self, ruta_imagen_original, imagen_procesada, resultados_detallados, puntaje, carpeta_salida):
        """Guarda los resultados de la calificación"""
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
        
        nombre_base = os.path.splitext(os.path.basename(ruta_imagen_original))[0]
        
        # Guardar imagen procesada
        ruta_imagen_guardada = os.path.join(carpeta_salida, f"{nombre_base}_calificada.png")
        cv2.imwrite(ruta_imagen_guardada, imagen_procesada)
        
        # Guardar reporte
        ruta_reporte = os.path.join(carpeta_salida, f"{nombre_base}_reporte.txt")
        reporte = self.generar_reporte_calificacion(resultados_detallados, puntaje, nombre_base)
        
        with open(ruta_reporte, 'w', encoding='utf-8') as f:
            f.write(reporte)
        
        return ruta_imagen_guardada, ruta_reporte

# Función de conveniencia para uso rápido (se mantiene igual)
def calificar_examen_rapido(ruta_imagen, ruta_json_clave, carpeta_salida=None, modo_depuracion=False):
    calificador = CalificadorAutomatico(modo_depuracion=modo_depuracion)
    
    if not calificador.cargar_clave_desde_json(ruta_json_clave):
        return 0, [], "Error al cargar la clave de respuestas"
    
    puntaje, imagen_procesada, resultados_detallados, error = calificador.procesar_hoja_respuestas(ruta_imagen)
    
    if error:
        return 0, [], error
    
    if carpeta_salida and imagen_procesada is not None:
        calificador.guardar_resultados(ruta_imagen, imagen_procesada, resultados_detallados, puntaje, carpeta_salida)
    
    return puntaje, resultados_detallados, None

# Función para convertir TXT a JSON (se mantiene igual)
def generar_json_clave_desde_txt(ruta_txt, ruta_salida_json=None):
    clave_respuestas = {}
    
    try:
        with open(ruta_txt, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
        
        for linea in lineas:
            linea = linea.strip()
            if not linea or 'Pregunta' not in linea:
                continue
                
            partes = linea.split(':')
            if len(partes) >= 2:
                pregunta_part = partes[0].strip()
                respuesta_part = partes[1].strip()
                
                num_pregunta = ''.join(filter(str.isdigit, pregunta_part))
                if num_pregunta:
                    num_pregunta = int(num_pregunta) - 1
                    
                    if respuesta_part and respuesta_part[0].isalpha():
                        clave_respuestas[num_pregunta] = respuesta_part[0].upper()
                    elif respuesta_part.isdigit():
                        clave_respuestas[num_pregunta] = int(respuesta_part)
    
    except Exception as e:
        raise ValueError(f"Error al procesar archivo TXT: {str(e)}")
    
    datos_json = {
        "respuestas": clave_respuestas,
        "total_preguntas": len(clave_respuestas),
        "fecha_generacion": str(np.datetime64('now')),
        "formato": "pregunta_idx: respuesta"
    }
    
    if ruta_salida_json:
        with open(ruta_salida_json, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)
    
    return datos_json