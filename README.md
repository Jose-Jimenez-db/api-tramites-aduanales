# API de Trámites Aduanales

Proyecto integrador · Desarrollo de Software IV · Universidad de Costa Rica, Sede del Pacífico

Backend REST para una **agencia aduanal que trabaja en Puerto Caldera**. Controla el proceso completo de un contenedor: desde que llega al puerto hasta que se libera y se entrega al transportista, con permisos de instituciones y cobros al cliente.

**Equipo**

| Integrante | Carné | Responsabilidades principales |
|---|---|---|
| José David Jiménez Araya | C5G177 | Configuración, modelos de cargas/trámites/cobros, API de trámites/cobros y reglas de negocio, reportes ORM, pruebas de trámites/cobros y colección Postman |
| Yerlin Oviedo Castro | C5I097 | Modelos de clientes/transportistas, seguridad (tokens y roles), API de clientes/transportistas/cargas con filtros y paginación, pruebas de clientes/cargas/cuentas, documentación |

Cada pull request fue revisado por la otra persona antes de unirse a `main`.

---

## 1. Problema que resuelve

En una agencia aduanal los trámites se controlan con hojas de cálculo y llamadas. Esto provoca errores costosos: se libera un contenedor con cobros sin pagar, se asigna un chofer con la licencia vencida o falta un permiso del Ministerio de Salud.

El sistema **centraliza el proceso** y **automatiza decisiones**:

- Asigna los permisos que exige cada tipo de carga al crear el trámite.
- Impide aprobar un trámite si falta algún permiso.
- Impide liberar una carga si hay cobros pendientes o el transportista no está habilitado.
- Anula los cobros pendientes cuando se cancela un trámite.
- Genera códigos de trámite y números de factura.

**Usuarios:** administrador de la agencia, operadores (tramitadores) y personal de consulta (contabilidad, servicio al cliente).

## 2. Módulos

| Módulo | Qué guarda | Se relaciona con |
|---|---|---|
| `clientes` | Empresas importadoras/exportadoras | Cargas (1:N) |
| `transportistas` | Choferes de cabezal y su licencia | Trámites (1:N) |
| `cargas` | Contenedores que llegan al puerto | Cliente (N:1), Trámites (1:N) |
| `tramites` | Proceso aduanero y permisos | Carga, Transportista, Permisos (N:M), Cobros (1:N) |
| `cobros` | Montos cobrados por trámite | Trámite (N:1) |
| `cuentas` | Login, tokens, roles y usuarios | Todos (seguridad) |
| `reportes` | Consultas ORM de resumen | Todos (solo lectura) |

El detalle completo está en [`docs/DOCUMENTO_TECNICO.md`](docs/DOCUMENTO_TECNICO.md): diagrama ER, reglas de negocio, matriz de permisos y catálogo de endpoints.

## 3. Tecnologías

- Python 3.11 o superior (probado con 3.13)
- Django 5.2 LTS y Django REST Framework 3.18
- MySQL 8
- Vistas basadas en funciones con `@api_view` y rutas con `path()` (sin routers ni ViewSets)
- Paginación con el `Paginator` de Django y filtros leídos de `request.query_params`, igual que en el proyecto de clase
- PyMySQL como conector (no necesita compilar nada en Windows)

## 4. Instalación desde cero

### 4.1 Clonar y crear el entorno virtual

```bash
git clone https://github.com/<usuario>/api-tramites-aduanales.git
cd api-tramites-aduanales

python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 4.2 Crear la base de datos en MySQL

Entre a MySQL como administrador (`mysql -u root -p`) y ejecute:

```sql
CREATE DATABASE aduana_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aduana_user'@'localhost' IDENTIFIED BY 'escriba-una-clave';
GRANT ALL PRIVILEGES ON aduana_db.* TO 'aduana_user'@'localhost';
-- Permiso para que Django cree la base de datos temporal de las pruebas:
GRANT ALL PRIVILEGES ON test_aduana_db.* TO 'aduana_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4.3 Configurar variables de entorno

```bash
# Windows
copy .env.example .env
# Linux / macOS
cp .env.example .env
```

Abra `.env` y complete:

- `DJANGO_SECRET_KEY`: genere una con  
  `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DB_PASSWORD`: la clave que usó en el paso 4.2.
- `DEMO_PASSWORD`: la clave que tendrán los usuarios de prueba.

### 4.4 Migraciones, superusuario y datos de prueba

```bash
python manage.py migrate
python manage.py createsuperuser        # opcional: acceso al panel /admin/
python manage.py cargar_datos           # usuarios de prueba y datos ficticios
```

