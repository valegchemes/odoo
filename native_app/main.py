#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Odoo Inmobiliaria - App Nativa Windows
Backend: Odoo + PostgreSQL embebidos
Frontend: WebView2 (Edge) ventana nativa
"""

import os
import sys
import subprocess
import threading
import time
import json
import signal
import atexit
import logging
from pathlib import Path
from typing import Optional

import webview

# ============================================================
# CONFIGURACIÓN
# ============================================================
APP_NAME = "OdooInmobiliaria"
VERSION = "19.0.1.0"

# Rutas en %APPDATA%
APPDATA_DIR = Path(os.environ.get('APPDATA', '')) / APP_NAME
DATA_DIR = APPDATA_DIR / "data"
POSTGRES_DIR = APPDATA_DIR / "postgresql"
ODOO_DIR = APPDATA_DIR / "odoo"
LOG_DIR = APPDATA_DIR / "logs"
CONFIG_DIR = APPDATA_DIR / "config"

# Puertos internos (solo localhost)
PG_PORT = 5433
ODOO_PORT = 8069

# URLs
ODOO_URL = f"http://localhost:{ODOO_PORT}"
ODOO_LOGIN_URL = f"{ODOO_URL}/web/login"

# Ventana
WINDOW_TITLE = "Odoo Inmobiliaria"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 768

# ============================================================
# LOGGING
# ============================================================
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# GESTOR DE SERVICIOS BACKEND
# ============================================================
class BackendManager:
    def __init__(self):
        self.pg_process: Optional[subprocess.Popen] = None
        self.odoo_process: Optional[subprocess.Popen] = None
        self.running = False
        
    def log(self, msg, level="info"):
        logger.log(getattr(logging, level.upper()), msg)
    
    def ensure_dirs(self):
        """Crea estructura de directorios"""
        for d in [DATA_DIR, POSTGRES_DIR, ODOO_DIR, LOG_DIR, CONFIG_DIR]:
            d.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "postgresql").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "odoo").mkdir(parents=True, exist_ok=True)
    
    def get_postgres_bin(self) -> Path:
        """Ruta a binarios PostgreSQL"""
        return POSTGRES_DIR / "bin"
    
    def get_odoo_bin(self) -> Path:
        """Ruta a odoo-bin"""
        return ODOO_DIR / "odoo-bin"
    
    def init_postgresql(self) -> bool:
        """Inicializa cluster PostgreSQL si no existe"""
        pg_bin = self.get_postgres_bin()
        pg_data = DATA_DIR / "postgresql"
        
        if not (pg_bin / "postgres.exe").exists():
            self.log("PostgreSQL no encontrado en directorio embebido", "warning")
            return False
        
        if not (pg_data / "PG_VERSION").exists():
            self.log("Inicializando cluster PostgreSQL...")
            initdb = pg_bin / "initdb.exe"
            if initdb.exists():
                result = subprocess.run([
                    str(initdb),
                    "-D", str(pg_data),
                    "-U", "odoo",
                    "-A", "trust",
                    "-E", "UTF8"
                ], capture_output=True, text=True)
                if result.returncode != 0:
                    self.log(f"Error initdb: {result.stderr}", "error")
                    return False
                
                # Configurar puerto
                conf = pg_data / "postgresql.conf"
                with open(conf, "a", encoding="utf-8") as f:
                    f.write(f"\nport = {PG_PORT}\n")
                    f.write("listen_addresses = 'localhost'\n")
                    f.write("max_connections = 100\n")
                    f.write("shared_buffers = 128MB\n")
                    f.write("work_mem = 4MB\n")
                self.log("Cluster PostgreSQL inicializado")
            else:
                self.log("initdb.exe no encontrado", "error")
                return False
        return True
    
    def start_postgresql(self) -> bool:
        """Inicia PostgreSQL"""
        if self.pg_process and self.pg_process.poll() is None:
            return True
        
        if not self.init_postgresql():
            return False
        
        pg_bin = self.get_postgres_bin()
        pg_data = DATA_DIR / "postgresql"
        postgres_exe = pg_bin / "postgres.exe"
        
        if not postgres_exe.exists():
            self.log("postgres.exe no encontrado", "error")
            return False
        
        self.log("Iniciando PostgreSQL...")
        self.pg_process = subprocess.Popen(
            [str(postgres_exe), "-D", str(pg_data)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Esperar a que esté listo
        for _ in range(30):
            time.sleep(0.5)
            if self.check_port(PG_PORT):
                self.log(f"PostgreSQL listo en puerto {PG_PORT}")
                return True
        
        self.log("Timeout esperando PostgreSQL", "error")
        return False
    
    def stop_postgresql(self):
        """Detiene PostgreSQL"""
        if self.pg_process:
            self.log("Deteniendo PostgreSQL...")
            self.pg_process.terminate()
            try:
                self.pg_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.pg_process.kill()
            self.pg_process = None
    
    def ensure_database(self) -> bool:
        """Crea BD si no existe"""
        pg_bin = self.get_postgres_bin()
        createdb = pg_bin / "createdb.exe"
        psql = pg_bin / "psql.exe"
        
        if not createdb.exists() or not psql.exists():
            return False
        
        # Verificar si existe
        check = subprocess.run([
            str(psql), "-h", "localhost", "-p", str(PG_PORT),
            "-U", "odoo", "-d", "postgres",
            "-t", "-c", "SELECT 1 FROM pg_database WHERE datname = 'inmobiliaria'"
        ], capture_output=True, text=True)
        
        if "1" not in check.stdout:
            self.log("Creando base de datos 'inmobiliaria'...")
            result = subprocess.run([
                str(createdb), "-h", "localhost", "-p", str(PG_PORT),
                "-U", "odoo", "inmobiliaria"
            ], capture_output=True, text=True)
            if result.returncode != 0:
                self.log(f"Error creando BD: {result.stderr}", "error")
                return False
        return True
    
    def start_odoo(self) -> bool:
        """Inicia Odoo"""
        if self.odoo_process and self.odoo_process.poll() is None:
            return True
        
        if not self.ensure_database():
            return False
        
        odoo_bin = self.get_odoo_bin()
        if not odoo_bin.exists():
            self.log("odoo-bin no encontrado", "error")
            return False
        
        # Configuración Odoo
        config_file = CONFIG_DIR / "odoo.conf"
        config_content = f"""[options]
