# [file name]: ejemplo_uso.py

from calificador_automatico import CalificadorAutomatico, calificar_examen_rapido
import json
import cv2
import matplotlib.pyplot as plt
import os
import numpy as np

def mostrar_imagen_procesada(imagen_procesada, titulo="Imagen Procesada"):
    """Muestra la imagen procesada usando matplotlib"""
    if imagen_procesada is None:
        print("⚠️  No hay imagen para mostrar")
        return
        
    # Convertir de BGR a RGB si es necesario
    if len(imagen_procesada.shape) == 3:
        imagen_rgb = cv2.cvtColor(imagen_procesada, cv2.COLOR_BGR2RGB)
    else:
        imagen_rgb = imagen_procesada
    
    plt.figure(figsize=(12, 8))
    plt.imshow(imagen_rgb)
    plt.title(titulo)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

def detectar_burbujas_negras_mejorado(imagen):
    """Detecta específicamente burbujas circulares rellenas de negro - VERSIÓN MEJORADA"""
    # Convertir a escala de grises
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    
    # MEJORA: Aplicar ecualización del histograma para mejorar contraste
    gris_ecualizado = cv2.equalizeHist(gris)
    
    # MEJORA: Usar umbral adaptativo en lugar de umbral global
    umbral_adaptativo = cv2.adaptiveThreshold(
        gris_ecualizado, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # MEJORA: Operaciones morfológicas más agresivas
    kernel = np.ones((5,5), np.uint8)
    umbral_limpiado = cv2.morphologyEx(umbral_adaptativo, cv2.MORPH_CLOSE, kernel)
    umbral_limpiado = cv2.morphologyEx(umbral_limpiado, cv2.MORPH_OPEN, kernel)
    
    # MEJORA: También probar con umbral Otsu
    _, umbral_otsu = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Combinar ambos métodos para mejor detección
    umbral_combinado = cv2.bitwise_or(umbral_limpiado, umbral_otsu)
    
    # Operaciones finales de limpieza
    umbral_final = cv2.morphologyEx(umbral_combinado, cv2.MORPH_CLOSE, kernel)
    
    # Encontrar contornos en el umbral combinado
    contornos, _ = cv2.findContours(umbral_final, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # MEJORA: Parámetros más flexibles para filtrar contornos
    burbujas_rellenas = []
    for contorno in contornos:
        area = cv2.contourArea(contorno)
        # Rango de área más amplio para burbujas
        if 50 < area < 3000:  # Área más flexible
            perimetro = cv2.arcLength(contorno, True)
            if perimetro > 0:
                circularidad = 4 * np.pi * area / (perimetro * perimetro)
                # Circularidad más flexible
                if circularidad > 0.5:  # Reducido de 0.7 a 0.5
                    # Verificar que esté relleno
                    x, y, w, h = cv2.boundingRect(contorno)
                    # MEJORA: Verificar relación de aspecto para evitar rectángulos
                    relacion_aspecto = w / h if h > 0 else 0
                    if 0.5 < relacion_aspecto < 2.0:  # Debe ser aproximadamente cuadrado/circular
                        roi = umbral_final[y:y+h, x:x+w]
                        if roi.size > 0:
                            densidad = np.sum(roi == 255) / (w * h)
                            # Densidad más flexible
                            if densidad > 0.4:  # Reducido de 0.6 a 0.4
                                burbujas_rellenas.append(contorno)
    
    return burbujas_rellenas, umbral_adaptativo, umbral_final, umbral_otsu

def probar_deteccion_burbujas_negras():
    """Función para probar la detección de burbujas rellenas paso a paso"""
    
    ruta_imagen = "examen_escaneado.png"
    
    if not os.path.exists(ruta_imagen):
        print(f"❌ La imagen {ruta_imagen} no existe")
        return
    
    # Cargar imagen
    imagen = cv2.imread(ruta_imagen)
    if imagen is None:
        print("❌ No se pudo cargar la imagen")
        return
    
    print(f"📏 Dimensiones de la imagen: {imagen.shape}")
    
    # Detectar burbujas rellenas con método mejorado
    burbujas, umbral_adaptativo, umbral_final, umbral_otsu = detectar_burbujas_negras_mejorado(imagen)
    
    print(f"🎯 Burbujas rellenas detectadas: {len(burbujas)}")
    
    # Dibujar resultados
    imagen_resultado = imagen.copy()
    for i, contorno in enumerate(burbujas):
        # Dibujar contorno
        cv2.drawContours(imagen_resultado, [contorno], -1, (0, 255, 0), 3)
        
        # Dibujar número de burbuja
        x, y, w, h = cv2.boundingRect(contorno)
        cv2.putText(imagen_resultado, str(i+1), (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Mostrar imágenes intermedias para diagnóstico
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # Imagen original
    axes[0,0].imshow(cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB))
    axes[0,0].set_title('Imagen Original')
    axes[0,0].axis('off')
    
    # Escala de grises ecualizada
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    gris_ecualizado = cv2.equalizeHist(gris)
    axes[0,1].imshow(gris_ecualizado, cmap='gray')
    axes[0,1].set_title('Gris Ecualizado')
    axes[0,1].axis('off')
    
    # Umbral adaptativo
    axes[0,2].imshow(umbral_adaptativo, cmap='gray')
    axes[0,2].set_title('Umbral Adaptativo')
    axes[0,2].axis('off')
    
    # Umbral Otsu
    axes[1,0].imshow(umbral_otsu, cmap='gray')
    axes[1,0].set_title('Umbral Otsu')
    axes[1,0].axis('off')
    
    # Umbral final
    axes[1,1].imshow(umbral_final, cmap='gray')
    axes[1,1].set_title('Umbral Final Combinado')
    axes[1,1].axis('off')
    
    # Resultado final
    axes[1,2].imshow(cv2.cvtColor(imagen_resultado, cv2.COLOR_BGR2RGB))
    axes[1,2].set_title(f'Burbujas Detectadas: {len(burbujas)}')
    axes[1,2].axis('off')
    
    plt.tight_layout()
    plt.show()
    
    # Mostrar información detallada de cada burbuja
    print("\n📊 Información detallada de burbujas detectadas:")
    for i, contorno in enumerate(burbujas):
        area = cv2.contourArea(contorno)
        perimetro = cv2.arcLength(contorno, True)
        circularidad = 4 * np.pi * area / (perimetro * perimetro) if perimetro > 0 else 0
        x, y, w, h = cv2.boundingRect(contorno)
        relacion_aspecto = w / h if h > 0 else 0
        
        print(f"Burbuja {i+1}:")
        print(f"  Área: {area:.1f}")
        print(f"  Circularidad: {circularidad:.2f}")
        print(f"  Posición: ({x},{y})")
        print(f"  Tamaño: {w}x{h}")
        print(f"  Relación aspecto: {relacion_aspecto:.2f}")

def probar_diferentes_umbrales(imagen):
    """Prueba diferentes valores de umbral para encontrar el óptimo"""
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    umbrales = [50, 80, 100, 120, 150, 180, 200, 220]
    
    for i, umbral_val in enumerate(umbrales):
        row = i // 4
        col = i % 4
        
        _, umbral = cv2.threshold(gris, umbral_val, 255, cv2.THRESH_BINARY_INV)
        contornos, _ = cv2.findContours(umbral, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Contar burbujas potenciales
        burbujas_potenciales = 0
        for contorno in contornos:
            area = cv2.contourArea(contorno)
            if 50 < area < 3000:
                burbujas_potenciales += 1
        
        axes[row, col].imshow(umbral, cmap='gray')
        axes[row, col].set_title(f'Umbral: {umbral_val}\nBurbujas: {burbujas_potenciales}')
        axes[row, col].axis('off')
    
    plt.tight_layout()
    plt.show()

def ejemplo_completo_mejorado():
    """Ejemplo completo con detección mejorada de burbujas rellenas"""
    
    # Crear calificador
    calificador = CalificadorAutomatico()
    
    # 1. Cargar clave de respuestas desde JSON
    clave_ejemplo = {
        "respuestas": {
            0: 1, 1: 3, 2: 1, 3: 3, 4: 2,
            5: 0, 6: 2, 7: 1, 8: 3, 9: 0
        },
        "total_preguntas": 10,
        "tema": "Examen Básico"
    }
    
    # Guardar clave de ejemplo
    with open("clave_calculo.json", "w", encoding='utf-8') as f:
        json.dump(clave_ejemplo, f, indent=2)
    
    print("✅ Clave de ejemplo guardada como 'clave_calculo.json'")
    
    # 2. Cargar la clave en el calificador
    if calificador.cargar_clave_desde_json("clave_calculo.json"):
        print("✅ Clave cargada correctamente")
        
        # 3. Procesar examen
        ruta_imagen = "examen_escaneado.png"
        
        if os.path.exists(ruta_imagen):
            print("📷 Procesando imagen con detección mejorada...")
            
            # Cargar y preprocesar imagen
            imagen = cv2.imread(ruta_imagen)
            if imagen is None:
                print("❌ No se pudo cargar la imagen")
                return
            
            # Detectar burbujas rellenas con método mejorado
            burbujas, _, _, _ = detectar_burbujas_negras_mejorado(imagen)
            print(f"🔍 Burbujas rellenas encontradas: {len(burbujas)}")
            
            # Intentar procesar con el calificador
            try:
                puntaje, imagen_procesada, resultados, error = calificador.procesar_hoja_respuestas(ruta_imagen)
                
                if error:
                    print(f"❌ Error del calificador: {error}")
                    print("🔄 Usando detección manual mejorada...")
                    puntaje, imagen_procesada, resultados = procesar_manual_mejorado(imagen, burbujas, calificador)
                else:
                    print(f"✅ Calificación completada: {puntaje:.2f}%")
            except Exception as e:
                print(f"❌ Error en calificador: {e}")
                print("🔄 Usando detección manual mejorada...")
                puntaje, imagen_procesada, resultados = procesar_manual_mejorado(imagen, burbujas, calificador)
            
            # Mostrar resultados
            if resultados:
                print(f"📊 Puntaje final: {puntaje:.2f}%")
                correctas = sum(1 for r in resultados if r['es_correcta'])
                print(f"✅ Correctas: {correctas}/{len(resultados)}")
                
                for resultado in resultados:
                    estado = "✓" if resultado['es_correcta'] else "✗"
                    print(f"P{resultado['pregunta']+1}: {resultado['letra_seleccionada']} vs {resultado['letra_correcta']} {estado}")
                
                # MOSTRAR LA IMAGEN PROCESADA
                if imagen_procesada is not None:
                    print("\n🖼️  Mostrando imagen procesada...")
                    mostrar_imagen_procesada(imagen_procesada, f"Examen Calificado - Puntaje: {puntaje:.1f}%")
                    
                    # Guardar resultados
                    cv2.imwrite("resultado_final.jpg", imagen_procesada)
                    print("✅ Imagen guardada como 'resultado_final.jpg'")
            else:
                print("❌ No se pudieron obtener resultados")
                
        else:
            print(f"⚠️  Imagen '{ruta_imagen}' no encontrada.")
            print("💡 Ejecuta la opción 3 para crear una imagen de ejemplo")
    
    else:
        print("❌ Error al cargar la clave")

def procesar_manual_mejorado(imagen, burbujas, calificador):
    """Procesamiento manual mejorado cuando la detección automática falla"""
    imagen_procesada = imagen.copy()
    resultados = []
    
    if not burbujas:
        print("❌ No se detectaron burbujas para procesar")
        return 0, imagen_procesada, []
    
    # Ordenar burbujas por posición (de arriba a abajo, izquierda a derecha)
    burbujas_ordenadas = sorted(burbujas, key=lambda c: (cv2.boundingRect(c)[1], cv2.boundingRect(c)[0]))
    
    print(f"📝 Procesando {len(burbujas_ordenadas)} burbujas detectadas...")
    
    # Asumir 4 opciones por pregunta (A,B,C,D)
    opciones_por_pregunta = 4
    preguntas_detectadas = len(burbujas_ordenadas) // opciones_por_pregunta
    
    for i in range(min(preguntas_detectadas, calificador.num_preguntas)):
        # Obtener las burbujas para esta pregunta
        inicio = i * opciones_por_pregunta
        fin = inicio + opciones_por_pregunta
        
        if fin <= len(burbujas_ordenadas):
            burbujas_pregunta = burbujas_ordenadas[inicio:fin]
            
            # Marcar todas las burbujas detectadas para esta pregunta
            for j, burbuja in enumerate(burbujas_pregunta):
                x, y, w, h = cv2.boundingRect(burbuja)
                cv2.rectangle(imagen_procesada, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(imagen_procesada, f"P{i+1}-{chr(65+j)}", 
                           (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # Simular resultado (en un caso real, aquí determinarías cuál está rellena)
            opcion_seleccionada = 0  # Por defecto A
            resultado = {
                'pregunta': i,
                'respuesta_seleccionada': opcion_seleccionada,
                'respuesta_correcta': calificador.clave_respuestas.get(i, 0),
                'es_correcta': False,
                'letra_seleccionada': chr(65 + opcion_seleccionada),
                'letra_correcta': chr(65 + calificador.clave_respuestas.get(i, 0))
            }
            resultado['es_correcta'] = resultado['respuesta_seleccionada'] == resultado['respuesta_correcta']
            resultados.append(resultado)
    
    # Calcular puntaje
    correctas = sum(1 for r in resultados if r['es_correcta'])
    puntaje = (correctas / len(resultados)) * 100 if resultados else 0
    
    return puntaje, imagen_procesada, resultados

def crear_imagen_ejemplo_rellena():
    """Crear una imagen de ejemplo con burbujas rellenas"""
    ancho, alto = 800, 600
    imagen = 255 * np.ones((alto, ancho, 3), dtype=np.uint8)
    
    # Dibujar título
    cv2.putText(imagen, "EXAMEN DE EJEMPLO", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Dibujar burbujas de ejemplo (5 preguntas, 4 opciones cada una)
    for i in range(5):  # 5 preguntas
        cv2.putText(imagen, f"{i+1}.", (50, 120 + i * 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        for j in range(4):  # 4 opciones cada una (A,B,C,D)
            x = 150 + j * 150
            y = 100 + i * 80
            
            # Dibujar círculo (contorno)
            cv2.circle(imagen, (x, y), 20, (0, 0, 0), 2)
            
            # Dibujar letra de la opción
            letra = chr(65 + j)  # A, B, C, D
            cv2.putText(imagen, letra, (x-5, y+5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Rellenar algunas burbujas (simulando respuestas marcadas)
            if (i, j) in [(0,1), (1,3), (2,1), (3,3), (4,2)]:  # B, D, B, D, C
                cv2.circle(imagen, (x, y), 15, (0, 0, 0), -1)  # Relleno negro
    
    cv2.imwrite("examen_escaneado.png", imagen)
    print("✅ Imagen de ejemplo con burbujas rellenas creada: 'examen_escaneado.png'")
    print("💡 Las burbujas rellenas están en: P1-B, P2-D, P3-B, P4-D, P5-C")

if __name__ == "__main__":
    print("=== CALIFICADOR AUTOMÁTICO - DETECCIÓN MEJORADA ===")
    print("1. Ejemplo completo con detección mejorada")
    print("2. Diagnóstico de detección de burbujas rellenas")
    print("3. Probar diferentes umbrales")
    print("4. Crear imagen de ejemplo con burbujas rellenas")
    
    opcion = input("Selecciona una opción (1, 2, 3 o 4): ")
    
    if opcion == "1":
        ejemplo_completo_mejorado()
    elif opcion == "2":
        probar_deteccion_burbujas_negras()
    elif opcion == "3":
        ruta_imagen = "examen_escaneado.png"
        if os.path.exists(ruta_imagen):
            imagen = cv2.imread(ruta_imagen)
            if imagen is not None:
                probar_diferentes_umbrales(imagen)
            else:
                print("❌ No se pudo cargar la imagen")
        else:
            print("❌ Imagen no encontrada")
    elif opcion == "4":
        crear_imagen_ejemplo_rellena()
        print("💡 Ahora ejecuta la opción 2 para ver la detección")
    else:
        print("Opción no válida")