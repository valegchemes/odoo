#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Odoo Inmobiliaria - Launcher Windows
Aplicación nativa para gestionar Odoo 100% local offline
"""

import os
import sys
import subprocess
import threading
import time
import json
import shutil
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import queue
import logging
from datetime import datetime

# ============================================================
# CONFIGURACIÓN DE RUTAS LOCALES
# ============================================================
APP_NAME = "OdooInmobiliaria"
APPDATA_DIR = Path(os.environ.get('APPDATA', '')) / APP_NAME
DATA_DIR = APPDATA_DIR / "data"
POSTGRES_DIR = APPDATA_DIR / "postgresql"
ODOO_DIR = APPDATA_DIR / "odoo"
LOG_DIR = APPDATA_DIR / "logs"
CONFIG_FILE = APPDATA_DIR / "config.json"

# Puertos
PG_PORT = 5433  # Puerto no estándar para evitar conflictos
ODOO_PORT = 8069

# Crear directorios
for d in [DATA_DIR, POSTGRES_DIR, ODOO_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "launcher.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# GESTOR DE PROCESOS
# ============================================================
class ProcessManager:
    def __init__(self, log_callback=None):
        self.pg_process = None
        self.odoo_process = None
        self.log_callback = log_callback
        self.log_queue = queue.Queue()
        
    def log(self, msg, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        if self.log_callback:
            self.log_callback(entry, level)
        logger.log(getattr(logging, level.upper()), msg)
    
    def run_command(self, cmd, cwd=None, env=None):
        """Ejecuta comando y captura salida en tiempo real"""
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            return proc
        except Exception as e:
            self.log(f"Error ejecutando {cmd}: {e}", "error")
            return None
    
    def start_postgres(self):
        """Inicia PostgreSQL portable"""
        self.log("Iniciando PostgreSQL...")
        
        pg_bin = POSTGRES_DIR / "bin"
        pg_data = DATA_DIR / "postgresql"
        
        if not pg_data.exists():
            pg_data.mkdir(parents=True)
            # Inicializar cluster
            self.log("Inicializando cluster PostgreSQL...")
            initdb = pg_bin / "initdb.exe"
            if initdb.exists():
                proc = self.run_command([
                    str(initdb),
                    "-D", str(pg_data),
                    "-U", "odoo",
                    "-A", "trust",
                    "-E", "UTF8"
                ])
                if proc:
                    proc.wait()
        
        # Configurar postgresql.conf para puerto 5433
        conf_file = pg_data / "postgresql.conf"
        if conf_file.exists():
            content = conf_file.read_text(encoding='utf-8')
            if f"port = {PG_PORT}" not in content:
                content += f"\nport = {PG_PORT}\n"
                content += "listen_addresses = 'localhost'\n"
                content += "max_connections = 100\n"
                conf_file.write_text(content, encoding='utf-8')
        
        # Iniciar postgres
        postgres_exe = pg_bin / "postgres.exe"
        if postgres_exe.exists():
            self.pg_process = self.run_command([
                str(postgres_exe),
                "-D", str(pg_data)
            ])
            if self.pg_process:
                self.log(f"PostgreSQL iniciado (PID: {self.pg_process.pid})")
                return True
        self.log("No se encontró postgres.exe", "error")
        return False
    
    def stop_postgres(self):
        """Detiene PostgreSQL"""
        if self.pg_process:
            self.log("Deteniendo PostgreSQL...")
            self.pg_process.terminate()
            try:
                self.pg_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.pg_process.kill()
            self.pg_process = None
            self.log("PostgreSQL detenido")
    
    def start_odoo(self):
        """Inicia Odoo"""
        self.log("Iniciando Odoo...")
        
        odoo_bin = ODOO_DIR / "odoo-bin"
        if not odoo_bin.exists():
            # Buscar en instalación de Python
            odoo_bin = Path(sys.executable).parent / "odoo-bin"
        
        if not odoo_bin.exists():
            self.log("No se encontró odoo-bin", "error")
            return False
        
        # Configuración
        config = {
            'db_host': 'localhost',
            'db_port': PG_PORT,
            'db_user': 'odoo',
            'db_password': 'odoo',
            'db_name': 'inmobiliaria',
            'addons_path': str(ODOO_DIR / "addons") + "," + str(ODOO_DIR / "odoo" / "addons"),
            'data_dir': str(DATA_DIR / "odoo"),
            'logfile': str(LOG_DIR / "odoo.log"),
            'log_level': 'info',
            'http_port': ODOO_PORT,
            'admin_passwd': 'admin123',
            'without_demo': 'False',
            'proxy_mode': 'False',
        }
        
        # Escribir config temporal
        config_file = DATA_DIR / "odoo.conf"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write("[options]\n")
            for k, v in config.items():
                f.write(f"{k} = {v}\n")
        
        # Crear BD si no existe
        self.ensure_database()
        
        # Iniciar Odoo
        env = os.environ.copy()
        env['PYTHONPATH'] = str(ODOO_DIR) + ";" + env.get('PYTHONPATH', '')
        
        self.odoo_process = self.run_command([
            sys.executable, str(odoo_bin),
            "-c", str(config_file)
        ], env=env)
        
        if self.odoo_process:
            self.log(f"Odoo iniciado (PID: {self.odoo_process.pid})")
            return True
        return False
    
    def ensure_database(self):
        """Crea la base de datos si no existe"""
        import psycopg2
        try:
            conn = psycopg2.connect(
                host='localhost', port=PG_PORT,
                user='odoo', password='odoo',
                database='postgres'
            )
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'inmobiliaria'")
            if not cur.fetchone():
                self.log("Creando base de datos 'inmobiliaria'...")
                cur.execute("CREATE DATABASE inmobiliaria OWNER odoo")
            cur.close()
            conn.close()
        except Exception as e:
            self.log(f"Error verificando BD: {e}", "warning")
    
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
            self.log("Odoo detenido")
    
    def open_browser(self):
        """Abre navegador en Odoo"""
        url = f"http://localhost:{ODOO_PORT}"
        self.log(f"Abriendo {url}")
        webbrowser.open(url)


# ============================================================
# INTERFAZ GRÁFICA (TKINTER)
# ============================================================
class OdooLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} - Gestor Local")
        self.root.geometry("700x550")
        self.root.minsize(600, 450)
        
        # Icono
        try:
            icon_path = ODOO_DIR / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass
        
        # Process manager
        self.pm = ProcessManager(self.on_log)
        
        # Estado
        self.pg_running = False
        self.odoo_running = False
        
        # Construir UI
        self.build_ui()
        
        # Verificar instalación al inicio
        self.check_installation()
        
        # Timer para actualizar estado
        self.update_status()
    
    def build_ui(self):
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Status.TLabel', font=('Segoe UI', 10))
        style.configure('Green.TLabel', foreground='#27ae60')
        style.configure('Red.TLabel', foreground='#e74c3c')
        style.configure('Orange.TLabel', foreground='#f39c12')
        
        # Frame principal
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title = ttk.Label(main, text=f"🏠 {APP_NAME}", style='Title.TLabel')
        title.pack(pady=(0, 5))
        
        subtitle = ttk.Label(main, text="Sistema Inmobiliario 100% Local & Offline", style='Status.TLabel')
        subtitle.pack(pady=(0, 20))
        
        # Panel de estado
        status_frame = ttk.LabelFrame(main, text="Estado de Servicios", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        # PostgreSQL
        pg_frame = ttk.Frame(status_frame)
        pg_frame.pack(fill=tk.X, pady=3)
        ttk.Label(pg_frame, text="PostgreSQL:", width=15).pack(side=tk.LEFT)
        self.pg_status = ttk.Label(pg_frame, text="● Detenido", style='Red.TLabel')
        self.pg_status.pack(side=tk.LEFT, padx=5)
        self.pg_btn = ttk.Button(pg_frame, text="Iniciar", command=self.toggle_postgres, width=12)
        self.pg_btn.pack(side=tk.LEFT, padx=5)
        
        # Odoo
        odoo_frame = ttk.Frame(status_frame)
        odoo_frame.pack(fill=tk.X, pady=3)
        ttk.Label(odoo_frame, text="Odoo Server:", width=15).pack(side=tk.LEFT)
        self.odoo_status = ttk.Label(odoo_frame, text="● Detenido", style='Red.TLabel')
        self.odoo_status.pack(side=tk.LEFT, padx=5)
        self.odoo_btn = ttk.Button(odoo_frame, text="Iniciar", command=self.toggle_odoo, width=12)
        self.odoo_btn.pack(side=tk.LEFT, padx=5)
        
        # Botón abrir navegador
        self.browser_btn = ttk.Button(odoo_frame, text="🌐 Abrir en Navegador", 
                                      command=self.pm.open_browser, state=tk.DISABLED)
        self.browser_btn.pack(side=tk.LEFT, padx=10)
        
        # Barra de progreso
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
        # Logs
        log_frame = ttk.LabelFrame(main, text="Registro de Actividad", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=12, wrap=tk.WORD,
            font=('Consolas', 9), bg='#1e1e1e', fg='#d4d4d4',
            insertbackground='white'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Colores para log
        self.log_text.tag_config('info', foreground='#9cdcfe')
        self.log_text.tag_config('success', foreground='#4ec9b0')
        self.log_text.tag_config('warning', foreground='#dcdcaa')
        self.log_text.tag_config('error', foreground='#f44747')
        
        # Botones inferiores
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="⚙️ Configuración", command=self.show_config).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="📁 Abrir Carpeta Datos", command=self.open_data_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Reiniciar Todo", command=self.restart_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Salir", command=self.on_close).pack(side=tk.RIGHT)
        
        # Estado inicial
        self.log("Sistema listo. PostgreSQL y Odoo se ejecutan 100% local.", "info")
    
    def on_log(self, msg, level="info"):
        """Callback para logs del ProcessManager"""
        self.root.after(0, lambda: self.append_log(msg, level))
    
    def append_log(self, msg, level="info"):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def log(self, msg, level="info"):
        self.append_log(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", level)
    
    def check_installation(self):
        """Verifica si está todo instalado"""
        missing = []
        if not (POSTGRES_DIR / "bin" / "postgres.exe").exists():
            missing.append("PostgreSQL")
        if not (ODOO_DIR / "odoo-bin").exists() and not (Path(sys.executable).parent / "odoo-bin").exists():
            missing.append("Odoo")
        
        if missing:
            self.log(f"⚠️ Faltan componentes: {', '.join(missing)}", "warning")
            self.log("Ejecuta el instalador completo o instala manualmente.", "warning")
    
    def update_status(self):
        """Actualiza estado de servicios"""
        # Verificar PostgreSQL
        pg_ok = self.check_port(PG_PORT)
        if pg_ok != self.pg_running:
            self.pg_running = pg_ok
            if pg_ok:
                self.pg_status.config(text="● Ejecutándose", style='Green.TLabel')
                self.pg_btn.config(text="Detener")
            else:
                self.pg_status.config(text="● Detenido", style='Red.TLabel')
                self.pg_btn.config(text="Iniciar")
        
        # Verificar Odoo
        odoo_ok = self.check_port(ODOO_PORT)
        if odoo_ok != self.odoo_running:
            self.odoo_running = odoo_ok
            if odoo_ok:
                self.odoo_status.config(text="● Ejecutándose", style='Green.TLabel')
                self.odoo_btn.config(text="Detener")
                self.browser_btn.config(state=tk.NORMAL)
            else:
                self.odoo_status.config(text="● Detenido", style='Red.TLabel')
                self.odoo_btn.config(text="Iniciar")
                self.browser_btn.config(state=tk.DISABLED)
        
        self.root.after(3000, self.update_status)
    
    def check_port(self, port):
        import socket
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except:
            return False
    
    def toggle_postgres(self):
        if self.pg_running:
            self.progress.start()
            threading.Thread(target=self._stop_pg_thread, daemon=True).start()
        else:
            self.progress.start()
            threading.Thread(target=self._start_pg_thread, daemon=True).start()
    
    def _start_pg_thread(self):
        ok = self.pm.start_postgres()
        self.root.after(0, lambda: self.progress.stop())
        if ok:
            self.root.after(2000, lambda: self.log("PostgreSQL listo en puerto 5433", "success"))
    
    def _stop_pg_thread(self):
        self.pm.stop_postgres()
        self.root.after(0, lambda: self.progress.stop())
    
    def toggle_odoo(self):
        if self.odoo_running:
            self.progress.start()
            threading.Thread(target=self._stop_odoo_thread, daemon=True).start()
        else:
            if not self.pg_running:
                self.log("Iniciando PostgreSQL primero...", "info")
                self.pm.start_postgres()
                time.sleep(3)
            self.progress.start()
            threading.Thread(target=self._start_odoo_thread, daemon=True).start()
    
    def _start_odoo_thread(self):
        ok = self.pm.start_odoo()
        self.root.after(0, lambda: self.progress.stop())
        if ok:
            self.root.after(3000, lambda: self.log("Odoo listo en puerto 8069", "success"))
    
    def _stop_odoo_thread(self):
        self.pm.stop_odoo()
        self.root.after(0, lambda: self.progress.stop())
    
    def restart_all(self):
        self.log("Reiniciando todos los servicios...", "info")
        self.pm.stop_odoo()
        self.pm.stop_postgres()
        time.sleep(2)
        self.pm.start_postgres()
        time.sleep(3)
        self.pm.start_odoo()
    
    def open_data_folder(self):
        os.startfile(str(APPDATA_DIR))
    
    def show_config(self):
        msg = f"""Configuración Local:
        
