#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de preparación para Odoo 100% Local (sin Docker)
Configura PostgreSQL portable, instala dependencias y prepara el entorno
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
APPDATA_DIR = Path(os.environ.get('APPDATA', '')) / "OdooInmobiliaria"

def run_cmd(cmd, cwd=None, shell=False):
    print(f"🔧 {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode == 0

def main():
    print("=" * 60)
    print("🏗️  PREPARANDO Odoo Inmobiliaria 100% LOCAL")
    print("=" * 60)
    
    # 1. Crear estructura de directorios
    print("\n📁 Creando directorios...")
    dirs = [
        APPDATA_DIR / "data" / "postgresql",
        APPDATA_DIR / "data" / "odoo",
        APPDATA_DIR / "postgresql" / "bin",
        APPDATA_DIR / "logs",
        APPDATA_DIR / "config",
        APPDATA_DIR / "addons",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {d}")
    
    # 2. Instalar dependencias Python
    print("\n📦 Instalando dependencias Python...")
    reqs = PROJECT_ROOT / "launcher" / "requirements.txt"
    if reqs.exists():
        run_cmd([sys.executable, "-m", "pip", "install", "-r", str(reqs)])
    
    # 3. Instalar Odoo en modo desarrollo
    print("\n🐍 Instalando Odoo (modo desarrollo)...")
    odoo_setup = PROJECT_ROOT / "odoo"
    if (odoo_setup / "setup.py").exists():
        run_cmd([sys.executable, "-m", "pip", "install", "-e", str(odoo_setup)])
    else:
        print("   ⚠️ No se encontró setup.py en odoo/")
    
    # 4. Descargar PostgreSQL portable si no existe
    print("\n🐘 Verificando PostgreSQL portable...")
    pg_bin = APPDATA_DIR / "postgresql" / "bin" / "postgres.exe"
    if not pg_bin.exists():
        print("   📥 Descargando PostgreSQL 16 portable...")
        download_postgresql(APPDATA_DIR / "postgresql")
    else:
        print("   ✅ PostgreSQL ya instalado")
    
    # 5. Inicializar cluster PostgreSQL
    print("\n🗄️ Inicializando cluster PostgreSQL...")
    pg_data = APPDATA_DIR / "data" / "postgresql"
    if not (pg_data / "PG_VERSION").exists():
        initdb = APPDATA_DIR / "postgresql" / "bin" / "initdb.exe"
        if initdb.exists():
            run_cmd([
                str(initdb),
                "-D", str(pg_data),
                "-U", "odoo",
                "-A", "trust",
                "-E", "UTF8"
            ])
            # Configurar puerto
            conf = pg_data / "postgresql.conf"
            with open(conf, "a", encoding="utf-8") as f:
                f.write("\nport = 5433\nlisten_addresses = 'localhost'\nmax_connections = 100\n")
            print("   ✅ Cluster inicializado en puerto 5433")
        else:
            print("   ⚠️ initdb.exe no encontrado")
    else:
        print("   ✅ Cluster ya existe")
    
    # 6. Crear base de datos
    print("\n🗃️ Creando base de datos 'inmobiliaria'...")
    createdb = APPDATA_DIR / "postgresql" / "bin" / "createdb.exe"
    if createdb.exists():
        # Iniciar postgres temporalmente
        pg_ctl = APPDATA_DIR / "postgresql" / "bin" / "pg_ctl.exe"
        if pg_ctl.exists():
            run_cmd([str(pg_ctl), "start", "-D", str(pg_data), "-w", "-t", "300"])
            run_cmd([str(createdb), "-h", "localhost", "-p", "5433", "-U", "odoo", "inmobiliaria"])
            run_cmd([str(pg_ctl), "stop", "-D", str(pg_data), "-m", "fast"])
            print("   ✅ Base de datos creada")
    
    # 7. Copiar módulos personalizados
    print("\n📦 Copiando módulos personalizados...")
    src_addons = PROJECT_ROOT / "addons"
    dst_addons = APPDATA_DIR / "addons"
    if src_addons.exists():
        for item in src_addons.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                dst = dst_addons / item.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
                print(f"   ✅ {item.name}")
    
    # 8. Copiar configuración
    print("\n⚙️ Copiando configuración...")
    config_src = PROJECT_ROOT / "config" / "odoo.conf"
    config_dst = APPDATA_DIR / "config" / "odoo.conf"
    if config_src.exists():
        shutil.copy2(config_src, config_dst)
        print(f"   ✅ {config_dst}")
    
    # 9. Crear accesos directos
    print("\n🔗 Creando accesos directos...")
    create_shortcuts()
    
    print("\n" + "=" * 60)
    print("✅ ¡PREPARACIÓN COMPLETA!")
    print("=" * 60)
    print(f"""
📁 Datos en: {APPDATA_DIR}
🐘 PostgreSQL: {APPDATA_DIR}/postgresql/bin
🐍 Odoo: instalado en modo desarrollo

🚀 PARA EJECUTAR:
   Opción 1 - Launcher GUI (recomendado):
      python {PROJECT_ROOT / 'launcher' / 'odoo_launcher.py'}
   
   Opción 2 - Script directo:
      {APPDATA_DIR / 'start_odoo.bat'}

🌐 ACCESO:
   http://localhost:8069
   👤 valegchemes@gmail.com
   🔑 Poloaco123!

📝 NOTAS:
   - Todo se guarda en %APPDATA%\\OdooInmobiliaria\\
   - 100% offline, sin Docker, sin nube
   - Puerto PostgreSQL: 5433 (para no chocar con otras instalaciones)
   - Puerto Odoo: 8069
""")

def download_postgresql(dest_dir):
    """Descarga y extrae PostgreSQL portable"""
    url = "https://get.enterprisedb.com/postgresql/postgresql-16.2-1-windows-x64-binaries.zip"
    zip_path = dest_dir.parent / "postgresql.zip"
    
    try:
        print(f"   Descargando desde {url}...")
        urllib.request.urlretrieve(url, zip_path)
        
        print("   Extrayendo...")
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_dir.parent)
        
        # La zip extrae a 'pgsql', mover a 'bin'
        pgsql_dir = dest_dir.parent / "pgsql"
        if pgsql_dir.exists():
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.move(str(pgsql_dir), str(dest_dir))
        
        zip_path.unlink()
        print("   ✅ PostgreSQL portable instalado")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   ⚠️ Instale PostgreSQL 16+ manualmente desde https://www.postgresql.org/download/windows/")

def create_shortcuts():
    """Crea accesos directos en Escritorio y Menú Inicio"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        start_menu = winshell.start_menu()
        app_dir = APPDATA_DIR
        launcher = PROJECT_ROOT / "launcher" / "odoo_launcher.py"
        icon = PROJECT_ROOT / "launcher" / "icon.ico"
        
        # Acceso directo en Escritorio
        shortcut_path = Path(desktop) / "Odoo Inmobiliaria.lnk"
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.Targetpath = sys.executable
        shortcut.Arguments = f'"{launcher}"'
        shortcut.WorkingDirectory = str(PROJECT_ROOT)
        if icon.exists():
            shortcut.IconLocation = str(icon)
        shortcut.save()
        
        # Acceso en Menú Inicio
        programs = Path(start_menu) / "Programs" / "OdooInmobiliaria"
        programs.mkdir(parents=True, exist_ok=True)
        shortcut2 = shell.CreateShortCut(str(programs / "Odoo Inmobiliaria.lnk"))
        shortcut2.Targetpath = sys.executable
        shortcut2.Arguments = f'"{launcher}"'
        shortcut2.WorkingDirectory = str(PROJECT_ROOT)
        if icon.exists():
            shortcut2.IconLocation = str(icon)
        shortcut2.save()
        
        print("   ✅ Accesos directos creados")
    except ImportError:
        print("   ⚠️ winshell/pywin32 no instalados, saltando accesos directos")
        print("   Instale con: pip install winshell pywin32")
    except Exception as e:
        print(f"   ⚠️ Error creando accesos: {e}")

if __name__ == "__main__":
    main()