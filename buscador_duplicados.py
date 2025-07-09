# buscador_duplicados.py
import os
import hashlib
import asyncio
import logging

from config import LOG_FILE_PATH

logger = logging.getLogger(__name__)

async def calcular_hash_archivo(ruta_archivo, tam_bloque=65536):
    """
    Calcula el hash SHA256 de un archivo dado.
    
    Args:
        ruta_archivo (str): La ruta del archivo.
        tam_bloque (int): Tamaño del bloque para leer el archivo.
    Returns:
        str: El hash SHA256 del archivo o None si hay un error.
    """
    if not os.path.exists(ruta_archivo):
        logger.warning(f"Archivo no encontrado para calcular hash: {ruta_archivo}")
        return None
    
    sha256 = hashlib.sha256()
    try:
        with open(ruta_archivo, 'rb') as f:
            while True:
                bloque = await asyncio.to_thread(f.read, tam_bloque)
                if not bloque:
                    break
                sha256.update(bloque)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error al calcular el hash de {ruta_archivo}: {e}")
        return None

async def encontrar_archivos_duplicados(directorio: str, en_progreso=None):
    """
    Escanea un directorio en busca de archivos duplicados basándose en su contenido (hash SHA256).
    
    Args:
        directorio (str): El directorio a escanear.
        en_progreso (callable, optional): Una función de callback para actualizar el progreso.
                                         Se llamará con (progreso_actual, total).
    Returns:
        dict: Un diccionario donde las claves son hashes de archivo y los valores son listas de rutas de archivos duplicados.
    """
    if not os.path.isdir(directorio):
        logger.error(f"El directorio especificado no existe o no es válido: {directorio}")
        return {}

    mapa_hashes = {}
    todos_los_archivos = []
    for raiz, _, archivos in os.walk(directorio):
        for archivo in archivos:
            ruta_archivo = os.path.join(raiz, archivo)
            if os.path.isfile(ruta_archivo):
                todos_los_archivos.append(ruta_archivo)

    total_archivos = len(todos_los_archivos)
    logger.info(f"Escaneando {total_archivos} archivos en busca de duplicados en {directorio}")

    for i, ruta_archivo in enumerate(todos_los_archivos):
        hash_archivo = await calcular_hash_archivo(ruta_archivo)
        if hash_archivo:
            mapa_hashes.setdefault(hash_archivo, []).append(ruta_archivo)
        
        if en_progreso:
            en_progreso((i + 1), total_archivos)
    
    archivos_duplicados = {valor_hash: rutas for valor_hash, rutas in mapa_hashes.items() if len(rutas) > 1}
    logger.info(f"Escaneo de duplicados completado. Encontrados {len(archivos_duplicados)} grupos de duplicados.")
    return archivos_duplicados

def eliminar_archivos(rutas_archivos: list[str]) -> int:
    """
    Elimina los archivos especificados.
    
    Args:
        rutas_archivos (list[str]): Una lista de rutas de archivos a eliminar.
    Returns:
        int: El número de archivos eliminados exitosamente.
    """
    contador_eliminados = 0
    for ruta in rutas_archivos:
        if os.path.exists(ruta):
            try:
                os.remove(ruta)
                logger.info(f"Archivo eliminado: {ruta}")
                contador_eliminados += 1
            except OSError as e:
                logger.error(f"Error al eliminar {ruta}: {e}")
            except Exception as e:
                logger.error(f"Un error inesperado ocurrió al eliminar {ruta}: {e}")
        else:
            logger.warning(f"Intento de eliminar archivo no existente: {ruta}")
    return contador_eliminados