addons_path = {APPDATA_DIR / "addons"},{ODOO_DIR / "addons"}
data_dir = {DATA_DIR / "odoo"}
db_host = localhost
db_port = {PG_PORT}
db_user = odoo
db_password = odoo
db_name = inmobiliaria
db_maxconn = 64
dev_mode = reload,qweb,werkzeug,xml
log_level = info
logfile = {LOG_DIR / "odoo.log"}
log_handler = :INFO
log_db = False
log_db_level = warning
workers = 0
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
limit_request = 8192
limit_time_cpu = 600
limit_time_real = 1200
max_cron_threads = 1
admin_passwd = admin123
without_demo = False
unaccent = True
translate_modules = all
http_port = {ODOO_PORT}
longpolling_port = 8072
proxy_mode = False
"""
        config_file.write_text(config_content, encoding="utf-8")
        
        # Environment
        env = os.environ.copy()
        env['PYTHONPATH'] = str(ODOO_DIR) + ";" + env.get('PYTHONPATH', '')
        
        self.log("Iniciando Odoo...")
        self.odoo_process = subprocess.Popen(
            [sys.executable, str(odoo_bin), "-c", str(config_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Esperar a que esté listo
        for _ in range(60):
            time.sleep(0.5)
            if self.check_port(ODOO_PORT):
                self.log(f"Odoo listo en puerto {ODOO_PORT}")
                return True
        
        self.log("Timeout esperando Odoo", "error")
        return False
    
    def stop_odoo(self):
        """Detiene Odoo"""
        if self.odoo_process:
            self.log("Deteniendo Odoo...")
            self.odoo_process.terminate()
            try:
                self.odoo_process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.odoo_process.kill()
            self.odoo_process = None
    
    def check_port(self, port: int) -> bool:
        import socket
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except:
            return False
    
    def start_all(self) -> bool:
        """Inicia todo el stack"""
        self.ensure_dirs()
        self.running = True
        
        if not self.start_postgresql():
            return False
        
        if not self.start_odoo():
            self.stop_postgresql()
            return False
        
        return True
    
    def stop_all(self):
        """Detiene todo"""
        self.running = False
        self.stop_odoo()
        self.stop_postgresql()


# ============================================================
# API PARA WEBVIEW (JavaScript ↔ Python)
# ============================================================
class NativeAPI:
    def __init__(self, backend: BackendManager, window: webview.Window):
        self.backend = backend
        self.window = window
    
    def get_version(self):
        return VERSION
    
    def get_status(self):
        return {
            "postgres": self.backend.check_port(PG_PORT),
            "odoo": self.backend.check_port(ODOO_PORT),
            "url": ODOO_URL
        }
    
    def restart_backend(self):
        threading.Thread(target=self._restart_thread, daemon=True).start()
        return {"status": "restarting"}
    
    def _restart_thread(self):
        self.backend.stop_all()
        time.sleep(2)
        self.backend.start_all()
        # Recargar ventana cuando listo
        for _ in range(60):
            if self.backend.check_port(ODOO_PORT):
                self.window.load_url(ODOO_LOGIN_URL)
                break
            time.sleep(0.5)
    
    def minimize_window(self):
        self.window.minimize()
    
    def maximize_window(self):
        if self.window.maximized:
            self.window.restore()
        else:
            self.window.maximize()
    
    def close_window(self):
        self.backend.stop_all()
        self.window.destroy()
    
    def is_maximized(self):
        return self.window.maximized
    
    def open_dev_tools(self):
        # WebView2 no tiene dev tools expuestos fácilmente
        pass
    
    def get_app_info(self):
        return {
            "name": APP_NAME,
            "version": VERSION,
            "data_dir": str(APPDATA_DIR),
            "postgres_port": PG_PORT,
            "odoo_port": ODOO_PORT
        }


# ============================================================
# VENTANA PRINCIPAL
# ============================================================
class NativeWindow:
    def __init__(self):
        self.backend = BackendManager()
        self.api = None
        self.window = None
        
    def create_window(self):
        """Crea la ventana WebView2"""
        # Configurar WebView2
        webview.settings = {
            'ALLOW_DOWNLOADS': True,
            'ALLOW_FILE_URLS': True,
        }
        
        # Crear ventana
        self.window = webview.create_window(
            title=WINDOW_TITLE,
            url=ODOO_LOGIN_URL,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT),
            resizable=True,
            frameless=False,  # True para ventana sin bordes personalizada
            easy_drag=False,
            on_top=False,
            confirm_close=True,
            background_color='#FFFFFF',
            text_select=True,
        )
        
        # Inyectar API
        self.api = NativeAPI(self.backend, self.window)
        self.window.expose(self.api)
        
        # Eventos
        self.window.events.closing += self.on_closing
        self.window.events.loaded += self.on_loaded
        
        return self.window
    
    def on_loaded(self):
        """Cuando la página carga"""
        logger.info("Ventana cargada")
        # Inyectar CSS/JS personalizado si se desea
        self.inject_custom_styles()
    
    def inject_custom_styles(self):
        """Inyecta estilos para sentir nativo"""
        css = """
        /* Ocultar elementos web no necesarios en app nativa */
        .o_main_navbar { display: none !important; }
        .o_web_client { background: #f8f9fa; }
        /* Scrollbar nativo */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #f1f1f1; }
        ::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #a1a1a1; }
        """
        js = f"""
        var style = document.createElement('style');
        style.textContent = `{css}`;
        document.head.appendChild(style);
        """
        self.window.evaluate_js(js)
    
    def on_closing(self):
        """Al cerrar ventana"""
        logger.info("Cerrando aplicación...")
        self.backend.stop_all()
        return True  # Permitir cierre


# ============================================================
# ENTRY POINT
# ============================================================
def main():
    # Single instance lock
    import socket
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_socket.bind(('localhost', 18069))
    except OSError:
        # Ya hay instancia corriendo
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Ya en ejecución",
            f"{APP_NAME} ya está ejecutándose.\n"
            "Revisa la barra de tareas o bandejita del sistema."
        )
        return 0
    
    # Crear app nativa
    app = NativeWindow()
    window = app.create_window()
    
    # Iniciar backend en thread separado
    def start_backend():
        if not app.backend.start_all():
            logger.error("Error iniciando backend")
            if window:
                window.destroy()
            return
        
        # Cargar URL cuando listo
        for _ in range(60):
            if app.backend.check_port(ODOO_PORT):
                window.load_url(ODOO_LOGIN_URL)
                break
            time.sleep(0.5)
    
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Iniciar loop WebView2 (bloqueante)
    try:
        webview.start(
            func=None,
            window=window,
            debug=False,
            storage_path=str(APPDATA_DIR / "webview2_data"),
            private_mode=False,
        )
    except KeyboardInterrupt:
        pass
    finally:
        app.backend.stop_all()
        lock_socket.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())