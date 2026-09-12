# 🏪 Gestión Comercial — Productos, Inventario, POS y Facturación

Aplicación web completa para un negocio que vende **productos con variantes** (color, talla, sabor…) y **productos a granel** (por libra o kilo). Cubre todo el ciclo comercial:

**Crear productos → Registrar compras → Configurar precios → Controlar inventario → Vender (POS) → Facturar.**

Pensada para tiendas, misceláneas, tiendas de ropa o graneros que necesitan un sistema simple con dos roles: **Administrador** (gestiona todo) y **Vendedor** (solo vende en mostrador).

**Novedades de la versión 2:**

- **Actualización en tiempo real (WebSocket):** al crear un producto, registrar una compra o ajustar inventario, los cambios se reflejan al instante en el POS, inventario y listados de todos los usuarios conectados — sin recargar el navegador.
- **Reportes** (admin): ventas por periodo y por día, métodos de pago, productos más vendidos y **utilidad estimada** (precio de venta vs. último costo de compra al momento de vender).
- **Cliente en la factura**: nombre y cédula/NIT opcionales al cobrar.
- **Descuentos por línea** en el punto de venta (%), reflejados en la factura.
- **Lector de código de barras**: asigna un código a cada variante y escanéalo en el POS para agregar directo al carrito (los lectores USB escriben el código + Enter).
- **Cierre de caja**: apertura de turno con base, arqueo al cierre con efectivo esperado vs. contado y diferencia; historial de turnos.
- **Anulación de compras** con reversión de inventario (bloqueada si la mercancía ya se vendió).
- **Búsqueda de facturas por número** en toda la base de datos.
- **Migraciones con Alembic** (`backend/alembic/`), validación de `JWT_SECRET` al arrancar en producción, integración opcional con Sentry (variable `SENTRY_DSN`), CI en GitHub Actions y cabeceras de seguridad HTTP en el frontend.

---

## Tabla de contenido

