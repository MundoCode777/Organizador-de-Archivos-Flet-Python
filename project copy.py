import os
import shutil
import logging
from datetime import datetime
import flet as ft
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from moviepy import VideoFileClip
import hashlib # Import hashlib for file hashing
import asyncio # Import asyncio for run_in_executor
from PIL import Image # Import Pillow for image processing

# Asumiendo que config.py existe y contiene DEFAULT_FOLDERS
# from config import DEFAULT_FOLDERS
# Placeholder for DEFAULT_FOLDERS if config.py is not available
DEFAULT_FOLDERS = {
    'Music': ['mp3', 'wav', 'flac', 'aac'],
    'Photos': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'],
    'Docs': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf'],
    'Videos': ['mp4', 'mov', 'avi', 'mkv', 'webm'],
}


# --- Configuración e Inicialización de Logs ---
LOG_FILE = './assets/file_manager.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

plt.switch_backend('Agg')

DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 760

class FileManagerApp:
    """
    Una aplicación Flet para organizar archivos en carpetas categorizadas y ofrecer
    otras utilidades de gestión de archivos.
    """
    def __init__(self, page: ft.Page):
        self.page = page
        self._configure_page()

        self._current_target_textfield: ft.TextField = None # Atributo para almacenar el campo de texto objetivo
        self._file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        self.page.overlay.append(self._file_picker)

        self._init_ui_components()
        self._add_ui_to_page()
        self.page.update()

        self.custom_folders: list[tuple[str, list[str]]] = []
        self.selected_files_for_merge: list[str] = [] # Para fusión de PDFs
        self.selected_files_for_rename: list[str] = [] # Para renombrar archivos
        self.selected_dir_for_duplication: str = "" # Para eliminar duplicados
        self.duplicate_files_map: dict[str, list[str]] = {} # Almacena hashes y rutas de archivos

    def _configure_page(self):
        """Configura las propiedades de la página Flet."""
        self.page.title = "Gestor de Archivos Inteligente"
        self.page.window_width = DEFAULT_WINDOW_WIDTH
        self.page.window_height = DEFAULT_WINDOW_HEIGHT
        self.page.window_min_width = DEFAULT_WINDOW_WIDTH
        self.page.window_min_height = DEFAULT_WINDOW_HEIGHT
        self.page.window_resizable = True
        self.page.scroll = ft.ScrollMode.ALWAYS

    def _init_ui_components(self):
        """Inicializa todos los componentes de la interfaz de usuario de la aplicación."""
        # --- Componentes para Organizar Archivos ---
        self.src_dir_input = ft.TextField(label="Carpeta de origen", width=300, read_only=True)
        self.pick_src_button = ft.ElevatedButton(
            text="Seleccionar carpeta",
            on_click=lambda _: self._launch_directory_picker(self.src_dir_input)
        )
        self.music_input = ft.TextField(label="Carpeta de música", width=300, value="Música")
        self.photos_input = ft.TextField(label="Carpeta de fotos", width=300, value="Fotos")
        self.docs_input = ft.TextField(label="Carpeta de documentos", width=300, value="Documentos")
        self.videos_input = ft.TextField(label="Carpeta de videos", width=300, value="Videos")
        self.custom_folder_input = ft.TextField(label="Nombre de carpeta personalizada", width=300)
        self.custom_exts_input = ft.TextField(label="Extensiones (separadas por coma)", width=300,
                                               hint_text="ej: pdf, docx, xlsx")
        self.add_custom_button = ft.ElevatedButton(
            text="Agregar carpeta personalizada",
            on_click=self._on_add_custom_click,
        )
        self.custom_list = ft.Column()
        self.organize_button = ft.ElevatedButton(
            text="Organizar archivos",
            on_click=self._on_organize_click,
        )
        self.summary_input = ft.TextField(
            label="Resumen de archivos",
            multiline=True,
            width=300,
            height=200,
            read_only=True,
        )
        self.progress_bar = ft.ProgressBar(width=300, value=0)
        self.progress_bar.visible = False
        self.plot_image = ft.Image(width=600, height=400, src_base64="", fit=ft.ImageFit.CONTAIN, visible=False)

        # --- Componentes para Eliminar Archivos Duplicados ---
        self.dup_dir_input = ft.TextField(label="Carpeta a escanear", width=400, read_only=True)
        self.pick_dup_dir_button = ft.ElevatedButton(
            text="Seleccionar carpeta",
            on_click=lambda _: self._launch_directory_picker(self.dup_dir_input)
        )
        self.scan_duplicates_button = ft.ElevatedButton(
            text="Escanear duplicados",
            on_click=self._on_scan_duplicates_click
        )
        self.dup_progress_bar = ft.ProgressBar(width=400, value=0, visible=False) # Added progress bar for duplicates
        self.duplicate_files_list = ft.ListView(expand=True, spacing=5, padding=10)
        self.delete_duplicates_button = ft.ElevatedButton(
            text="Eliminar seleccionados",
            on_click=self._on_delete_duplicates_click,
            disabled=True
        )
        self.dup_status_text = ft.Text("")

        # --- Componentes para Redimensionar Imágenes ---
        self.resize_input_dir = ft.TextField(label="Carpeta de origen de imágenes", width=400, read_only=True)
        self.pick_resize_dir_button = ft.ElevatedButton(
            text="Seleccionar carpeta",
            on_click=lambda _: self._launch_directory_picker(self.resize_input_dir)
        )
        self.resize_width_input = ft.TextField(label="Nuevo ancho (px)", keyboard_type=ft.KeyboardType.NUMBER, width=150)
        self.resize_height_input = ft.TextField(label="Nuevo alto (px)", keyboard_type=ft.KeyboardType.NUMBER, width=150)
        self.resize_percentage_input = ft.TextField(label="Porcentaje (%)", keyboard_type=ft.KeyboardType.NUMBER, width=150)
        self.resize_output_dir = ft.TextField(label="Carpeta de destino", width=400, read_only=True)
        self.pick_resize_output_dir_button = ft.ElevatedButton(
            text="Seleccionar destino",
            on_click=lambda _: self._launch_directory_picker(self.resize_output_dir)
        )
        self.perform_resize_button = ft.ElevatedButton(
            text="Redimensionar imágenes",
            on_click=self._on_resize_images_click
        )
        self.resize_status_text = ft.Text("")

        # --- Componentes para Convertir Formatos de Imagen ---
        self.convert_input_dir = ft.TextField(label="Carpeta de origen de imágenes", width=400, read_only=True)
        self.pick_convert_dir_button = ft.ElevatedButton(
            text="Seleccionar carpeta",
            on_click=lambda _: self._launch_directory_picker(self.convert_input_dir)
        )
        self.target_format_dropdown = ft.Dropdown(
            label="Formato de destino",
            options=[
                ft.dropdown.Option("JPEG"),
                ft.dropdown.Option("PNG"),
                ft.dropdown.Option("GIF"),
                ft.dropdown.Option("BMP"),
                ft.dropdown.Option("WEBP"),
            ],
            width=200
        )
        self.convert_output_dir = ft.TextField(label="Carpeta de destino", width=400, read_only=True)
        self.pick_convert_output_dir_button = ft.ElevatedButton(
            text="Seleccionar destino",
            on_click=lambda _: self._launch_directory_picker(self.convert_output_dir)
        )
        self.perform_convert_button = ft.ElevatedButton(
            text="Convertir formato",
            on_click=self._on_convert_images_click
        )
        self.convert_status_text = ft.Text("")

        # --- Componentes para Extraer Audio de Videos ---
        self.extract_video_input = ft.TextField(label="Archivo de video", width=400, read_only=True)
        self.pick_video_button = ft.ElevatedButton(
            text="Seleccionar video",
            on_click=lambda _: self._file_picker.pick_files(
                allow_multiple=False,
                allowed_file_extensions=["mp4", "mov", "avi", "mkv"],
                on_result=self._on_pick_video_for_audio_result # Este es para un archivo, no un directorio
            )
        )
        self.extract_output_dir = ft.TextField(label="Carpeta de destino de audio", width=400, read_only=True)
        self.pick_audio_output_dir_button = ft.ElevatedButton(
            text="Seleccionar destino",
            on_click=lambda _: self._launch_directory_picker(self.extract_output_dir)
        )
        self.perform_audio_extract_button = ft.ElevatedButton(
            text="Extraer Audio",
            on_click=self._on_extract_audio_click
        )
        self.extract_audio_status_text = ft.Text("")

        # --- Componentes para Fusionar PDFs ---
        self.pdf_list_view = ft.ListView(expand=True, spacing=5, padding=10)
        self.add_pdf_button = ft.ElevatedButton(
            text="Añadir PDF",
            on_click=lambda _: self._file_picker.pick_files(
                allow_multiple=True,
                allowed_file_extensions=["pdf"],
                on_result=self._on_pick_pdfs_to_merge_result # Este es para archivos, no un directorio
            )
        )
        self.clear_pdf_list_button = ft.ElevatedButton(
            text="Limpiar lista",
            on_click=self._on_clear_pdf_list_click
        )
        self.merged_pdf_name_input = ft.TextField(label="Nombre del PDF resultante", width=400, value="documento_fusionado.pdf")
        self.merge_pdf_output_dir = ft.TextField(label="Carpeta de destino", width=400, read_only=True)
        self.pick_merge_output_dir_button = ft.ElevatedButton(
            text="Seleccionar destino",
            on_click=lambda _: self._launch_directory_picker(self.merge_pdf_output_dir)
        )
        self.perform_merge_pdf_button = ft.ElevatedButton(
            text="Fusionar PDFs",
            on_click=self._on_merge_pdfs_click
        )
        self.merge_pdf_status_text = ft.Text("")

        # --- Componentes para Renombrar Archivos ---
        self.rename_dir_input = ft.TextField(label="Carpeta de origen para renombrar", width=400, read_only=True)
        self.pick_rename_dir_button = ft.ElevatedButton(
            text="Seleccionar carpeta",
            on_click=lambda _: self._launch_directory_picker(self.rename_dir_input)
        )
        self.rename_prefix_input = ft.TextField(label="Prefijo", width=200)
        self.rename_suffix_input = ft.TextField(label="Sufijo", width=200)
        self.rename_search_input = ft.TextField(label="Buscar", width=200)
        self.rename_replace_input = ft.TextField(label="Reemplazar con", width=200)
        self.rename_numbering_checkbox = ft.Checkbox(label="Añadir numeración", value=False)
        self.rename_start_num_input = ft.TextField(label="Inicio num.", keyboard_type=ft.KeyboardType.NUMBER, width=100)
        self.rename_padding_input = ft.TextField(label="Relleno num. (ej: 3 para 001)", keyboard_type=ft.KeyboardType.NUMBER, width=150)

        self.rename_preview_list = ft.ListView(expand=True, spacing=5, padding=10)
        self.preview_rename_button = ft.ElevatedButton(
            text="Previsualizar cambios",
            on_click=self._on_preview_rename_click
        )
        self.perform_rename_button = ft.ElevatedButton(
            text="Renombrar archivos",
            on_click=self._on_rename_files_click
        )
        self.rename_status_text = ft.Text("")

    def _add_ui_to_page(self):
        """Añade los componentes de la interfaz de usuario inicializados al diseño de la página Flet."""
        self.page.add(
            ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text="Organizar Archivos",
                        content=ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text("Configuración de Carpetas", size=18, weight=ft.FontWeight.BOLD),
                                        ft.Divider(),
                                        self.src_dir_input,
                                        self.pick_src_button,
                                        ft.Text("Carpetas Predefinidas:", size=16),
                                        self.music_input,
                                        self.photos_input,
                                        self.docs_input,
                                        self.videos_input,
                                        ft.Text("Agregar Carpeta Personalizada:", size=16),
                                        self.custom_folder_input,
                                        self.custom_exts_input,
                                        self.add_custom_button,
                                        ft.Text("Carpetas Personalizadas Agregadas:", size=16),
                                        self.custom_list,
                                    ],
                                    scroll=ft.ScrollMode.AUTO,
                                    expand=1
                                ),
                                ft.VerticalDivider(),
                                ft.Column(
                                    [
                                        ft.Text("Gráfico de Resumen", size=18, weight=ft.FontWeight.BOLD),
                                        ft.Divider(),
                                        self.plot_image,
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    expand=2
                                ),
                                ft.VerticalDivider(),
                                ft.Column(
                                    [
                                        ft.Text("Control y Resumen", size=18, weight=ft.FontWeight.BOLD),
                                        ft.Divider(),
                                        self.organize_button,
                                        self.progress_bar,
                                        self.summary_input,
                                    ],
                                    scroll=ft.ScrollMode.AUTO,
                                    expand=1
                                ),
                            ],
                            expand=True,
                            vertical_alignment=ft.CrossAxisAlignment.START
                        )
                    ),
                    ft.Tab(
                        text="Eliminar Duplicados",
                        content=ft.Column(
                            [
                                ft.Text("Eliminar Archivos Duplicados", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Row([self.dup_dir_input, self.pick_dup_dir_button]),
                                self.scan_duplicates_button,
                                self.dup_progress_bar, # Added progress bar here
                                self.dup_status_text,
                                ft.Text("Archivos Duplicados Encontrados:"),
                                ft.Container(
                                    content=self.duplicate_files_list,
                                    height=300,
                                    border=ft.border.all(1),
                                    border_radius=5
                                ),
                                self.delete_duplicates_button,
                            ],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ),
                    ft.Tab(
                        text="Redimensionar Imágenes",
                        content=ft.Column(
                            [
                                ft.Text("Redimensionar Imágenes", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Row([self.resize_input_dir, self.pick_resize_dir_button]),
                                ft.Text("Dimensiones (ingrese ancho/alto O porcentaje):"),
                                ft.Row([self.resize_width_input, self.resize_height_input, self.resize_percentage_input]),
                                ft.Row([self.resize_output_dir, self.pick_resize_output_dir_button]),
                                self.perform_resize_button,
                                self.resize_status_text
                            ],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ),
                    ft.Tab(
                        text="Convertir Imágenes",
                        content=ft.Column(
                            [
                                ft.Text("Convertir Formatos de Imagen", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Row([self.convert_input_dir, self.pick_convert_dir_button]),
                                self.target_format_dropdown,
                                ft.Row([self.convert_output_dir, self.pick_convert_output_dir_button]),
                                self.perform_convert_button,
                                self.convert_status_text
                            ],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ),
                    ft.Tab(
                        text="Extraer Audio",
                        content=ft.Column(
                            [
                                ft.Text("Extraer Audio de Videos", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Row([self.extract_video_input, self.pick_video_button]),
                                ft.Row([self.extract_output_dir, self.pick_audio_output_dir_button]),
                                self.perform_audio_extract_button,
                                self.extract_audio_status_text
                            ],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ),
                    ft.Tab(
                        text="Fusionar PDFs",
                        content=ft.Column(
                            [
                                ft.Text("Fusionar Documentos PDF", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Row([self.add_pdf_button, self.clear_pdf_list_button]),
                                ft.Text("PDFs a Fusionar (en orden):"),
                                ft.Container(
                                    content=self.pdf_list_view,
                                    height=300,
                                    border=ft.border.all(1),
                                    border_radius=5
                                ),
                                self.merged_pdf_name_input,
                                ft.Row([self.merge_pdf_output_dir, self.pick_merge_output_dir_button]),
                                self.perform_merge_pdf_button,
                                self.merge_pdf_status_text
                            ],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ),
                    ft.Tab(
                        text="Renombrar Archivos",
                        content=ft.Column(
                            [
                                ft.Text("Renombrar Archivos por Lotes", size=18, weight=ft.FontWeight.BOLD),
                                ft.Divider(),
                                ft.Row([self.rename_dir_input, self.pick_rename_dir_button]),
                                ft.Text("Opciones de Renombrado:"),
                                ft.Row([self.rename_prefix_input, self.rename_suffix_input]),
                                ft.Row([self.rename_search_input, self.rename_replace_input]),
                                self.rename_numbering_checkbox,
                                ft.Row([self.rename_start_num_input, self.rename_padding_input]),
                                self.preview_rename_button,
                                ft.Text("Previsualización de Nombres:"),
                                ft.Container(
                                    content=self.rename_preview_list,
                                    height=200,
                                    border=ft.border.all(1),
                                    border_radius=5
                                ),
                                self.perform_rename_button,
                                self.rename_status_text
                            ],
                            expand=True,
                            scroll=ft.ScrollMode.AUTO
                        )
                    ),
                ],
                expand=True,
            )
        )

    # --- Métodos Genéricos para el FilePicker ---
    def _launch_directory_picker(self, target_textfield: ft.TextField):
        """
        Almacena el campo de texto objetivo y lanza el selector de directorios.
        Este método es llamado por los botones que necesitan seleccionar una carpeta.
        """
        self._current_target_textfield = target_textfield
        self._file_picker.get_directory_path()
        self.page.update()

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """
        Manejador genérico de eventos para el resultado del selector de archivos (solo directorios).
        Actualiza el campo de texto que se estableció como objetivo.
        """
        if e.path and os.path.isdir(e.path):
            if self._current_target_textfield:
                self._current_target_textfield.value = e.path
                # Asignaciones específicas para campos que necesitan almacenar la ruta para lógica posterior
                if self._current_target_textfield == self.dup_dir_input:
                    self.selected_dir_for_duplication = e.path
                elif self._current_target_textfield == self.rename_dir_input:
                    self.selected_files_for_rename = [os.path.join(e.path, f) for f in os.listdir(e.path) if os.path.isfile(os.path.join(e.path, f))]
                # Puedes añadir más condiciones 'elif' aquí para otros campos si necesitan lógica adicional
                # o almacenamiento específico de la ruta más allá de simplemente mostrarla en el TextField.
            logging.info(f"Directorio seleccionado: {e.path}")
        elif e.path: # Es un archivo, no un directorio, y no se esperaba un archivo en este handler.
            logging.warning(f"La ruta seleccionada no es un directorio: {e.path}. Se esperaba un directorio.")
            self.page.snack_bar = ft.SnackBar(ft.Text("La ruta seleccionada no es una carpeta válida."), open=True)
        else:
            logging.info("Selección de directorio cancelada.")
            self.page.snack_bar = ft.SnackBar(ft.Text("Selección de directorio cancelada."), open=True) # Added feedback
        
        self._current_target_textfield = None # Limpiar el objetivo después de usarlo
        self.page.update()

    # --- Métodos existentes para "Organizar Archivos" ---
    def _get_configured_folders(self) -> dict[str, list[str]]:
        """
        Recupera el mapeo de nombres de carpetas a sus extensiones de archivo asociadas,
        priorizando las carpetas personalizadas en el orden de iteración.
        """
        folders = {}
        
        # 1. Add custom folders first. If a custom folder has the same name as a default,
        #    its extensions will be stored/overwritten here.
        for folder_name, folder_exts in self.custom_folders:
            folders[folder_name] = folder_exts # Directly set/overwrite for custom folders

        # 2. Then add default folders. If a default folder's name conflicts with a custom one
        #    (which shouldn't happen often unless user manually names 'Music'), the custom one prevails.
        #    If a default folder is new, add it.
        #    If a default folder name exists from custom, do not overwrite its extensions.
        default_folder_values = {
            self.music_input.value: DEFAULT_FOLDERS['Music'],
            self.photos_input.value: DEFAULT_FOLDERS['Photos'],
            self.docs_input.value: DEFAULT_FOLDERS['Docs'],
            self.videos_input.value: DEFAULT_FOLDERS['Videos']
        }
        
        # Merge default folders, ensuring custom folders take precedence for extensions
        for default_name, default_exts in default_folder_values.items():
            # If the folder name is already used by a custom folder, extend its extensions
            # to include any default ones that aren't already present.
            if default_name in folders:
                folders[default_name].extend([ext for ext in default_exts if ext not in folders[default_name]])
            else:
                # Otherwise, add the default folder and its extensions
                folders[default_name] = default_exts
        
        folders["Otros"] = []
        return folders

    def _create_destination_directories(self, base_dir: str, folders: dict):
        """
        Crea directorios de destino si no existen.
        Args:
            base_dir (str): El directorio raíz donde se crearán las carpetas.
            folders (dict): Un diccionario de nombres de carpetas y sus extensiones.
        """
        for folder in folders.keys():
            folder_path = os.path.join(base_dir, folder)
            try:
                os.makedirs(folder_path, exist_ok=True)
                logging.info(f"Directorio creado: {folder_path}")
            except OSError as e:
                logging.error(f"Error al crear el directorio {folder_path}: {e}")

    def _move_single_file(self, file_name: str, src_dir: str, folders: dict):
        """
        Mueve un solo archivo a su carpeta de categoría designada.
        Si ninguna categoría coincide, mueve el archivo a la carpeta "Otros".
        Args:
            file_name (str): El nombre del archivo a mover.
            src_dir (str): El directorio de origen del archivo.
            folders (dict): El diccionario que mapea nombres de carpetas a extensiones.
        """
        file_ext = file_name.split('.')[-1].lower()
        source_path = os.path.join(src_dir, file_name)
        destination_folder = "Otros"

        for folder, exts in folders.items():
            if file_ext in exts:
                destination_folder = folder
                break

        destination_path = os.path.join(src_dir, destination_folder, file_name)
        try:
            shutil.move(source_path, destination_path)
            logging.info(f"Movido '{file_name}' a '{destination_folder}'")
        except shutil.Error as e:
            logging.error(f"Error al mover el archivo {file_name}: {e}")
        except FileNotFoundError:
             logging.warning(f"Archivo no encontrado, omitiendo: {file_name}")

    def _organize_files_in_directory(self, src_dir: str, folders: dict):
        """
        Orquesta el proceso de organización de archivos para un directorio dado.
        Args:
            src_dir (str): El directorio a organizar.
            folders (dict): El diccionario que mapea nombres de carpetas a extensiones.
        """
        self._create_destination_directories(src_dir, folders)
        files_to_process = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
        total_files = len(files_to_process)
        logging.info(f"Iniciando organización de {total_files} archivos en {src_dir}")

        for i, file in enumerate(files_to_process):
            self._move_single_file(file, src_dir, folders)
            self.progress_bar.value = (i + 1) / total_files
            self.page.update()
        logging.info("Organización de archivos completada.")

    def _summarize_directory_files(self, src_dir: str) -> dict[str, float]:
        """
        Calcula el tamaño total de los archivos agrupados por sus extensiones dentro de un directorio.
        Args:
            src_dir (str): El directorio a resumir.
        Returns:
            dict: Un diccionario donde las claves son extensiones de archivo y los valores son sus tamaños totales en MB.
        """
        file_sizes = {}
        for root, _, files in os.walk(src_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    try:
                        ext = os.path.splitext(file)[1].lower()
                        size = os.path.getsize(file_path) / (1024 * 1024)
                        file_sizes[ext] = file_sizes.get(ext, 0) + size
                    except OSError as e:
                        logging.warning(f"No se pudo obtener el tamaño para {file_path}: {e}")
        return file_sizes

    def _format_summary_text(self, file_sizes: dict[str, float]) -> str:
        """
        Formatea el resumen del tamaño de los archivos en una cadena legible por humanos.
        Args:
            file_sizes (dict): Diccionario de extensiones de archivo y sus tamaños.
        Returns:
            str: Cadena de resumen formateada.
        """
        if not file_sizes:
            return "No hay archivos para resumir o el directorio está vacío."

        sorted_files = sorted(file_sizes.items(), key=lambda x: x[1], reverse=True)
        return "\n".join([f"{ext.upper()[1:]}: {size:.1f} MB" for ext, size in sorted_files])

    def _generate_plot_summary(self, file_sizes: dict[str, float]) -> str:
        """
        Genera un gráfico circular de los tamaños de archivo por tipo y lo devuelve como una cadena base64.
        No se guarda ningún archivo de imagen en el disco.
        Args:
            file_sizes (dict): Diccionario de extensiones de archivo y sus tamaños.
        Returns:
            str: La cadena codificada en base64 de la imagen del gráfico (formato PNG),
                 o una cadena vacía si no hay datos para graficar.
        """
        if not file_sizes:
            logging.info("No hay tamaños de archivo para graficar. Devolviendo cadena base64 vacía.")
            return ""

        extensions = list(file_sizes.keys())
        sizes = list(file_sizes.values())

        # Manejo para el caso de pocos colores para evitar errores
        cmap_name = 'tab20c' if len(extensions) > 20 else 'viridis' if len(extensions) > 10 else 'Set3'
        colors = plt.cm.get_cmap(cmap_name, len(extensions))(np.arange(len(extensions)))

        fig, ax = plt.subplots(facecolor='white')

        text_color = 'black'
        title_color = 'black'

        patches, texts, autotexts = ax.pie(sizes, labels=extensions, colors=colors,
                                           autopct='%1.1f%%', startangle=140,
                                                              textprops={'color': text_color})

        ax.set_title("Tamaño por tipo de archivo", color=title_color)

        total_size_mb = sum(sizes)
        plt.text(0, -1.5, f"Total: {total_size_mb:.2f} MB", ha='center', color=text_color,
                 fontsize=12, bbox=dict(facecolor='none', edgecolor='none', pad=5))

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True)
        buf.seek(0)
        plt.close(fig)

        img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        logging.info("Gráfico generado como cadena base64.")
        return img_base64

    # --- Controladores de Eventos para "Organizar Archivos" ---
    def _on_add_custom_click(self, e: ft.ControlEvent):
        """Manejador de eventos para añadir una carpeta y extensiones personalizadas."""
        folder_name = self.custom_folder_input.value.strip()
        extensions_raw = self.custom_exts_input.value.strip()

        if not folder_name or not extensions_raw:
            logging.warning("El nombre de la carpeta personalizada o las extensiones no pueden estar vacíos.")
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, ingrese un nombre de carpeta y extensiones."), open=True)
            self.page.update()
            return

        exts = [ext.strip().lower() for ext in extensions_raw.split(',') if ext.strip()]
        if not exts:
            logging.warning("No se proporcionaron extensiones válidas para la carpeta personalizada.")
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, ingrese extensiones válidas."), open=True)
            self.page.update()
            return

        self.custom_folders.append((folder_name, exts))
        self.custom_list.controls.append(
            ft.Container(
                content=ft.Text(f"• {folder_name}: {', '.join(exts)}", color="onSurfaceVariant"),
                padding=ft.padding.only(left=10, top=2, bottom=2)
            )
        )
        self.custom_folder_input.value = ""
        self.custom_exts_input.value = ""
        self.page.update()
        logging.info(f"Carpeta personalizada añadida: '{folder_name}' con extensiones: {exts}")

    def _on_organize_click(self, e: ft.ControlEvent):
        """Manejador de eventos para el botón 'Organizar archivos'."""
        src_dir = self.src_dir_input.value

        if not src_dir or not os.path.isdir(src_dir):
            logging.warning(f"Directorio de origen inválido seleccionado: {src_dir}")
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de origen válida."), open=True)
            self.page.update()
            return

        try:
            self.organize_button.disabled = True
            self.progress_bar.value = 0
            self.progress_bar.visible = True
            self.summary_input.value = "Organizando archivos..."
            self.plot_image.visible = False
            self.page.update()

            folders_config = self._get_configured_folders()
            self._organize_files_in_directory(src_dir, folders_config)

            file_sizes_summary = self._summarize_directory_files(src_dir)
            self.summary_input.value = self._format_summary_text(file_sizes_summary)

            plot_base64_string = self._generate_plot_summary(file_sizes_summary)
            if plot_base64_string:
                self.plot_image.src_base64 = plot_base64_string
                self.plot_image.visible = True
            else:
                self.plot_image.src_base64 = ""
                self.plot_image.visible = False

            logging.info("Proceso de organización de archivos completado exitosamente.")
            self.page.snack_bar = ft.SnackBar(ft.Text("¡Archivos organizados exitosamente!"), open=True)


        except Exception as ex:
            logging.exception(f"Ocurrió un error durante la organización de archivos: {ex}")
            self.summary_input.value = f"Error: {ex}"
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Ocurrió un error: {ex}"), open=True)
        finally:
            self.progress_bar.visible = False
            self.organize_button.disabled = False
            self.page.update()

    # --- Métodos y Controladores para Eliminar Archivos Duplicados ---
    def _calculate_file_hash(self, filepath: str, block_size=65536) -> str:
        """Calcula el hash SHA256 de un archivo."""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    sha256.update(block)
            return sha256.hexdigest()
        except Exception as e:
            logging.error(f"Error al calcular el hash para {filepath}: {e}")
            return ""

    def _get_image_thumbnail_base64(self, image_path: str, size=(50, 50)) -> str:
        """
        Genera una miniatura de una imagen y la devuelve como una cadena base64.
        """
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size)
                buffered = io.BytesIO()
                # Ensure correct format for saving, handling transparency if needed
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img.save(buffered, format="PNG")
                else:
                    img.save(buffered, format="JPEG")
                return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            logging.warning(f"No se pudo generar la miniatura para {image_path}: {e}")
            return ""

    async def _on_scan_duplicates_click(self, e: ft.ControlEvent):
        src_dir = self.dup_dir_input.value
        if not src_dir or not os.path.isdir(src_dir):
            self.dup_status_text.value = "Por favor, seleccione una carpeta válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta válida para escanear duplicados."), open=True)
            self.page.update()
            return

        self.dup_status_text.value = "Escaneando duplicados..."
        self.dup_progress_bar.value = 0
        self.dup_progress_bar.visible = True
        self.duplicate_files_list.controls.clear()
        self.delete_duplicates_button.disabled = True
        self.page.update()
        
        self.duplicate_files_map = {} # Reset map for new scan
        all_files = []
        for root, _, files in os.walk(src_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                if os.path.isfile(filepath):
                    all_files.append(filepath)
        
        total_files = len(all_files)
        if total_files == 0:
            self.dup_status_text.value = "No se encontraron archivos en la carpeta."
            self.dup_progress_bar.visible = False
            self.page.update()
            return

        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp') # Common image extensions

        for i, filepath in enumerate(all_files):
            file_hash = await asyncio.get_event_loop().run_in_executor(None, self._calculate_file_hash, filepath)
            if file_hash:
                self.duplicate_files_map.setdefault(file_hash, []).append(filepath)
            
            # Update progress bar and status text
            self.dup_progress_bar.value = (i + 1) / total_files
            self.dup_status_text.value = f"Escaneando {i + 1}/{total_files} archivos..."
            self.page.update() # Update UI frequently enough to show progress
            
        found_duplicates_count = 0
        for _hash, paths in self.duplicate_files_map.items():
            if len(paths) > 1:
                # Ordenar para una consistencia en cuál es el "original" (ej. por nombre de archivo)
                paths.sort() 
                found_duplicates_count += len(paths) - 1 # Contar solo las copias
                
                self.duplicate_files_list.controls.append(ft.Text(f"Grupo de Duplicados (Hash: {_hash[:8]}...):", weight=ft.FontWeight.BOLD))
                
                for i, p in enumerate(paths):
                    file_name = os.path.basename(p)
                    file_dir = os.path.dirname(p)
                    _, ext = os.path.splitext(file_name)
                    
                    thumbnail_image = None
                    if ext.lower() in image_extensions:
                        thumbnail_base64 = await asyncio.get_event_loop().run_in_executor(None, self._get_image_thumbnail_base64, p)
                        if thumbnail_base64:
                            thumbnail_image = ft.Image(src_base64=thumbnail_base64, width=50, height=50, fit=ft.ImageFit.CONTAIN)

                    # El primer archivo de cada grupo se considera el "original", no se marca para eliminar por defecto
                    cb = ft.Checkbox(label=f"{file_name} ({file_dir})", value=(i != 0), data=p)
                    
                    if thumbnail_image:
                        # Add image and checkbox in a Row
                        self.duplicate_files_list.controls.append(
                            ft.Row([thumbnail_image, cb], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                        )
                    else:
                        # Just add checkbox if not an image or thumbnail failed
                        self.duplicate_files_list.controls.append(cb)
                        
                self.duplicate_files_list.controls.append(ft.Divider()) # Separador entre grupos
        
        if found_duplicates_count > 0:
            self.dup_status_text.value = f"Escaneo completado. Se encontraron {found_duplicates_count} duplicados."
            self.delete_duplicates_button.disabled = False
        else:
            self.dup_status_text.value = "No se encontraron archivos duplicados."
            self.delete_duplicates_button.disabled = True
        
        self.dup_progress_bar.visible = False # Hide progress bar after completion
        self.page.update()

    async def _on_delete_duplicates_click(self, e: ft.ControlEvent):
        files_to_delete = []
        for control in self.duplicate_files_list.controls:
            # Check if the control is a Row containing a Checkbox, or directly a Checkbox
            if isinstance(control, ft.Row) and len(control.controls) > 1 and isinstance(control.controls[1], ft.Checkbox):
                cb = control.controls[1]
                if cb.value:
                    files_to_delete.append(cb.data)
            elif isinstance(control, ft.Checkbox) and control.value:
                files_to_delete.append(control.data) # `data` contendrá la ruta completa


        if not files_to_delete:
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione al menos un archivo para eliminar."), open=True)
            self.page.update()
            return
        
        confirm = await self.page.show_dialog_async(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmar Eliminación"),
                content=ft.Text(f"¿Está seguro de que desea eliminar {len(files_to_delete)} archivo(s) duplicado(s)? Esta acción es irreversible."),
                actions=[
                    ft.TextButton("Sí, Eliminar", on_click=lambda e: self.page.close_dialog(True)),
                    ft.TextButton("Cancelar", on_click=lambda e: self.page.close_dialog(False)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )
        if not confirm:
            self.page.update()
            return

        self.dup_status_text.value = "Eliminando duplicados..."
        self.delete_duplicates_button.disabled = True
        self.scan_duplicates_button.disabled = True
        self.page.update()

        deleted_count = 0
        for f_path in files_to_delete:
            try:
                os.remove(f_path)
                logging.info(f"Eliminado archivo duplicado: {f_path}")
                deleted_count += 1
            except OSError as ex:
                logging.error(f"Error al eliminar {f_path}: {ex}")
        
        self.dup_status_text.value = f"Eliminación completada. Se eliminaron {deleted_count} archivos."
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Se eliminaron {deleted_count} duplicados."), open=True)
        await self._on_scan_duplicates_click(None) # Vuelve a escanear la carpeta para actualizar la lista
        self.delete_duplicates_button.disabled = False
        self.scan_duplicates_button.disabled = False
        self.page.update()

    # --- Métodos y Controladores para Redimensionar Imágenes ---
    async def _on_resize_images_click(self, e: ft.ControlEvent):
        input_dir = self.resize_input_dir.value
        output_dir = self.resize_output_dir.value
        
        if not input_dir or not os.path.isdir(input_dir):
            self.resize_status_text.value = "Seleccione una carpeta de origen válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de origen de imágenes."), open=True)
            self.page.update()
            return
        if not output_dir or not os.path.isdir(output_dir):
            self.resize_status_text.value = "Seleccione una carpeta de destino válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de destino para las imágenes redimensionadas."), open=True)
            self.page.update()
            return
        
        width = self.resize_width_input.value
        height = self.resize_height_input.value
        percentage = self.resize_percentage_input.value

        if not ((width and height) or percentage):
            self.resize_status_text.value = "Ingrese ancho y alto, O un porcentaje."
            self.page.snack_bar = ft.SnackBar(ft.Text("Debe especificar las dimensiones (ancho/alto) o un porcentaje de redimensionado."), open=True)
            self.page.update()
            return

        try:
            target_width = int(width) if width else None
            target_height = int(height) if height else None
            target_percentage = float(percentage) / 100 if percentage else None
        except ValueError:
            self.resize_status_text.value = "Ancho, alto o porcentaje inválidos."
            self.page.snack_bar = ft.SnackBar(ft.Text("Los valores de ancho, alto o porcentaje deben ser números válidos."), open=True)
            self.page.update()
            return

        self.resize_status_text.value = "Redimensionando imágenes..."
        self.perform_resize_button.disabled = True
        self.page.update()

        # Lógica para redimensionar imágenes usando Pillow
        supported_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
        resized_count = 0
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(supported_exts):
                filepath = os.path.join(input_dir, filename)
                try:
                    with Image.open(filepath) as img:
                        # Determinar nuevas dimensiones
                        if target_percentage:
                            new_width = int(img.width * target_percentage)
                            new_height = int(img.height * target_percentage)
                        else:
                            # Si solo uno de los valores está dado, mantener la proporción
                            if target_width and target_height:
                                new_width = target_width
                                new_height = target_height
                            elif target_width and not target_height:
                                new_width = target_width
                                new_height = int(img.height * (target_width / img.width))
                            elif target_height and not target_width:
                                new_height = target_height
                                new_width = int(img.width * (target_height / img.height))
                            else:
                                new_width = img.width
                                new_height = img.height

                        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                        output_filepath = os.path.join(output_dir, filename)
                        # Mantener formato original
                        save_format = img.format if img.format else "PNG"
                        resized_img.save(output_filepath, format=save_format)
                        logging.info(f"Redimensionado {filename} a {new_width}x{new_height}")
                        resized_count += 1
                except Exception as ex:
                    logging.error(f"Error al redimensionar {filename}: {ex}")
                
        self.resize_status_text.value = f"Redimensionado completado. Se procesaron {resized_count} imágenes."

        self.resize_status_text.value = "Redimensionado completado."
        self.page.snack_bar = ft.SnackBar(ft.Text("Imágenes redimensionadas exitosamente."), open=True)
        self.perform_resize_button.disabled = False
        self.page.update()

    # --- Métodos y Controladores para Convertir Formatos de Imagen ---
    async def _on_convert_images_click(self, e: ft.ControlEvent):
        input_dir = self.convert_input_dir.value
        output_dir = self.convert_output_dir.value
        target_format = self.target_format_dropdown.value

        if not input_dir or not os.path.isdir(input_dir):
            self.convert_status_text.value = "Seleccione una carpeta de origen válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de origen de imágenes."), open=True)
            self.page.update()
            return
        if not output_dir or not os.path.isdir(output_dir):
            self.convert_status_text.value = "Seleccione una carpeta de destino válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de destino para las imágenes convertidas."), open=True)
            self.page.update()
            return
        if not target_format:
            self.convert_status_text.value = "Seleccione un formato de destino."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione el formato al que desea convertir."), open=True)
            self.page.update()
            return

        self.convert_status_text.value = f"Convirtiendo imágenes a {target_format}..."
        self.perform_convert_button.disabled = True
        self.page.update()

        # Lógica para convertir imágenes usando Pillow
        supported_exts = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
        converted_count = 0
        for filename in os.listdir(input_dir):
            name, ext = os.path.splitext(filename)
            if ext.lower() in supported_exts:
                filepath = os.path.join(input_dir, filename)
                try:
                    with Image.open(filepath) as img:
                        # Convertir a modo compatible si es necesario
                        save_format = target_format.upper()
                        out_name = f"{name}.{target_format.lower()}"
                        output_filepath = os.path.join(output_dir, out_name)
                        # Para JPEG, convertir a RGB si es necesario
                        if save_format == "JPEG" and img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.save(output_filepath, format=save_format)
                        logging.info(f"Convertido {filename} a {target_format}")
                        converted_count += 1
                except Exception as ex:
                    logging.error(f"Error al convertir {filename}: {ex}")
        self.convert_status_text.value = f"Conversión completada. Se procesaron {converted_count} imágenes."

        self.convert_status_text.value = "Conversión completada."
        self.page.snack_bar = ft.SnackBar(ft.Text("Imágenes convertidas exitosamente."), open=True)
        self.perform_convert_button.disabled = False
        self.page.update()

    # --- Métodos y Controladores para Extraer Audio de Videos ---
    def _on_pick_video_for_audio_result(self, e: ft.FilePickerResultEvent):
        """
        Manejador para la selección de un archivo de video (no un directorio).
        """
        if e.files and e.files[0].path:
            self.extract_video_input.value = e.files[0].path
            logging.info(f"Video seleccionado para audio: {e.files[0].path}")
        else:
            logging.info("Selección de video para audio cancelada o sin archivos.")
            self.page.snack_bar = ft.SnackBar(ft.Text("Selección de video cancelada."), open=True) # Added feedback
        self.page.update()

    async def _on_extract_audio_click(self, e: ft.ControlEvent):
        video_path = self.extract_video_input.value

        if not video_path or not os.path.isfile(video_path):
            self.extract_audio_status_text.value = "Seleccione un archivo de video válido."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione un archivo de video."), open=True)
            self.page.update()
            return
        
        output_dir = self.extract_output_dir.value
        if not output_dir or not os.path.isdir(output_dir):
            self.extract_audio_status_text.value = "Seleccione una carpeta de destino válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de destino para el audio."), open=True)
            self.page.update()
            return

        self.extract_audio_status_text.value = "Extrayendo audio..."
        self.perform_audio_extract_button.disabled = True
        self.page.update()

        # Lógica para extraer audio usando moviepy
        try:
            clip = VideoFileClip(video_path)
            audio = clip.audio
            if audio is None:
                self.extract_audio_status_text.value = "El video no contiene pista de audio."
                self.page.snack_bar = ft.SnackBar(ft.Text("El video no tiene audio para extraer."), open=True)
                logging.warning(f"El video {video_path} no tiene pista de audio.")
            else:
                audio_filename = os.path.splitext(os.path.basename(video_path))[0] + ".mp3"
                output_audio_path = os.path.join(output_dir, audio_filename)
                audio.write_audiofile(output_audio_path)
                audio.close()
                self.extract_audio_status_text.value = f"Audio extraído a {output_audio_path}"
                self.page.snack_bar = ft.SnackBar(ft.Text("Audio extraído exitosamente."), open=True)
                logging.info(f"Audio extraído de {video_path} a {output_audio_path}")
            clip.close()
        except Exception as ex:
            self.extract_audio_status_text.value = f"Error al extraer audio: {ex}"
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error al extraer audio: {ex}"), open=True)
            logging.error(f"Error al extraer audio de {video_path}: {ex}")

        self.extract_audio_status_text.value = "Extracción de audio completada."
        self.perform_audio_extract_button.disabled = False
        self.page.update()

    # --- Métodos y Controladores para Fusionar PDFs ---
    def _on_pick_pdfs_to_merge_result(self, e: ft.FilePickerResultEvent):
        """
        Manejador para la selección de múltiples archivos PDF (no un directorio).
        """
        if e.files:
            for f in e.files:
                if f.path and f.path.lower().endswith(".pdf") and f.path not in self.selected_files_for_merge:
                    self.selected_files_for_merge.append(f.path)
                    self.pdf_list_view.controls.append(ft.Text(f"• {os.path.basename(f.path)}", data=f.path))
            self.page.update()
            logging.info(f"PDFs seleccionados para fusionar: {self.selected_files_for_merge}")
        else:
            logging.info("Selección de PDFs cancelada o sin archivos.")
            self.page.snack_bar = ft.SnackBar(ft.Text("Selección de PDFs cancelada."), open=True) # Added feedback
        self.page.update()

    def _on_clear_pdf_list_click(self, e: ft.ControlEvent):
        self.selected_files_for_merge.clear()
        self.pdf_list_view.controls.clear()
        self.page.update()
        logging.info("Lista de PDFs a fusionar limpiada.")

    async def _on_merge_pdfs_click(self, e: ft.ControlEvent):
        if not self.selected_files_for_merge:
            self.merge_pdf_status_text.value = "Añada al menos un PDF para fusionar."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, añada archivos PDF para fusionar."), open=True)
            self.page.update()
            return
        
        output_dir = self.merge_pdf_output_dir.value
        if not output_dir or not os.path.isdir(output_dir):
            self.merge_pdf_status_text.value = "Seleccione una carpeta de destino válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de destino para el PDF fusionado."), open=True)
            self.page.update()
            return
            
        output_filename = self.merged_pdf_name_input.value.strip()
        if not output_filename:
            self.merge_pdf_status_text.value = "Ingrese un nombre para el PDF resultante."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, ingrese un nombre para el archivo PDF resultante."), open=True)
            self.page.update()
            return

        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"

        output_path = os.path.join(output_dir, output_filename)

        self.merge_pdf_status_text.value = "Fusionando PDFs..."
        self.perform_merge_pdf_button.disabled = True
        self.page.update()

        # Aquí iría la lógica para fusionar PDFs usando pypdf
        # Ejemplo:
        # from pypdf import PdfWriter, PdfReader
        # try:
        #     writer = PdfWriter()
        #     for pdf_file in self.selected_files_for_merge:
        #         reader = PdfReader(pdf_file)
        #         for page in reader.pages:
        #             writer.add_page(page)
        #     
        #     with open(output_path, "wb") as f:
        #         writer.write(f)
        #     self.merge_pdf_status_text.value = f"PDFs fusionados exitosamente en {output_path}"
        #     self.page.snack_bar = ft.SnackBar(ft.Text("PDFs fusionados exitosamente."), open=True)
        #     logging.info(f"PDFs fusionados en: {output_path}")
        #     self._on_clear_pdf_list_click(None) # Limpiar lista después de fusionar
        # except Exception as ex:
        #     self.merge_pdf_status_text.value = f"Error al fusionar PDFs: {ex}"
        #     self.page.snack_bar = ft.SnackBar(ft.Text(f"Error al fusionar PDFs: {ex}"), open=True)
        #     logging.error(f"Error al fusionar PDFs: {ex}")

        self.merge_pdf_status_text.value = "Fusión de PDFs completada."
        self.perform_merge_pdf_button.disabled = False
        self.page.update()

    # --- Métodos y Controladores para Renombrar Archivos ---
    async def _on_preview_rename_click(self, e: ft.ControlEvent):
        src_dir = self.rename_dir_input.value
        if not src_dir or not os.path.isdir(src_dir):
            self.rename_status_text.value = "Seleccione una carpeta de origen válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta para previsualizar el renombrado."), open=True)
            self.page.update()
            return
        
        self.rename_preview_list.controls.clear()
        self.rename_status_text.value = "Generando previsualización..."
        self.page.update()

        prefix = self.rename_prefix_input.value
        suffix = self.rename_suffix_input.value
        search_text = self.rename_search_input.value
        replace_text = self.rename_replace_input.value
        add_numbering = self.rename_numbering_checkbox.value
        
        try:
            start_num = int(self.rename_start_num_input.value) if self.rename_start_num_input.value else 1
            padding = int(self.rename_padding_input.value) if self.rename_padding_input.value else 0
        except ValueError:
            self.rename_status_text.value = "Número de inicio o relleno inválido."
            self.page.snack_bar = ft.SnackBar(ft.Text("El número de inicio o el relleno deben ser números enteros."), open=True)
            self.page.update()
            return
            
        files_in_dir = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
        
        preview_count = 0
        for i, original_name in enumerate(files_in_dir):
            base_name, ext = os.path.splitext(original_name)
            new_base_name = base_name

            # Búsqueda y reemplazo
            if search_text and replace_text is not None:
                new_base_name = new_base_name.replace(search_text, replace_text)
            
            # Prefijo
            new_base_name = prefix + new_base_name

            # Sufijo
            new_base_name = new_base_name + suffix

            # Numeración
            if add_numbering:
                num_str = str(start_num + i).zfill(padding)
                new_base_name = f"{new_base_name}_{num_str}" # Puedes ajustar el formato aquí

            new_full_name = f"{new_base_name}{ext}"
            
            self.rename_preview_list.controls.append(ft.Text(f"'{original_name}' -> '{new_full_name}'"))
            preview_count += 1
            if preview_count > 50: # Limitar la previsualización para rendimiento
                self.rename_preview_list.controls.append(ft.Text("... (más archivos no mostrados en la previsualización)"))
                break
        
        if not files_in_dir:
            self.rename_status_text.value = "No hay archivos en la carpeta seleccionada."
        else:
            self.rename_status_text.value = "Previsualización generada."
        self.page.update()

    async def _on_rename_files_click(self, e: ft.ControlEvent):
        src_dir = self.rename_dir_input.value
        if not src_dir or not os.path.isdir(src_dir):
            self.rename_status_text.value = "Seleccione una carpeta de origen válida."
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta para renombrar."), open=True)
            self.page.update()
            return

        confirm = await self.page.show_dialog_async(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmar Renombrado"),
                content=ft.Text("¿Está seguro de que desea renombrar los archivos? Esta acción puede ser irreversible."),
                actions=[
                    ft.TextButton("Sí, Renombrar", on_click=lambda e: self.page.close_dialog(True)),
                    ft.TextButton("Cancelar", on_click=lambda e: self.page.close_dialog(False)),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )
        if not confirm:
            self.page.update()
            return

        self.rename_status_text.value = "Renombrando archivos..."
        self.perform_rename_button.disabled = True
        self.preview_rename_button.disabled = True
        self.page.update()

        prefix = self.rename_prefix_input.value
        suffix = self.rename_suffix_input.value
        search_text = self.rename_search_input.value
        replace_text = self.rename_replace_input.value
        add_numbering = self.rename_numbering_checkbox.value
        
        try:
            start_num = int(self.rename_start_num_input.value) if self.rename_start_num_input.value else 1
            padding = int(self.rename_padding_input.value) if self.rename_padding_input.value else 0
        except ValueError:
            self.rename_status_text.value = "Número de inicio o relleno inválido."
            self.page.snack_bar = ft.SnackBar(ft.Text("El número de inicio o el relleno deben ser números enteros."), open=True)
            self.page.update()
            self.perform_rename_button.disabled = False
            self.preview_rename_button.disabled = False
            return
        
        files_to_rename = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
        renamed_count = 0

        for i, original_name in enumerate(files_to_rename):
            original_path = os.path.join(src_dir, original_name)
            base_name, ext = os.path.splitext(original_name)
            new_base_name = base_name

            # Aplicar transformaciones de renombrado (lógica similar a la previsualización)
            if search_text and replace_text is not None:
                new_base_name = new_base_name.replace(search_text, replace_text)
            
            new_base_name = prefix + new_base_name

            new_base_name = new_base_name + suffix

            if add_numbering:
                num_str = str(start_num + i).zfill(padding)
                new_base_name = f"{new_base_name}_{num_str}"
            
            new_full_name = f"{new_base_name}{ext}"
            new_path = os.path.join(src_dir, new_full_name)

            try:
                if original_path != new_path: # Evitar renombrar si el nombre es idéntico
                    os.rename(original_path, new_path)
                    logging.info(f"Renombrado '{original_name}' a '{new_full_name}'")
                    renamed_count += 1
            except OSError as ex:
                logging.error(f"Error al renombrar {original_name} a {new_full_name}: {ex}")
                self.rename_status_text.value = f"Error al renombrar {original_name}: {ex}"
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error al renombrar: {ex}"), open=True)
                break # Detener si hay un error grave

        self.rename_status_text.value = f"Renombrado completado. Se renombraron {renamed_count} archivos."
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Se renombraron {renamed_count} archivos."), open=True)
        self.perform_rename_button.disabled = False
        self.preview_rename_button.disabled = False
        # Vuelve a generar la previsualización para mostrar el estado actual del directorio
        await self._on_preview_rename_click(None) 
        self.page.update()

def main(page: ft.Page):
    """Función principal para ejecutar la aplicación Flet."""
    FileManagerApp(page)

if __name__ == "__main__":
    os.makedirs('./assets', exist_ok=True)
    ft.app(target=main)