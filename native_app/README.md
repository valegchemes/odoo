# 🏠 Odoo Inmobiliaria - App Nativa Windows

**Aplicación de escritorio 100% nativa** para Windows. Sin navegador, sin localhost visible, sin Docker, sin nube.

---

## ✨ Qué es esto

Una **app .exe instalable** que incluye todo embebido:
- 🐘 **PostgreSQL 16** portable (puerto 5433 interno)
- 🐍 **Python 3.11+** + Odoo 19 completo
- 🌐 **WebView2** (motor Microsoft Edge) como interfaz nativa
- 📦 **Tu módulo `inmobiliaria_core`** preinstalado

**Resultado:** Un solo `.exe` (≈120 MB) que instalas como cualquier programa Windows.

---

## 🎯 Características Nativas

| Característica | Implementación |
|----------------|----------------|
| Ventana propia | WebView2 (Edge Chromium) sin barra de direcciones |
| Sin localhost visible | Puerto 8069 solo interno (127.0.0.1) |
| Inicio automático | Opcional: se lanza minimizado al boot |
| Datos locales | `%APPDATA%\OdooInmobiliaria\` (persiste tras desinstalar) |
| Hot-reload dev | `dev_mode=reload,qweb,werkzeug,xml` activo |
| Acceso directo | `odooinmobiliaria://` protocolo personalizado |
| Sistema de archivos | Acceso nativo a archivos locales desde Odoo |

---

## 🚀 Compilar el .EXE

### Requisitos
- Windows 10/11 (x64)
- Python 3.11+ instalado
- Visual C++ Build Tools (para psycopg2)

### Pasos

```powershell
cd E:\proyectos\Odoo Flipping\odoo-19.0

# 1. Instalar dependencias de build
pip install pyinstaller pillow

# 2. Compilar (descarga PostgreSQL portable automáticamente)
python native_app/build_native.py
```

### Resultado
```
dist_native/OdooInmobiliaria.exe    (~120 MB)
```
> Incluye: Python + WebView2 runtime + Odoo 19 + psycopg2 + tu módulo + config

---

## 📦 Crear Instalador .EXE/.MSI (Inno Setup)

### 1. Instalar Inno Setup 6+
https://jrsoftware.org/isdl.php

### 2. Compilar instalador
```powershell
# Abre en Inno Setup Compiler:
E:\proyectos\Odoo Flipping\odoo-19.0\installer\setup_native.iss
# → Build → Compile
```

### 3. Resultado
```
dist_native/OdooInmobiliaria_Setup_19.0.1.0.exe
```
> Instalador profesional con: acceso directo, autostart opcional, desinstalador, protocolo `odooinmobiliaria://`

---

## 🖥️ Ejecutar en Desarrollo (Sin Compilar)

```powershell
cd E:\proyectos\Odoo Flipping\odoo-19.0

# Instalar dependencias
pip install -r native_app/requirements.txt
pip install -e odoo

# Ejecutar app nativa
python native_app/main.py
```

> Se abre ventana nativa con WebView2, inicia PostgreSQL + Odoo en background, carga `http://localhost:8069/web/login`

---

## 🏗️ Arquitectura Interna

```
OdooInmobiliaria.exe (PyInstaller onefile)
│
├── 🌐 WebView2 Window (main.py)
│   ├── NativeAPI (exposed to JS)
│   │   ├── get_status()
│   │   ├── restart_backend()
│   │   ├── minimize/maximize/close_window()
│   │   └── get_app_info()
│   └── Custom CSS injection (native scrollbars, hide web UI)
│
├── ⚙️ BackendManager (thread separado)
│   ├── PostgreSQL Manager
│   │   ├── initdb() → %APPDATA%\data\postgresql
│   │   ├── start() → puerto 5433
│   │   └── stop()
│   │
│   └── Odoo Manager
│       ├── generate config → %APPDATA%\config\odoo.conf
│       ├── ensure_database() → createdb inmobiliaria
│       ├── start() → puerto 8069 (workers=0, dev_mode)
│       └── stop()
│
└── 📁 Datos Persistentes (%APPDATA%\OdooInmobiliaria\)
    ├── data\postgresql\     # Cluster PG
    ├── data\odoo\           # Filestore, sessions
    ├── addons\              # Tu módulo inmobiliaria_core
    ├── config\odoo.conf     # Config resuelta
    ├── logs\                # app.log, odoo.log
    └── webview2_data\       # Cache WebView2
```

