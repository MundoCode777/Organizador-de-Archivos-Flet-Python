import os
import shutil
import logging
from datetime import datetime
import flet as ft
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import hashlib
import asyncio
from PIL import Image # Todavía necesario para Image.LANCZOS u otras operaciones directas, o mover todas las referencias.

# Importar desde config.py
from config import DEFAULT_FOLDERS, LOG_FILE_PATH

# Importar las funciones de los módulos existentes
from organizador_archivos import (
    obtener_carpetas_configuradas,
    organizar_archivos_en_directorio,
    resumir_archivos_directorio,
    formatear_texto_resumen,
    generar_grafico_resumen,
)
from buscador_duplicados import (
    encontrar_archivos_duplicados,
    eliminar_archivos,
)
from procesador_imagenes import (
    redimensionar_imagenes,
    convertir_imagenes_formato
)

# --- Importar las funciones de los NUEVOS módulos ---
from renombrador_archivos import (
    previsualizar_renombrado_archivos,
    realizar_renombrado_masivo
)
from fusionador_pdfs import (
    fusionar_pdfs
)

# --- Configuración e Inicialización de Logs (centralizado aquí) ---
def configurar_logging():
    """Configura el sistema de logging para la aplicación."""
    # Asegúrate de que el directorio 'assets' existe para el log
    directorio_log = os.path.dirname(LOG_FILE_PATH)
    os.makedirs(directorio_log, exist_ok=True)
    
    logging.basicConfig(filename=LOG_FILE_PATH, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        encoding='utf-8')
    # Configurar un manejador para la consola también para ver logs en tiempo real
    manejador_consola = logging.StreamHandler()
    manejador_consola.setLevel(logging.INFO)
    manejador_consola.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    if not any(isinstance(handler, logging.StreamHandler) for handler in logging.root.handlers):
        logging.root.addHandler(manejador_consola)

configurar_logging()

logger = logging.getLogger(__name__)

plt.switch_backend('Agg')

ANCHO_VENTANA_POR_DEFECTO = 1280
ALTO_VENTANA_POR_DEFECTO = 760

