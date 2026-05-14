-- =========================================
-- CONTROL DE ESTACIONAMIENTO
-- POSTGRESQL
-- =========================================

-- =========================
-- TABLA USUARIOS
-- =========================
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    rol VARCHAR(20) DEFAULT 'admin'
);

-- =========================
-- TABLA ESPACIOS
-- =========================
CREATE TABLE espacios (
    id SERIAL PRIMARY KEY,
    numero INTEGER NOT NULL UNIQUE,
    estado VARCHAR(30) NOT NULL
);

-- =========================
-- TABLA VEHICULOS
-- =========================
CREATE TABLE vehiculos (
    id SERIAL PRIMARY KEY,
    placa VARCHAR(20) NOT NULL UNIQUE,
    conductor VARCHAR(100) NOT NULL,
    tipo VARCHAR(30) NOT NULL
);

-- =========================
-- TABLA TICKETS
-- =========================
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,

    vehiculo_id INTEGER NOT NULL,
    espacio_id INTEGER NOT NULL,

    hora_entrada TIMESTAMP NOT NULL,
    hora_salida TIMESTAMP,

    estado VARCHAR(30) NOT NULL,

    total NUMERIC(10,2) DEFAULT 0,

    CONSTRAINT fk_vehiculo
        FOREIGN KEY (vehiculo_id)
        REFERENCES vehiculos(id),

    CONSTRAINT fk_espacio
        FOREIGN KEY (espacio_id)
        REFERENCES espacios(id)
);

-- =========================
-- TABLA PAGOS
-- =========================
CREATE TABLE pagos (
    id SERIAL PRIMARY KEY,

    ticket_id INTEGER NOT NULL,

    metodo_pago VARCHAR(30) NOT NULL,

    monto NUMERIC(10,2) NOT NULL,

    fecha_pago TIMESTAMP NOT NULL,

    CONSTRAINT fk_ticket
        FOREIGN KEY (ticket_id)
        REFERENCES tickets(id)
);

-- =========================
-- TABLA TARIFAS
-- =========================
CREATE TABLE tarifas (
    id SERIAL PRIMARY KEY,

    tipo_vehiculo VARCHAR(30) NOT NULL,

    precio_hora NUMERIC(10,2) NOT NULL
);

-- =========================================
-- DATOS INICIALES
-- =========================================

-- Usuario administrador
INSERT INTO usuarios (
    username,
    password,
    nombre,
    rol
)
VALUES (
    'admin',
    'admin123',
    'Administrador',
    'admin'
);

-- Tarifas
INSERT INTO tarifas (
    tipo_vehiculo,
    precio_hora
)
VALUES
('automovil', 25),
('motocicleta', 15),
('camioneta', 30),
('otro', 20);

-- Espacios iniciales
INSERT INTO espacios (
    numero,
    estado
)
VALUES
(1, 'disponible'),
(2, 'disponible'),
(3, 'disponible'),
(4, 'disponible'),
(5, 'disponible'),
(6, 'disponible'),
(7, 'disponible'),
(8, 'disponible'),
(9, 'disponible'),
(10, 'disponible');