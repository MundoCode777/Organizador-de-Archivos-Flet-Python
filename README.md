# 📁 Administrador de Archivos Multi-herramienta

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-UI-purple?style=for-the-badge&logo=flet&logoColor=white)](https://flet.dev/)

Este es un **Administrador de Archivos** completo desarrollado con **Flet**, diseñado para simplificar y automatizar diversas tareas de gestión de archivos en tu sistema. Desde la organización de tu librería multimedia hasta la limpieza de duplicados y el procesamiento de imágenes, esta herramienta centraliza varias utilidades esenciales en una interfaz de usuario intuitiva y moderna.

## ✨ Características Principales

El programa ofrece las siguientes funcionalidades, accesibles a través de pestañas dedicadas:

* **Organizador de Archivos:**
    * Clasifica automáticamente archivos en carpetas predefinidas (Música, Fotos, Documentos, Videos) o categorías personalizadas basadas en sus extensiones.
    * Genera un resumen textual y un gráfico visual de la distribución de archivos en el directorio procesado.
    * Ideal para mantener tu directorio de descargas o cualquier carpeta grande ordenada.

* **Eliminador de Duplicados:**
    * Escanea un directorio para encontrar archivos idénticos utilizando la verificación de hash.
    * Presenta una lista clara de duplicados, permitiéndote seleccionar cuáles deseas eliminar para liberar espacio en disco.

* **Redimensionador de Imágenes:**
    * Procesa lotes de imágenes, permitiendo redimensionarlas a dimensiones específicas (ancho/alto en píxeles) o a un porcentaje de su tamaño original.
    * Útil para optimizar imágenes para la web o para colecciones personales.

* **Conversor de Imágenes:**
    * Convierte colecciones completas de imágenes de un formato a otro (ej., JPG a PNG, PNG a WebP).
    * Soporta formatos comunes como PNG, JPEG, GIF, BMP y WebP.

* **Renombrador de Archivos:**
    * Renombra masivamente archivos en un directorio añadiendo prefijos, sufijos y una numeración secuencial.
    * Ofrece una función de previsualización para asegurar que los nuevos nombres son los deseados antes de aplicar los cambios.

* **Fusionador de PDFs:**
    * Combina varios archivos PDF en un único documento consolidado.
    * Perfecto para unir reportes, capítulos o cualquier conjunto de documentos PDF.

## 📂 Estructura del Proyecto

El proyecto está modularizado para una mejor organización y mantenimiento:

.

├── project.py                # Archivo principal de la aplicación Flet

├── organizador_archivos.py   # Lógica para organizar archivos y generar resúmenes

├── buscador_duplicados.py    # Lógica para encontrar y eliminar archivos duplicados

├── procesador_imagenes.py    # Lógica para redimensionar y convertir imágenes

├── config.py                 # Configuraciones por defecto (extensiones de carpetas, rutas de logs)

└── assets/                   # Directorio para recursos de la aplicación (ej. logs)

└── file_manager.log      # Archivo de registro de la aplicación


## 🚀 Uso
* 1.- Clona o descarga este repositorio en tu máquina local.

* 2.- Navega al directorio del proyecto en tu terminal.

* **3.- Ejecuta la aplicación principal:**

    * python main.py

* Una ventana de la aplicación de escritorio se abrirá, presentándote la interfaz con todas las funcionalidades.


## Guía Rápida de Funcionalidades:
* Organizar Archivos: Selecciona la "Ruta de Origen", define tus preferencias de carpetas (por defecto o personalizadas) y haz clic en "Organizar Archivos".

* Eliminar Duplicados: Elige la "Carpeta para Duplicados", "Escanear Duplicados", revisa la lista y selecciona los archivos a "Eliminar Seleccionados".

* Redimensionar Imágenes: Especifica "Carpeta de Origen" y "Carpeta de Destino", introduce las dimensiones o porcentaje deseado y "Redimensionar Imágenes".

* Renombrar Archivos: Selecciona la "Carpeta a Renombrar", configura prefijos/sufijos/inicio numérico, "Previsualizar Renombrado" y luego "Realizar Renombrado".

* Fusionar PDFs: Haz clic en "Seleccionar PDFs para Fusionar", elige tus archivos, ingresa un "Nombre del PDF de Salida" y "Fusionar PDFs".

* Convertir Imágenes: Elige "Carpeta de Origen" y "Carpeta de Destino", selecciona el "Formato de Destino" y haz clic en "Convertir Imágenes".


## Cómo usar cada funcionalidad:
* **1. Organizar Archivos**
    * Ruta de Origen: Selecciona la carpeta que deseas organizar.

    * Carpetas por Defecto: Puedes cambiar los nombres de las carpetas por defecto (Música, Fotos, Documentos, Videos).

    * Carpetas Personalizadas:

    * Ingresa un Nombre de Carpeta y Extensiones separadas por comas (ej. zip,rar,7z para una carpeta "Comprimidos").

    * Haz clic en "Añadir Personalizada".

    * Haz clic en "Organizar Archivos" para iniciar el proceso.

    * Se mostrará un resumen de los archivos organizados y un gráfico de distribución.

* **2. Eliminar Duplicados**
    * Carpeta para Duplicados: Selecciona el directorio donde deseas buscar duplicados.

    * Haz clic en "Escanear Duplicados".

    * La aplicación listará los grupos de archivos duplicados. Marca las casillas de los archivos que deseas eliminar (el primero de cada grupo se considera el original y no está marcado por defecto).

    * Haz clic en "Eliminar Seleccionados" para borrarlos permanentemente.

* **3. Redimensionar Imágenes**
    * Carpeta de Origen de Imágenes: Selecciona la carpeta que contiene las imágenes a redimensionar.

    * Carpeta de Destino para Imágenes: Selecciona la carpeta donde se guardarán las imágenes redimensionadas.

    * Opciones de Redimensionado: Ingresa un Ancho, Alto o Porcentaje para el redimensionamiento. Solo necesitas uno de ellos (ej. 800 en ancho, o 50 en porcentaje).

    * Haz clic en "Redimensionar Imágenes".

* **4. Renombrar Archivos**
    * Carpeta a Renombrar: Selecciona el directorio con los archivos que deseas renombrar.

    * Prefijo / Sufijo: Opcionalmente, añade un prefijo o sufijo al nombre del archivo.

    * Inicio Numérico: Define el número de inicio para la secuencia numérica (ej. 1 para archivo_001.ext).

    * Haz clic en "Previsualizar Renombrado" para ver cómo se verán los nombres de los archivos antes de aplicar los cambios.

    * Haz clic en "Realizar Renombrado" para aplicar los cambios.

* **5. Fusionar PDFs**
    * Seleccionar PDFs para Fusionar: Haz clic en este botón para abrir un explorador de archivos y seleccionar múltiples archivos PDF.

    * Nombre del PDF de Salida: Ingresa el nombre del archivo PDF combinado que se creará.

    * Haz clic en "Fusionar PDFs". El PDF resultante se guardará en el mismo directorio que el primer PDF seleccionado.

* **6. Convertir Imágenes**
    * Carpeta de Origen de Imágenes: Selecciona la carpeta que contiene las imágenes a convertir.

    * Carpeta de Destino para Imágenes: Selecciona la carpeta donde se guardarán las imágenes convertidas.

    * Formato de Destino: Elige el formato al que deseas convertir las imágenes (ej. png, jpeg).

    * Haz clic en "Convertir Imágenes".

## 📝 Registro de Actividades
Todas las operaciones importantes y errores son registrados en el archivo assets/file_manager.log. Esto es útil para la depuración y para mantener un registro de las acciones realizadas por la aplicación.

## 📄 Licencia
Este proyecto está distribuido bajo la licencia [SAVC16, MundoCode777].

## 🛠️ Requisitos e Instalación

Asegúrate de tener **Python 3.9 o superior** instalado en tu sistema.

Para instalar las bibliotecas necesarias, ejecuta el siguiente comando en tu terminal:

```bash
pip install -r requirements.txt