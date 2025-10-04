CREATE DATABASE db_restraurante_la_media_luna;

USE db_restraurante_la_media_luna;

-- =========================================================
-- Tablas Base (Catálogos)
-- =========================================================

-- 1. Tipo de Identificación
CREATE TABLE type_identification(
    id INT PRIMARY KEY AUTO_INCREMENT,
    type_identification VARCHAR(20) NOT NULL UNIQUE, -- Se agrega UNIQUE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 2. Status/Estado
CREATE TABLE status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(20) NOT NULL UNIQUE, -- Se agrega UNIQUE
    description VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 3. Métodos de Pago
CREATE TABLE payment_method (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(30) NOT NULL UNIQUE, -- Se agrega UNIQUE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);


-- =========================================================
-- Gestión de Usuarios, Roles y Permisos
-- =========================================================

-- 4. Roles
CREATE TABLE roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE, -- Se agrega UNIQUE
    id_status INT NOT NULL, -- Se hace NOT NULL ya que un rol siempre debe tener estado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);

-- 5. Usuarios
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    id_role INT, 
    id_status INT NOT NULL,
    active BOOLEAN DEFAULT TRUE, -- Campo útil para FastAPI/Autenticación (adicional al soft delete)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_role) REFERENCES roles(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);

-- 6. Tokens
CREATE TABLE tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_user INT NOT NULL,
    token VARCHAR(255) NOT NULL,
    status_token BOOLEAN NOT NULL, -- Uso BOOLEAN/TINYINT(1) en lugar de TINYINT
    expiration DATETIME NOT NULL,
    date_token DATETIME NOT NULL,
    FOREIGN KEY (id_user) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 7. Vistas (Recursos de Permisos)
CREATE TABLE views (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE, 
    path VARCHAR(100) NOT NULL UNIQUE, 
    id_status INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);

-- 8. Enlace Usuario-Roles (Relación M:N) - CAMBIO DE NOMBRE A 'user_role_link' para evitar conflictos
CREATE TABLE user_role_link ( 
    id_user INT,
    id_role INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_user, id_role),
    FOREIGN KEY (id_user) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_role) REFERENCES roles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- 9. Enlace role_view_link (Permisos M:N) 
CREATE TABLE role_view_link ( 
    id_role INT,
    id_view INT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_role, id_view),
    FOREIGN KEY (id_role) REFERENCES roles(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_view) REFERENCES views(id) ON DELETE CASCADE ON UPDATE CASCADE
);


-- =========================================================
-- Gestión de Clientes, Ubicación y Mesas
-- =========================================================

-- 10. Clientes
CREATE TABLE clients (
    id INT PRIMARY KEY AUTO_INCREMENT,
    fullname VARCHAR(100) NOT NULL,
    address VARCHAR(100),
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    id_type_identificacion INT NOT NULL,
    identification_number VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_type_identificacion) REFERENCES type_identification(id) ON UPDATE CASCADE
);

-- 11. Ubicaciones
CREATE TABLE locations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE, -- Se agrega UNIQUE
    description VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 12. Mesas
CREATE TABLE tables (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(20) NOT NULL UNIQUE, -- Se agrega UNIQUE para el nombre de mesa
    id_location INT NOT NULL,
    capacity INT NOT NULL,
    id_status INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_location) REFERENCES locations(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);


-- =========================================================
-- Gestión de Menú
-- =========================================================

-- 13. Categorías
CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE, -- Se agrega UNIQUE
    description VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 14. Ítems de Menú
CREATE TABLE menu_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE, -- Se agrega UNIQUE al nombre del ítem
    id_category INT NOT NULL,
    ingredients VARCHAR(255) NOT NULL, -- Aumentado a 255 para ingredientes
    estimated_time INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    id_status INT NOT NULL,
    image VARCHAR(255),-- Aumentado a 255 para el path
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_category) REFERENCES categories(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);


-- =========================================================
-- Pedidos y Facturación
-- =========================================================

-- 15. Pedidos
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_table INT NOT NULL,
    id_status INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_table) REFERENCES tables(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);

-- 16. Ítems del Pedido
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_order INT NOT NULL, -- Se hace NOT NULL ya que un ítem debe pertenecer a una orden
    id_menu_item INT NOT NULL, -- Se hace NOT NULL
    quantity INT NOT NULL CHECK (quantity > 0), -- Se agrega restricción de cantidad
    note VARCHAR(100), -- Aumentado el tamaño
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_order) REFERENCES orders(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_menu_item) REFERENCES menu_items(id) ON UPDATE CASCADE,
    -- Restricción para que solo haya un ítem de menú por orden (si lo necesitas)
    UNIQUE (id_order, id_menu_item) 
);