---

## 🔧 Configuración Avanzada

### Cambiar puertos
Edita `native_app/main.py`:
```python
PG_PORT = 5433      # PostgreSQL
ODOO_PORT = 8069    # Odoo HTTP
```

### Ventana sin bordes (frameless)
En `main.py`:
```python
frameless=True,  # Ventana sin barra título nativa
easy_drag=True,  # Arrastrar desde cualquier punto
```
> Requiere implementar botones cerrar/min/max custom en HTML/JS

### Inyectar JavaScript personalizado
```python
def inject_custom_styles(self):
    js = """
    // Tu JS aquí - acceso a NativeAPI via pywebview.api
    window.pywebview.api.get_status().then(console.log);
    """
    self.window.evaluate_js(js)
```

### Protocolo personalizado `odooinmobiliaria://`
El instalador registra:
```
odooinmobiliaria://abrir/propiedad/123
```
En `main.py` maneja:
```python
def handle_protocol(self, url):
    # url = "odooinmobiliaria://abrir/propiedad/123"
    # parsear y navegar en WebView2
    self.window.load_url(f"{ODOO_URL}/web#id=123&model=real.estate.property")
```

---

## 📋 Checklist Producción

- [ ] Compilar con `python native_app/build_native.py`
- [ ] Probar .exe en máquina limpia (sin Python, sin PostgreSQL)
- [ ] Verificar: primera ejecución descarga PG, crea BD, abre login
- [ ] Firmar código (certificado EV) para evitar SmartScreen
- [ ] Crear instalador con Inno Setup (`setup_native.iss`)
- [ ] Probar instalador: instalar → lanzar → login → trabajar
- [ ] Probar desinstalador: borra app, mantiene datos en AppData
- [ ] Probar autostart: reiniciar PC → app minimizada en tray
- [ ] Configurar actualizaciones automáticas (GitHub Releases API)

---

## 🆘 Solución de Problemas

| Error | Solución |
|-------|----------|
| `WebView2 not found` | Windows 10 1803+ lo incluye. Si no: `winget install Microsoft.EdgeWebView2Runtime` |
| `postgres.exe not found` | El .exe lo descarga automáticamente en primera ejecución (requiere internet 1 vez) |
| `Port 5433 in use` | Cambiar `PG_PORT` en `main.py` y recompilar |
| `Module not found: odoo` | `pip install -e odoo` antes de compilar |
| Ventana blanca | Verificar `webview.start()` y que Odoo esté listo en puerto 8069 |
| `Permission denied` en AppData | Ejecutar como Admin una vez, o `icacls %APPDATA%\OdooInmobiliaria /grant Everyone:F /T` |

---

## 📦 Distribución

### Opciones:
1. **Solo .exe** (`dist_native/OdooInmobiliaria.exe`) → Portable, sin instalador
2. **Instalador .exe** (`setup_native.iss` → Inno Setup) → Profesional, con shortcuts, autostart, desinstalador
3. **Microsoft Store** → Empaquetar como MSIX (requiere certificado)
4. **Winget/Chocolatey** → Publicar en repositorios comunitarios

### Tamaños aproximados:
| Componente | Tamaño |
|------------|--------|
| .exe standalone | ~120 MB |
| Instalador .exe | ~115 MB (comprimido lzma) |
| Instalado en disco | ~350 MB (incluye PG data, Odoo cache) |

---

## 🔐 Seguridad

- **Sin red externa**: Solo localhost (127.0.0.1)
- **Datos encriptados**: Opcional - habilitar `cryptography` en `requirements.txt`
- **Firma digital**: Requerida para distribución pública (evita SmartScreen)
- **Actualizaciones**: Verificar firma antes de auto-update

---

## 📞 Soporte

- **Logs**: `%APPDATA%\OdooInmobiliaria\logs\app.log`
- **Config**: `%APPDATA%\OdooInmobiliaria\config\odoo.conf`
- **Datos**: `%APPDATA%\OdooInmobiliaria\data\`

---

**¡App 100% tuya, 100% local, 100% nativa Windows!** 🏠💻