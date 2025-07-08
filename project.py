import os
import shutil
import logging
from datetime import datetime
import flet as ft
import matplotlib.pyplot as plt
import numpy as np
from darkdetect import isDark
import io
import base64

# Assuming config.py exists and contains DEFAULT_FOLDERS
from config import DEFAULT_FOLDERS

# --- Configuration and Setup ---
LOG_FILE = './assets/file_manager.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

plt.switch_backend('Agg')

DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 760

# Base64 para una imagen PNG transparente de 1x1 píxel
TRANSPARENT_PIXEL_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

class FileManagerApp:
    """
    A Flet application for organizing files into categorized folders.
    It allows users to select a source directory, define custom categories,
    and then organize files based on their extensions.
    The application also provides a summary and a visual plot of file sizes by type.
    """
    def __init__(self, page: ft.Page):
        self.page = page
        self._configure_page()

        self._file_picker = ft.FilePicker(on_result=self._on_pick_result)
        self.page.overlay.append(self._file_picker)

        self._init_ui_components()
        self._add_ui_to_page()
        self.page.update()

        self.custom_folders: list[tuple[str, list[str]]] = []

    def _configure_page(self):
        """Configures the Flet page properties."""
        self.page.title = "Gestor de Archivos"
        self.page.window_width = DEFAULT_WINDOW_WIDTH
        self.page.window_height = DEFAULT_WINDOW_HEIGHT
        self.page.window_min_width = DEFAULT_WINDOW_WIDTH
        self.page.window_min_height = DEFAULT_WINDOW_HEIGHT
        self.page.window_resizable = True
        self.page.window_icon = "./assets/icon1.png"
        self.page.scroll = ft.ScrollMode.ALWAYS

    def _init_ui_components(self):
        """Initializes all UI components for the application."""
        self.src_dir_input = ft.TextField(label="Carpeta de origen", width=300, read_only=True)
        self.pick_src_button = ft.ElevatedButton(
            text="Seleccionar carpeta",
            on_click=self._on_pick_src_click,
            color="blue"
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
            color="green"
        )
        self.custom_list = ft.Column()

        self.organize_button = ft.ElevatedButton(
            text="Organizar archivos",
            on_click=self._on_organize_click,
            color="purple"
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

        # **MODIFICADO AQUÍ:** Aumento el tamaño del control ft.Image
        self.plot_image = ft.Image(
            width=800, # Antes 600
            height=600, # Antes 400
            src_base64=TRANSPARENT_PIXEL_BASE64,
            fit=ft.ImageFit.CONTAIN
        )

    def _add_ui_to_page(self):
        """Adds the initialized UI components to the Flet page layout."""
        self.page.add(
            ft.Row(
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
                        expand=2 # Podrías aumentar esto a 3 o 4 si el gráfico es mucho más grande y quieres que la columna lo ocupe más
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
        )

    def _get_configured_folders(self) -> dict[str, list[str]]:
        """
        Retrieves the mapping of folder names to their associated file extensions.
        Includes both default and custom-defined folders.
        """
        folders = {
            self.music_input.value: DEFAULT_FOLDERS['Music'],
            self.photos_input.value: DEFAULT_FOLDERS['Photos'],
            self.docs_input.value: DEFAULT_FOLDERS['Docs'],
            self.videos_input.value: DEFAULT_FOLDERS['Videos']
        }
        for folder_name, folder_exts in self.custom_folders:
            folders[folder_name] = folder_exts
        folders["Otros"] = []
        return folders

    def _create_destination_directories(self, base_dir: str, folders: dict):
        """
        Creates destination directories if they don't already exist.
        Args:
            base_dir (str): The root directory where folders will be created.
            folders (dict): A dictionary of folder names and their extensions.
        """
        for folder in folders.keys():
            folder_path = os.path.join(base_dir, folder)
            try:
                os.makedirs(folder_path, exist_ok=True)
                logging.info(f"Created directory: {folder_path}")
            except OSError as e:
                logging.error(f"Error creating directory {folder_path}: {e}")

    def _move_single_file(self, file_name: str, src_dir: str, folders: dict):
        """
        Moves a single file to its designated category folder.
        If no category matches, it moves the file to the "Otros" folder.
        Args:
            file_name (str): The name of the file to move.
            src_dir (str): The source directory of the file.
            folders (dict): The dictionary mapping folder names to extensions.
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
            logging.info(f"Moved '{file_name}' to '{destination_folder}'")
        except shutil.Error as e:
            logging.error(f"Error moving file {file_name}: {e}")
        except FileNotFoundError:
             logging.warning(f"File not found, skipping: {file_name}")

    def _organize_files_in_directory(self, src_dir: str, folders: dict):
        """
        Orchestrates the file organization process for a given directory.
        Args:
            src_dir (str): The source directory to organize.
            folders (dict): The dictionary mapping folder names to extensions.
        """
        self._create_destination_directories(src_dir, folders)
        files_to_process = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
        total_files = len(files_to_process)
        logging.info(f"Starting organization of {total_files} files in {src_dir}")

        for i, file in enumerate(files_to_process):
            self._move_single_file(file, src_dir, folders)
            self.progress_bar.value = (i + 1) / total_files
            self.page.update()
        logging.info("File organization completed.")

    def _summarize_directory_files(self, src_dir: str) -> dict[str, float]:
        """
        Calculates the total size of files grouped by their extensions within a directory.
        Args:
            src_dir (str): The directory to summarize.
        Returns:
            dict: A dictionary where keys are file extensions and values are their total sizes in MB.
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
                        logging.warning(f"Could not get size for {file_path}: {e}")
        return file_sizes

    def _format_summary_text(self, file_sizes: dict[str, float]) -> str:
        """
        Formats the file size summary into a human-readable string.
        Args:
            file_sizes (dict): Dictionary of file extensions and their sizes.
        Returns:
            str: Formatted summary string.
        """
        if not file_sizes:
            return "No hay archivos para resumir o el directorio está vacío."

        sorted_files = sorted(file_sizes.items(), key=lambda x: x[1], reverse=True)
        return "\n".join([f"{ext.upper()[1:]}: {size:.1f} MB" for ext, size in sorted_files])

    def _generate_plot_summary(self, file_sizes: dict[str, float], dark_mode: bool) -> str:
        """
        Generates a pie chart of file sizes by type and returns it as a base64 string.
        No image file is saved to disk.
        Args:
            file_sizes (dict): Dictionary of file extensions and their sizes.
            dark_mode (bool): True if dark mode is active, False otherwise.
        Returns:
            str: The base64 encoded string of the plot image (PNG format),
                 o la imagen transparente 1x1 si no hay datos.
        """
        if not file_sizes:
            logging.info("No file sizes to plot. Returning empty base64 string.")
            return TRANSPARENT_PIXEL_BASE64

        extensions = list(file_sizes.keys())
        sizes = list(file_sizes.values())

        colors = plt.cm.get_cmap('tab20c', len(extensions))(np.arange(len(extensions)))

        # **MODIFICADO AQUÍ:** Aumento el figsize para Matplotlib
        fig, ax = plt.subplots(figsize=(8, 6), facecolor='black' if dark_mode else 'white') # Antes sin figsize

        text_color = 'white' if dark_mode else 'black'
        title_color = 'white' if dark_mode else 'black'

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
        logging.info("Generated plot as base64 string.")
        return img_base64

    def _on_pick_src_click(self, e: ft.ControlEvent):
        """Event handler for the 'Select Folder' button click."""
        self._file_picker.get_directory_path()

    def _on_add_custom_click(self, e: ft.ControlEvent):
        """Event handler for adding a custom folder and extensions."""
        folder_name = self.custom_folder_input.value.strip()
        extensions_raw = self.custom_exts_input.value.strip()

        if not folder_name or not extensions_raw:
            logging.warning("Custom folder name or extensions cannot be empty.")
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, ingrese un nombre de carpeta y extensiones."), open=True)
            self.page.update()
            return

        exts = [ext.strip().lower() for ext in extensions_raw.split(',') if ext.strip()]
        if not exts:
            logging.warning("No valid extensions provided for custom folder.")
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
        logging.info(f"Added custom folder: '{folder_name}' with extensions: {exts}")

    def _on_organize_click(self, e: ft.ControlEvent):
        """Event handler for the 'Organize Files' button click."""
        src_dir = self.src_dir_input.value

        if not src_dir or not os.path.isdir(src_dir):
            logging.warning(f"Invalid source directory selected: {src_dir}")
            self.page.snack_bar = ft.SnackBar(ft.Text("Por favor, seleccione una carpeta de origen válida."), open=True)
            self.page.update()
            return

        try:
            self.organize_button.disabled = True
            self.progress_bar.value = 0
            self.progress_bar.visible = True
            self.summary_input.value = "Organizando archivos..."
            self.plot_image.src_base64 = TRANSPARENT_PIXEL_BASE64 # Mantenemos la imagen transparente aquí
            self.page.update()

            folders_config = self._get_configured_folders()
            self._organize_files_in_directory(src_dir, folders_config)

            file_sizes_summary = self._summarize_directory_files(src_dir)
            self.summary_input.value = self._format_summary_text(file_sizes_summary)

            plot_base64_string = self._generate_plot_summary(file_sizes_summary, isDark())
            
            self.plot_image.src_base64 = plot_base64_string

            logging.info("File organization process completed successfully.")

        except Exception as ex:
            logging.exception(f"An error occurred during file organization: {ex}")
            self.summary_input.value = f"Error: {ex}"
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Ocurrió un error: {ex}"), open=True)
        finally:
            self.progress_bar.visible = False
            self.organize_button.disabled = False
            self.page.update()

    def _on_pick_result(self, e: ft.FilePickerResultEvent):
        """Event handler for the file picker result."""
        if e.path and os.path.isdir(e.path):
            self.src_dir_input.value = e.path
            logging.info(f"Source directory selected: {e.path}")
        elif e.path:
            logging.warning(f"Selected path is not a directory: {e.path}")
            self.page.snack_bar = ft.SnackBar(ft.Text("La ruta seleccionada no es una carpeta válida."), open=True)
        else:
            logging.info("File picking cancelled.")
        self.page.update()

def main(page: ft.Page):
    """Main function to run the Flet application."""
    FileManagerApp(page)

if __name__ == "__main__":
    os.makedirs('./assets', exist_ok=True)
    ft.app(target=main)