📁 Datos: {DATA_DIR}
🐘 PostgreSQL: {POSTGRES_DIR}
🐍 Odoo: {ODOO_DIR}
📝 Logs: {LOG_DIR}

🔌 Puertos:
   PostgreSQL: {PG_PORT}
   Odoo: {ODOO_PORT}

👤 Usuario BD: odoo
🔑 Password BD: odoo
🗄️ Base de datos: inmobiliaria

🌐 Acceso: http://localhost:{ODOO_PORT}
👤 Login: valegchemes@gmail.com
🔑 Pass: Poloaco123!
"""
        messagebox.showinfo("Configuración", msg)
    
    def on_close(self):
        if self.pg_running or self.odoo_running:
            if messagebox.askyesno("Salir", "¿Detener servicios y salir?"):
                self.pm.stop_odoo()
                self.pm.stop_postgres()
                self.root.destroy()
        else:
            self.root.destroy()


# ============================================================
# ENTRY POINT
# ============================================================
def main():
    # Verificar si ya hay instancia corriendo
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 18069))  # Puerto de lock
    except:
        messagebox.showinfo("Ya en ejecución", 
            f"{APP_NAME} ya está ejecutándose.\nRevisa la bandeja del sistema.")
        return
    
    root = tk.Tk()
    app = OdooLauncherApp(root)
    
    # Manejar cierre de ventana
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Centrar ventana
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()


if __name__ == "__main__":
    main()