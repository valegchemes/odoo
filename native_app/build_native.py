#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compila Odoo Inmobiliaria como .exe nativo Windows standalone
Incluye: Python + WebView2 + Odoo + PostgreSQL portable
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
NATIVE_DIR = PROJECT_ROOT / "native_app"
DIST_DIR = PROJECT_ROOT / "dist_native"
BUILD_DIR = PROJECT_ROOT / "build_native"
APPDATA_DIR = Path(os.environ.get('APPDATA', '')) / "OdooInmobiliaria"

def run_cmd(cmd, cwd=None, shell=False):
    print(f"🔧 {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode == 0

def download_postgresql(dest_dir: Path) -> bool:
    """Descarga PostgreSQL portable binaries"""
    url = "https://get.enterprisedb.com/postgresql/postgresql-16.2-1-windows-x64-binaries.zip"
    zip_path = dest_dir.parent / "postgresql.zip"
    
    try:
        print(f"📥 Descargando PostgreSQL 16 portable...")
        urllib.request.urlretrieve(url, zip_path)
        
        print("📦 Extrayendo...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_dir.parent)
        
        # La zip extrae como 'pgsql', mover a 'bin'
        pgsql_dir = dest_dir.parent / "pgsql"
        if pgsql_dir.exists():
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.move(str(pgsql_dir), str(dest_dir))
        
        zip_path.unlink(missing_ok=True)
        print(f"✅ PostgreSQL en {dest_dir}")
        return True
    except Exception as e:
        print(f"❌ Error descargando PostgreSQL: {e}")
        return False

def create_icon(path: Path):
    """Crea icono .ico si no existe"""
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Fondo azul corporativo
        draw.rounded_rectangle([10, 10, 246, 246], radius=30, fill='#1e3a5f')
        # Casa blanca
        draw.polygon([(128, 50), (80, 110), (176, 110)], fill='white')
        draw.rectangle([80, 110, 176, 180], fill='white')
        # Puerta
        draw.rectangle([110, 130, 146, 180], fill='#1e3a5f')
        # Ventanas
        draw.rectangle([90, 125, 110, 145], fill='#1e3a5f')
        draw.rectangle([146, 125, 166, 145], fill='#1e3a5f')
        img.save(path, format='ICO', sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
        print(f"🎨 Icono creado: {path}")
    except Exception as e:
        print(f"⚠️ No se pudo crear icono: {e}")

def main():
    print("=" * 70)
    print("🏗️  COMPILANDO Odoo Inmobiliaria - APP NATIVA WINDOWS")
    print("=" * 70)
    
    # Limpiar builds anteriores
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            print(f"🧹 Limpiando {d}...")
            shutil.rmtree(d)
    
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Verificar PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("📦 Instalando PyInstaller...")
        if not run_cmd([sys.executable, "-m", "pip", "install", "pyinstaller"]):
            return 1
    
    # Verificar/crear icono
    icon_path = NATIVE_DIR / "icon.ico"
    if not icon_path.exists():
        create_icon(icon_path)
    
    # Preparar PostgreSQL portable para embeber
    print("\n🐘 Preparando PostgreSQL portable...")
    pg_dest = APPDATA_DIR / "postgresql"
    if not (pg_dest / "bin" / "postgres.exe").exists():
        if not download_postgresql(pg_dest):
            print("⚠️ PostgreSQL se descargará en primera ejecución")
    
    # Copiar Odoo source y addons al directorio de build para embeber
    print("\n📦 Preparando fuentes Odoo...")
    odoo_src = PROJECT_ROOT / "odoo"
    addons_src = PROJECT_ROOT / "addons"
    build_odoo = BUILD_DIR / "embedded_odoo"
    build_addons = BUILD_DIR / "embedded_addons"
    
    if odoo_src.exists():
        shutil.copytree(odoo_src, build_odoo, 
            ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '.git*', '*.egg-info'))
        print(f"   ✅ Odoo copiado a build")
    
    if addons_src.exists():
        shutil.copytree(addons_src, build_addons,
            ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '.git*'))
        print(f"   ✅ Addons copiados a build")
    
    # Configuración Odoo para embeber
    config_embed = BUILD_DIR / "odoo_embedded.conf"
    config_embed.write_text(f"""[options]
addons_path = {{APPDATA}}/OdooInmobiliaria/addons,{{ODOO_DIR}}/addons
data_dir = {{APPDATA}}/OdooInmobiliaria/data/odoo
db_host = localhost
db_port = 5433
db_user = odoo
db_password = odoo
db_name = inmobiliaria
dev_mode = reload,qweb,werkzeug,xml
log_level = info
logfile = {{APPDATA}}/OdooInmobiliaria/logs/odoo.log
workers = 0
admin_passwd = admin123
without_demo = False
http_port = 8069
proxy_mode = False
""", encoding="utf-8")
    
    # Compilar con PyInstaller
    print("\n🔨 Compilando ejecutable nativo...")
    
    # Hidden imports necesarios para Odoo + WebView2
    hidden_imports = [
        # WebView2
        'webview',
        'webview.platforms.edgechromium',
        'webview.util',
        # Odoo core
        'odoo',
        'odoo.api', 'odoo.fields', 'odoo.models', 'odoo.tools',
        'odoo.modules.registry', 'odoo.modules.loading',
        'odoo.service.server', 'odoo.http',
        'odoo.addons.base.models.res_users',
        'odoo.addons.base.models.res_partner',
        # PostgreSQL
        'psycopg2', 'psycopg2._psycopg', 'psycopg2.extensions',
        'psycopg2.extras', 'psycopg2.errors', 'psycopg2.pool',
        # Stdlib
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog',
        # Terceros
        'werkzeug', 'jinja2', 'babel', 'babel.dates', 'pytz',
        'dateutil', 'dateutil.parser', 'dateutil.relativedelta',
        'passlib', 'passlib.context', 'cryptography', 'cryptography.fernet',
        'PIL', 'PIL.Image', 'PIL.ImageTk',
        'watchdog', 'watchdog.observers', 'watchdog.events',
    ]
    
    cmd = [
        "pyinstaller",
        f"--name=OdooInmobiliaria",
        "--onefile",
        "--windowed",  # GUI sin consola
        f"--icon={icon_path}",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={PROJECT_ROOT}",
        # Hidden imports
        *[f"--hidden-import={imp}" for imp in hidden_imports],
        # Datos embebidos
        f"--add-data={build_odoo};embedded_odoo",
        f"--add-data={build_addons};embedded_addons",
        f"--add-data={config_embed};.",
        f"--add-data={NATIVE_DIR / 'requirements.txt'};.",
        # Optimizaciones
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=notebook",
        "--exclude-module=test",
        "--exclude-module=unittest",
        "--strip",
        "--noupx",  # UPX puede causar problemas con WebView2
        "native_app/main.py"
    ]
    
    print(f"   Comando: {' '.join(cmd[:10])}... (+{len(cmd)-10} args)")
    
    if not run_cmd(cmd):
        print("❌ Error compilando")
        return 1
    
    # Verificar resultado
    exe_path = DIST_DIR / "OdooInmobiliaria.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ ¡ÉXITO! Ejecutable nativo creado:")
        print(f"   📁 {exe_path}")
        print(f"   📦 Tamaño: {size_mb:.1f} MB")
        
        # Crear instalador MSI
        print("\n📦 Para crear instalador .msi:")
        print("   1. Instala Inno Setup 6+")
        print("   2. Abre installer/setup.iss")
        print("   3. Modifica [Files] para usar dist_native/OdooInmobiliaria.exe")
        print("   4. Build → Genera Setup.exe instalable")
        
        print(f"\n🚀 Para probar ahora:")
        print(f"   {exe_path}")
        return 0
    else:
        print("❌ No se generó el ejecutable")
        return 1

if __name__ == "__main__":
    sys.exit(main())