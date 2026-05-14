from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# =========================
# MODELO USUARIOS
# =========================
class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='admin')

    def __repr__(self):
        return f'<Usuario {self.username}>'

# =========================
# MODELO ESPACIOS
# =========================
class Espacio(db.Model):
    __tablename__ = 'espacios'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    estado = db.Column(db.String(30), nullable=False)

    def __repr__(self):
        return f'<Espacio {self.numero}>'

# =========================
# MODELO VEHICULOS
# =========================
class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'

    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(20), unique=True, nullable=False)
    conductor = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    archivado = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'<Vehiculo {self.placa}>'

# =========================
# MODELO TICKETS
# =========================
class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)

    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculos.id'),
        nullable=False
    )

    espacio_id = db.Column(
        db.Integer,
        db.ForeignKey('espacios.id'),
        nullable=False
    )

    hora_entrada = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    hora_salida = db.Column(db.DateTime)

    estado = db.Column(
        db.String(30),
        nullable=False,
        default='activo'
    )

    total = db.Column(
        db.Numeric(10,2),
        default=0
    )

    vehiculo = db.relationship('Vehiculo')
    espacio = db.relationship('Espacio')

    def __repr__(self):
        return f'<Ticket {self.id}>'

# =========================
# MODELO PAGOS
# =========================
class Pago(db.Model):
    __tablename__ = 'pagos'

    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey('tickets.id'),
        nullable=False
    )

    metodo_pago = db.Column(
        db.String(30),
        nullable=False
    )

    monto = db.Column(
        db.Numeric(10,2),
        nullable=False
    )

    fecha_pago = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    ticket = db.relationship('Ticket')

    def __repr__(self):
        return f'<Pago {self.id}>'

# =========================
# MODELO TARIFAS
# =========================
class Tarifa(db.Model):
    __tablename__ = 'tarifas'

    id = db.Column(db.Integer, primary_key=True)

    tipo_vehiculo = db.Column(
        db.String(30),
        nullable=False
    )

    precio_hora = db.Column(
        db.Numeric(10,2),
        nullable=False
    )

    def __repr__(self):
        return f'<Tarifa {self.tipo_vehiculo}>'
