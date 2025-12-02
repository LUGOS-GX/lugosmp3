#!/usr/bin/env python3
"""
Script para verificar que todo está listo para deployment
"""
import os
import subprocess
import sys

def check_deployment():
    print("🔍 Verificando entorno para deployment...")
    
    checks = {
        'ffmpeg': False,
        'project_structure': False,
        'dependencies': False
    }
    
    # Verificar FFmpeg en proyecto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ffmpeg_paths = [
        os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg', 'bin', 'ffmpeg'),
        os.path.join(base_dir, 'ffmpeg', 'ffmpeg.exe'),
        os.path.join(base_dir, 'ffmpeg', 'ffmpeg'),
    ]
    
    for path in ffmpeg_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, '-version'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    checks['ffmpeg'] = True
                    print(f"✅ FFmpeg encontrado: {path}")
                    break
            except:
                continue
    
    # Verificar estructura del proyecto
    required_folders = ['templates', 'static', 'downloads']
    missing_folders = []
    
    for folder in required_folders:
        if os.path.exists(os.path.join(base_dir, folder)):
            print(f"✅ Carpeta {folder} encontrada")
        else:
            missing_folders.append(folder)
            print(f"❌ Carpeta {folder} no encontrada")
    
    checks['project_structure'] = len(missing_folders) == 0
    
    # Verificar dependencias
    try:
        import yt_dlp
        import flask
        checks['dependencies'] = True
        print("✅ Dependencias Python encontradas")
    except ImportError as e:
        print(f"❌ Dependencias faltantes: {e}")
    
    # Resumen
    print("\n📊 RESUMEN DE DEPLOYMENT:")
    for check, status in checks.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {check}: {'LISTO' if status else 'FALTA'}")
    
    if all(checks.values()):
        print("\n🎉 ¡Todo listo para deployment!")
        return True
    else:
        print("\n⚠️  Hay problemas que resolver antes del deployment")
        return False

if __name__ == '__main__':
    check_deployment()