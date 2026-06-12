@echo off
chcp 65001 >nul
title Odoo Inmobiliaria - Sistema Local 100% Offline

:: ============================================================
:: CONFIGURACIÓN
:: ============================================================
set APP_NAME=OdooInmobiliaria
set APPDATA_DIR=%APPDATA%\%APP_NAME%
set PG_PORT=5433
set ODOO_PORT=8069

:: Directorios
set DATA_DIR=%APPDATA_DIR%\data
set POSTGRES_DIR=%APPDATA_DIR%\postgresql
set ODOO_DIR=%APPDATA_DIR%\odoo
set LOG_DIR=%APPDATA_DIR%\logs
set CONFIG_FILE=%APPDATA_DIR%\config\odoo.conf

:: ============================================================
:: CREAR DIRECTORIOS
:: ============================================================
mkdir "%DATA_DIR%\postgresql" 2>nul
mkdir "%DATA_DIR%\odoo" 2>nul
mkdir "%LOG_DIR%" 2>nul
mkdir "%APPDATA_DIR%\config" 2>nul

:: ============================================================
:: VERIFICAR POSTGRESQL
:: ============================================================
echo [INFO] Verificando PostgreSQL...
if not exist "%POSTGRES_DIR%\bin\postgres.exe" (
    echo [WARN] PostgreSQL no encontrado en %POSTGRES_DIR%
    echo [INFO] Buscando en instalación del sistema...
    where postgres.exe >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] PostgreSQL no instalado.
        echo [INFO] Instale PostgreSQL 16+ o use el instalador completo.
        pause
        exit /b 1
    )
    set POSTGRES_BIN=postgres.exe
) else (
    set POSTGRES_BIN="%POSTGRES_DIR%\bin\postgres.exe"
)

:: ============================================================
:: INICIAR POSTGRESQL
:: ============================================================
echo [INFO] Iniciando PostgreSQL en puerto %PG_PORT%...
set PGDATA=%DATA_DIR%\postgresql

:: Verificar si ya está corriendo
netstat -an | findstr ":%PG_PORT%" >nul
if %errorlevel% equ 0 (
    echo [INFO] PostgreSQL ya está ejecutándose en puerto %PG_PORT%
) else (
    :: Inicializar cluster si no existe
    if not exist "%PGDATA%\PG_VERSION" (
        echo [INFO] Inicializando cluster PostgreSQL...
        "%POSTGRES_DIR%\bin\initdb.exe" -D "%PGDATA%" -U odoo -A trust -E UTF8
        if %errorlevel% neq 0 (
            echo [ERROR] Falló inicialización de PostgreSQL
            pause
            exit /b 1
        )
        :: Configurar puerto
        echo port = %PG_PORT% >> "%PGDATA%\postgresql.conf"
        echo listen_addresses = 'localhost' >> "%PGDATA%\postgresql.conf"
        echo max_connections = 100 >> "%PGDATA%\postgresql.conf"
    )
    
    :: Iniciar PostgreSQL en background
    start /b "" %POSTGRES_BIN% -D "%PGDATA%"
    echo [INFO] PostgreSQL iniciado (PID capturado en logs)
    
    :: Esperar a que esté listo
    echo [INFO] Esperando a PostgreSQL...
    timeout /t 3 >nul
)

:: ============================================================
:: CREAR BASE DE DATOS SI NO EXISTE
:: ============================================================
echo [INFO] Verificando base de datos...
"%POSTGRES_DIR%\bin\psql.exe" -h localhost -p %PG_PORT% -U odoo -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'inmobiliaria'" 2>nul | findstr "1 row" >nul
if %errorlevel% neq 0 (
    echo [INFO] Creando base de datos 'inmobiliaria'...
    "%POSTGRES_DIR%\bin\createdb.exe" -h localhost -p %PG_PORT% -U odoo inmobiliaria
)

:: ============================================================
:: VERIFICAR ODOO
:: ============================================================
echo [INFO] Verificando Odoo...
if not exist "%ODOO_DIR%\odoo-bin" (
    :: Buscar en instalación Python
    where odoo-bin >nul 2>nul
    if %errorlevel% equ 0 (
        set ODOO_BIN=odoo-bin
    ) else (
        echo [ERROR] Odoo no encontrado.
        echo [INFO] Ejecute: pip install -e %~dp0..\odoo
        pause
        exit /b 1
    )
) else (
    set ODOO_BIN="%ODOO_DIR%\odoo-bin"
)

:: ============================================================
:: GENERAR CONFIGURACIÓN ODOO
:: ============================================================
echo [INFO] Generando configuración...
(
    echo [options]
    echo db_host = localhost
    echo db_port = %PG_PORT%
    echo db_user = odoo
    echo db_password = odoo
    echo db_name = inmobiliaria
    echo addons_path = %APPDATA_DIR%\addons,%ODOO_DIR%\addons
    echo data_dir = %DATA_DIR%\odoo
    echo logfile = %LOG_DIR%\odoo.log
    echo log_level = info
    echo http_port = %ODOO_PORT%
    echo admin_passwd = admin123
    echo without_demo = False
    echo proxy_mode = False
    echo dev_mode = reload,qweb,werkzeug,xml
    echo limit_memory_hard = 2684354560
    echo limit_memory_soft = 2147483648
    echo workers = 0
) > "%CONFIG_FILE%"

:: ============================================================
:: INICIAR ODOO
:: ============================================================
echo [INFO] Iniciando Odoo en puerto %ODOO_PORT%...
echo [INFO] Acceso: http://localhost:%ODOO_PORT%
echo [INFO] Usuario: valegchemes@gmail.com
echo [INFO] Password: Poloaco123!
echo.
echo [INFO] Presione Ctrl+C para detener ambos servicios
echo.

:: Abrir navegador automáticamente
start "" "http://localhost:%ODOO_PORT%"

:: Ejecutar Odoo
python %ODOO_BIN% -c "%CONFIG_FILE%"

:: ============================================================
:: LIMPIEZA AL SALIR
:: ============================================================
echo.
echo [INFO] Deteniendo servicios...
taskkill /f /im postgres.exe >nul 2>nul
echo [INFO] Servicios detenidos. ¡Hasta luego!
pause