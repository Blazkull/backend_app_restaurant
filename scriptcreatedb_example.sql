CREATE DATABASE db_restraurante_la_media_luna;

USE db_restraurante_la_media_luna;

-- =========================================================
-- Tablas Base (Catálogos)
-- =========================================================

-- 1. Tipo de Identificación
CREATE TABLE type_identification(
    id INT PRIMARY KEY AUTO_INCREMENT,
    type_identificaction VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 2. Status/Estado
CREATE TABLE status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(20) NOT NULL,
    description VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 3. Métodos de Pago
CREATE TABLE payment_method (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(30) NOT NULL,
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
    name VARCHAR(50) NOT NULL,
    id_status INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_status) REFERENCES status(id)
);

-- 5. Usuarios
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    id_role INT,
    id_status INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_role) REFERENCES roles(id),
    FOREIGN KEY (id_status) REFERENCES status(id)
);

-- 6. Tokens
CREATE TABLE tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_user INT NOT NULL,
    token VARCHAR(255) NOT NULL,
    status_token TINYINT NOT NULL,
    expiration DATETIME NOT NULL,
    date_token DATETIME NOT NULL,
    FOREIGN KEY (id_user) REFERENCES users(id)
);

-- 7. Vistas (Recursos de Permisos)
CREATE TABLE views (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    id_status INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_status) REFERENCES status(id)
);

-- 8. Enlace Usuario-Roles (Relación M:N)
CREATE TABLE user_roles (
    id_user INT,
    id_role INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Campos de auditoría en los links
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_user, id_role),
    FOREIGN KEY (id_user) REFERENCES users(id),
    FOREIGN KEY (id_role) REFERENCES roles(id)
);

-- 9. Enlace Rol-Vistas (Permisos M:N)
CREATE TABLE role_views (
    id_role INT,
    id_view INT,
    enabled BOOLEAN DEFAULT TRUE, -- ¡NUEVO CAMPO DE PERMISOS!
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id_role, id_view),
    FOREIGN KEY (id_role) REFERENCES roles(id),
    FOREIGN KEY (id_view) REFERENCES views(id)
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
    FOREIGN KEY (id_type_identificacion) REFERENCES type_identification(id)
);

-- 11. Ubicaciones
CREATE TABLE locations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 12. Mesas
CREATE TABLE tables (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(20) NOT NULL, 
    id_location INT NOT NULL,
    capacity INT NOT NULL,
    id_status INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_location) REFERENCES locations(id),
    FOREIGN KEY (id_status) REFERENCES status(id)
);


-- =========================================================
-- Gestión de Menú
-- =========================================================

-- 13. Categorías
CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL
);

-- 14. Ítems de Menú
CREATE TABLE menu_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    id_category INT NOT NULL,
    ingredients VARCHAR(50) NOT NULL,
    estimated_time INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    id_status INT NOT NULL,
    image VARCHAR(100),-- path de ruta en el repositorio
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_category) REFERENCES categories(id),
    FOREIGN KEY (id_status) REFERENCES status(id) 
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
    FOREIGN KEY (id_table) REFERENCES tables(id),
    FOREIGN KEY (id_status) REFERENCES status(id)
);

-- 16. Ítems del Pedido
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_order INT,
    id_menu_item INT,
    quantity INT NOT NULL,
    note VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_order) REFERENCES orders(id),
    FOREIGN KEY (id_menu_item) REFERENCES menu_items(id)
);

-- 17. Información de la Empresa (SIN Soft Delete)
CREATE TABLE information_company (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    address VARCHAR(30) NOT NULL, -- Corregido de 'adress' a 'address'
    location VARCHAR (50) NOT NULL,
    identification_number VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    -- Eliminados deleted y deleted_on según lo acordado.
);

-- 18. Facturas
CREATE TABLE invoices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    id_client INT NOT NULL,
    id_order INT NOT NULL,
    id_payment_method INT NOT NULL,
    returned DECIMAL(10, 2) NOT NULL, -- Cambio devuelto
    ammount_paid DECIMAL(10, 2) NOT NULL, -- Monto pagado
    total DECIMAL(10, 2) NOT NULL,
    id_status INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_on TIMESTAMP NULL,
    FOREIGN KEY (id_order) REFERENCES orders(id),
    FOREIGN KEY (id_client) REFERENCES clients(id),
    FOREIGN KEY (id_payment_method) REFERENCES payment_method(id),
    FOREIGN KEY (id_status) REFERENCES status(id)
);