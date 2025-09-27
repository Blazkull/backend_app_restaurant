CREATE DATABASE db_restraurante_la_media_luna;

USE db_restraurante_la_media_luna;

-- tipo de identificacion
CREATE TABLE type_identification(
	id INT PRIMARY KEY AUTO_INCREMENT,
    type_identificaction VARCHAR(20),
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	deleted_at TIMESTAMP NULL
);


-- Gestión de Clientes, Usuarios, Roles y Permisos
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
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_type_identificacion) REFERENCES type_identification(id)
);

CREATE TABLE status (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(20) NOT NULL,
  description VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL
);

CREATE TABLE roles (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  id_status INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_status) REFERENCES status(id)
);

CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  password VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  id_role INT,
  id_status INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_role) REFERENCES roles(id),
  FOREIGN KEY (id_status) REFERENCES status(id)
);

CREATE TABLE tokens (
  id INT PRIMARY KEY AUTO_INCREMENT,
  id_user INT NOT NULL,
  token VARCHAR(255) NOT NULL,
  status_token TINYINT NOT NULL,
  expiration DATETIME NOT NULL,
  date_token DATETIME NOT NULL,
  FOREIGN KEY (id_user) REFERENCES users(id)
);

CREATE TABLE views (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  id_status INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_status) REFERENCES status(id)
);

CREATE TABLE user_roles (
  id_user INT,
  id_role INT,
  PRIMARY KEY (id_user, id_role),
  FOREIGN KEY (id_user) REFERENCES users(id),
  FOREIGN KEY (id_role) REFERENCES roles(id)
);

CREATE TABLE role_views (
  id_role INT,
  id_view INT,
  PRIMARY KEY (id_role, id_view),
  FOREIGN KEY (id_role) REFERENCES roles(id),
  FOREIGN KEY (id_view) REFERENCES views(id)
);

-- Gestión de Ubicaciones y Mesas
CREATE TABLE locations (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  description VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL
);


-- Gestión de Menú
CREATE TABLE categories (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  description VARCHAR(50) ,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL
);

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
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_category) REFERENCES categories(id),
  FOREIGN KEY (id_status) REFERENCES status(id) 
);

CREATE TABLE tables (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(20) NOT NULL,     
  id_location INT NOT NULL,
  capacity INT NOT NULL,
  id_status INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_location) REFERENCES locations(id),
  FOREIGN KEY (id_status) REFERENCES status(id)
);

-- Gestión de Pedidos y Facturación
CREATE TABLE orders (
  id INT PRIMARY KEY AUTO_INCREMENT,
  id_table INT NOT NULL,
  id_status INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_table) REFERENCES tables(id),
  FOREIGN KEY (id_status) REFERENCES status(id)
);

CREATE TABLE order_items (
  id INT PRIMARY KEY AUTO_INCREMENT,
  id_order INT,
  id_menu_item INT,
  quantity INT NOT NULL,
  note VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_order) REFERENCES orders(id),
  FOREIGN KEY (id_menu_item) REFERENCES menu_items(id)
  
);

CREATE TABLE payment_method (
	id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(30) NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	deleted_at TIMESTAMP NULL
);

CREATE TABLE information_company (
	id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    adress VARCHAR(30) NOT NULL,
    location VARCHAR (50) NOT NULL,
    identification_number VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE invoices (
  id INT PRIMARY KEY AUTO_INCREMENT,
  id_client INT NOT NULL,
  id_order INT NOT NULL,
  id_payment_method INT NOT NULL,
  returned DECIMAL(10, 2) NOT NULL,
  ammount_paid DECIMAL(10, 2) NOT NULL,
  total DECIMAL(10, 2) NOT NULL,
  id_status INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  FOREIGN KEY (id_order) REFERENCES orders(id),
  FOREIGN KEY (id_client) REFERENCES clients(id),
  FOREIGN KEY (id_payment_method) REFERENCES payment_method(id),
  FOREIGN KEY (id_status) REFERENCES status(id)
);


 
