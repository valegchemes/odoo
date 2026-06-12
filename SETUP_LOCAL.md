# Odoo 19 - Setup Local para Desarrollo Inmobiliario

## 📋 Requisitos Previos

| Herramienta | Versión | Instalación |
|-------------|---------|-------------|
| **Docker Desktop** | 4.0+ | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **Git** | 2.0+ | [git-scm.com](https://git-scm.com/) |
| **VS Code** (opcional) | - | [code.visualstudio.com](https://code.visualstudio.com/) + extensiones: Python, Docker, YAML |

> **Windows:** Habilita WSL2 en Docker Desktop → Settings → General → Use WSL2 based engine
> **Mac:** Docker Desktop para Apple Silicon o Intel
> **Linux:** `sudo apt install docker.io docker-compose-plugin` + `sudo usermod -aG docker $USER`

---

## 🚀 Paso a Paso (5 minutos)

### 1. Clonar/Ubicar el proyecto
```bash
cd E:/proyectos/Odoo\ Flipping/odoo-19.0
```

### 2. Crear estructura de carpetas
```bash
mkdir -p addons config logs backups
```
> `addons/` → **Tus módulos custom aquí** (inmobiliaria_core, inmobiliaria_website, etc.)
> `config/` → ya tiene `odoo.conf`
> `logs/` → logs persistentes
> `backups/` → para `pg_dump`

### 3. Levantar todo
```bash
docker compose up -d
```

### 4. Verificar que arrancó
```bash
# Ver logs en tiempo real
docker compose logs -f odoo

# Deberías ver al final:
# INFO odoo.service.server: HTTP service running on 0.0.0.0:8069
```

### 5. Acceder a Odoo
| Servicio | URL | Credenciales |
|----------|-----|--------------|
| **Odoo** | http://localhost:8069 | Primera vez: crea BD + admin |
| **pgAdmin** | http://localhost:5050 | admin@local.com / admin |
| **PostgreSQL** | localhost:5432 | odoo / odoo / odoo |

---

## 🎯 Primera Configuración en Odoo

1. Abre http://localhost:8069
2. **Master Password:** `admin123` (la de `odoo.conf`)
3. **Database Name:** `inmobiliaria_dev`
4. **Email:** `admin@local.com`
5. **Password:** `admin123`
6. ✅ **Load demonstration data** (para ver ejemplos)
7. Click **Create database**

> Espera 30-60 seg la primera vez (crea tablas, carga módulos base, demo data)

---

## 🏗️ Estructura para tu Módulo Inmobiliario

```
addons/
└── inmobiliaria_core/          # Tu módulo principal
    ├── __manifest__.py         # Metadatos (requerido)
    ├── __init__.py             # Importa models, controllers, wizards
    ├── models/
    │   ├── __init__.py
    │   ├── property.py         # Modelo: inmueble
    │   ├── property_type.py    # Tipo: casa, depto, terreno, local
    │   ├── offer.py            # Ofertas de compra/alquiler
    │   └── tag.py              # Etiquetas: piscina, jardín, céntrico
    ├── views/
    │   ├── property_views.xml  # Vistas tree/form/kanban/search
    │   ├── property_menu.xml   # Menús y actions
    │   └── templates.xml       # Plantillas QWeb (web)
    ├── security/
    │   ├── ir.model.access.csv # Permisos ACL
    │   └── security.xml        # Reglas record rules
    ├── data/
    │   └── demo_data.xml       # Datos de prueba
    └── wizards/
        └── export_wizard.py    # Asistentes (exportar PDF, etc.)
```

### __manifest__.py mínimo
```python
{
    'name': 'Inmobiliaria Core',
    'version': '19.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Gestión de propiedades, ofertas y clientes',
    'depends': ['base', 'mail', 'website', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/property_views.xml',
        'views/property_menu.xml',
        'data/demo_data.xml',
    ],
    'demo': ['data/demo_data.xml'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

---

## 🔄 Flujo de Trabajo Diario

### Cambiar código Python → **Auto-reload** (3 seg)
```bash
# Editas addons/inmobiliaria_core/models/property.py
# Odoo recarga solo, NO reinicia container
```

### Cambiar vistas XML → **Auto-reload** (instantáneo)
```bash
# Editas addons/inmobiliaria_core/views/property_views.xml
# Refresca navegador (F5)
```

### Añadir campo nuevo al modelo
```bash
# 1. Editas models/property.py → añades campo
# 2. Editas views/property_views.xml → añades campo en form/tree
# 3. En Odoo: Apps → Update Apps List → Update inmobiliaria_core
#    (o reinicia: docker compose restart odoo)
```

### Ver logs en vivo
```bash
docker compose logs -f odoo --tail=100
```

### Debugging en VS Code
1. `Ctrl+Shift+P` → "Docker: Attach to Container" → `odoo19_app`
2. Pon breakpoints en `.py`
3. Ejecuta acción en Odoo → se para en breakpoint

---

## 🛠️ Comandos Útiles

```bash
# Parar todo (datos persisten en volumes)
docker compose down

# Parar + BORRAR base de datos (¡cuidado!)
docker compose down -v

# Reiniciar solo Odoo (mantiene BD)
docker compose restart odoo

# Rebuild imagen (si cambias Dockerfile o requirements)
docker compose up -d --build

# Backup BD
docker exec odoo19_db pg_dump -U odoo odoo > backups/backup_$(date +%F).sql

# Restore BD
docker exec -i odoo19_db psql -U odoo odoo < backups/backup_2024-01-15.sql

# Shell en contenedor Odoo
docker exec -it odoo19_app bash

# Shell en PostgreSQL
docker exec -it odoo19_db psql -U odoo -d odoo

# Ver uso de recursos
docker stats
```

---

## 🌐 Exponer en Red Local (opcional)

Para probar desde móvil/tablet en misma WiFi:

```bash
# Obtuve tu IP local
ipconfig | findstr IPv4   # Windows
ifconfig | grep inet      # Mac/Linux

# Edita docker-compose.yml → odoo service:
#   environment:
#     - HTTP_HOST=0.0.0.0
#   ports:
#     - "0.0.0.0:8069:8069"

docker compose up -d
# Accede desde móvil: http://192.168.1.XX:8069
```

---

## 📦 Módulos Base Útiles para Inmobiliaria

| Módulo | Descripción | Instalar |
|--------|-------------|----------|
| `real_estate` | **Core inmobiliario nativo Odoo 17+** | ✅ Obligatorio |
| `website` | Web pública + CMS | ✅ |
| `website_blog` | Blog para novedades | ✅ |
| `crm` | Leads, oportunidades, pipeline | ✅ |
| `account` | Facturación, contabilidad | ✅ |
| `sign` | Firmas digitales contratos | ✅ |
| `documents` | Gestión docs (escrituras, planos) | ✅ |
| `project` | Seguimiento obras/gestiones | Opcional |
| `hr_expense` | Gastos agentes/visitas | Opcional |
| `mail` | Chatter, notificaciones | Ya viene |

> En Odoo: **Apps** → quita filtro "Apps" → busca `real_estate` → Install

---

## ⚠️ Problemas Comunes

| Error | Solución |
|-------|----------|
| `port 5432 already in use` | Tenés PostgreSQL local corriendo → `sudo systemctl stop postgresql` o cambia puerto en `docker-compose.yml` |
| `permission denied /var/lib/odoo` | `sudo chown -R 101:101 ./addons ./config ./logs` (Linux/Mac) |
| `ModuleNotFoundError` en tu módulo | Verifica `__init__.py` importa todo: `from . import models, controllers, wizards` |
| Vista no refleja cambios | Apps → Update Apps List → Update tu_módulo |
| BD corrupta / no arranca | `docker compose down -v && docker compose up -d` (pierdes datos) |

---

## 🎯 Próximos Pasos Recomendados

1. **Instala `real_estate`** nativo y explora sus modelos
2. **Crea `inmobiliaria_core`** heredando/extendiendo `real_estate.property`
3. **Añade campos específicos:** `m2_cubiertos`, `m2_descubiertos`, `expensas`, `cochera`, `amenities`
4. **Website:** Crea páginas públicas con `website_sale` + `real_estate` para publicar propiedades
5. **CRM:** Configura pipeline: Lead → Visita → Oferta → Reserva → Escritura
6. **Account:** Plan contable AR (AFIP) + facturación automática al cerrar operación

---

## 📚 Recursos

- **Docs Odoo 19:** https://www.odoo.com/documentation/19.0/
- **Dev Tutorial:** https://www.odoo.com/documentation/19.0/developer/howtos.html
- **Real Estate Module:** https://github.com/odoo/odoo/tree/19.0/addons/real_estate
- **Foro ES:** https://www.odoo.com/forum/es
- **Discord Odoo ES:** https://discord.gg/odoo

---

**¿Listo? Ejecuta `docker compose up -d` y en 2 minutos tienes Odoo 19 corriendo local.** 🚀