from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)

def redimensionar_imagenes(input_dir, output_dir, target_width=None, target_height=None, target_percentage=None):
    """
    Redimensiona todas las imágenes en `input_dir` y las guarda en `output_dir`.
    
    Parámetros:
    - input_dir (str): Directorio de entrada con las imágenes.
    - output_dir (str): Directorio donde se guardarán las imágenes redimensionadas.
    - target_width (int): Ancho objetivo en píxeles.
    - target_height (int): Alto objetivo en píxeles.
    - target_percentage (float): Porcentaje de redimensionado (ej. 0.5 para 50%).
    
    Retorna:
    - int: El número de imágenes redimensionadas exitosamente.
    """
    os.makedirs(output_dir, exist_ok=True)
    resized_count = 0
    supported_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff')

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(supported_exts):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            try:
                with Image.open(input_path) as img:
                    new_width, new_height = img.width, img.height
                    
                    if target_percentage:
                        new_width = int(img.width * target_percentage)
                        new_height = int(img.height * target_percentage)
                    elif target_width and target_height:
                        new_width, new_height = target_width, target_height
                    elif target_width:
                        new_height = int(img.height * (target_width / img.width))
                        new_width = target_width
                    elif target_height:
                        new_width = int(img.width * (target_height / img.height))
                        new_height = target_height
                    else:
                        logger.warning(f"No se especificó un método de redimensionado para {filename}. Se omitirá.")
                        continue

                    # Asegurarse de que las dimensiones sean al menos 1x1
                    new_width = max(1, new_width)
                    new_height = max(1, new_height)

                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Asegurarse de que el formato de guardado sea compatible
                    save_format = img.format if img.format else "PNG" # Default to PNG if format is unknown
                    if save_format == "JPEG" and resized_img.mode == "RGBA":
                        resized_img = resized_img.convert("RGB") # JPEG does not support alpha channel

                    resized_img.save(output_path, format=save_format)
                    logger.info(f"Redimensionado: {filename} -> {new_width}x{new_height}")
                    resized_count += 1

            except Exception as e:
                logger.error(f"Error al procesar {filename} para redimensionar: {e}")
                
    return resized_count


def convertir_imagenes_formato(input_dir, output_dir, target_format):
    """
    Convierte todas las imágenes soportadas en `input_dir` al `target_format`
    y las guarda en `output_dir`.

    Parámetros:
    - input_dir (str): Directorio de entrada con las imágenes.
    - output_dir (str): Directorio donde se guardarán las imágenes convertidas.
    - target_format (str): El formato de destino (ej. "png", "jpeg", "webp").

    Retorna:
    - int: El número de imágenes convertidas exitosamente.
    """
    os.makedirs(output_dir, exist_ok=True)
    converted_count = 0
    supported_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp') # Agrega aquí más si son necesarios

    for filename in os.listdir(input_dir):
        name, ext = os.path.splitext(filename)
        if ext.lower() in supported_exts:
            filepath = os.path.join(input_dir, filename)
            try:
                with Image.open(filepath) as img:
                    save_format = target_format.upper()
                    out_name = f"{name}.{target_format.lower()}"
                    output_filepath = os.path.join(output_dir, out_name)

                    # Para JPEG, convertir a RGB si la imagen tiene canal alfa o es indexada
                    if save_format == "JPEG" and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    # Para PNG, convertir a RGBA si la imagen es RGB y el original era RGBA, para mantener transparencia si es posible.
                    # O si el original es RGBA y el target es PNG, asegúrate de que se guarda con transparencia.
                    elif save_format == "PNG" and img.mode == "RGB" and ext.lower() == ".png":
                        # Si la imagen original era PNG con transparencia y ahora es RGB, intentar recuperar RGBA
                        try:
                            original_img = Image.open(filepath)
                            if original_img.mode == "RGBA":
                                img = img.convert("RGBA")
                        except Exception as e:
                            logger.warning(f"No se pudo verificar el modo RGBA original para {filename}: {e}")

                    img.save(output_filepath, format=save_format)
                    logger.info(f"Convertido {filename} a {target_format}")
                    converted_count += 1
            except Exception as ex:
                logger.error(f"Error al convertir {filename}: {ex}")
    return converted_count