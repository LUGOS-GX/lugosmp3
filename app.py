from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
import os
import subprocess
import sys
import yt_dlp
import threading
import time
from urllib.parse import quote

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB max file size
#MALDITA SEA NO TOCAR NADA, Todo ESTÁ FUNCIONANDOOOOOOOOO NO TOCAAAAR NADAAAAAAA.
# Crear carpeta de descargas si no existe
if not os.path.exists(app.config['DOWNLOAD_FOLDER']):
    os.makedirs(app.config['DOWNLOAD_FOLDER'])

def setup_ffmpeg():
    """Para deployment - confía en yt-dlp o FFmpeg del sistema"""
    print(" Configurando para deployment...")
    
    try:
        # yt-dlp trae su propio ffmpeg
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("yt-dlp disponible (incluye FFmpeg)")
            return 'yt-dlp'
    except:
        pass
    
    try:
        # O verificar si hay FFmpeg en el sistema
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(" FFmpeg disponible en sistema")
            return 'ffmpeg'
    except:
        print("FFmpeg no encontrado, pero yt-dlp debería funcionar")
        return None

# Configurar al inicio
ffmpeg_info = setup_ffmpeg()

class DownloadManager:
    def __init__(self):
        self.downloads = {}
    
    def get_video_info(self, url):
        """Obtiene información del video sin descargarlo"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            # Configuraciones para evitar detección como bot
            'extract_flat': False,
            'ignoreerrors': True,
            'no_check_certificate': True,
            'prefer_insecure': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
                'Accept-Encoding': 'gzip, deflate',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
        }
    
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            
                # Formatear la información
                formats = {
                    'mp3': [],
                    'mp4': []
                }
            
                # Obtener formatos de audio disponibles - MEJORADO
                audio_formats = []
                for f in info.get('formats', []):
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                        audio_quality = f.get('abr', 0)
                        if audio_quality and isinstance(audio_quality, (int, float)):
                            # Convertir a entero y evitar duplicados
                            audio_quality_int = int(audio_quality)
                            if audio_quality_int not in [a['quality'] for a in audio_formats]:
                                audio_formats.append({
                                    'quality': audio_quality_int,
                                    'format_id': f.get('format_id'),
                                    'ext': f.get('ext'),
                                    'acodec': f.get('acodec', 'unknown')
                                })
            
                # Ordenar y filtrar calidades de audio
                audio_formats.sort(key=lambda x: x['quality'], reverse=True)
            
                # Si no hay formatos de audio o son de baja calidad, ofrecer opciones de alta calidad
                max_audio_quality = max([a['quality'] for a in audio_formats]) if audio_formats else 0
            
                if not audio_formats or max_audio_quality < 192:
                    # Ofrecer calidades de MP3 estándar
                    audio_formats = [
                        {'quality': 320, 'format_id': 'bestaudio/best', 'ext': 'mp3', 'acodec': 'mp3'},
                        {'quality': 256, 'format_id': 'bestaudio/best', 'ext': 'mp3', 'acodec': 'mp3'},
                        {'quality': 192, 'format_id': 'bestaudio/best', 'ext': 'mp3', 'acodec': 'mp3'},
                        {'quality': 128, 'format_id': 'bestaudio/best', 'ext': 'mp3', 'acodec': 'mp3'}
                    ]   
                else:
                    # Usar las calidades detectadas pero asegurar que tengamos opciones altas
                    high_quality_options = [320, 256, 192]
                    for hq in high_quality_options:
                        if hq not in [a['quality'] for a in audio_formats] and hq <= max_audio_quality:
                            audio_formats.append({
                                'quality': hq,
                                'format_id': 'bestaudio/best',
                                'ext': 'mp3',
                                'acodec': 'mp3'
                            })
                
                    # Re-ordenar
                    audio_formats.sort(key=lambda x: x['quality'], reverse=True)
            
                formats['mp3'] = audio_formats
            
                # Obtener formatos de video disponibles (código existente)
                video_formats = []
                for f in info.get('formats', []):
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('height'):
                        height = f.get('height', 0)
                        if height and isinstance(height, (int, float)):
                            height_int = int(height)
                            if height_int not in [v['quality'] for v in video_formats]:
                                video_formats.append({
                                    'quality': height_int,
                                    'format_id': f.get('format_id'),
                                    'ext': f.get('ext')
                                })
            
                video_formats.sort(key=lambda x: x['quality'], reverse=True)
            
                if not video_formats:
                    video_formats = [
                        {'quality': 1080, 'format_id': 'bestvideo+bestaudio/best', 'ext': 'mp4'},
                        {'quality': 720, 'format_id': 'bestvideo+bestaudio/best', 'ext': 'mp4'},
                        {'quality': 480, 'format_id': 'bestvideo+bestaudio/best', 'ext': 'mp4'},
                        {'quality': 360, 'format_id': 'bestvideo+bestaudio/best', 'ext': 'mp4'}
                    ]
            
                formats['mp4'] = video_formats
            
                print(f"🔊 Calidades de audio detectadas: {[a['quality'] for a in audio_formats]}")
                print(f"🎥 Calidades de video detectadas: {[v['quality'] for v in video_formats]}")
            
                return {
                    'title': info.get('title', 'Sin título'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': formats,
                    'success': True
                }
            
        except Exception as e:
            print(f"Error en get_video_info: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_video(self, url, format_type, quality, download_id):
        """Descarga el video - Versión para deployment"""
        try:
            download_path = os.path.join(app.config['DOWNLOAD_FOLDER'], download_id)
            if not os.path.exists(download_path):
                os.makedirs(download_path)
        
            ydl_opts = {
                'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
            }

            if format_type == 'mp3':
                # Configuración para MP3 - yt-dlp usa su FFmpeg interno
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': quality,
                    }],
                })
                print(f"🎵 Descargando MP3 a {quality}kbps")
            
            else:
                # Configuración para MP4 (no necesita FFmpeg)
                ydl_opts.update({
                    'format': f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]',
                    'merge_output_format': 'mp4',
                })
                print(f" Descargando MP4 a {quality}p")
        
            print(f"!! Iniciando descarga completa: {url}")
        
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            
                # Buscar el archivo descargado
                downloaded_files = os.listdir(download_path)
                main_file = None
            
                for file in downloaded_files:
                    file_path = os.path.join(download_path, file)
                    if format_type == 'mp3' and file.endswith('.mp3'):
                        main_file = file_path
                        break
                    elif format_type == 'mp4' and file.endswith('.mp4'):
                        main_file = file_path
                        break
            
                if not main_file and downloaded_files:
                    # Tomar el primer archivo y renombrar si es necesario
                    main_file = os.path.join(download_path, downloaded_files[0])
                    if format_type == 'mp3' and not main_file.endswith('.mp3'):
                        new_file = main_file.rsplit('.', 1)[0] + '.mp3'
                        os.rename(main_file, new_file)
                        main_file = new_file
                    elif format_type == 'mp4' and not main_file.endswith('.mp4'):
                        new_file = main_file.rsplit('.', 1)[0] + '.mp4'
                        os.rename(main_file, new_file)
                        main_file = new_file
            
                if main_file:
                    self.downloads[download_id] = {
                        'status': 'completed',
                        'filename': main_file,
                        'title': info.get('title', 'video'),
                        'format': format_type
                    }
                    print(f" Descarga completada: {os.path.basename(main_file)}")
                
                    # Verificar tamaño del archivo
                    file_size = os.path.getsize(main_file) / (1024 * 1024)  # MB
                    print(f" Tamaño del archivo: {file_size:.2f} MB")
                else:
                    raise Exception("No se pudo encontrar el archivo descargado")
                
        except Exception as e:
            print(f" Error en descarga: {str(e)}")
            self.downloads[download_id] = {
                'status': 'error',
                'error': str(e)
            }   

    def _find_downloaded_file(self, download_path, format_type):
        """Busca el archivo descargado y lo renombra si es necesario"""
        downloaded_files = os.listdir(download_path)
        main_file = None
    
        for file in downloaded_files:
            file_path = os.path.join(download_path, file)
            if format_type == 'mp3' and file.endswith('.mp3'):
                main_file = file_path
                break
            elif format_type == 'mp4' and file.endswith('.mp4'):
                main_file = file_path
                break
    
        if not main_file and downloaded_files:
            # Renombrar si es necesario
            main_file = os.path.join(download_path, downloaded_files[0])
            if format_type == 'mp3' and not main_file.endswith('.mp3'):
                new_file = main_file.rsplit('.', 1)[0] + '.mp3'
                os.rename(main_file, new_file)
                main_file = new_file
            elif format_type == 'mp4' and not main_file.endswith('.mp4'):
                new_file = main_file.rsplit('.', 1)[0] + '.mp4'
                os.rename(main_file, new_file)
                main_file = new_file
    
        return main_file   

# Instancia global del administrador de descargas
download_manager = DownloadManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    url = request.json.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'URL no proporcionada'})
    
    info = download_manager.get_video_info(url)
    return jsonify(info)

@app.route('/download', methods=['POST'])
def download():
    try:
        url = request.form.get('url')
        format_type = request.form.get('format')
        quality = request.form.get('quality')
        
        if not url or not format_type or not quality:
            flash('Faltan parámetros requeridos', 'error')
            return redirect(url_for('index'))
        
        # Generar ID único para la descarga
        download_id = f"download_{int(time.time())}_{hash(url) % 10000}"
        
        # Iniciar descarga en un hilo separado
        thread = threading.Thread(
            target=download_manager.download_video,
            args=(url, format_type, quality, download_id)
        )
        thread.daemon = True
        thread.start()
        
        # Guardar información inicial de la descarga
        download_manager.downloads[download_id] = {
            'status': 'downloading',
            'url': url,
            'format': format_type,
            'quality': quality
        }
        
        return jsonify({
            'success': True,
            'download_id': download_id,
            'message': 'Descarga iniciada'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/download_status/<download_id>')
def download_status(download_id):
    download_info = download_manager.downloads.get(download_id, {})
    return jsonify(download_info)

@app.route('/download_file/<download_id>')
def download_file(download_id):
    download_info = download_manager.downloads.get(download_id, {})
    
    if download_info.get('status') != 'completed':
        return "Archivo no disponible", 404
    
    filename = download_info.get('filename')
    original_title = download_info.get('title', 'video')
    format_type = download_info.get('format', 'mp4')
    
    if not os.path.exists(filename):
        return "Archivo no encontrado", 404
    
    # Crear nombre de archivo seguro para descarga
    safe_filename = f"{original_title}.{format_type}"
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
    
    return send_file(
        filename,
        as_attachment=True,
        download_name=safe_filename
    )

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Limpiar archivos descargados más antiguos de 1 hora"""
    try:
        current_time = time.time()
        download_folder = app.config['DOWNLOAD_FOLDER']
        
        for item in os.listdir(download_folder):
            item_path = os.path.join(download_folder, item)
            if os.path.isdir(item_path):
                # Eliminar carpetas más antiguas de 1 hora
                if current_time - os.path.getctime(item_path) > 3600:
                    import shutil
                    shutil.rmtree(item_path)
        
        return jsonify({'success': True, 'message': 'Limpieza completada'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/status')
def status():
    """Estado simple de la aplicación"""
    #http://localhost:5000/status
    return {
        'status': 'running',
        'ffmpeg': 'available' if ffmpeg_info else 'unavailable',
        'downloads_folder': os.path.exists('downloads')
    }

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)