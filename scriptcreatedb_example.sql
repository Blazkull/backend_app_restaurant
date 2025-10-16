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
    last_connection TIMESTAMP NULL,
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
    id_user_assigned INT, -- Se permite NULL si no hay usuario asignado
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_location) REFERENCES locations(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_user_assigned) REFERENCES users(id) ON UPDATE CASCADE
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
    id_user_created INT NOT NULL,
    total_value DECIMAL(10, 2) DEFAULT 0,
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
    note VARCHAR(100),
    price_at_order DECIMAL(10, 2) NOT NULL, -- Precio al momento del pedido
    id_kitchen_ticket INT, -- Se permite NULL si no se ha generado ticket de cocina
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_order) REFERENCES orders(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_menu_item) REFERENCES menu_items(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_kitchen_ticket) REFERENCES kitchen_tickets(id) ON UPDATE CASCADE
);

-- 17. kitchen_tickets table (para referencia en order_items)
CREATE TABLE kitchen_tickets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_order INT NOT NULL,
    id_status INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_order) REFERENCES orders(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);


-- 18. Información de la Empresa (SIN Soft Delete)
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

-- 19. Facturas
CREATE TABLE invoices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_client INT,
    id_order INT NOT NULL UNIQUE,
    id_payment_method INT NOT NULL,
    returned DECIMAL(10,2),
    ammount_paid DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    id_status INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_client) REFERENCES clients(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_order) REFERENCES orders(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_payment_method) REFERENCES payment_method(id) ON UPDATE CASCADE,
    FOREIGN KEY (id_status) REFERENCES status(id) ON UPDATE CASCADE
);


-- =========================================================
-- Inserción de Datos Iniciales (Seeders)
-- =========================================================
-- 1. Tipo de Identificación (type_identification)
INSERT INTO type_identification (type_identification) VALUES
('Cédula Ciudadanía'),
('Cédula Extranjería'),
('Pasaporte'),
('NIT');

-- 2. Status/Estado (status)
INSERT INTO status (name, description) VALUES
-- 1-2: Estados generales
('Activo', 'Registro activo y en uso'),
('Inactivo', 'Registro inactivo o deshabilitado'),

-- 3-4: Estados para mesas
('Ocupada', 'Mesa ocupada'),
('Disponible', 'Mesa disponible'),

-- 5-7: Estados para órdenes
('Creada', 'Orden creada'),
('En Proceso', 'Orden en proceso'),
('Entregado', 'Pedido entregado'),

-- 8-12: Estados para tickets de cocina
('Pendiente', 'Pedido pendiente de cocina'),
('Preparación', 'Pedido en preparacion'),
('Listo', 'Pedido listo para servir'),
('Entregado', 'Pedido entregado al cliente'),
('Cancelada', 'Orden, factura o item cancelado'), -- Reutilizado para cancelaciones

-- 13: Estados para facturas
('Pagada', 'Factura pagada');
('Anulada', 'Factura anulada');

-- 3. Métodos de Pago (payment_method)
INSERT INTO payment_method (name) VALUES
('Efectivo'),
('Tarjeta Crédito/Débito'),
('Transferencia');


-- 4. Roles (roles) - id_status = 1 (Activo)
INSERT INTO roles (name, id_status) VALUES
('Administrador', 1), -- ID 1
('Mesero', 1),        -- ID 2
('Jefe de Cocina', 1), -- ID 3
('Cajero', 1);        -- ID 4

-- 5. Usuarios (users)
-- NOTA: La contraseña '$2a$12$GByghX4O968/l61.1zzJiO2a/qgXCms75GZITCb1.6mIjT6BeUEnK' corresponde a 'admin'
-- id_role = 1 (Administrador), id_status = 1 (Activo)
INSERT INTO users (name, username, password, email, id_role, id_status, active) VALUES
('Jhon Acosta Acosta', 'admin', '$2a$12$GByghX4O968/l61.1zzJiO2a/qgXCms75GZITCb1.6mIjT6BeUEnK', 'admin@gmail.com', 1, 1, TRUE), -- ID 1
('Ana García', 'anamesera', 'password_mesera', 'ana.garcia@rest.com', 2, 1, TRUE),                                        -- ID 2
('Pedro Pérez', 'pedrococina', 'password_cocina', 'pedro.perez@rest.com', 3, 1, TRUE);                                      -- ID 3

-- 7. Vistas (views) - id_status = 1 (Activo)
INSERT INTO views (name, path, id_status) VALUES
('Dashboard', '/api/dashboard', 1),                      -- ID 1
('Pedidos', '/api/orders', 1),                           -- ID 2
('Menú', '/api/menu_items', 1),                          -- ID 3
('Mesas', '/api/tables', 1),                             -- ID 4
('Clientes', '/api/clients', 1),                         -- ID 5
('Usuarios', '/api/users', 1),                           -- ID 6
('Reportes', '/api/reports', 1),                         -- ID 7
('Roles', '/api/roles', 1),                              -- ID 8
('Vistas', '/api/views', 1),                             -- ID 9
('Estados', '/api/status', 1),                           -- ID 10
('Categorías', '/api/categories', 1),                    -- ID 11
('Información de Empresa', '/api/info', 1),              -- ID 12
('Facturas', '/api/invoices', 1),                        -- ID 13
('Órdenes de Cocina', '/api/kitchen_orders', 1),         -- ID 14
('Ubicaciones', '/api/locations', 1),                    -- ID 15
('Ítems de Pedido', '/api/order_items', 1),              -- ID 16
('Pagos', '/api/payments', 1),                           -- ID 17
('Tipos de Identificación', '/api/type_identifications', 1); -- ID 18


