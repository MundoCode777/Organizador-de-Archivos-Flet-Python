import os
import logging
from PyPDF2 import PdfMerger # Asegúrate de tener PyPDF2 instalado (pip install PyPDF2)

logger = logging.getLogger(__name__)

def fusionar_pdfs(lista_archivos_pdf: list[str], ruta_salida: str) -> bool:
    """
    Fusiona una lista de archivos PDF en un único PDF de salida.

    Args:
        lista_archivos_pdf (list[str]): Una lista de rutas a los archivos PDF de entrada.
        ruta_salida (str): La ruta completa donde se guardará el PDF fusionado.

    Returns:
        bool: True si la fusión fue exitosa, False en caso contrario.
    """
    if not lista_archivos_pdf:
        logger.warning("No se proporcionaron archivos PDF para fusionar.")
        return False
    
    try:
        fusionador = PdfMerger()
        for pdf_path in lista_archivos_pdf:
            if os.path.exists(pdf_path) and pdf_path.lower().endswith(".pdf"):
                fusionador.append(pdf_path)
            else:
                logger.warning(f"Archivo no encontrado o no es PDF válido, ignorando: {pdf_path}")
        
        if not fusionador.pages:
            logger.error("No se pudieron añadir páginas de ningún PDF válido al fusionador.")
            return False

        fusionador.write(ruta_salida)
        fusionador.close()
        logger.info(f"PDFs fusionados exitosamente en: {ruta_salida}")
        return True
    except Exception as ex:
        logger.error(f"Error al fusionar PDFs en {ruta_salida}: {ex}")
        return False