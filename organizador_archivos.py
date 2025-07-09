# organizador_archivos.py
import os
import shutil
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import io
import base64

from config import DEFAULT_FOLDERS, LOG_FILE_PATH

logger = logging.getLogger(__name__)

plt.switch_backend('Agg')

def obtener_carpetas_configuradas(carpetas_personalizadas: list[tuple[str, list[str]]], entradas_carpetas_por_defecto: dict) -> dict[str, list[str]]:
    """
    Recupera el mapeo de nombres de carpetas a sus extensiones de archivo asociadas,
    priorizando las carpetas personalizadas.
    
    Parámetros:
    - carpetas_personalizadas (list[tuple[str, list[str]]]): Lista de tuplas (nombre_carpeta, extensiones).
    - entradas_carpetas_por_defecto (dict): Diccionario con los valores de los TextField para carpetas por defecto.
                                    Ej: {'Music': 'Música', 'Photos': 'Fotos'}

    Retorna:
    dict: Un diccionario donde las claves son nombres de carpetas y los valores son sus extensiones.
    """
    carpetas_finales = {}
    
    # 1. Añadir carpetas personalizadas primero
    for nombre_carpeta, extensiones_carpeta in carpetas_personalizadas:
        carpetas_finales[nombre_carpeta] = extensiones_carpeta

    # 2. Añadir carpetas por defecto, asegurándose de que las personalizadas prevalezcan
    #    Las extensiones de carpetas por defecto que no estén en una carpeta personalizada existente se añaden.
    #    Las carpetas por defecto que no existan se añaden completamente.
    mapeo_por_defecto = {
        entradas_carpetas_por_defecto['Music']: DEFAULT_FOLDERS['Music'],
        entradas_carpetas_por_defecto['Photos']: DEFAULT_FOLDERS['Photos'],
        entradas_carpetas_por_defecto['Docs']: DEFAULT_FOLDERS['Docs'],
        entradas_carpetas_por_defecto['Videos']: DEFAULT_FOLDERS['Videos']
    }
    
    for nombre_defecto, extensiones_defecto in mapeo_por_defecto.items():
        if nombre_defecto in carpetas_finales:
            carpetas_finales[nombre_defecto].extend([ext for ext in extensiones_defecto if ext not in carpetas_finales[nombre_defecto]])
        else:
            carpetas_finales[nombre_defecto] = extensiones_defecto
    
    carpetas_finales["Otros"] = []
    return carpetas_finales

def crear_directorios_destino(directorio_base: str, carpetas: dict):
    """
    Crea directorios de destino si no existen.
    Args:
        directorio_base (str): El directorio raíz donde se crearán las carpetas.
        carpetas (dict): Un diccionario de nombres de carpetas y sus extensiones.
    """
    for carpeta in carpetas.keys():
        ruta_carpeta = os.path.join(directorio_base, carpeta)
        try:
            os.makedirs(ruta_carpeta, exist_ok=True)
            logger.info(f"Directorio creado: {ruta_carpeta}")
        except OSError as e:
            logger.error(f"Error al crear el directorio {ruta_carpeta}: {e}")
            raise

def mover_archivo_unico(ruta_archivo: str, directorio_base_destino: str, carpetas: dict):
    """
    Mueve un solo archivo a su carpeta de categoría designada.
    Si ninguna categoría coincide, mueve el archivo a la carpeta "Otros".
    
    Args:
        ruta_archivo (str): La ruta completa del archivo a mover.
        directorio_base_destino (str): El directorio base donde se encuentran las carpetas de destino.
        carpetas (dict): El diccionario que mapea nombres de carpetas a extensiones.
    Returns:
        bool: True si el archivo fue movido exitosamente, False en caso contrario.
    """
    nombre_archivo = os.path.basename(ruta_archivo)
    extension_archivo = nombre_archivo.split('.')[-1].lower() if '.' in nombre_archivo else ''
    nombre_carpeta_destino = "Otros"

    for carpeta, exts in carpetas.items():
        if extension_archivo in exts:
            nombre_carpeta_destino = carpeta
            break

    ruta_destino = os.path.join(directorio_base_destino, nombre_carpeta_destino, nombre_archivo)
    
    try:
        shutil.move(ruta_archivo, ruta_destino)
        logger.info(f"Movido '{nombre_archivo}' a '{nombre_carpeta_destino}'")
        return True
    except shutil.Error as e:
        logger.error(f"Error al mover el archivo {nombre_archivo}: {e}")
        return False
    except FileNotFoundError:
        logger.warning(f"Archivo no encontrado, omitiendo: {nombre_archivo}")
        return False
    except Exception as e:
        logger.error(f"Un error inesperado ocurrió al mover {nombre_archivo}: {e}")
        return False

