from PIL import Image
import os

def batch_resize(folder_in,folder_out, width, height):
    for filaname in os.listdir(folder_in):
        if filaname.endswith(('.jpeg', '.jpg', '.png')):
            img =Image.open(os.path.join(folder_in, filaname))
            img = img.resize((width, height))
            img.save(os.path.join(folder_out, f"resized_{filaname}"))
            print(f'{filaname} Redimensionado')
            
if __name__ == "__main__":
    batch_resize(folder_in='imagenes', folder_out='imagenes_redimensionadas', width=800, height=600)
    
    
# --- Logica mia para usar un archivo aparte y llamar la funcion ---
# redimensionar_imagenes.py

from PIL import Image
import os

def redimensionar_imagenes(input_dir, output_dir, target_width=None, target_height=None, target_percentage=None):
    """
    Redimensiona todas las imágenes en `input_dir` y las guarda en `output_dir`.
    
    Parámetros:
    - input_dir (str): Directorio de entrada con las imágenes.
    - output_dir (str): Directorio donde se guardarán las imágenes redimensionadas.
    - target_width (int): Ancho objetivo en píxeles.
    - target_height (int): Alto objetivo en píxeles.
    - target_percentage (float): Porcentaje de escala (ejemplo: 0.5 para 50%).

    Retorna:
    - int: Número de imágenes redimensionadas.
    """
    # Extensiones soportadas
    supported_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
    
    # Validar directorios
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Directorio de entrada no encontrado: {input_dir}")
    if not os.path.isdir(output_dir):
        raise FileNotFoundError(f"Directorio de salida no encontrado: {output_dir}")

    # Verificar si se proporcionó al menos una opción de redimensionado
    if not ((target_width and target_height) or target_percentage):
        raise ValueError("Debe especificar dimensiones (ancho/alto) o un porcentaje.")

    resized_count = 0

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(supported_exts):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)

            try:
                with Image.open(input_path) as img:
                    # Determinar nuevas dimensiones
                    if target_percentage:
                        new_width = int(img.width * target_percentage)
                        new_height = int(img.height * target_percentage)
                    else:
                        new_width = target_width if target_width else img.width
                        new_height = target_height if target_height else img.height

                        # Si solo se da ancho o alto, mantener proporción
                        if not target_width and target_height:
                            new_width = int(img.width * (new_height / img.height))
                        elif target_width and not target_height:
                            new_height = int(img.height * (new_width / img.width))

                    # Redimensionar imagen
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)

                    # Guardar imagen en destino
                    resized_img.save(output_path, format=img.format)

                    print(f"Redimensionado: {filename} -> {new_width}x{new_height}")
                    resized_count += 1

            except Exception as e:
                print(f"Error al procesar {filename}: {e}")

    return resized_count