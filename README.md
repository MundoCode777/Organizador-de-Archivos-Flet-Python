# Administrador de Archivos Multi-herramienta

Este es un administrador de archivos basado en Flet que proporciona varias utilidades para organizar, limpiar y procesar tus archivos de manera eficiente.

## Características

* **Organizador de Archivos:** Categoriza y mueve automáticamente tus archivos en carpetas predefinidas (Música, Fotos, Documentos, Videos) o personalizadas basadas en sus extensiones.
* **Eliminador de Duplicados:** Escanea un directorio en busca de archivos duplicados (basado en hash) y te permite previsualizarlos y eliminar los seleccionados.
* **Redimensionador de Imágenes:** Procesa imágenes por lotes desde una carpeta de origen, permitiéndote redimensionarlas a un ancho/alto específico o a un porcentaje del tamaño original.
* **Conversor de Imágenes:** Convierte lotes de imágenes a diferentes formatos (PNG, JPEG, GIF, BMP, WebP) manteniendo la calidad.
* **Renombrador de Archivos:** Renombra archivos en un directorio con prefijos, sufijos y numeración secuencial, con una función de previsualización.
* **Fusionador de PDFs:** Combina múltiples archivos PDF en un solo documento.

## Estructura del Proyecto

El proyecto está organizado en varios módulos para una mejor modularidad y mantenimiento:

.
├── project.py                # Archivo principal de la aplicación Flet
├── organizador_archivos.py   # Lógica para organizar archivos y generar resúmenes
├── buscador_duplicados.py    # Lógica para encontrar y eliminar archivos duplicados
├── procesador_imagenes.py    # Lógica para redimensionar y convertir imágenes
├── config.py                 # Configuraciones por defecto (extensiones de carpetas, rutas de logs)
└── assets/                   # Directorio para recursos de la aplicación (ej. logs)
└── file_manager.log      # Archivo de registro de la aplicación


## Requisitos

Asegúrate de tener Python 3.9 o superior instalado.

Para instalar las dependencias necesarias, ejecuta el siguiente comando:

```bash
pip install -r requirements.txt


Uso
Clona o descarga el repositorio.

Asegúrate de tener todas las dependencias instaladas (ver sección "Requisitos").

Ejecuta la aplicación principal:

python main.py

Cómo usar cada funcionalidad:
1. Organizar Archivos
Ruta de Origen: Selecciona la carpeta que deseas organizar.

Carpetas por Defecto: Puedes cambiar los nombres de las carpetas por defecto (Música, Fotos, Documentos, Videos).

Carpetas Personalizadas:

Ingresa un Nombre de Carpeta y Extensiones separadas por comas (ej. zip,rar,7z para una carpeta "Comprimidos").

Haz clic en "Añadir Personalizada".

Haz clic en "Organizar Archivos" para iniciar el proceso.

Se mostrará un resumen de los archivos organizados y un gráfico de distribución.

2. Eliminar Duplicados
Carpeta para Duplicados: Selecciona el directorio donde deseas buscar duplicados.

Haz clic en "Escanear Duplicados".

La aplicación listará los grupos de archivos duplicados. Marca las casillas de los archivos que deseas eliminar (el primero de cada grupo se considera el original y no está marcado por defecto).

Haz clic en "Eliminar Seleccionados" para borrarlos permanentemente.

3. Redimensionar Imágenes
Carpeta de Origen de Imágenes: Selecciona la carpeta que contiene las imágenes a redimensionar.

Carpeta de Destino para Imágenes: Selecciona la carpeta donde se guardarán las imágenes redimensionadas.

Opciones de Redimensionado: Ingresa un Ancho, Alto o Porcentaje para el redimensionamiento. Solo necesitas uno de ellos (ej. 800 en ancho, o 50 en porcentaje).

Haz clic en "Redimensionar Imágenes".

4. Renombrar Archivos
Carpeta a Renombrar: Selecciona el directorio con los archivos que deseas renombrar.

Prefijo / Sufijo: Opcionalmente, añade un prefijo o sufijo al nombre del archivo.

Inicio Numérico: Define el número de inicio para la secuencia numérica (ej. 1 para archivo_001.ext).

Haz clic en "Previsualizar Renombrado" para ver cómo se verán los nombres de los archivos antes de aplicar los cambios.

Haz clic en "Realizar Renombrado" para aplicar los cambios.

5. Fusionar PDFs
Seleccionar PDFs para Fusionar: Haz clic en este botón para abrir un explorador de archivos y seleccionar múltiples archivos PDF.

Nombre del PDF de Salida: Ingresa el nombre del archivo PDF combinado que se creará.

Haz clic en "Fusionar PDFs". El PDF resultante se guardará en el mismo directorio que el primer PDF seleccionado.

6. Convertir Imágenes
Carpeta de Origen de Imágenes: Selecciona la carpeta que contiene las imágenes a convertir.

Carpeta de Destino para Imágenes: Selecciona la carpeta donde se guardarán las imágenes convertidas.

Formato de Destino: Elige el formato al que deseas convertir las imágenes (ej. png, jpeg).

Haz clic en "Convertir Imágenes".

Registro de Actividades
La aplicación registra sus actividades en un archivo file_manager.log dentro de la carpeta assets/. Esto es útil para depurar problemas o revisar las operaciones realizadas.

Licencia
Este proyecto está bajo la licencia [SAVC16, MundoCode777].