-- 17. Información de la Empresa (SIN Soft Delete)
CREATE TABLE information_company (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(100) NOT NULL, 
    location VARCHAR (50) NOT NULL,
    identification_number VARCHAR(50) NOT NULL UNIQUE, -- Se agrega UNIQUE
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 18. Facturas
CREATE TABLE invoices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_client INT, -- Se permite NULL si es venta anónima/público general
    id_order INT NOT NULL UNIQUE, -- Una orden solo se factura una vez
    id_payment_method INT NOT NULL,
    -- Los campos returned y ammount_paid no son estrictamente necesarios en la BD para la lógica total, 
    -- ya que pueden calcularse, pero se mantienen si los necesitas para la auditoría de caja.
    returned DECIMAL(10, 2), -- Puede ser nulo o 0
    ammount_paid DECIMAL(10, 2) NOT NULL, 
    total DECIMAL(10, 2) NOT NULL,
    id_status INT NOT NULL, -- El estado de la factura (Pagada, Cancelada, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_order) REFERENCES orders(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_client) REFERENCES clients(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_payment_method) REFERENCES payment_method(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);


-- =========================================================
-- Inserción de Datos Iniciales (Seeders)
-- =========================================================

-- Asumiendo que esta es la primera ejecución:

-- 1. Tipo de Identificación (Necesario para 'clients')
INSERT INTO type_identification (type_identification) VALUES
('Cédula Ciudadanía'),
('Cédula Extranjería'),
('Pasaporte'),
('NIT');

-- 2. Status/Estado (Necesario para casi todas las tablas)
INSERT INTO status (name, description) VALUES
('Activo', 'Registro activo y en uso'),
('Inactivo', 'Registro inactivo o deshabilitado'),
('Pendiente', 'Registro en espera de alguna acción'),
('Ocupada', 'Mesa ocupada'),
('Disponible', 'Mesa disponible'),
('Preparación', 'Pedido en cocina'),
('Entregado', 'Pedido entregado'),
('Pagada', 'Factura pagada'),
('Cancelada', 'Factura cancelada');


-- 3. Métodos de Pago (Necesario para 'invoices')
INSERT INTO payment_method (name) VALUES
('Efectivo'),
('Tarjeta Crédito/Débito'),
('Transferencia');


-- 4. Roles (Asumiendo id_status = 1 para 'Activo')
INSERT INTO roles (name, id_status) VALUES
('Administrador', 1),
('Mesero', 1),
('Jefe de Cocina', 1),
('Cajero', 1);


-- 5. Usuarios (Asumiendo id_role = 1 para 'Administrador' y id_status = 1 para 'Activo')
-- NOTA: La contraseña '$2a$12$GByghX4O968/l61.1zzJiO2a/qgXCms75GZITCb1.6mIjT6BeUEnK' corresponde a 'admin'
INSERT INTO users (name, username, password, email, id_role, id_status, active) VALUES
('Jhon Acosta Acosta', 'admin', '$2a$12$GByghX4O968/l61.1zzJiO2a/qgXCms75GZITCb1.6mIjT6BeUEnK', 'admin@gmail.com', 1, 1, TRUE);


-- 7. Vistas (Recursos de Permisos) - ACTUALIZADO con la columna 'path' y NUEVOS REGISTROS
-- Asignación de paths a los registros existentes:
INSERT INTO views (name, path, id_status) VALUES
('Dashboard', '/api/dashboard/admin', 1),
('Pedidos', '/api/orders/admin', 1),
('Menú', '/api/menu_items/admin', 1),
('Mesas', '/api/tables/admin', 1),
('Clientes', '/api/clients/admin', 1),
('Usuarios', '/api/users/admin', 1),
('Reportes', '/api/reports/admin', 1),
('Roles', '/api/roles/admin', 1),
('Vistas', '/api/views/admin', 1),
('Estados', '/api/status/admin', 1),
('Categorías', '/api/categories/admin', 1),
('Información de Empresa', '/api/info/admin', 1),
('Facturas', '/api/invoices/admin', 1),
('Órdenes de Cocina', '/api/kitchen_orders/admin', 1),
('Ubicaciones', '/api/locations/admin', 1),
('Ítems de Pedido', '/api/order_items/admin', 1),
('Pagos', '/api/payments/admin', 1),
('Tipos de Identificación', '/api/type_identifications/admin', 1);

-- 9. Enlace Rol-Vistas (Permisos M:N) - Asignación de TODOS los recursos al rol Administrador
-- NOTA: Se asume que el Administrador (id_role=1) tiene acceso a TODOS los 18 recursos.
INSERT INTO role_view_link (id_role, id_view, enabled) VALUES
(1, 1, TRUE), (1, 2, TRUE), (1, 3, TRUE), (1, 4, TRUE), (1, 5, TRUE), (1, 6, TRUE), (1, 7, TRUE), (1, 8, TRUE),
(1, 9, TRUE), (1, 10, TRUE), (1, 11, TRUE), (1, 12, TRUE), (1, 13, TRUE), (1, 14, TRUE), (1, 15, TRUE), (1, 16, TRUE),
(1, 17, TRUE), (1, 18, TRUE);


-- 11. Ubicaciones (Necesario para 'tables')
INSERT INTO locations (name, description) VALUES
('Salón Principal', 'Zona de mesas cerca de la entrada'),
('Terraza', 'Zona al aire libre'),
('Barra', 'Asientos en la barra');


-- 13. Categorías (Necesario para 'menu_items')
INSERT INTO categories (name, description) VALUES
('Platos Fuertes', 'Comidas principales'),
('Entradas', 'Aperitivos y sopas'),
('Bebidas', 'Jugos, gaseosas, y licores'),
('Postres', 'Dulces y cafés');


-- 17. Información de la Empresa 
INSERT INTO information_company (name, address, location, identification_number, email) VALUES
('Restaurante La Media Luna', 'Calle 123 #45-67', 'Barranquilla, Atlantico', '900123456-7','admin@lamedialuna.com');