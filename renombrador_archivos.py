import os
import logging

logger = logging.getLogger(__name__)

def previsualizar_renombrado_archivos(directorio_origen: str, prefijo: str, sufijo: str, inicio_numerico: int):
    """
    Genera una previsualización de cómo se renombrarían los archivos en un directorio.

    Args:
        directorio_origen (str): La ruta del directorio donde se encuentran los archivos.
        prefijo (str): El prefijo a añadir a los nombres de los archivos.
        sufijo (str): El sufijo a añadir a los nombres de los archivos.
        inicio_numerico (int): El número inicial para la secuencia numérica.

    Returns:
        tuple[list[tuple[str, str]], list[str]]: Una tupla que contiene:
            - Una lista de tuplas (nombre_original, nuevo_nombre_completo) para previsualización.
            - Una lista de rutas originales completas de los archivos.
    """
    if not os.path.isdir(directorio_origen):
        logger.error(f"El directorio de origen no es válido: {directorio_origen}")
        return [], []

    archivos_en_directorio = [f for f in os.listdir(directorio_origen) if os.path.isfile(os.path.join(directorio_origen, f))]
    archivos_en_directorio.sort() # Opcional: ordenar para una previsualización consistente

    previsualizaciones = []
    rutas_originales_completas = []

    for i, nombre_original in enumerate(archivos_en_directorio):
        nombre_base, ext = os.path.splitext(nombre_original)
        num_str = str(inicio_numerico + i)
        
        partes_nuevo_nombre_base = [parte for parte in [prefijo, nombre_base, num_str, sufijo] if parte]
        nuevo_nombre_base = "_".join(partes_nuevo_nombre_base)
        
        nuevo_nombre_completo = f"{nuevo_nombre_base}{ext}"
        
        previsualizaciones.append((nombre_original, nuevo_nombre_completo))
        rutas_originales_completas.append(os.path.join(directorio_origen, nombre_original))
    
    logger.info(f"Previsualización de renombrado generada para {len(archivos_en_directorio)} archivos en {directorio_origen}.")
    return previsualizaciones, rutas_originales_completas

def realizar_renombrado_masivo(archivos_a_renombrar: list[tuple[str, str]]):
    """
    Realiza el renombrado masivo de archivos basado en una lista de pares (ruta_original, nueva_ruta).

    Args:
        archivos_a_renombrar (list[tuple[str, str]]): Lista de tuplas donde cada tupla
                                                       contiene (ruta_original_completa, nueva_ruta_completa).

    Returns:
        int: El número de archivos renombrados exitosamente.
    """
    contador = 0
    for original_path, new_path in archivos_a_renombrar:
        try:
            if original_path != new_path: # Evitar renombrar si el nombre es idéntico
                os.rename(original_path, new_path)
                logger.info(f"Renombrado '{os.path.basename(original_path)}' a '{os.path.basename(new_path)}'")
                contador += 1
        except OSError as ex:
            logger.error(f"Error al renombrar {os.path.basename(original_path)} a {os.path.basename(new_path)}: {ex}")
    return contador