def organizar_archivos_en_directorio(dir_origen: str, carpetas: dict, en_progreso=None):
    """
    Orquesta el proceso de organización de archivos para un directorio dado.
    
    Args:
        dir_origen (str): El directorio a organizar.
        carpetas (dict): El diccionario que mapea nombres de carpetas a extensiones.
        en_progreso (callable, optional): Una función de callback para actualizar el progreso.
                                         Se llamará con (progreso_actual, total).
    Retorna:
        int: Número de archivos organizados.
    """
    try:
        crear_directorios_destino(dir_origen, carpetas)
    except Exception as e:
        logger.error(f"Falló la creación de directorios de destino: {e}")
        raise

    archivos_a_procesar = [f for f in os.listdir(dir_origen) if os.path.isfile(os.path.join(dir_origen, f))]
    total_archivos = len(archivos_a_procesar)
    logger.info(f"Iniciando organización de {total_archivos} archivos en {dir_origen}")
    
    contador_organizados = 0
    for i, nombre_archivo in enumerate(archivos_a_procesar):
        ruta_archivo = os.path.join(dir_origen, nombre_archivo)
        if mover_archivo_unico(ruta_archivo, dir_origen, carpetas):
            contador_organizados += 1
        if en_progreso:
            en_progreso((i + 1), total_archivos)
            
    logger.info("Organización de archivos completada.")
    return contador_organizados

def resumir_archivos_directorio(dir_origen: str) -> dict[str, float]:
    """
    Calcula el tamaño total de los archivos agrupados por sus extensiones dentro de un directorio.
    Args:
        dir_origen (str): El directorio a resumir.
    Returns:
        dict: Un diccionario donde las claves son extensiones de archivo y los valores son sus tamaños totales en MB.
    """
    tamanios_archivos = {}
    for raiz, _, archivos in os.walk(dir_origen):
        for archivo in archivos:
            ruta_archivo = os.path.join(raiz, archivo)
            if os.path.isfile(ruta_archivo):
                try:
                    ext = os.path.splitext(archivo)[1].lower()
                    tamanio = os.path.getsize(ruta_archivo) / (1024 * 1024)
                    tamanios_archivos[ext] = tamanios_archivos.get(ext, 0) + tamanio
                except OSError as e:
                    logger.warning(f"No se pudo obtener el tamaño para {ruta_archivo}: {e}")
    return tamanios_archivos

def formatear_texto_resumen(tamanios_archivos: dict[str, float]) -> str:
    """
    Formatea el resumen del tamaño de los archivos en una cadena legible por humanos.
    Args:
        tamanios_archivos (dict): Diccionario de extensiones de archivo y sus tamaños.
    Returns:
        str: Cadena de resumen formateada.
    """
    if not tamanios_archivos:
        return "No hay archivos para resumir o el directorio está vacío."
    archivos_ordenados = sorted(tamanios_archivos.items(), key=lambda x: x[1], reverse=True)
    return "\n".join([f"{ext.upper()[1:]}: {tamanio:.1f} MB" for ext, tamanio in archivos_ordenados])

def generar_grafico_resumen(tamanios_archivos: dict[str, float]) -> str:
    """
    Genera un gráfico circular de los tamaños de archivo por tipo y lo devuelve como una cadena base64.
    No se guarda ningún archivo de imagen en el disco.
    Args:
        tamanios_archivos (dict): Diccionario de extensiones de archivo y sus tamaños.
    Returns:
        str: La cadena codificada en base64 de la imagen del gráfico (formato PNG), o una cadena vacía si no hay datos para graficar.
    """
    if not tamanios_archivos:
        logger.info("No hay tamaños de archivo para graficar. Devolviendo cadena base64 vacía.")
        return ""
    
    extensiones = list(tamanios_archivos.keys())
    tamanios = list(tamanios_archivos.values())

    cmap_nombre = 'tab20c' if len(extensiones) > 20 else 'viridis' if len(extensiones) > 10 else 'Set3'
    colores = plt.cm.get_cmap(cmap_nombre, len(extensiones))(np.arange(len(extensiones)))
    
    fig, ax = plt.subplots(facecolor='white')
    color_texto = 'black'
    color_titulo = 'black'
    
    parches, textos, autotextos = ax.pie(tamanios, labels=extensiones, colors=colores, autopct='%1.1f%%', startangle=140, textprops={'color': color_texto})
    
    ax.set_title("Tamaño por tipo de archivo", color=color_titulo)
    tamanio_total_mb = sum(tamanios)
    plt.text(0, -1.5, f"Total: {tamanio_total_mb:.2f} MB", ha='center', color=color_texto, fontsize=12, bbox=dict(facecolor='none', edgecolor='none', pad=5))
    
    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', transparent=True)
    buffer.seek(0)
    plt.close(fig)
    
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    logger.info("Gráfico generado como cadena base64.")
    return img_base64