-- 9. Enlace Rol-Vistas (role_view_link) - Permisos M:N
-- Administrador (id_role=1) tiene acceso a TODOS los 18 recursos (enabled=TRUE).
INSERT INTO role_view_link (id_role, id_view, enabled) VALUES
(1, 1, TRUE), (1, 2, TRUE), (1, 3, TRUE), (1, 4, TRUE), (1, 5, TRUE), (1, 6, TRUE), (1, 7, TRUE), (1, 8, TRUE),
(1, 9, TRUE), (1, 10, TRUE), (1, 11, TRUE), (1, 12, TRUE), (1, 13, TRUE), (1, 14, TRUE), (1, 15, TRUE), (1, 16, TRUE),
(1, 17, TRUE), (1, 18, TRUE);
-- Mesero (id_role=2) tiene acceso limitado
INSERT INTO role_view_link (id_role, id_view, enabled) VALUES
(2, 2, TRUE), -- Pedidos
(2, 3, TRUE), -- Menú
(2, 4, TRUE), -- Mesas
(2, 5, TRUE); -- Clientes
-- Jefe de Cocina (id_role=3)
INSERT INTO role_view_link (id_role, id_view, enabled) VALUES
(3, 14, TRUE), -- Órdenes de Cocina
(3, 3, TRUE);  -- Menú (para verificar ingredientes/tiempos)



-- 11. Ubicaciones (locations) - id_status = 1 (Activo)
INSERT INTO locations (name, description) VALUES
('Salón Principal', 'Zona de mesas cerca de la entrada'), -- ID 1
('Terraza', 'Zona al aire libre'),                       -- ID 2
('Barra', 'Asientos en la barra');                       -- ID 3

-- 12. Mesas (tables) - id_location, id_status (3=Ocupada, 4=Disponible)
INSERT INTO tables (name, id_location, capacity, id_status, id_user_assigned) VALUES
('Mesa 1', 1, 4, 4, NULL), -- Salón Principal, Disponible
('Mesa 2', 1, 2, 3, 2),    -- Salón Principal, Ocupada, Asignada a Ana (id_user=2)
('Mesa 3', 1, 6, 4, 2),    -- Salón Principal, Disponible, Asignada a Ana (id_user=2)
('Mesa T1', 2, 4, 4, NULL),-- Terraza, Disponible
('Barra A', 3, 2, 4, NULL);-- Barra, Disponible


-- 13. Categorías (categories)
INSERT INTO categories (name, description) VALUES
('Platos Fuertes', 'Comidas principales'), -- ID 1
('Entradas', 'Aperitivos y sopas'),        -- ID 2 (Corregido, se usa este para los ítems)
('Bebidas', 'Jugos, gaseosas, y licores'), -- ID 3
('Postres', 'Dulces y cafés');             -- ID 4

-- 14. Ítems de Menú (menu_items)
-- id_status: 1=Activo, 2=Inactivo
INSERT INTO menu_items (name, id_category, ingredients, estimated_time, price, id_status, image) VALUES
-- ID 1-2: Entradas (id_category = 2)
('Nachos Supremes', 2, 'Totopos de maíz, queso cheddar fundido, carne molida, frijoles refritos, pico de gallo, crema agria y jalapeños.', 15, 9.99, 1, 'nachos_supremes.jpg'),
('Aros de Cebolla Gourmet', 2, 'Cebolla blanca en rodajas gruesas, rebozado crujiente de cerveza, salsa ranch de la casa.', 10, 6.50, 1, 'aros_cebolla.jpg'),

-- ID 3-7: Platos Fuertes (id_category = 1)
('Hamburguesa Clásica Especial', 1, 'Doble carne de res (200g), queso cheddar, tocino, lechuga, tomate, cebolla caramelizada, salsa BBQ, pan brioche.', 20, 14.75, 1, 'hamburguesa_especial.jpg'), -- Estado 1 (Activo)
('Salmón a la Plancha con Asparagus',1, 'Filete de salmón (180g) a la plancha, espárragos salteados, reducción de balsámico y limón.', 25, 21.90, 1, 'salmon_asparagus.jpg'),
('Pizza Margarita Artesanal', 1, 'Masa fermentada, salsa de tomate San Marzano, mozzarella fresca, albahaca y aceite de oliva virgen extra.', 18, 12.00, 1, 'pizza_margarita.jpg'),
('Curry de Garbanzos y Verduras', 1, 'Garbanzos, espinacas, pimientos, cebolla en salsa curry cremosa de coco, servido con arroz basmati.', 20, 15.50, 1, 'curry_garbanzos.jpg'),
('Pasta Alfredo con Camarones', 1, 'Fettuccine en salsa cremosa Alfredo con camarones jumbo y un toque de ajo y perejil.', 22, 18.25, 2, 'pasta_camarones.jpg'), -- Estado 2 (Inactivo, estaba en 3)

-- ID 8-9: Postres (id_category = 4)
('Volcán de Chocolate con Helado', 4, 'Bizcocho de chocolate con centro líquido, servido con helado de vainilla y coulis de frambuesa.', 12, 7.50, 1, 'volcan_chocolate.jpg'),
('Tiramisú Clásico', 4, 'Capas de bizcocho de soletilla empapadas en café, crema de mascarpone y cacao en polvo.', 5, 6.95, 1, 'tiramisu_clasico.jpg'),

-- ID 10: Bebidas (id_category = 3)
('Limonada de Menta Refrescante', 3, 'Jugo de limón natural, agua, azúcar, hojas de menta fresca.', 5, 3.50, 1, 'limonada_menta.jpg');