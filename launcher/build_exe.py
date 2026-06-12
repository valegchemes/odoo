#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para compilar el launcher a .exe standalone con PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LAUNCHER_DIR = PROJECT_ROOT / "launcher"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

def run_cmd(cmd, cwd=None):
    print(f"🔧 Ejecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def main():
    print("=" * 60)
    print("🏗️  COMPILANDO OdooInmobiliaria Launcher a .EXE")
    print("=" * 60)
    
    # Limpiar builds anteriores
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            print(f"🧹 Limpiando {d}...")
            shutil.rmtree(d)
    
    # Verificar PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} encontrado")
    except ImportError:
        print("📦 Instalando PyInstaller...")
        if not run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller"]):
            print("❌ Error instalando PyInstaller")
            return 1
    
    # Crear icono si no existe
    icon_path = LAUNCHER_DIR / "icon.ico"
    if not icon_path.exists():
        print("🎨 Creando icono por defecto...")
        create_default_icon(icon_path)
    
    # Compilar con PyInstaller
    print("\n🔨 Compilando ejecutable...")
    
    # Archivos de datos a incluir
    datas = [
        (str(PROJECT_ROOT / "config"), "config"),
        (str(PROJECT_ROOT / "addons"), "addons"),
    ]
    
    # Opciones de PyInstaller
    cmd = [
        "pyinstaller",
        "--name=OdooInmobiliaria",
        "--onefile",
        "--windowed",  # Sin consola (GUI)
        f"--icon={icon_path}",
        "--add-data=launcher/odoo_launcher.py;.",
        "--add-data=config/odoo.conf;config",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.scrolledtext",
        "--hidden-import=tkinter.messagebox",
        "--hidden-import=psycopg2",
        "--hidden-import=psycopg2._psycopg",
        "--hidden-import=psycopg2.extensions",
        "--hidden-import=psycopg2.extras",
        "--hidden-import=psycopg2.errors",
        "--hidden-import=psycopg2.pool",
        "--hidden-import=watchdog",
        "--hidden-import=watchdog.observers",
        "--hidden-import=watchdog.events",
        "--hidden-import=werkzeug",
        "--hidden-import=jinja2",
        "--hidden-import=babel",
        "--hidden-import=babel.dates",
        "--hidden-import=pytz",
        "--hidden-import=dateutil",
        "--hidden-import=dateutil.parser",
        "--hidden-import=dateutil.relativedelta",
        "--hidden-import=passlib",
        "--hidden-import=passlib.context",
        "--hidden-import=passlib.handlers",
        "--hidden-import=cryptography",
        "--hidden-import=cryptography.fernet",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={PROJECT_ROOT}",
        "launcher/odoo_launcher.py"
    ]
    
    if not run_cmd(cmd):
        print("❌ Error compilando")
        return 1
    
    # Verificar resultado
    exe_path = DIST_DIR / "OdooInmobiliaria.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ ¡ÉXITO! Ejecutable creado:")
        print(f"   📁 {exe_path}")
        print(f"   📦 Tamaño: {size_mb:.1f} MB")
        
        # Copiar archivos necesarios al lado del exe
        print("\n📋 Copiando archivos de soporte...")
        copy_support_files(exe_path.parent)
        
        print("\n🎉 ¡Listo para distribuir!")
        print(f"   Ejecute: {exe_path}")
        return 0
    else:
        print("❌ No se generó el ejecutable")
        return 1

def create_default_icon(path):
    """Crea un icono simple si no existe"""
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Fondo azul
        draw.rounded_rectangle([10, 10, 246, 246], radius=30, fill='#2c3e50')
        # Casa simple
        draw.polygon([(128, 50), (80, 110), (176, 110)], fill='#3498db')
        draw.rectangle([80, 110, 176, 180], fill='#3498db')
        draw.rectangle([110, 130, 146, 180], fill='#2c3e50')
        img.save(path, format='ICO', sizes=[(256,256), (128,128), (64,64), (32,32), (16,16)])
        print(f"   Icono creado: {path}")
    except Exception as e:
        print(f"   ⚠️ No se pudo crear icono: {e}")

def copy_support_files(dest_dir):
    """Copia archivos necesarios junto al .exe"""
    support = {
        "config/odoo.conf": "config/odoo.conf",
        "addons": "addons",
        "README.md": "README.md",
    }
    
    for src, dst in support.items():
        src_path = PROJECT_ROOT / src
        dst_path = dest_dir / dst
        if src_path.exists():
            if src_path.is_dir():
                if dst_path.exists():
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"   📁 {dst}/")
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"   📄 {dst}")

if __name__ == "__main__":
    sys.exit(main())