`cargar_datos` crea tres usuarios (su contraseña es la de `DEMO_PASSWORD`):

| Usuario | Rol |
|---|---|
| `admin_demo` | Administrador |
| `operador_demo` | Operador |
| `consulta_demo` | Consulta |

También crea 4 clientes, 4 transportistas (uno con licencia vencida), 6 cargas, 5 trámites en distintos estados y 7 cobros. Todos los datos son inventados. Se puede ejecutar varias veces sin duplicar registros.

### 4.5 Ejecutar el servidor

```bash
python manage.py runserver
```

- API: <http://127.0.0.1:8000/api/>
- Panel de administración: <http://127.0.0.1:8000/admin/>

## 5. Cómo autenticarse

```http
POST /api/auth/login/
Content-Type: application/json

{"username": "operador_demo", "password": "<DEMO_PASSWORD>"}
```

Respuesta:

```json
{"token": "9f3c...", "usuario": "operador_demo", "rol": "Operador"}
```

En las demás solicitudes envíe el encabezado:

```
Authorization: Token 9f3c...
```

## 6. Pruebas automatizadas

```bash
python manage.py test
```

Hay **62 pruebas** que cubren CRUD, reglas de negocio, permisos (401/403), filtros, paginación y consultas ORM. Para ver el nombre de cada prueba:

```bash
python manage.py test -v 2
```

Para guardar la evidencia de ejecución:

```bash
python manage.py test -v 2 > docs/evidencia_pruebas.txt 2>&1
```

| Requisito del enunciado | Mínimo | En el proyecto |
|---|---|---|
| Pruebas CRUD | 5 | 11 |
| Reglas de negocio y validaciones | 4 | 32 |
| Permisos y seguridad (401/403) | 3 | 12 |
| Paginación, filtros, búsqueda u orden | 1 | 11 |
| **Total de pruebas** | **15** | **62** |

Cada prueba indica su categoría al inicio de su descripción, por ejemplo `[REGLA RN-07]`. Algunas pruebas cubren dos categorías.

## 7. Colección Postman

En la carpeta `postman/`:

- `aduana_api.postman_collection.json`: 60 solicitudes en 10 carpetas, cada una con rol, respuesta esperada, ejemplo de respuesta y pruebas automáticas.
- `aduana_local.postman_environment.json`: variables de entorno de ejemplo.

Pasos:

1. Ejecute `python manage.py cargar_datos` y deje el servidor encendido.
2. En Postman: **Import** → seleccione los dos archivos.
3. Elija el entorno **Aduana - Local** y escriba en `demo_password` la misma clave de su `.env`.
4. Abra la colección → **Run** → ejecute todo en orden.

La colección se puede ejecutar varias veces: genera cédulas y contenedores al azar.

También se puede ejecutar por consola con Newman:

```bash
npx newman run postman/aduana_api.postman_collection.json -e postman/aduana_local.postman_environment.json --env-var demo_password=<su-clave>
```

## 8. Estructura del proyecto

```
├── config_backend/    Proyecto creado con startproject: configuración (settings, urls)
├── cuentas/           Login, logout, perfil, usuarios, roles (permisos.py), datos de prueba (pruebas.py) y comando cargar_datos
├── clientes/          Módulo 1
├── transportistas/    Módulo 2
├── cargas/            Módulo 3
├── tramites/          Módulo 4 (incluye servicios.py con la lógica del proceso)
├── cobros/            Módulo 5
├── reportes/          Consultas ORM (consultas.py) y sus endpoints
├── docs/              Documento técnico
└── postman/           Colección y entorno
```

Cada solicitud sigue el flujo: **URL (`path()`) → vista (`@api_view`) → serializador (valida datos) → servicio (reglas) → ORM → respuesta JSON**.

Los listados se paginan con el `Paginator` de Django, 5 registros por página (`?page=2`):

```json
{"pagina_actual": 2, "total_paginas": 3, "total_registros": 25, "resultados": [ ... ]}
```

## 9. Limitaciones conocidas

- No hay frontend; la API se usa con Postman (así lo indica el enunciado).
- Los permisos de instituciones (DUA, SFE, Ministerio de Salud…) se registran manualmente; no hay conexión real con TICA ni con otros sistemas del gobierno.
- Los montos se manejan en colones y no se calculan impuestos automáticamente.
- El código de trámite usa el año de creación en hora UTC; un trámite creado entre las 6 p. m. y medianoche del 31 de diciembre quedaría con el año siguiente.
- No hay límite de intentos de inicio de sesión ni expiración automática de tokens (el token se elimina con `logout`).
- El servidor de desarrollo (`runserver`) no es apto para producción.
