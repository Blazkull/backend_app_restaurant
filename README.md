# Backend del Sistema de Gestión para Restaurante La Media Luna

## 📘 Descripción General

El **Backend del Sistema de Gestión para Restaurante La Media Luna** es una aplicación desarrollada con **FastAPI** que permite gestionar de forma integral las operaciones de un restaurante, incluyendo la administración de usuarios, mesas, pedidos, cocina, facturación y panel de control.  
Está diseñado para ofrecer un entorno seguro, escalable y eficiente, facilitando la conexión con un frontend o panel administrativo web.

---

## 🧩 Arquitectura y Tecnologías Utilizadas

El proyecto sigue una arquitectura modular basada en **FastAPI + SQLModel**, donde cada módulo representa una entidad del negocio (clientes, pedidos, facturas, etc.).  
Las principales tecnologías y librerías empleadas son:

- **Lenguaje:** Python 3.11+  
- **Framework principal:** FastAPI  
- **ORM:** SQLModel (basado en SQLAlchemy + Pydantic)  
- **Base de datos:** MySQL  
- **Autenticación:** JWT (JSON Web Tokens)  
- **Servidor de desarrollo:** Uvicorn  
- **Configuración:** Variables de entorno con `python-dotenv`  
- **Control de CORS:** `fastapi.middleware.cors.CORSMiddleware`  
- **Documentación automática:** Swagger UI (`/docs`) y Redoc (`/redoc`)

---

## ⚙️ Requisitos Mínimos del Sistema

| Recurso | Requisito mínimo |
|----------|------------------|
| **Python** | 3.11 o superior |
| **MySQL** | 8.0 o superior |
| **Pip** | Versión actualizada |
| **SO Recomendado** | Windows 10 / Ubuntu 22.04 |
| **RAM** | 4 GB mínimo |
| **Almacenamiento** | 500 MB libres |

---

## 🚀 Instalación y Ejecución (Entorno Local)

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Blazkull/backend_app_restaurant
   cd backend_app_restaurant
   ```

2. **Crear un entorno virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux / Mac
   venv\Scripts\activate    # Windows
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el archivo `.env`:**
   Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido de ejemplo:
   ```env
   DATABASE_URL=mysql+mysqlconnector://user:password@localhost:3306/db_restaurante
   SECRET_KEY=clave_secreta_jwt
   ALGORITHM=HS256
   TOKEN_EXPIRE_MINUTES=1440
   ```

5. **Ejecutar la aplicación:**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Abrir la documentación:**
   - Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🔐 Sistema de Autenticación y Seguridad

El backend implementa autenticación basada en **JWT** (JSON Web Token) mediante el endpoint `/api/auth/login`.  
Cada solicitud a rutas protegidas debe incluir el **token JWT** en el encabezado:

```bash
Authorization: Bearer <token>
```

El token contiene información del usuario autenticado (nombre, rol, email, id) y tiene una expiración configurada mediante variables de entorno.  
Todas las rutas críticas, como `/api/users`, `/api/orders`, `/api/invoices`, requieren el uso del token para garantizar la seguridad de acceso.

---

## 🗂️ Estructura del Proyecto

```
backend_app_restaurant/
│
├── app/
│   ├── main.py                # Punto de entrada de la aplicación
│   ├── core/                  # Configuración central (DB, seguridad, etc.)
│   ├── models/                # Modelos SQLModel
│   ├── routers/               # Rutas API (modulares)
│   ├── schemas/               # Esquemas de validación
│   ├── static/                # Archivos estáticos (imágenes del menú)
│   └── __init__.py
│
├── requirements.txt
├── .env (configuración local)
└── README.md
```

---

## 🍽️ Descripción Funcional por Módulos

### 🔸 Módulo de Autenticación (`/api/auth`)
Gestión de login y generación de tokens JWT.

### 🔸 Usuarios (`/api/users`)
Permite la creación, actualización, eliminación y consulta de usuarios con control de roles.

### 🔸 Roles (`/api/roles`)
Define los diferentes niveles de acceso (Administrador, Mesero, Cajero, etc.).

### 🔸 Clientes (`/api/clients`)
Gestión de clientes del restaurante, incluyendo búsqueda, paginación y eliminación lógica.

### 🔸 Menú y Categorías (`/api/menu_items`, `/api/categories`)
Permiten gestionar los ítems del menú (platos, bebidas, postres) y sus respectivas categorías.

### 🔸 Pedidos (`/api/orders`)
Registro y seguimiento de los pedidos. Incluye relación con mesas y meseros.

### 🔸 Cocina (`/api/kitchen/orders`)
Panel de cocina con estados automáticos: *Pendiente → Preparación → Listo → Entregado*.

### 🔸 Facturación (`/api/invoices`)
Generación de facturas asociadas a pedidos, control de pagos y totales.

### 🔸 Tablas y Estados (`/api/tables`, `/api/status`)
Administración del estado de las mesas (disponibles, ocupadas) y estados del sistema.

### 🔸 Dashboard (`/api/dashboard`)
Ofrece métricas de rendimiento diario:  
- Ventas totales del día  
- Pedidos procesados  
- Ocupación de mesas  
- Producto más vendido  
- Desempeño por mesero y por categoría de plato

---

## 📊 Base de Datos y Modelos Principales

El sistema utiliza **SQLModel** con base en MySQL, implementando un enfoque relacional entre tablas como:

- `users`, `roles`, `status`  
- `clients`, `tables`, `orders`, `order_items`  
- `menu_items`, `categories`  
- `invoices`, `payment_methods`

La eliminación suave (*soft delete*) está presente en todas las entidades, mediante los campos `deleted` y `deleted_on`.

---

## 🧾 Documentación de API y Ejemplos de Consumo

La documentación interactiva se genera automáticamente con **Swagger UI**.  
Cada endpoint puede probarse directamente desde `/docs`.  
Ejemplo de consumo de rutas protegidas:

**Login:**
```bash
POST /api/auth/login
{
  "username": "admin",
  "password": "123456"
}
```

**Obtener lista de clientes:**
```bash
GET /api/clients
Authorization: Bearer <token>
```

**Actualizar estado de pedido en cocina:**
```bash
PATCH /api/kitchen/orders/{order_id}/next-status
Authorization: Bearer <token>
```

---

## 🧰 Variables de Entorno

| Variable | Descripción |
|-----------|-------------|
| `DATABASE_URL` | URL de conexión a la base de datos |
| `SECRET_KEY` | Clave secreta para firma de tokens JWT |
| `ALGORITHM` | Algoritmo de cifrado (HS256 recomendado) |
| `TOKEN_EXPIRE_MINUTES` | Duración del token en minutos |

---

## 📈 Pruebas y Monitoreo

El proyecto puede probarse utilizando **Swagger UI** o herramientas como **Postman**.  
Los logs de ejecución se muestran en consola gracias al nivel de detalle de **SQLAlchemy Engine Logs**, permitiendo depurar consultas y excepciones en tiempo real.

---

## 👨‍💻 Autor

**Desarrollado por:**
| Nombre     | Rol               | GitHub                                 |
|------------|------------------ |----------------------------------------|
| Jhoan Acosta| Backend Developer| https://github.com/Blazkull            |
| Joel Orozco | Backend Developer| https://github.com/JowelBB             |

**Proyecto académico y demostrativo — Backend del Restaurante La Media Luna**  
© 2025 Todos los derechos reservados.