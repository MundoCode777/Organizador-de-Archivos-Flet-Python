import os
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import shutil

#Libre de peso solo una funcion para poder verificar si ffmpeg esta instalado

logger = logging.getLogger(__name__)

# Formatos de audio soportados
FORMATOS_AUDIO_SOPORTADOS = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']

def verificar_ffmpeg() -> bool:
    """Verifica si FFmpeg está disponible de múltiples formas."""
    print("Verificando FFmpeg...")
    
    # Método 1: Verificar con shutil.which
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        print(f"FFmpeg encontrado en: {ffmpeg_path}")
        return True
    
    # Método 2: Buscar en rutas comunes de Windows
    rutas_comunes = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        os.path.expanduser("~\\AppData\\Local\\ffmpeg\\bin\\ffmpeg.exe"),
        "ffmpeg.exe"
    ]
    
    for ruta in rutas_comunes:
        if os.path.exists(ruta):
            print(f"FFmpeg encontrado en: {ruta}")
            return True
    
    # Método 3: Intentar ejecutar directamente
    try:
        resultado = subprocess.run(['ffmpeg', '-version'], 
                                 capture_output=True, text=True, timeout=10,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        if resultado.returncode == 0:
            print("FFmpeg ejecutable desde terminal")
            return True
    except Exception as e:
        print(f"Error ejecutando ffmpeg: {e}")
    
    print("FFmpeg no encontrado")
    print("Soluciones posibles:")
    print("   1. Reinicia tu terminal/IDE")
    print("   2. Agrega FFmpeg al PATH del sistema")
    print("   3. Descarga FFmpeg portable")
    
    return False

def obtener_comando_ffmpeg():
    """Obtiene el comando correcto para FFmpeg."""
    # Buscar FFmpeg en diferentes ubicaciones
    comandos_posibles = [
        'ffmpeg',
        'ffmpeg.exe',
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
    ]
    
    for comando in comandos_posibles:
        try:
            resultado = subprocess.run([comando, '-version'], 
                                     capture_output=True, timeout=5,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if resultado.returncode == 0:
                return comando
        except:
            continue
    
    return 'ffmpeg'  # Fallback

def es_archivo_video_simple(ruta_archivo: str) -> bool:
    """
    Detecta videos por extensión y tamaño (método de respaldo).
    """
    try:
        # Extensiones de video comunes
        extensiones_video = {
            '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', 
            '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.vob', '.f4v',
            '.mpg', '.mpeg', '.m2v', '.divx', '.xvid'
        }
        
        extension = Path(ruta_archivo).suffix.lower()
        tamaño_mb = os.path.getsize(ruta_archivo) / (1024 * 1024)
        
        # Si tiene extensión de video
        if extension in extensiones_video:
            return True
        
        # Si no tiene extensión pero es grande y contiene "video" en el nombre
        if extension == '' and tamaño_mb > 10:
            nombre = os.path.basename(ruta_archivo).lower()
            if 'video' in nombre or tamaño_mb > 100:  # Archivos grandes sin extensión
                return True
        
        return False
        
    except Exception:
        return False

def obtener_todos_archivos_multimedia(directorio: str) -> List[str]:
    """
    Encuentra archivos multimedia con múltiples métodos.
    """
    videos_encontrados = []
    
    print(f"\nBUSCANDO VIDEOS EN: {directorio}")
    
    try:
        # Verificar directorio
        if not os.path.exists(directorio):
            print(f"ERROR: Directorio no existe: {directorio}")
            return []
        
        # Obtener archivos
        archivos = os.listdir(directorio)
        print(f"Total de archivos: {len(archivos)}")
        
        # Verificar FFmpeg
        ffmpeg_disponible = verificar_ffmpeg()
        comando_ffmpeg = obtener_comando_ffmpeg()
        
        for archivo in archivos:
            ruta_completa = os.path.join(directorio, archivo)
            
            if os.path.isfile(ruta_completa):
                tamaño_mb = os.path.getsize(ruta_completa) / (1024 * 1024)
                extension = Path(archivo).suffix.lower()
                
                print(f"\nANALIZANDO: {archivo}")
                print(f"   Extension: {extension if extension else 'Sin extension'}")
                print(f"   Tamaño: {tamaño_mb:.1f} MB")
                
                es_video = False
                
                # Método 1: Detección simple por extensión/tamaño
                if es_archivo_video_simple(ruta_completa):
                    print("   DETECTADO como video (metodo simple)")
                    es_video = True
                
                # Método 2: Verificar con FFmpeg si está disponible
                elif ffmpeg_disponible:
                    try:
                        print("   Verificando con FFmpeg...")
                        comando = [
                            comando_ffmpeg, '-i', ruta_completa, '-t', '1', '-f', 'null', '-'
                        ]
                        
                        resultado = subprocess.run(comando, capture_output=True, text=True, 
                                                 timeout=30,
                                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                        
                        # Si FFmpeg puede procesar el archivo, es multimedia
                        if 'Video:' in resultado.stderr or 'Audio:' in resultado.stderr:
                            print("   CONFIRMADO como video (FFmpeg)")
                            es_video = True
                        else:
                            print("   No es video segun FFmpeg")
                    
                    except Exception as e:
                        print(f"   Error con FFmpeg: {e}")
                        # Fallback al método simple
                        if es_archivo_video_simple(ruta_completa):
                            print("   DETECTADO como video (metodo simple - fallback)")
                            es_video = True
                
                if es_video:
                    videos_encontrados.append(ruta_completa)
                else:
                    print("   No es video")
        
        print(f"\nRESULTADO: {len(videos_encontrados)} videos encontrados")
        
        if videos_encontrados:
            print("Videos detectados:")
            for video in videos_encontrados:
                print(f"   - {os.path.basename(video)}")
        else:
            print("NO SE ENCONTRARON VIDEOS")
            print("Verificar:")
            print("   - Que los archivos sean videos validos")
            print("   - FFmpeg este instalado correctamente")
        
        return videos_encontrados
        
    except Exception as e:
        print(f"ERROR: {e}")
        return []

def obtener_archivos_video(directorio: str) -> List[str]:
    """Alias para compatibilidad."""
    return obtener_todos_archivos_multimedia(directorio)

def extraer_audio_individual(ruta_video: str, ruta_audio: str, formato_audio: str = 'mp3', 
                           calidad: str = '192k') -> bool:
    """
    Extrae audio usando FFmpeg con manejo robusto.
    """
    try:
        print(f"\nEXTRAYENDO AUDIO:")
        print(f"Video: {os.path.basename(ruta_video)}")
        print(f"Audio: {os.path.basename(ruta_audio)}")
        print(f"Formato: {formato_audio}")
        
        # Obtener comando FFmpeg
        comando_ffmpeg = obtener_comando_ffmpeg()
        
        # Construir comando
        comando = [
            comando_ffmpeg,
            '-i', ruta_video,           # Archivo de entrada
            '-vn',                      # Sin video
            '-acodec', 'libmp3lame',    # Codec de audio (por defecto MP3)
            '-ab', calidad,             # Bitrate
            '-y',                       # Sobrescribir archivo de salida
            ruta_audio                  # Archivo de salida
        ]
        
        # Ajustar según formato
        if formato_audio == 'wav':
            comando[comando.index('-acodec') + 1] = 'pcm_s16le'
            # Remover bitrate para WAV
            if '-ab' in comando:
                idx = comando.index('-ab')
                comando.pop(idx)  # Remover -ab
                comando.pop(idx)  # Remover valor
        elif formato_audio == 'flac':
            comando[comando.index('-acodec') + 1] = 'flac'
        elif formato_audio == 'aac':
            comando[comando.index('-acodec') + 1] = 'aac'
        
        print("Ejecutando FFmpeg...")
        
        # Ejecutar comando
        resultado = subprocess.run(comando, capture_output=True, text=True, 
                                 timeout=300,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        
        if resultado.returncode == 0:
            # Verificar archivo creado
            if os.path.exists(ruta_audio) and os.path.getsize(ruta_audio) > 0:
                tamaño_audio = os.path.getsize(ruta_audio) / (1024 * 1024)
                print(f"EXITO: Audio extraido ({tamaño_audio:.2f} MB)")
                return True
            else:
                print("ERROR: Archivo no se creo")
                return False
        else:
            print(f"ERROR FFmpeg:")
            print(f"   Stderr: {resultado.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print("ERROR: Timeout - archivo muy grande")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def extraer_audio_videos(directorio_origen: str, directorio_destino: str, 
                        formato_audio: str = 'mp3', calidad: str = '192k',
                        callback_progreso: Optional[callable] = None) -> int:
    """
    Extrae audio con manejo robusto de errores.
    """
    print(f"\nINICIANDO EXTRACCION")
    print(f"Origen: {directorio_origen}")
    print(f"Destino: {directorio_destino}")
    print(f"Formato: {formato_audio}")
    
    # Buscar videos (sin requerir FFmpeg estrictamente)
    archivos_video = obtener_todos_archivos_multimedia(directorio_origen)
    
    if not archivos_video:
        print("NO SE ENCONTRARON VIDEOS")
        return 0
    
    # Crear directorio destino
    try:
        os.makedirs(directorio_destino, exist_ok=True)
        print(f"Directorio destino listo")
    except Exception as e:
        print(f"Error creando directorio: {e}")
        return 0
    
    # Procesar videos
    extraidos_exitosamente = 0
    total_archivos = len(archivos_video)
    
    print(f"\nPROCESANDO {total_archivos} VIDEO(S)")
    
    for indice, ruta_video in enumerate(archivos_video, 1):
        try:
            print(f"\n[{indice}/{total_archivos}] Procesando:")
            
            # Generar nombre de audio
            nombre_base = Path(ruta_video).stem
            if not nombre_base:
                nombre_base = f"audio_{indice}"
            
            nombre_audio = f"{nombre_base}.{formato_audio}"
            ruta_audio = os.path.join(directorio_destino, nombre_audio)
            
            # Extraer audio
            if extraer_audio_individual(ruta_video, ruta_audio, formato_audio, calidad):
                extraidos_exitosamente += 1
                print(f"COMPLETADO: {nombre_audio}")
            else:
                print(f"FALLO: {os.path.basename(ruta_video)}")
            
            # Callback progreso
            if callback_progreso:
                callback_progreso(indice, total_archivos)
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\nEXTRACCION COMPLETADA")
    print(f"Exitosos: {extraidos_exitosamente}")
    print(f"Fallidos: {total_archivos - extraidos_exitosamente}")
    
    return extraidos_exitosamente

def obtener_info_video(ruta_video: str) -> dict:
    """Obtiene información básica."""
    try:
        return {
            'duracion': 0,
            'tamaño': os.path.getsize(ruta_video) if os.path.exists(ruta_video) else 0,
            'bitrate': 0,
            'codec_audio': 'Desconocido',
            'canales': 0,
            'sample_rate': 0
        }
    except:
        return {}

def validar_parametros_extraccion(directorio_origen: str, directorio_destino: str, 
                                 formato_audio: str) -> Tuple[bool, str]:
    """Valida parámetros básicos."""
    if not directorio_origen or not os.path.isdir(directorio_origen):
        return False, "Directorio de origen inválido"
    
    if not directorio_destino:
        return False, "Directorio de destino requerido"
    
    if formato_audio not in FORMATOS_AUDIO_SOPORTADOS:
        return False, f"Formato no soportado: {formato_audio}"
    
    return True, ""

def convertir_audio_con_pydub(ruta_entrada: str, ruta_salida: str, formato_salida: str) -> bool:
    """Función de compatibilidad."""
    return False