class AplicacionGestorArchivos:
    """
    Una aplicación Flet para organizar archivos en carpetas categorizadas y ofrecer
    otras utilidades de gestión de archivos.
    """
    def __init__(self, pagina: ft.Page):
        self.pagina = pagina
        self._configurar_pagina()

        self._campo_texto_destino_actual: ft.TextField = None
        self._selector_archivos = ft.FilePicker(on_result=self._al_seleccionar_archivo_resultado)
        self.pagina.overlay.append(self._selector_archivos)

        self._inicializar_componentes_ui()
        self._anadir_ui_a_pagina()
        self.pagina.update()

        self.carpetas_personalizadas: list[tuple[str, list[str]]] = []
        self.archivos_seleccionados_para_fusion: list[str] = []
        self.archivos_seleccionados_para_renombrar: list[str] = [] # Almacena las rutas originales para renombrar
        self.mapa_archivos_duplicados: dict[str, list[str]] = {}

    def _configurar_pagina(self):
        self.pagina.title = "Administrador de Archivos"
        self.pagina.vertical_alignment = ft.CrossAxisAlignment.START
        self.pagina.window_width = ANCHO_VENTANA_POR_DEFECTO
        self.pagina.window_height = ALTO_VENTANA_POR_DEFECTO
        self.pagina.window_min_width = ANCHO_VENTANA_POR_DEFECTO
        self.pagina.window_min_height = ALTO_VENTANA_POR_DEFECTO
        self.pagina.padding = 20
        self.pagina.theme_mode = ft.ThemeMode.SYSTEM # Cambiado para seguir el tema del sistema

    def _inicializar_componentes_ui(self):
        """Inicializa todos los componentes de la interfaz de usuario."""
        # Componentes comunes
        self.entrada_ruta_origen = ft.TextField(
            label="Ruta de Origen",
            read_only=True,
            expand=True,
            on_focus=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_ruta_origen)
        )
        # Este botón ahora es específico para la ruta de origen principal
        self.boton_seleccionar_carpeta_origen_principal = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_ruta_origen)
        )
        self.barra_progreso_general = ft.ProgressBar(value=0, visible=False, width=400)
        
        self._inicializar_ui_organizacion()
        self._inicializar_ui_duplicados()
        self._inicializar_ui_redimensionar()
        self._inicializar_ui_renombrar()
        self._inicializar_ui_fusion_pdf()
        self._inicializar_ui_convertir_imagenes()

    def _inicializar_ui_organizacion(self):
        self.entrada_musica = ft.TextField(label="Carpeta Música", value="Música", width=150)
        self.entrada_fotos = ft.TextField(label="Carpeta Fotos", value="Fotos", width=150)
        self.entrada_documentos = ft.TextField(label="Carpeta Documentos", value="Documentos", width=150)
        self.entrada_videos = ft.TextField(label="Carpeta Videos", value="Videos", width=150)

        self.boton_organizar_archivos = ft.ElevatedButton(
            "Organizar Archivos",
            icon=ft.Icons.AUTO_AWESOME,
            on_click=self._al_hacer_click_organizar,
            width=200
        )
        self.area_texto_resumen = ft.TextField(
            label="Resumen de Archivos",
            multiline=True,
            read_only=True,
            min_lines=5,
            max_lines=10,
            expand=True
        )
        self.imagen_grafico_resumen = ft.Image(visible=False, width=300, height=300, fit=ft.ImageFit.CONTAIN)

        self.entrada_nombre_carpeta_personalizada = ft.TextField(label="Nombre de Carpeta", width=150)
        self.entrada_extensiones_personalizadas = ft.TextField(
            label="Extensiones (separadas por ,)",
            hint_text="ej: mp3,wav",
            width=250
        )
        self.boton_anadir_personalizada = ft.ElevatedButton(
            "Añadir Personalizada",
            icon=ft.Icons.ADD,
            on_click=self._al_hacer_click_anadir_personalizada
        )
        self.lista_carpetas_personalizadas_ui = ft.Column()

    def _inicializar_ui_duplicados(self):
        self.entrada_ruta_duplicados = ft.TextField(
            label="Carpeta para Duplicados",
            read_only=True,
            expand=True,
            on_focus=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_ruta_duplicados)
        )
        self.boton_seleccionar_carpeta_duplicados = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_ruta_duplicados)
        )
        self.boton_escanear_duplicados = ft.ElevatedButton(
            "Escanear Duplicados",
            icon=ft.Icons.SEARCH,
            on_click=self._al_hacer_click_escanear_duplicados
        )
        self.boton_eliminar_duplicados = ft.ElevatedButton(
            "Eliminar Seleccionados",
            icon=ft.Icons.DELETE_FOREVER,
            on_click=self._al_hacer_click_eliminar_duplicados,
            disabled=True
        )
        self.texto_estado_duplicados = ft.Text("Listo para escanear duplicados.")
        self.barra_progreso_duplicados = ft.ProgressBar(value=0, visible=False, width=400)
        self.lista_archivos_duplicados_ui = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    def _inicializar_ui_redimensionar(self):
        self.entrada_dir_redimensionar_origen = ft.TextField(
            label="Carpeta de Origen de Imágenes",
            read_only=True,
            expand=True,
            on_focus=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_redimensionar_origen)
        )
        self.boton_seleccionar_redimensionar_origen = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_redimensionar_origen)
        )
        self.entrada_dir_redimensionar_destino = ft.TextField(
            label="Carpeta de Destino para Imágenes",
            read_only=True,
            expand=True,
            on_focus=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_redimensionar_destino)
        )
        self.boton_seleccionar_redimensionar_destino = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_redimensionar_destino)
        )
        self.entrada_ancho_redimensionar = ft.TextField(label="Ancho (px)", keyboard_type=ft.KeyboardType.NUMBER, width=100)
        self.entrada_alto_redimensionar = ft.TextField(label="Alto (px)", keyboard_type=ft.KeyboardType.NUMBER, width=100)
        self.entrada_porcentaje_redimensionar = ft.TextField(label="Porcentaje (%)", keyboard_type=ft.KeyboardType.NUMBER, width=100)
        self.boton_redimensionar = ft.ElevatedButton(
            "Redimensionar Imágenes",
            icon=ft.Icons.ASPECT_RATIO,
            on_click=self._al_hacer_click_redimensionar
        )
        self.texto_estado_redimensionar = ft.Text("Listo para redimensionar imágenes.")

    def _inicializar_ui_renombrar(self):
        self.entrada_ruta_dir_renombrar = ft.TextField(
            label="Carpeta a Renombrar",
            read_only=True,
            expand=True,
            on_focus=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_ruta_dir_renombrar)
        )
        self.boton_seleccionar_renombrar = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_ruta_dir_renombrar)
        )
        self.entrada_prefijo_renombrar = ft.TextField(label="Prefijo", width=150)
        self.entrada_sufijo_renombrar = ft.TextField(label="Sufijo", width=150)
        self.entrada_inicio_numerico_renombrar = ft.TextField(label="Inicio Numérico", keyboard_type=ft.KeyboardType.NUMBER, value="1", width=150)
        self.boton_previsualizar_renombrar = ft.ElevatedButton(
            "Previsualizar Renombrado",
            icon=ft.Icons.PREVIEW,
            on_click=self._al_hacer_click_previsualizar_renombrar
        )
        self.boton_realizar_renombrado = ft.ElevatedButton(
            "Realizar Renombrado",
            icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
            on_click=self._al_hacer_click_realizar_renombrado,
            disabled=True
        )
        self.texto_estado_renombrar = ft.Text("Listo para renombrar archivos.")
        self.lista_previsualizacion_renombrar_ui = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    def _inicializar_ui_fusion_pdf(self):
        self.boton_seleccionar_pdfs = ft.ElevatedButton(
            "Seleccionar PDFs para Fusionar",
            icon=ft.Icons.ATTACH_FILE,
            on_click=self._al_hacer_click_seleccionar_pdfs_fusion
        )
        self.lista_pdfs_seleccionados_ui = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True)
        self.entrada_nombre_pdf_salida = ft.TextField(label="Nombre del PDF de Salida", expand=True)
        self.boton_fusionar_pdfs = ft.ElevatedButton(
            "Fusionar PDFs",
            icon=ft.Icons.MERGE_TYPE,
            on_click=self._al_hacer_click_fusionar_pdfs,
            disabled=True
        )
        self.texto_estado_fusion_pdf = ft.Text("Listo para fusionar PDFs.")

    def _inicializar_ui_convertir_imagenes(self):
        self.entrada_dir_convertir_origen = ft.TextField(
            label="Carpeta de Origen de Imágenes",
            read_only=True,
            expand=True,
            on_focus=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_convertir_origen)
        )
        self.boton_seleccionar_convertir_origen = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_convertir_origen)
        )
        self.entrada_dir_convertir_destino = ft.TextField(
            label="Carpeta de Destino para Imágenes",
            read_only=True,
            expand=True,
            on_focus=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_convertir_destino)
        )
        self.boton_seleccionar_convertir_destino = ft.ElevatedButton(
            "Seleccionar Carpeta",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=lambda e: self._abrir_dialogo_seleccion_carpeta(self.entrada_dir_convertir_destino)
        )
        self.dropdown_formato_destino = ft.Dropdown(
            label="Formato de Destino",
            options=[
                ft.dropdown.Option("png"),
                ft.dropdown.Option("jpeg"),
                ft.dropdown.Option("gif"),
                ft.dropdown.Option("bmp"),
                ft.dropdown.Option("webp"),
            ],
            width=150
        )
        self.boton_realizar_conversion = ft.ElevatedButton(
            "Convertir Imágenes",
            icon=ft.Icons.TRANSFORM,
            on_click=self._al_hacer_click_convertir_imagenes
        )
        self.texto_estado_convertir = ft.Text("Listo para convertir imágenes.")
    
    def _anadir_ui_a_pagina(self):
        """Añade los controles UI a la página de Flet."""
        self.pagina.add(
            ft.AppBar(title=ft.Text("Administrador de Archivos"), center_title=True),
            ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    ft.Tab(
                        text="Organizar Archivos",
                        icon=ft.Icons.FOLDER_OPEN,
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [self.entrada_ruta_origen, self.boton_seleccionar_carpeta_origen_principal],
                                        alignment=ft.MainAxisAlignment.START,
                                    ),
                                    ft.Divider(),
                                    ft.Text("Carpetas por Defecto:"),
                                    ft.Row([self.entrada_musica, self.entrada_fotos, self.entrada_documentos, self.entrada_videos]),
                                    ft.Divider(),
                                    ft.Text("Carpetas Personalizadas:"),
                                    ft.Row(
                                        [self.entrada_nombre_carpeta_personalizada, self.entrada_extensiones_personalizadas, self.boton_anadir_personalizada]
                                    ),
                                    ft.Column(
                                        controls=[
                                            ft.Text("Carpetas Añadidas:", weight=ft.FontWeight.BOLD),
                                            self.lista_carpetas_personalizadas_ui
                                        ]
                                    ),
                                    ft.Divider(),
                                    self.boton_organizar_archivos,
                                    self.barra_progreso_general,
                                    ft.Row([self.area_texto_resumen, self.imagen_grafico_resumen]),
                                ],
                                scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True
                            ),
                            padding=10
                        ),
                    ),
                    ft.Tab(
                        text="Eliminar Duplicados",
                        icon=ft.Icons.COPY_ALL,
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [self.entrada_ruta_duplicados, self.boton_seleccionar_carpeta_duplicados],
                                        alignment=ft.MainAxisAlignment.START,
                                    ),
                                    ft.Row(
                                        [self.boton_escanear_duplicados, self.boton_eliminar_duplicados]
                                    ),
                                    self.texto_estado_duplicados,
                                    self.barra_progreso_duplicados,
                                    ft.Container(
                                        content=self.lista_archivos_duplicados_ui,
                                        expand=True,
                                        border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
                                        border_radius=5,
                                        padding=10
                                    )
                                ],
                                scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True
                            ),
                            padding=10
                        )
                    ),
                    ft.Tab(
                        text="Redimensionar Imágenes",
                        icon=ft.Icons.PHOTO_SIZE_SELECT_LARGE,
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row([self.entrada_dir_redimensionar_origen, self.boton_seleccionar_redimensionar_origen]),
                                    ft.Row([self.entrada_dir_redimensionar_destino, self.boton_seleccionar_redimensionar_destino]),
                                    ft.Divider(),
                                    ft.Text("Opciones de Redimensionado (solo una es necesaria):"),
                                    ft.Row([self.entrada_ancho_redimensionar, self.entrada_alto_redimensionar, self.entrada_porcentaje_redimensionar]),
                                    self.boton_redimensionar,
                                    self.texto_estado_redimensionar,
                                ],
                                scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True
                            ),
                            padding=10
                        )
                    ),
                    ft.Tab(
                        text="Renombrar Archivos",
                        icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE,
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row([self.entrada_ruta_dir_renombrar, self.boton_seleccionar_renombrar]),
                                    ft.Divider(),
                                    ft.Row([self.entrada_prefijo_renombrar, self.entrada_sufijo_renombrar, self.entrada_inicio_numerico_renombrar]),
                                    ft.Row([self.boton_previsualizar_renombrar, self.boton_realizar_renombrado]),
                                    self.texto_estado_renombrar,
                                    ft.Container(
                                        content=self.lista_previsualizacion_renombrar_ui,
                                        expand=True,
                                        border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
                                        border_radius=5,
                                        padding=10
                                    )
                                ],
                                scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True
                            ),
                            padding=10
                        )
                    ),
                    ft.Tab(
                        text="Fusionar PDFs",
                        icon=ft.Icons.PICTURE_AS_PDF,
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    self.boton_seleccionar_pdfs,
                                    ft.Container(
                                        content=self.lista_pdfs_seleccionados_ui,
                                        expand=True,
                                        border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
                                        border_radius=5,
                                        padding=10
                                    ),
                                    ft.Row([self.entrada_nombre_pdf_salida, self.boton_fusionar_pdfs]),
                                    self.texto_estado_fusion_pdf,
                                ],
                                scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True
                            ),
                            padding=10
                        )
                    ),
                    ft.Tab(
                        text="Convertir Imágenes",
                        icon=ft.Icons.TRANSFORM,
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row([self.entrada_dir_convertir_origen, self.boton_seleccionar_convertir_origen]),
                                    ft.Row([self.entrada_dir_convertir_destino, self.boton_seleccionar_convertir_destino]),
                                    ft.Divider(),
                                    ft.Row([self.dropdown_formato_destino, self.boton_realizar_conversion]),
                                    self.texto_estado_convertir,
                                ],
                                scroll=ft.ScrollMode.ADAPTIVE,
                                expand=True
                            ),
                            padding=10
                        )
                    )
                ],
                expand=1,
            ),
            ft.Container( # Pie de página
                content=ft.Text(
                    "Desarrolladores: [SAVC16-S.A.V.C16, MundoCode777-Andres.dev] | Autore: [Steven Alexander Villamar Cevallos]",
                    size=10,
                    color=ft.Colors.GREY_500,
                    text_align=ft.TextAlign.CENTER
                ),
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=10)
            )
        )

    def _abrir_dialogo_seleccion_carpeta(self, campo_texto_objetivo: ft.TextField):
        self._campo_texto_destino_actual = campo_texto_objetivo
        self._selector_archivos.get_directory_path(dialog_title="Seleccionar Carpeta")

    def _al_seleccionar_archivo_resultado(self, e: ft.FilePickerResultEvent):
        if e.path:
            if self._campo_texto_destino_actual:
                self._campo_texto_destino_actual.value = e.path
                self.pagina.update()
            else:
                logger.warning("No hay TextField objetivo para la ruta seleccionada.")
        elif e.files:
            self.archivos_seleccionados_para_fusion = [file.path for file in e.files]
            self.lista_pdfs_seleccionados_ui.controls.clear()
            if self.archivos_seleccionados_para_fusion:
                for ruta_archivo in self.archivos_seleccionados_para_fusion:
                    self.lista_pdfs_seleccionados_ui.controls.append(ft.Text(os.path.basename(ruta_archivo)))
                self.boton_fusionar_pdfs.disabled = False
            else:
                self.boton_fusionar_pdfs.disabled = True
            self.pagina.update()

    async def _al_hacer_click_organizar(self, e: ft.ControlEvent):
        directorio_origen = self.entrada_ruta_origen.value
        if not directorio_origen or not os.path.isdir(directorio_origen):
            logger.warning(f"Directorio de origen inválido: {directorio_origen}")
            self._mostrar_snackbar("Por favor, seleccione una carpeta de origen válida.")
            return
        
        try:
            self.boton_organizar_archivos.disabled = True
            self.barra_progreso_general.value = 0
            self.barra_progreso_general.visible = True
            self.area_texto_resumen.value = "Organizando archivos..."
            self.pagina.update()

            entradas_carpetas_por_defecto = {
                'Music': self.entrada_musica.value,
                'Photos': self.entrada_fotos.value,
                'Docs': self.entrada_documentos.value,
                'Videos': self.entrada_videos.value,
            }
            carpetas_configuradas = obtener_carpetas_configuradas(self.carpetas_personalizadas, entradas_carpetas_por_defecto)

            await asyncio.to_thread(
                organizar_archivos_en_directorio,
                directorio_origen,
                carpetas_configuradas,
                lambda actual, total: self._actualizar_progreso_organizacion(actual, total)
            )

            tamanios_archivos = resumir_archivos_directorio(directorio_origen)
            texto_resumen = formatear_texto_resumen(tamanios_archivos)
            base64_grafico = generar_grafico_resumen(tamanios_archivos)

            self.area_texto_resumen.value = texto_resumen
            self.imagen_grafico_resumen.src_base64 = base64_grafico
            self.imagen_grafico_resumen.visible = bool(base64_grafico)
            self._mostrar_snackbar("Organización completada.")
            logger.info("Organización de archivos completada exitosamente.")

        except Exception as ex:
            logger.error(f"Error durante la organización de archivos: {ex}")
            self.area_texto_resumen.value = f"Error: {ex}"
            self._mostrar_snackbar(f"Error al organizar archivos: {ex}")
        finally:
            self.barra_progreso_general.visible = False
            self.boton_organizar_archivos.disabled = False
            self.pagina.update()

    def _al_hacer_click_anadir_personalizada(self, e: ft.ControlEvent):
        nombre_carpeta = self.entrada_nombre_carpeta_personalizada.value.strip()
        extensiones_str = self.entrada_extensiones_personalizadas.value.strip()
        if not nombre_carpeta or not extensiones_str:
            self._mostrar_snackbar("Por favor, ingrese el nombre de la carpeta y las extensiones.")
            return

        extensiones = [ext.strip().lower() for ext in extensiones_str.split(',') if ext.strip()]
        if not extensiones:
            self._mostrar_snackbar("Por favor, ingrese extensiones válidas separadas por comas.")
            return

        self.carpetas_personalizadas.append((nombre_carpeta, extensiones))
        self.lista_carpetas_personalizadas_ui.controls.append(
            ft.Text(f"• {nombre_carpeta}: {', '.join(extensiones)}")
        )
        self.entrada_nombre_carpeta_personalizada.value = ""
        self.entrada_extensiones_personalizadas.value = ""
        self.pagina.update()
        self._mostrar_snackbar(f"Carpeta personalizada '{nombre_carpeta}' añadida.")
        logger.info(f"Carpeta personalizada añadida: {nombre_carpeta} con extensiones {extensiones}")

    async def _al_hacer_click_escanear_duplicados(self, e: ft.ControlEvent):
        directorio_escaneo = self.entrada_ruta_duplicados.value
        if not directorio_escaneo or not os.path.isdir(directorio_escaneo):
            self.texto_estado_duplicados.value = "Por favor, seleccione una carpeta válida para escanear."
            self._mostrar_snackbar("Seleccione una carpeta válida para duplicados.")
            return

        self.boton_escanear_duplicados.disabled = True
        self.boton_eliminar_duplicados.disabled = True
        self.barra_progreso_duplicados.value = 0
        self.barra_progreso_duplicados.visible = True
        self.texto_estado_duplicados.value = "Escaneando duplicados..."
        self.lista_archivos_duplicados_ui.controls.clear()
        self.pagina.update()

        try:
            self.mapa_archivos_duplicados = await encontrar_archivos_duplicados(
                directorio_escaneo,
                lambda actual, total: self._actualizar_progreso_escaneo_duplicados(actual, total)
            )
            
            if self.mapa_archivos_duplicados:
                self.texto_estado_duplicados.value = f"Se encontraron {len(self.mapa_archivos_duplicados)} grupos de archivos duplicados."
                for valor_hash, rutas in self.mapa_archivos_duplicados.items():
                    self._anadir_entrada_duplicado_ui(rutas)
                self.boton_eliminar_duplicados.disabled = False
            else:
                self.texto_estado_duplicados.value = "No se encontraron archivos duplicados."
            self._mostrar_snackbar("Escaneo de duplicados completado.")

        except Exception as ex:
            logger.error(f"Error al escanear duplicados: {ex}")
            self.texto_estado_duplicados.value = f"Error al escanear duplicados: {ex}"
            self._mostrar_snackbar(f"Error al escanear duplicados: {ex}")
        finally:
            self.barra_progreso_duplicados.visible = False
            self.boton_escanear_duplicados.disabled = False
            self.pagina.update()

    async def _al_hacer_click_eliminar_duplicados(self, e: ft.ControlEvent):
        archivos_a_eliminar = []
        for contenedor_item in self.lista_archivos_duplicados_ui.controls:
            if isinstance(contenedor_item, ft.Container) and contenedor_item.content:
                for control_in_column in contenedor_item.content.controls:
                    if isinstance(control_in_column, ft.Row):
                        for inner_control in control_in_column.controls:
                            if isinstance(inner_control, ft.Checkbox):
                                checkbox = inner_control
                                if checkbox.value:
                                    ruta_archivo = checkbox.label
                                    if ruta_archivo:
                                        archivos_a_eliminar.append(ruta_archivo)
                                break
        
        if not archivos_a_eliminar:
            self.texto_estado_duplicados.value = "No se seleccionaron archivos para eliminar."
            self._mostrar_snackbar("Seleccione archivos para eliminar.")
            return
        
        self.boton_eliminar_duplicados.disabled = True
        self.boton_escanear_duplicados.disabled = True
        self.texto_estado_duplicados.value = f"Eliminando {len(archivos_a_eliminar)} archivos..."
        self.pagina.update()

        try:
            contador_eliminados = await asyncio.to_thread(eliminar_archivos, archivos_a_eliminar)
            self.texto_estado_duplicados.value = f"Se eliminaron {contador_eliminados} archivos."
            self._mostrar_snackbar(f"Se eliminaron {contador_eliminados} archivos.")
            
            await self._al_hacer_click_escanear_duplicados(None)

        except Exception as ex:
            logger.error(f"Error al eliminar duplicados: {ex}")
            self.texto_estado_duplicados.value = f"Error al eliminar: {ex}"
            self._mostrar_snackbar(f"Error al eliminar: {ex}")
        finally:
            self.boton_eliminar_duplicados.disabled = False
            self.boton_escanear_duplicados.disabled = False
            self.pagina.update()

    def _anadir_entrada_duplicado_ui(self, rutas_archivos: list[str]):
        original_archivo = rutas_archivos[0]
        candidatos_duplicados = rutas_archivos[1:]

        controles_grupo = [
            ft.Text(f"Original: {os.path.basename(original_archivo)}", weight=ft.FontWeight.BOLD),
            ft.Text(f"Ruta: {original_archivo}", size=10, color=ft.Colors.WHITE70),
            ft.Divider()
        ]

        for ruta_dup in candidatos_duplicados:
            controles_grupo.append(
                ft.Row([
                    ft.Checkbox(label=ruta_dup, value=True, expand=True),
                    ft.Text(f"({os.path.basename(ruta_dup)})", size=10, color=ft.Colors.WHITE54)
                ])
            )
        
        self.lista_archivos_duplicados_ui.controls.append(
            ft.Container(
                content=ft.Column(controles_grupo, spacing=5),
                padding=10,
                margin=ft.margin.symmetric(vertical=5),
                border=ft.border.all(1, ft.Colors.BLUE_GREY_800),
                border_radius=5
            )
        )
        self.pagina.update()

    # --- Métodos para Redimensionar Imágenes ---
    async def _al_hacer_click_redimensionar(self, e: ft.ControlEvent):
        directorio_entrada = self.entrada_dir_redimensionar_origen.value
        directorio_salida = self.entrada_dir_redimensionar_destino.value
        
        if not directorio_entrada or not os.path.isdir(directorio_entrada):
            self._mostrar_snackbar("Seleccione una carpeta de origen de imágenes válida.")
            return
        if not directorio_salida:
            self._mostrar_snackbar("Seleccione una carpeta de destino válida para imágenes.")
            return
        
        try:
            ancho_objetivo = int(self.entrada_ancho_redimensionar.value) if self.entrada_ancho_redimensionar.value else None
            alto_objetivo = int(self.entrada_alto_redimensionar.value) if self.entrada_alto_redimensionar.value else None
            porcentaje_objetivo = float(self.entrada_porcentaje_redimensionar.value) / 100 if self.entrada_porcentaje_redimensionar.value else None

            if not (ancho_objetivo or alto_objetivo or porcentaje_objetivo):
                self._mostrar_snackbar("Ingrese un ancho, alto o porcentaje para redimensionar.")
                return

            self.boton_redimensionar.disabled = True
            self.texto_estado_redimensionar.value = "Redimensionando imágenes..."
            self.pagina.update()

            contador_redimensionados = await asyncio.to_thread(
                redimensionar_imagenes, 
                directorio_entrada, 
                directorio_salida, 
                ancho_objetivo, 
                alto_objetivo, 
                porcentaje_objetivo
            )
            
            self.texto_estado_redimensionar.value = f"Redimensionado completado. Se procesaron {contador_redimensionados} imágenes."
            self._mostrar_snackbar(f"Se redimensionaron {contador_redimensionados} imágenes.")
            logger.info("Redimensionamiento de imágenes completado.")

        except ValueError:
            self._mostrar_snackbar("Por favor, ingrese valores numéricos válidos para las dimensiones/porcentaje.")
            self.texto_estado_redimensionar.value = "Error: Entrada numérica inválida."
        except Exception as ex:
            logger.error(f"Error general al redimensionar imágenes: {ex}")
            self.texto_estado_redimensionar.value = f"Error: {ex}"
            self._mostrar_snackbar(f"Error al redimensionar imágenes: {ex}")
        finally:
            self.boton_redimensionar.disabled = False
            self.pagina.update()

    # --- Métodos para Renombrar Archivos (actualizados para usar el nuevo módulo) ---
    async def _al_hacer_click_previsualizar_renombrar(self, e: ft.ControlEvent):
        directorio_origen = self.entrada_ruta_dir_renombrar.value
        if not directorio_origen or not os.path.isdir(directorio_origen):
            self.texto_estado_renombrar.value = "Por favor, seleccione una carpeta válida."
            self._mostrar_snackbar("Seleccione una carpeta válida para renombrar.")
            return

        prefijo = self.entrada_prefijo_renombrar.value.strip()
        sufijo = self.entrada_sufijo_renombrar.value.strip()
        try:
            inicio_numerico = int(self.entrada_inicio_numerico_renombrar.value)
        except ValueError:
            self.texto_estado_renombrar.value = "El 'Inicio Numérico' debe ser un número válido."
            self._mostrar_snackbar("Inicio numérico inválido.")
            return

        self.lista_previsualizacion_renombrar_ui.controls.clear()
        
        previsualizaciones, rutas_originales = await asyncio.to_thread(
            previsualizar_renombrado_archivos, directorio_origen, prefijo, sufijo, inicio_numerico
        )

        self.archivos_seleccionados_para_renombrar = rutas_originales # Guardar las rutas originales

        if not previsualizaciones:
            self.texto_estado_renombrar.value = "No hay archivos en el directorio seleccionado o hubo un error."
            self._mostrar_snackbar("No hay archivos para previsualizar.")
            self.boton_realizar_renombrado.disabled = True
            self.pagina.update()
            return

        for original_name, new_name in previsualizaciones:
            self.lista_previsualizacion_renombrar_ui.controls.append(
                ft.Text(f"{original_name}  ->  {new_name}")
            )
        
        self.texto_estado_renombrar.value = f"Previsualización generada para {len(previsualizaciones)} archivos."
        self.boton_realizar_renombrado.disabled = False
        self.pagina.update()
        logger.info(f"Previsualización de renombrado generada para {len(previsualizaciones)} archivos.")

    async def _al_hacer_click_realizar_renombrado(self, e: ft.ControlEvent):
        directorio_origen = self.entrada_ruta_dir_renombrar.value
        if not directorio_origen or not os.path.isdir(directorio_origen) or not self.archivos_seleccionados_para_renombrar:
            self._mostrar_snackbar("Primero, genere una previsualización válida.")
            return
        
        prefijo = self.entrada_prefijo_renombrar.value.strip()
        sufijo = self.entrada_sufijo_renombrar.value.strip()
        try:
            inicio_numerico = int(self.entrada_inicio_numerico_renombrar.value)
        except ValueError:
            self._mostrar_snackbar("El 'Inicio Numérico' debe ser un número válido.")
            return

        self.boton_realizar_renombrado.disabled = True
        self.boton_previsualizar_renombrar.disabled = True
        self.texto_estado_renombrar.value = "Renombrando archivos..."
        self.pagina.update()

        archivos_a_renombrar_list = []
        for i, ruta_original in enumerate(self.archivos_seleccionados_para_renombrar):
            nombre_original = os.path.basename(ruta_original)
            nombre_base, ext = os.path.splitext(nombre_original)
            num_str = str(inicio_numerico + i)
            
            partes_nuevo_nombre_base = [parte for parte in [prefijo, nombre_base, num_str, sufijo] if parte]
            nuevo_nombre_base = "_".join(partes_nuevo_nombre_base)
            nuevo_nombre_completo = f"{nuevo_nombre_base}{ext}"
            
            archivos_a_renombrar_list.append((ruta_original, os.path.join(directorio_origen, nuevo_nombre_completo)))

        try:
            contador_renombrados = await asyncio.to_thread(realizar_renombrado_masivo, archivos_a_renombrar_list)
            
            self.texto_estado_renombrar.value = f"Renombrado completado. Se renombraron {contador_renombrados} archivos."
            self._mostrar_snackbar(f"Se renombraron {contador_renombrados} archivos.")
            logger.info("Renombrado de archivos completado.")

        except Exception as ex:
            logger.error(f"Error durante el renombrado de archivos: {ex}")
            self.texto_estado_renombrar.value = f"Error al renombrar: {ex}"
            self._mostrar_snackbar(f"Error al renombrar: {ex}")
        finally:
            self.boton_realizar_renombrado.disabled = False
            self.boton_previsualizar_renombrar.disabled = False
            # Volver a generar la previsualización para reflejar los cambios
            await self._al_hacer_click_previsualizar_renombrar(None) 
            self.pagina.update()

    # --- Métodos para Fusionar PDFs (actualizados para usar el nuevo módulo) ---
    def _al_hacer_click_seleccionar_pdfs_fusion(self, e: ft.ControlEvent):
        self._selector_archivos.pick_files(
            allow_multiple=True,
            allowed_extensions=["pdf"],
            dialog_title="Seleccionar archivos PDF para fusionar"
        )

    async def _al_hacer_click_fusionar_pdfs(self, e: ft.ControlEvent):
        if not self.archivos_seleccionados_para_fusion:
            self._mostrar_snackbar("No se han seleccionado archivos PDF para fusionar.")
            return

        nombre_archivo_salida = self.entrada_nombre_pdf_salida.value.strip()
        if not nombre_archivo_salida:
            self._mostrar_snackbar("Ingrese un nombre para el PDF de salida.")
            return
        if not nombre_archivo_salida.lower().endswith(".pdf"):
            nombre_archivo_salida += ".pdf"

        if self.archivos_seleccionados_para_fusion:
            directorio_salida = os.path.dirname(self.archivos_seleccionados_para_fusion[0])
        else:
            directorio_salida = os.getcwd()

        ruta_salida = os.path.join(directorio_salida, nombre_archivo_salida)

        self.boton_fusionar_pdfs.disabled = True
        self.texto_estado_fusion_pdf.value = "Fusionando PDFs..."
        self.pagina.update()

        try:
            exito = await asyncio.to_thread(fusionar_pdfs, self.archivos_seleccionados_para_fusion, ruta_salida)

            if exito:
                self.texto_estado_fusion_pdf.value = f"PDFs fusionados exitosamente en: {ruta_salida}"
                self._mostrar_snackbar("PDFs fusionados correctamente.")
                self.archivos_seleccionados_para_fusion.clear()
                self.lista_pdfs_seleccionados_ui.controls.clear()
                self.entrada_nombre_pdf_salida.value = ""
            else:
                self.texto_estado_fusion_pdf.value = "Error al fusionar PDFs."
                self._mostrar_snackbar("Error al fusionar PDFs.")

        except Exception as ex:
            logger.error(f"Error al fusionar PDFs: {ex}")
            self.texto_estado_fusion_pdf.value = f"Error al fusionar PDFs: {ex}"
            self._mostrar_snackbar(f"Error al fusionar PDFs: {ex}")
        finally:
            self.boton_fusionar_pdfs.disabled = False
            self.pagina.update()

    # --- Métodos y Controladores para Convertir Formatos de Imagen ---
    async def _al_hacer_click_convertir_imagenes(self, e: ft.ControlEvent):
        input_dir = self.entrada_dir_convertir_origen.value
        output_dir = self.entrada_dir_convertir_destino.value
        target_format = self.dropdown_formato_destino.value

        if not input_dir or not os.path.isdir(input_dir):
            self.texto_estado_convertir.value = "Seleccione una carpeta de origen válida."
            self._mostrar_snackbar("Por favor, seleccione una carpeta de origen de imágenes.")
            return
        if not output_dir:
            self._mostrar_snackbar("Seleccione una carpeta de destino válida para las imágenes convertidas.")
            return
        if not target_format:
            self.texto_estado_convertir.value = "Seleccione un formato de destino."
            self._mostrar_snackbar("Por favor, seleccione el formato al que desea convertir.")
            return
        
        try:
            os.makedirs(output_dir, exist_ok=True)

            self.texto_estado_convertir.value = f"Convirtiendo imágenes a {target_format}..."
            self.boton_realizar_conversion.disabled = True
            self.pagina.update()

            converted_count = await asyncio.to_thread(
                convertir_imagenes_formato,
                input_dir,
                output_dir,
                target_format
            )

            self.texto_estado_convertir.value = f"Conversión completada. Se procesaron {converted_count} imágenes."
            self._mostrar_snackbar(f"Imágenes convertidas exitosamente: {converted_count} archivos.")
            logger.info(f"Conversión de imágenes completada. {converted_count} archivos convertidos a {target_format}.")

        except Exception as ex:
            logger.error(f"Error al convertir imágenes: {ex}")
            self.texto_estado_convertir.value = f"Error al convertir imágenes: {ex}"
            self._mostrar_snackbar(f"Error al convertir imágenes: {ex}")
        finally:
            self.boton_realizar_conversion.disabled = False
            self.pagina.update()

    # --- Métodos de Actualización de UI y Utilidades ---
    def _actualizar_progreso_organizacion(self, actual, total):
        """Actualiza la barra de progreso de organización de archivos."""
        self.barra_progreso_general.value = actual / total
        self.pagina.update()

    def _actualizar_progreso_escaneo_duplicados(self, actual, total):
        """Actualiza la barra de progreso de escaneo de duplicados."""
        self.barra_progreso_duplicados.value = actual / total
        self.pagina.update()

    def _mostrar_snackbar(self, mensaje: str):
        """Muestra un SnackBar en la página con el mensaje dado."""
        self.pagina.snack_bar = ft.SnackBar(
            ft.Text(mensaje),
            open=True,
            show_close_icon=True,
            action="Ok"
        )
        self.pagina.update()

def main(pagina: ft.Page):
    """Función principal para ejecutar la aplicación Flet."""
    AplicacionGestorArchivos(pagina)

if __name__ == "__main__":
    ft.app(target=main)