1. [Stack y arquitectura](#stack-y-arquitectura)
2. [Estructura de carpetas](#estructura-de-carpetas)
3. [Correr el proyecto en local](#correr-el-proyecto-en-local)
4. [Guía de uso paso a paso](#guía-de-uso-paso-a-paso)
5. [Roles de usuario](#roles-de-usuario)
6. [Pruebas](#pruebas)
7. [Despliegue gratis en Vercel + Supabase](#despliegue-gratis-en-vercel--supabase)
8. [Checklist E2E manual](#checklist-e2e-manual)
9. [Decisiones técnicas clave](#decisiones-técnicas-clave)

---

## Stack y arquitectura

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12+ · FastAPI · SQLAlchemy 2 · Pydantic v2 |
| Base de datos | PostgreSQL (Supabase) en producción · SQLite en desarrollo |
| Frontend | React 18 + Vite · React Router · TanStack Query · Tailwind CSS 4 |
| Auth | JWT (PyJWT, HS256) · contraseñas con pbkdf2-sha256 (600k iteraciones) |
| Despliegue | Vercel (backend serverless + frontend) · Supabase (Postgres gratis) · **Docker** (local) |

**¿Por qué módulos?** Backend y frontend replican la misma división por dominios (`products`, `purchases`, `pricing`, `inventory`, `sales`, `invoices`, `auth`). Cada módulo backend tiene `models.py` (tablas), `schemas.py` (validación), `service.py` (lógica de negocio y transacciones) y `router.py` (endpoints). Los routers nunca tocan la base de datos directamente: toda la lógica vive en los services, lo que facilita testear y mantener.

**Diseño serverless.** El backend corre como una función serverless de Vercel (`api/index.py`), sin estado en memoria: los consecutivos de SKU y de factura viven en contadores de la base de datos actualizados atómicamente, y las conexiones a Supabase van por su pooler (pgbouncer) con `NullPool` de SQLAlchemy.

**Puntos fuertes del modelo de datos:**

- **Atributos dinámicos**: color, talla y sabor no están "quemados" en el esquema. Son filas de las tablas `attributes`/`attribute_values`; puedes crear "Material" o "Aroma" desde la interfaz sin tocar la base de datos.
- **Todo se vende por variante**: un producto simple o a granel tiene una variante "default" transparente, así compras, stock y ventas siempre apuntan a `variant_id` (modelo uniforme).
- **Kardex append-only**: cada entrada/salida/ajuste queda registrada con el saldo resultante; nunca se edita ni borra.
- **Venta atómica**: el descuento de stock usa `UPDATE ... WHERE quantity >= cantidad` — dos vendedores no pueden sobrevender la misma unidad, y si una línea falla, toda la venta se revierte (ni stock, ni kardex, ni factura).
- **Facturas inmutables**: cada línea guarda snapshot de SKU, descripción, precio e IVA; la factura guarda snapshot de los datos del negocio. Cambiar precios o el NIT después no altera facturas emitidas.
- **Consecutivo sin huecos**: el número de factura se toma de un contador con row-lock dentro de la misma transacción de la venta.

---

## Estructura de carpetas

```
saas_small/
├── backend/
│   ├── api/index.py                  # Entrypoint de Vercel (expone la app FastAPI)
│   ├── vercel.json                   # Rewrite: todo → /api/index
│   ├── requirements.txt              # Dependencias de producción (mínimas)
│   ├── requirements-dev.txt          # + uvicorn, pytest, httpx
│   ├── .env.example                  # Variables de entorno documentadas
│   ├── scripts/seed.py               # Crea tablas + admin + atributos base
│   ├── app/
│   │   ├── main.py                   # FastAPI, CORS, registro de routers
│   │   ├── core/
│   │   │   ├── config.py             # Settings desde variables de entorno
│   │   │   ├── db.py                 # Engine (NullPool en Postgres), get_db
│   │   │   ├── security.py           # Hash pbkdf2 + JWT
│   │   │   ├── deps.py               # get_current_user, require_admin
│   │   │   └── money.py             # Decimal, redondeo, conversión kg/lb
│   │   ├── models/base.py            # Base declarativa + timestamps
│   │   └── modules/
│   │       ├── auth/                 # Usuarios, login, configuración del negocio
│   │       ├── products/             # Productos, categorías, atributos, variantes, SKU
│   │       ├── purchases/            # Proveedores y compras (entradas)
│   │       ├── pricing/              # Precios, margen, borrador/publicado
│   │       ├── inventory/            # Stock, umbrales, kardex, ajustes
│   │       ├── sales/                # Catálogo POS y venta transaccional
│   │       ├── invoices/             # Facturas y consecutivo
│   │       └── dashboard/            # Resumen del panel admin
│   └── tests/                        # Suite pytest (29 tests de caja negra)
├── frontend/
│   ├── vercel.json                   # Fallback SPA → index.html
│   ├── vite.config.ts                # Proxy /api → localhost:8000 en dev
│   ├── .env.example                  # VITE_API_URL
│   └── src/
│       ├── lib/                      # api.ts (fetch+JWT), auth.tsx, money.ts (COP)
│       ├── components/               # UI reutilizable + layout con menú por rol
│       └── features/                 # Una carpeta por módulo (espejo del backend)
│           ├── auth/  products/  purchases/  pricing/
│           ├── inventory/  sales/  invoices/  dashboard/  settings/
└── README.md
```

---

## Correr el proyecto en local

Requisitos: **Python 3.12+** y **Node 20+**.

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
python scripts/seed.py          # crea la BD SQLite (dev.db) + usuario admin + atributos
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000 · Documentación interactiva: http://localhost:8000/api/docs
- Usuario inicial: **admin@negocio.com / admin123** (cámbialo después)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173 (o el puerto que indique Vite). En desarrollo no necesitas configurar nada: el proxy de Vite redirige `/api` al backend local.

---

### Despliegue local con Docker

> Requisito: **Docker** y **Docker Compose** instalados en cualquier sistema operativo.

```bash
git clone https://github.com/TU_USUARIO/saas_small.git
cd saas_small
docker compose up -d
```

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Documentación interactiva | http://localhost:8000/api/docs |
| Base de datos | `postgresql://postgres:postgres@localhost:5432/saas_small` |

El `docker compose up` hace todo automáticamente:

1. Crea un contenedor **PostgreSQL 16** con la base de datos `saas_small`.
2. Construye y arranca el **backend** (FastAPI), ejecuta las migraciones con Alembic y siembra los datos iniciales (admin, atributos base).
3. Construye y arranca el **frontend** (React + Vite) servido por Nginx, que también redirige `/api` al backend (sin CORS).

**Usuario inicial:** `admin@negocio.com` / `admin123`

> Todo el estado se guarda en un volumen Docker (`pgdata`). Los datos persisten entre reinicios. Para borrar todo: `docker compose down -v`.

**Variables de entorno configurables** (en `docker-compose.yml`, sección `backend.environment`):

| Variable | Defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/saas_small` | Conexión a la base local |
| `JWT_SECRET` | `dev-secret-no-usar-en-produccion` | Secreto para firmar tokens |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Orígenes permitidos |
| `ENV` | `development` | Entorno (`development` o `production`) |

> **Importante:** La configuración original de producción (Vercel + Supabase) está intacta. Los archivos `.env`, `vercel.json` y la lógica de `config.py` no se modificaron. El despliegue con Docker usa exclusivamente las variables definidas en `docker-compose.yml`.

---

## Actualización en tiempo real (WebSockets)

El sistema usa **WebSockets** para sincronizar los cambios entre todos los usuarios en vivo, sin necesidad de recargar el navegador.

### Qué se actualiza automáticamente

| Acción | Se refleja en |
|---|---|
| Crear/editar/eliminar producto | POS (catálogo), Productos |
| Registrar compra | Inventario, POS (stock), Compras, Dashboard |
| Ajustar inventario | Inventario, POS (stock) |
| Realizar venta | Inventario (stock), POS (catálogo), Ventas, Dashboard |

### Cómo funciona

1. El backend emite eventos por WebSocket cada vez que ocurre un cambio relevante.
2. El frontend mantiene una conexión WebSocket persistente (se reconecta automáticamente si se cae).
3. Al recibir un evento, React Query invalida las consultas afectadas, y TanStack Query re-fetch automáticamente los datos actualizados.
4. **Ambos usuarios** (admin y vendedor) ven los cambios instantáneamente sin hacer clic en nada.

### Endpoint WebSocket

```
ws://localhost:8000/api/v1/dashboard/ws?token=<JWT_TOKEN>
```

El token se obtiene del `localStorage` automáticamente. La reconexión es automática cada 3 segundos si la conexión se pierde.

---

## Auto-inicio al encender el equipo

Para que la aplicación arranque automáticamente al prender o reiniciar el computador:

### Opción 1: Docker con `restart: always` (recomendado)

El `docker-compose.yml` usa la política `restart: unless-stopped` por defecto. Si Docker Desktop está configurado para iniciar con Windows, los servicios arrancan solos.

1. **Configurar Docker Desktop para que inicie con Windows:**
   - Abre Docker Desktop → **Settings** → **General**
   - Marca **"Start Docker Desktop when you sign in to your computer"**
   - Aplica y cierra

2. **Agregar `restart: unless-stopped` a cada servicio en `docker-compose.yml`** (si no está):

   ```yaml
   services:
     db:
       restart: unless-stopped
       # ...
     backend:
       restart: unless-stopped
       # ...
     frontend:
       restart: unless-stopped
       # ...
   ```

3. **Probar:** Reinicia el equipo. Los contenedores arrancan solos en ~30 segundos.
   - Frontend: http://localhost:3000
   - API: http://localhost:8000

### Opción 2: Windows Task Scheduler

Crea una tarea programada que ejecute el script `deploy.bat` al iniciar sesión.

1. Abre **Task Scheduler** (`taskschd.msc`).
2. **Create Task**:
   - **General**: Nombre = "Gestion Comercial", marcado "Run whether user is logged on or not" y "Run with highest privileges".
   - **Triggers**: **New** → "At startup" (o "At log on").
   - **Actions**: **New** → Start a program → Programa = `C:\ruta\completa\a\deploy.bat`.
   - **Conditions**: Desmarca "Stop if the computer switches to battery power".
   - **Settings**: Marca "Allow task to run on demand" y "If task fails, restart every 5 minutes".
3. **OK** y pon tu contraseña de Windows cuando la pida.

Con esto, cada vez que inicies sesión en Windows, la aplicación se desplegará automáticamente.

### Opción 3: Script de inicio manual

Crea un acceso directo a `deploy.bat` en la carpeta de inicio de Windows:

1. Presiona `Win + R`, escribe `shell:startup`, Enter.
2. Copia un acceso directo a `deploy.bat` dentro de esa carpeta.
3. Al iniciar sesión, se ejecutará automáticamente.

---

## URLs del proyecto

| Servicio | URL |
|---|---|
| Frontend (producción Docker) | http://localhost:3000 |
| Frontend (desarrollo Vite) | http://localhost:5173 |
| API | http://localhost:8000 |
| Documentación interactiva | http://localhost:8000/api/docs |
| Health check | http://localhost:8000/api/health |

**Usuarios predefinidos:**

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | admin@negocio.com | admin123 |
| Vendedor | vendedor1@negocio.com | vendedor123 |

---

## Guía de uso paso a paso

### 1. Crear un producto con variantes

1. Entra como administrador → **Productos** → **+ Nuevo producto**.
2. Escribe el nombre (ej. *Camisa polo*). El SKU se genera solo (`CAMISA-001`).
3. Deja unidad de medida en **Por unidad**.
4. (Opcional) Define IVA %; si lo dejas vacío usa el predeterminado del negocio.
5. En **Variantes**, toca los valores que maneja el producto: p. ej. colores *Rojo* y *Azul* + tallas *M* y *L* → se crean 4 variantes (`CAMISA-001-ROJ-M`, `CAMISA-001-AZU-L`, …).
6. ¿Necesitas otro tipo de atributo (Material, Aroma…)? **Productos → Atributos → + Nuevo atributo**, sin tocar la base de datos.

**Producto a granel:** elige unidad **kilo (kg)** o **libra (lb)**. El stock se lleva internamente en kg y podrás vender en kg o lb indistintamente.

### 2. Registrar una compra

1. **Compras → + Registrar compra**.
2. Elige el proveedor (créalo en **Proveedores** si no existe) y la fecha.
3. Busca cada producto, selecciona la variante, e indica cantidad y costo unitario.
   - Granel: puedes digitar la compra **en kg o en lb**; el sistema convierte a kg con el factor exacto (1 lb = 0.45359237 kg) y guarda lo que digitaste para auditoría.
4. **Confirmar compra** → el stock sube automáticamente y queda el movimiento en el kardex.

### 3. Configurar un precio

1. **Precios** → busca la variante → **Editar**.
2. Dos formas:
   - **Precio directo**: escribes el precio de venta.
   - **Por margen**: escribes un % y el sistema calcula `último costo × (1 + margen)`.
3. Granel: defines precio por kg y el sistema **sugiere** el precio por lb equivalente, pero puedes redondearlo a un precio comercial (ej. $5.000/lb).
4. **Publicar** → solo entonces la variante aparece en el punto de venta. Mientras esté en *Borrador* no se puede vender.

### 4. Capturar un pedido y facturar

1. **Punto de venta** (pantalla principal del vendedor).
2. Busca por nombre o código en el buscador (siempre enfocado) y toca el producto para agregarlo al carrito.
   - Por unidad: botones −/+ para la cantidad.
   - Granel: digita el peso y elige kg o lb.
3. El carrito muestra subtotal, IVA y total en vivo (el total definitivo lo calcula el servidor).
4. Elige método de pago (efectivo / transferencia / tarjeta — informativo) y **Cobrar**.
5. Se descuenta el inventario, se genera la factura consecutiva (`FV-000001`) y se abre la vista de factura:
   - Selector **Ticket 80mm** (impresora térmica) o **Carta**.
   - **Imprimir** usa el diálogo del navegador con CSS de impresión.
6. Reimprime cualquier factura desde **Facturas**.

Si otro vendedor agotó el stock un segundo antes, la venta completa se rechaza con un mensaje claro indicando la línea sin stock — nunca se descuenta parcialmente.

---

## Roles de usuario

| Capacidad | Administrador | Vendedor |
|---|:-:|:-:|
| Punto de venta y facturar | ✅ | ✅ |
| Ver ventas/facturas | Todas | Solo las propias |
| Productos, variantes, atributos | ✅ | ❌ |
| Compras y proveedores | ✅ | ❌ |
| Precios y publicación | ✅ | ❌ |
| Inventario, ajustes, kardex | ✅ | Solo consulta de stock |
| Anular ventas | ✅ | ❌ |
| Usuarios y configuración | ✅ | ❌ |

La autorización se valida **en el backend** en cada endpoint (no solo ocultando botones).

---

## Pruebas

```bash
cd backend
.venv\Scripts\activate     # o source .venv/bin/activate
python -m pytest tests -q
```

37 tests de caja negra sobre la API (SQLite en memoria), cubriendo:

- Producto con matriz de variantes 2×2, SKUs derivados, combos duplicados (409), consecutivo por prefijo.
- Compra → stock + kardex con saldo; compra en lb convertida a kg exacto; ajustes con nota obligatoria.
- Margen 30% sobre costo 5.000 → precio 6.500,00 exacto (sin errores de redondeo).
- Publicar/despublicar controla el catálogo del POS.
- Venta completa: totales con IVA por producto, snapshots, factura consecutiva, stock descontado.
- Sobreventa → 409 con rollback total (multilínea incluida).
- Venta granel en lb y kg con decimales exactos.
- Permisos: vendedor no ve ventas ajenas, no anula, no accede a módulos admin; usuario desactivado → 401.

---

## Despliegue gratis en Vercel + Supabase

> **Registros que necesitas (todos gratis):**
> 1. Cuenta en **GitHub** → https://github.com/signup
> 2. Cuenta en **Supabase** → https://supabase.com (entra con GitHub)
> 3. Cuenta en **Vercel** → https://vercel.com/signup (entra con GitHub)

### Paso 1 — Sube el código a GitHub

```bash
cd saas_small
git init
git add .
git commit -m "Sistema de gestión comercial"
# Crea un repo vacío en github.com y luego:
git remote add origin https://github.com/TU_USUARIO/saas_small.git
git push -u origin main
```

### Paso 2 — Crea la base de datos en Supabase

1. En https://supabase.com/dashboard → **New project**: elige nombre, contraseña de base de datos (guárdala) y región (ej. *South America (São Paulo)*).
2. Cuando el proyecto esté listo, ve a **Connect** (botón arriba) y copia dos URLs:
   - **Transaction pooler** (puerto **6543**) → será `DATABASE_URL` de producción.
   - **Direct connection** (puerto **5432**) → solo para crear las tablas desde tu PC.
3. Reemplaza `[YOUR-PASSWORD]` en ambas URLs por tu contraseña.

### Paso 3 — Crea las tablas y el usuario admin

Desde tu PC (con el venv del backend activado):

```bash
cd backend
# Windows PowerShell:
$env:DATABASE_URL = "postgresql://postgres:TU_PASSWORD@db.xxxx.supabase.co:5432/postgres?sslmode=require"
python -m alembic upgrade head          # crea las tablas (migraciones)
$env:SEED_ADMIN_EMAIL = "tu-correo@tunegocio.com"
$env:SEED_ADMIN_PASSWORD = "una-clave-segura"
python scripts/seed.py                  # admin + configuración + atributos base
```

(En macOS/Linux: `DATABASE_URL="..." python -m alembic upgrade head && SEED_ADMIN_EMAIL="..." python scripts/seed.py`.)
Usa aquí la URL **directa (5432)** — la del pooler es solo para la API. Cuando en el futuro cambies el esquema, genera la migración con `alembic revision --autogenerate -m "descripcion"` y aplícala igual con `alembic upgrade head`.

### Paso 4 — Despliega el backend en Vercel

1. En https://vercel.com → **Add New → Project** → importa tu repo.
2. **Root Directory**: `backend` (¡importante!). Framework: *Other*.
3. En **Environment Variables** agrega:
   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | la URL del **pooler (6543)** con `?sslmode=require` |
   | `JWT_SECRET` | genera uno: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `CORS_ORIGINS` | déjalo por ahora en `http://localhost:5173` (lo cambias en el paso 6) |
   | `ENV` | `production` |
4. **Deploy**. Prueba: `https://tu-backend.vercel.app/api/health` debe responder `{"status":"ok"}`.

### Paso 5 — Despliega el frontend en Vercel

1. **Add New → Project** → importa **el mismo repo** otra vez.
2. **Root Directory**: `frontend`. Framework: *Vite* (se detecta solo).
3. Variable de entorno: `VITE_API_URL` = `https://tu-backend.vercel.app` (la URL del paso 4, sin barra final).
4. **Deploy** → obtendrás algo como `https://tu-negocio.vercel.app`.

### Paso 6 — Conecta CORS

1. Vuelve al proyecto **backend** en Vercel → Settings → Environment Variables.
2. Edita `CORS_ORIGINS` = `https://tu-negocio.vercel.app` (la URL del frontend; puedes poner varias separadas por coma).
3. **Redeploy** el backend (Deployments → ⋯ → Redeploy).

¡Listo! Entra a `https://tu-negocio.vercel.app` con el correo y clave que sembraste en el paso 3. Ninguno de los dos servicios "se duerme": Vercel serverless y Supabase responden siempre.

**Notas de producción**
- HTTPS lo dan Vercel y Supabase automáticamente.
- El token JWT viaja por header `Authorization` (no cookies) → sin CSRF; expira a las 8 horas.
- La documentación interactiva (`/api/docs`) queda deshabilitada con `ENV=production`.
- Si cambias el esquema en el futuro, aplica los cambios a Supabase con una herramienta de migraciones (p. ej. Alembic) usando la conexión directa (5432); nunca ejecutes DDL a través del pooler.

---

## Checklist E2E manual

Después de instalar (local o producción), valida el ciclo completo:

- [ ] **Login** como admin → redirige al Dashboard.
- [ ] **Configuración**: pon nombre del negocio, NIT y dirección (saldrán en la factura).
- [ ] **Producto con variantes**: crea *Camisa* con 2 colores × 1 talla → verifica 2 SKUs derivados.
- [ ] **Producto granel**: crea *Arroz* en kg.
- [ ] **Compra**: registra 10 camisas a $8.000 y 20 **lb** de arroz a $1.500/lb → en **Inventario** debe verse `9.072 kg` de arroz (conversión exacta).
- [ ] **Kardex**: dos movimientos de entrada con saldo.
- [ ] **Precios**: camisa por margen 50% → $12.000; arroz $11.000/kg y redondea la libra a $5.000/lb. **Publica ambos**.
- [ ] **POS** (como vendedor): vende 2 camisas + 2.5 lb de arroz → subtotal $36.500, IVA según configuración, factura `FV-000001`.
- [ ] **Factura**: revisa vista ticket y carta, imprime (o "guardar como PDF").
- [ ] **Inventario**: camisa 8 und; arroz `7.938 kg` (2.5 lb = 1.134 kg exacto).
- [ ] **Sobreventa**: intenta vender 999 camisas → error claro, nada cambia.
- [ ] **Roles**: como vendedor confirma que no ves Compras/Precios/Usuarios y solo ves tus ventas.
- [ ] **Anulación** (admin): anula la venta → stock repuesto + movimiento de ajuste en kardex.

---

---

## Modelo de datos (base de datos)

### Diagrama conceptual de tablas

```
┌───────────────┐       ┌────────────────────┐       ┌──────────────────┐
│  users        │       │  products           │       │  categories      │
│───────────────│       │─────────────────────│       │──────────────────│
│ id (PK)       │       │ id (PK)             │───┐   │ id (PK)          │
│ email         │       │ name                │   │   │ name             │
│ password_hash │       │ base_sku (unique)   │   │   └──────────────────┘
│ full_name     │       │ unit_of_measure     │   │
│ role          │       │ is_bulk             │   │   ┌──────────────────┐
│ is_active     │       │ tax_rate            │   │   │  attributes      │
└──────┬────────┘       │ is_active           │   │   │──────────────────│
       │                │ photo_path          │   │   │ id (PK)          │
       │                │ category_id (FK) ───┼───┘   │ name             │
       │                └─────────┬───────────┘       │ code             │
       │                          │                   │ sort_order       │
       │                          │                   └────────┬─────────┘
       │                          │                            │
       │                          │                            │
       │                ┌─────────▼───────────┐       ┌───────▼──────────┐
       │                │  variants            │       │ attribute_values │
       │                │──────────────────────│       │──────────────────│
       │                │ id (PK)              │       │ id (PK)          │
       │                │ product_id (FK) ─────│───┐   │ attribute_id(FK) │
       │                │ sku (unique)         │   │   │ value            │
       │                │ barcode (unique)     │   │   │ code             │
       │                │ attributes_signature │   │   └────────┬─────────┘
       │                │ unit_of_measure      │   │            │
       │                │ is_active            │   │            │
       │                └──┬───┬───┬───┬───┬───┘   │            │
       │                   │   │   │   │   │       │            │
       │    ┌──────────────┘   │   │   │   └───────────┬────────┘
       │    │                  │   │   │               │
       │    │       ┌──────────┘   │   └──────────┐    │
       │    │       │              │              │    │
       │    ▼       ▼              ▼              ▼    ▼
       │  ┌────────────┐  ┌──────────────┐  ┌───────────────────┐
       │  │ stock      │  │ variant_prices│  │ purchase_items    │
       │  │────────────│  │──────────────│  │───────────────────│
       │  │ variant_id │  │ variant_id   │  │ variant_id (FK)   │
       │  │ (PK/FK)    │  │ (unique FK)  │  │ purchase_id (FK)  │
       │  │ quantity   │  │ price        │  │ quantity          │
       │  │ low_stock  │  │ price_per_lb │  │ unit_cost         │
       │  │ threshold  │  │ status       │  │ line_total        │
       │  └────────────┘  │ (borrador/   │  └────────┬──────────┘
       │                  │  publicado)  │           │
       │                  │ published_at │           │
       │                  └──────────────┘           │
       │                                            │
       │  ┌──────────────────┐  ┌────────────────────▼──────────┐
       │  │ inventory_moves  │  │  purchases                    │
       │  │──────────────────│  │───────────────────────────────│
       │  │ variant_id (FK)  │  │ id (PK)                       │
       │  │ movement_type    │  │ supplier_id (FK)              │
       │  │ quantity (+/-)   │  │ purchase_date                 │
       │  │ balance_after    │  │ status                        │
       │  │ unit_cost        │  │ total_cost                    │
       │  │ reference_type   │  │ created_by (FK → users)       │
       │  │ reference_id     │  └───────────────────────────────┘
       │  │ created_by (FK)──│─── a users
       │  └──────────────────┘
       │
       │  ┌──────────────────┐  ┌────────────────────┐  ┌──────────────────┐
       │  │  sales           │  │  sale_items         │  │  invoices        │
       │  │──────────────────│  │─────────────────────│  │──────────────────│
       │  │ id (PK)          │  │ variant_id (FK)     │  │ sale_id (FK)     │
       │  │ user_id (FK) ────│─ │ sku_snapshot        │  │ invoice_prefix   │
       │  │ status           │  │ description_snap    │  │ invoice_number   │
       │  │ subtotal         │  │ quantity            │  │ business_name    │
       │  │ discount_amount  │  │ unit_snapshot       │  │ business_tax_id  │
       │  │ tax_amount       │  │ unit_price_snapshot │  │ (snapshot del    │
       │  │ total            │  │ discount_pct        │  │  negocio al      │
       │  │ payment_method   │  │ tax_rate_snapshot   │  │  emitir)         │
       │  │ customer_name    │  │ tax_amount          │  └──────────────────┘
       │  │ customer_id      │  │ line_total          │
       │  │ cash_session_id  │  │ unit_cost_snapshot  │  ┌──────────────────┐
       │  └──────────────────┘  └─────────┬───────────┘  │  sale_returns    │
       │                                  │              │──────────────────│
       │                                  │              │ sale_id (FK)     │
       │  ┌──────────────────┐            │              │ total_amount     │
       │  │  cash_sessions   │            │              │ reason           │
       │  │──────────────────│            │              └──────────────────┘
       │  │ id (PK)          │            │
       │  │ user_id (FK) ────│────────────│────────────── a users
       │  │ opened_at        │
       │  │ closed_at        │
       │  │ opening_amount   │
       │  │ closing_amount   │
       │  │ expected_cash    │
       │  │ cash_counted     │
       │  │ difference       │
       │  └──────────────────┘
```

### Tablas principales

#### `products` — Productos

Cada fila es un producto (ej. "Camisa polo", "Arroz"). No se vende directamente; es un contenedor de variantes.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | bigint PK | ID único del producto |
| `name` | varchar(150) | Nombre del producto |
| `description` | text | Descripción opcional |
| `category_id` | bigint FK → categories | Categoría opcional |
| `base_sku` | varchar(40) **unique** | SKU base generado automáticamente (ej. `CAMISA-001`) |
| `unit_of_measure` | varchar(10) | `unidad`, `kg` o `lb` |
| `is_bulk` | boolean | `true` si es a granel (kg/lb) |
| `tax_rate` | numeric(5,4) | IVA (0.19 = 19%) |
| `is_active` | boolean | `false` = desactivado (soft-delete) |
| `photo_path` | varchar(255) | Ruta de la foto |

#### `variants` — Variantes (unidad vendible)

**Esta es la tabla más importante.** Todo producto tiene al menos una variante. Las ventas, el stock, los precios y las compras siempre referencian un `variant_id`, nunca un `product_id` directamente.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | bigint PK | **ID único de la variante** (este es el `variant_id` que usan stock, precios, ventas) |
| `product_id` | bigint FK → products | Producto al que pertenece |
| `sku` | varchar(60) **unique** | SKU completo (ej. `CAMISA-001-ROJ-M`) |
| `barcode` | varchar(40) **unique** | Código de barras opcional (se escanea en POS) |
| `attributes_signature` | varchar(120) | Huella de atributos (ej. `"3-7"`) para detectar duplicados |
| `unit_of_measure` | varchar(10) | Unidad específica de esta variante (hereda del producto por defecto) |
| `is_active` | boolean | `false` = desactivada |

**Casos:**
- **Producto sin variantes** (por unidad): se crea una sola variante con `attributes_signature=""` y SKU = `base_sku`.
- **Producto con matriz de atributos** (ej. color×talla): se crea una variante por cada combinación, cada una con su propio SKU derivado (`CAMISA-001-ROJ-M`, `CAMISA-001-AZU-L`, etc.).
- **Producto a granel** (kg/lb): una sola variante por defecto, como los productos simples.

#### `variant_prices` — Precios

Cada variante puede tener **un solo precio activo** (relación 1:1). Si no existe fila, la variante no tiene precio configurado.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | bigint PK | |
| `variant_id` | bigint **unique** FK → variants | La variante (solo puede tener un precio) |
| `price` | numeric(12,2) | Precio de venta (por unidad o por kg si es granel) |
| `price_per_lb` | numeric(12,2) \| null | Solo granel: precio por libra (editable, se sugiere automático) |
| `cost_reference` | numeric(12,2) \| null | Último costo de compra al momento de publicar |
| `margin_percent` | numeric(6,2) \| null | Margen % (si se configuró por margen) |
| `status` | varchar(10) | **`borrador`** (no visible en POS) o **`publicado`** (visible en POS y vendible) |
| `published_at` | timestamp \| null | Fecha de publicación |

**Flujo de precios:**
1. Al crear un producto, se crea automáticamente un `VariantPrice` con `price=0` y `status='borrador'`.
2. El usuario va a **Precios**, fija un precio (directo o por margen).
3. **Publica** el precio → `status='publicado'`.
4. La variante aparece en el catálogo del POS y se puede vender.

**Auto-publicación en compras:** Cuando se registra una compra con costo > 0 y la variante aún tiene `price=0` y `status='borrador'`, el sistema **asigna automáticamente el costo de compra como precio de venta y lo publica**, para que el producto aparezca inmediatamente disponible en el punto de venta. Si ya tiene un precio definido manualmente (> 0), no lo modifica.

#### `stock` — Stock actual (una fila por variante)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `variant_id` | bigint PK/FK → variants | La variante (PK = FK, relación 1:1) |
| `quantity` | numeric(12,3) | Cantidad actual (0 por defecto, siempre ≥ 0) |
| `low_stock_threshold` | numeric(12,3) \| null | Umbral de alerta de stock bajo |
| `updated_at` | timestamp | Última actualización |

#### `inventory_movements` — Kardex (append-only)

Cada entrada, salida o ajuste queda registrado aquí. Nunca se edita ni borra.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | bigint PK | |
| `variant_id` | bigint FK → variants | |
| `movement_type` | varchar(20) | `entrada_compra`, `salida_venta`, `ajuste` |
| `quantity` | numeric(12,3) | Con signo (+ entra, - sale) |
| `balance_after` | numeric(12,3) | Saldo resultante después del movimiento |
| `unit_cost` | numeric(12,2) \| null | Costo unitario en el momento (para reportes) |
| `reference_type` | varchar(20) \| null | `purchase`, `sale`, `adjustment` |
| `reference_id` | bigint \| null | ID de la compra/venta/ajuste referenciado |
| `notes` | text \| null | Nota opcional (obligatoria en ajustes) |
| `created_by` | bigint FK → users | Quién hizo el movimiento |
| `created_at` | timestamp | Fecha del movimiento |

#### Otras tablas

| Tabla | Propósito |
|-------|-----------|
| `users` | Usuarios del sistema (admin/vendedor) |
| `business_settings` | Configuración del negocio (nombre, NIT, IVA predeterminado, prefijo de factura, etc.) — siempre fila con `id=1` |
| `categories` | Categorías de productos |
| `attributes` | Tipos de atributos dinámicos (Color, Talla, Sabor…) |
| `attribute_values` | Valores concretos de cada atributo (Rojo, Azul, M, L…) |
| `variant_attribute_values` | Tabla puente: qué valores tiene cada variante |
| `suppliers` | Proveedores |
| `purchases` | Compras (entradas de stock) |
| `purchase_items` | Líneas de cada compra (qué variante, cuánto, a qué costo) |
| `sales` | Ventas (una por transacción) |
| `sale_items` | Líneas de cada venta (snapshot inmutable de SKU, precio, IVA, costo) |
| `invoices` | Facturas (snapshot del negocio al emitir, consecutivo) |
| `invoice_counters` | Contador atómico del consecutivo de factura (fila única, `id=1`) |
| `sale_returns` | Devoluciones de venta (reversión de stock) |
| `sale_return_items` | Líneas de devolución |
| `cash_sessions` | Apertura/cierre de turnos de caja |
| `sku_counters` | Contador atómico por prefijo para generar SKUs |
| `variant_prices` | Precios y estado de publicación |
| `stock` | Stock actual por variante |
| `inventory_movements` | Kardex append-only |

### Cómo funciona el sistema de IDs

```
product_id = 15  (Camisa polo)
    │
    ├── variant_id = 42  (CAMISA-001-ROJ-M)  ← se vende, tiene stock, tiene precio
    ├── variant_id = 43  (CAMISA-001-ROJ-L)  ← se vende, tiene stock, tiene precio
    ├── variant_id = 44  (CAMISA-001-AZU-M)  ← se vende, tiene stock, tiene precio
    └── variant_id = 45  (CAMISA-001-AZU-L)  ← se vende, tiene stock, tiene precio
```

- **`product_id`** → agrupa variantes, contiene datos comunes (nombre, IVA, foto).
- **`variant_id`** → es la unidad atómica de todo el sistema. Aparece en:
  - `stock.variant_id` (stock actual)
  - `variant_prices.variant_id` (precio)
  - `inventory_movements.variant_id` (kardex)
  - `purchase_items.variant_id` (compras)
  - `sale_items.variant_id` (ventas)
  - `sale_return_items.variant_id` (devoluciones)

**Un producto "sin variantes"** (ej. un producto simple por unidad) igual tiene una variante creada automáticamente con el mismo SKU base. Esto garantiza que **todos** los movimientos del sistema (compras, stock, ventas) siempre apunten a `variant_id`, nunca a `product_id`.

### Flujo completo de datos

```
1. Crear producto
   └→ products (nueva fila)
   └→ variants (1 fila por variante + atributos en variant_attribute_values)
   └→ variant_prices (1 fila con price=0, status='borrador')

2. Registrar compra
   └→ purchases + purchase_items (costo, cantidad)
   └→ inventory_movements (entrada_compra, +delta)
   └→ stock.quantity += delta
   └→ variant_prices: si price=0 y status=borrador → se asigna costo como precio y se publica

3. Configurar precio (opcional si ya se auto-publicó en paso 2)
   └→ variant_prices.price = X
   └→ variant_prices.status = 'publicado'

4. Vender en POS
   └→ Consulta catálogo: variants activas + producto activo + price publicado
   └→ Crea sale + sale_items (snapshots)
   └→ inventory_movements (salida_venta, -delta)
   └→ stock.quantity -= delta (con WHERE quantity >= delta, evita sobreventa)
   └→ invoice_counter.nextval → invoice (consecutivo, snapshot del negocio)
```

---

## Decisiones técnicas clave

- **Decimales sin sorpresas.** Todo el dinero y las cantidades usan `Decimal` con `quantize(ROUND_HALF_UP)` (2 decimales dinero, 3 cantidades) en un único módulo (`app/core/money.py`). El frontend solo *muestra* totales; el backend es la fuente autoritativa.
- **Conversión kg/lb.** El inventario usa el factor exacto (1 lb = 0.45359237 kg) para que el kardex nunca se descuadre. Los **precios** por libra son editables para permitir precios comerciales redondos.
- **IVA por producto** con snapshot por línea de venta y desglose por tasa en la factura (compatible con productos exentos, 5%, 19%…).
- **Precios tax-exclusive**: el precio configurado es la base; el IVA se suma en la venta. 
- **pgbouncer transaction-mode**: por eso psycopg2 (sin prepared statements con nombre), `NullPool`, y nada de estado de sesión de Postgres.
- **Sin dependencias pesadas** en producción (~60 MB instalados): sin pandas, sin reportlab (la factura es HTML + `window.print()`), sin passlib (pbkdf2 de stdlib). Muy por debajo del límite de 250 MB de Vercel.

---

## Validar base de datos desde Excel / Power BI

Puedes conectar herramientas externas directamente a la base de datos PostgreSQL que corre en Docker.

### Datos de conexión

| Parámetro | Valor |
|---|---|
| Host | `localhost` |
| Puerto | `5432` |
| Base de datos | `saas_small` |
| Usuario | `postgres` |
| Contraseña | `postgres` |

### Conexión desde Excel (Windows)

1. Ve a **Datos → Obtener datos → Desde otras fuentes → Desde PostgreSQL**.
2. Ingresa los datos de conexión de la tabla anterior.
3. Selecciona las tablas que quieras consultar (`sales`, `sale_items`, `inventory_movements`, etc.).
4. Carga los datos y crea tablas dinámicas o gráficos.

### Conexión desde Power BI Desktop

1. **Obtener datos → PostgreSQL**.
2. Ingresa `localhost:5432`, base de datos `saas_small`, credenciales `postgres` / `postgres`.
3. Selecciona las tablas y crea tus reportes.

### Consultas útiles desde psql

```bash
# Conectar desde el contenedor
docker compose exec db psql -U postgres -d saas_small

# Ventas del mes actual (neto después de devoluciones)
SELECT
  COALESCE(SUM(s.total), 0) - COALESCE((
    SELECT SUM(sr.total_amount) FROM sale_returns sr
    JOIN sales s2 ON sr.sale_id = s2.id
    WHERE EXTRACT(MONTH FROM s2.created_at) = EXTRACT(MONTH FROM CURRENT_DATE)
      AND EXTRACT(YEAR FROM s2.created_at) = EXTRACT(YEAR FROM CURRENT_DATE)
  ), 0) AS ventas_netas_mes
FROM sales s
WHERE s.status = 'completada'
  AND EXTRACT(MONTH FROM s.created_at) = EXTRACT(MONTH FROM CURRENT_DATE)
  AND EXTRACT(YEAR FROM s.created_at) = EXTRACT(YEAR FROM CURRENT_DATE);

# Costo de ventas del mes (resumen por producto)
SELECT
  p.name AS producto,
  COUNT(DISTINCT s.id) AS veces_vendido,
  SUM(si.quantity) AS cantidad,
  SUM(si.line_total) AS total_venta
FROM sale_items si
JOIN sales s ON s.id = si.sale_id
JOIN variants v ON v.id = si.variant_id
JOIN products p ON p.id = v.product_id
WHERE s.status = 'completada'
  AND EXTRACT(MONTH FROM s.created_at) = EXTRACT(MONTH FROM CURRENT_DATE)
GROUP BY p.name
ORDER BY total_venta DESC;

# Devoluciones registradas
SELECT
  sr.id AS devolucion_id,
  sr.created_at AS fecha,
  sr.total_amount AS monto,
  sr.reason AS motivo,
  u.full_name AS procesado_por
FROM sale_returns sr
JOIN users u ON u.id = sr.user_id
ORDER BY sr.created_at DESC;

# Salir de psql
\q
```

### Notas

- Los datos persisten mientras no ejecutes `docker compose down -v`.
- Puedes refrescar las tablas en Excel/Power BI con **Actualizar todo**.
- Las conexiones externas no interfieren con el funcionamiento del sistema.

---

## Referencia rápida de comandos (Docker)

### Despliegue inicial (desde cero en cualquier PC)

```bash
git clone https://github.com/JhonECastellanos/saas_small.git
cd saas_small
git checkout V4
docker compose up -d
```

Los tres servicios (PostgreSQL, backend FastAPI, frontend Nginx) arrancan automáticamente. El backend ejecuta las migraciones de Alembic y siembra los datos iniciales (admin + atributos base) al iniciar.

**Usuario inicial:** `admin@negocio.com` / `admin123`

> ⚠️ En Windows, si Docker Desktop no arranca el backend, verifica que los puertos 3000, 5432 y 8000 no estén ocupados:
> ```bash
> netstat -ano | findstr "3000 5432 8000"
> ```

### Gestión de contenedores

```bash
# Ver estado de todos los servicios
docker compose ps

# Ver logs de todos los servicios en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db

# Detener servicios (sin borrar datos)
docker compose stop

# Reanudar servicios detenidos
docker compose start

# Reiniciar un servicio específico
docker compose restart backend

# Apagar y eliminar contenedores (los datos persisten)
docker compose down

# Apagar y eliminar contenedores + volúmenes (borra TODOS los datos)
docker compose down -v

# Reconstruir imágenes desde cero y arrancar
docker compose build --no-cache
docker compose up -d
```

### Validación del backend

```bash
# Health check básico
curl http://localhost:8000/api/health

# Probar login (debe devolver token + usuario)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@negocio.com","password":"admin123"}'

# Probar endpoint protegido (reemplaza TOKEN con el anterior)
curl http://localhost:8000/api/v1/products \
  -H "Authorization: Bearer TOKEN"

# Documentación interactiva (abrir en navegador)
start http://localhost:8000/api/docs
```

### Validación del frontend

```bash
# Abrir en navegador
start http://localhost:3000

# Verificar que el frontend carga (debe devolver HTML)
curl -s http://localhost:3000 | head -20

# Verificar que el proxy de API funciona (pide login → HTML)
curl -s http://localhost:3000/login | head -20
```

### Validación de la base de datos

```bash
# Conectar directo desde la terminal (si tienes psql instalado)
psql -h localhost -U postgres -d saas_small

# Desde dentro del contenedor
docker compose exec db psql -U postgres -d saas_small

# Comandos útiles dentro de psql:
#   \dt              — listar tablas
#   \d users         — describir tabla users
#   SELECT * FROM users;  — ver usuarios
#   \q               — salir
```

### Pruebas automatizadas del backend

```bash
# Ejecutar tests dentro del contenedor
docker compose exec backend python -m pytest tests -v

# Ejecutar tests con reporte de cobertura
docker compose exec backend python -m pytest tests -v --tb=short
```

### Solución de problemas comunes

```bash
# Verificar qué puertos están ocupados (Windows)
netstat -ano | findstr "3000 5432 8000"

# Ver logs de build de una imagen específica
docker compose build --no-cache backend 2>&1

# Entrar a una terminal dentro del backend
docker compose exec backend sh

# Entrar a la base de datos
docker compose exec db psql -U postgres -d saas_small -c "SELECT count(*) FROM users;"

# Reset completo: borrar imágenes, contenedores, volúmenes y reconstruir
docker compose down -v
docker compose build --no-cache
docker compose up -d
```
