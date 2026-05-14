from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# =========================
# CONFIGURACION APP
# =========================
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY',
    'parking_secret_key'
)

# =========================
# DATABASE URL RENDER
# =========================
database_url = os.getenv('DATABASE_URL')

# Para desarrollo local
if not database_url:
    database_url = 'postgresql://postgres:TU_PASSWORD@localhost/parking_db'

# Fix Render postgres://
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# =========================
# DATABASE
# =========================
db = SQLAlchemy()
db.init_app(app)

# =========================
# MODELOS
# =========================

class Vehiculo(db.Model):

    __tablename__ = 'vehiculos'

    id = db.Column(db.Integer, primary_key=True)

    placa = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    conductor = db.Column(
        db.String(100),
        nullable=False
    )

    tipo = db.Column(
        db.String(50),
        nullable=False
    )


class Espacio(db.Model):

    __tablename__ = 'espacios'

    id = db.Column(db.Integer, primary_key=True)

    numero = db.Column(
        db.String(10),
        unique=True,
        nullable=False
    )

    estado = db.Column(
        db.String(20),
        default='disponible'
    )


class Ticket(db.Model):

    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)

    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculos.id')
    )

    espacio_id = db.Column(
        db.Integer,
        db.ForeignKey('espacios.id')
    )

    hora_entrada = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    hora_salida = db.Column(
        db.DateTime,
        nullable=True
    )

    estado = db.Column(
        db.String(20),
        default='activo'
    )

    total = db.Column(
        db.Numeric(10, 2),
        default=0
    )

    vehiculo = db.relationship('Vehiculo')

    espacio = db.relationship('Espacio')

    pago = db.relationship(
        'Pago',
        backref='ticket_relacion',
        uselist=False
    )


class Pago(db.Model):

    __tablename__ = 'pagos'

    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey('tickets.id')
    )

    metodo_pago = db.Column(
        db.String(50),
        nullable=False
    )

    monto = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    fecha_pago = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    ticket = db.relationship('Ticket')


class Tarifa(db.Model):

    __tablename__ = 'tarifas'

    id = db.Column(db.Integer, primary_key=True)

    tipo_vehiculo = db.Column(
        db.String(50),
        nullable=False
    )

    precio_hora = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

# =========================
# CREAR TABLAS
# =========================
with app.app_context():
    db.create_all()

# =========================
# DASHBOARD
# =========================
@app.route('/')
def home():

    total_espacios = Espacio.query.count()

    disponibles = Espacio.query.filter_by(
        estado='disponible'
    ).count()

    ocupados = Espacio.query.filter_by(
        estado='ocupado'
    ).count()

    tickets_activos = Ticket.query.filter_by(
        estado='activo'
    ).count()

    tickets_finalizados = Ticket.query.filter(
        Ticket.estado.in_(['finalizado', 'pagado'])
    ).count()

    pagos = Pago.query.all()

    ingresos = sum(
        float(pago.monto)
        for pago in pagos
    )

    return render_template(
        'dashboard.html',

        total_espacios=total_espacios,
        disponibles=disponibles,
        ocupados=ocupados,

        tickets_activos=tickets_activos,
        tickets_finalizados=tickets_finalizados,

        ingresos=ingresos
    )

# =========================
# LISTAR VEHICULOS
# =========================
@app.route('/vehiculos')
def vehiculos():

    lista_vehiculos = Vehiculo.query.all()

    return render_template(
        'vehiculos.html',
        vehiculos=lista_vehiculos
    )

# =========================
# AGREGAR VEHICULO
# =========================
@app.route('/vehiculos/agregar', methods=['GET', 'POST'])
def agregar_vehiculo():

    if request.method == 'POST':

        placa = request.form['placa']
        conductor = request.form['conductor']
        tipo = request.form['tipo']

        nuevo_vehiculo = Vehiculo(
            placa=placa,
            conductor=conductor,
            tipo=tipo
        )

        db.session.add(nuevo_vehiculo)
        db.session.commit()

        return redirect('/vehiculos')

    return render_template(
        'agregar_vehiculo.html'
    )

# =========================
# ELIMINAR VEHICULO
# =========================
@app.route('/vehiculos/eliminar/<int:id>')
def eliminar_vehiculo(id):

    vehiculo = Vehiculo.query.get_or_404(id)

    db.session.delete(vehiculo)
    db.session.commit()

    return redirect('/vehiculos')

# =========================
# LISTAR TICKETS
# =========================
@app.route('/tickets')
def tickets():

    lista_tickets = Ticket.query.filter_by(
        estado='activo'
    ).all()

    return render_template(
        'tickets.html',
        tickets=lista_tickets
    )

# =========================
# NUEVO TICKET
# =========================
@app.route('/tickets/nuevo', methods=['GET', 'POST'])
def nuevo_ticket():

    vehiculos = Vehiculo.query.all()

    espacios = Espacio.query.filter_by(
        estado='disponible'
    ).all()

    if request.method == 'POST':

        vehiculo_id = request.form['vehiculo_id']
        espacio_id = request.form['espacio_id']

        ticket = Ticket(
            vehiculo_id=vehiculo_id,
            espacio_id=espacio_id,
            estado='activo'
        )

        db.session.add(ticket)

        espacio = Espacio.query.get(espacio_id)

        espacio.estado = 'ocupado'

        db.session.commit()

        return redirect('/tickets')

    return render_template(
        'nuevo_ticket.html',
        vehiculos=vehiculos,
        espacios=espacios
    )

# =========================
# REGISTRAR SALIDA
# =========================
@app.route('/tickets/salida/<int:id>')
def salida_ticket(id):

    ticket = Ticket.query.get_or_404(id)

    ticket.hora_salida = datetime.utcnow()

    tiempo = (
        ticket.hora_salida -
        ticket.hora_entrada
    ).total_seconds() / 3600

    horas = max(1, round(tiempo))

    tarifa = Tarifa.query.filter_by(
        tipo_vehiculo=ticket.vehiculo.tipo
    ).first()

    # Si no hay tarifa
    if not tarifa:
        total = 50
    else:
        total = horas * float(tarifa.precio_hora)

    ticket.total = total
    ticket.estado = 'finalizado'

    ticket.espacio.estado = 'disponible'

    db.session.commit()

    return redirect('/tickets')

# =========================
# HISTORIAL
# =========================
@app.route('/historial')
def historial():

    tickets = Ticket.query.order_by(
        Ticket.id.desc()
    ).all()

    return render_template(
        'historial.html',
        tickets=tickets
    )

# =========================
# LISTAR PAGOS
# =========================
@app.route('/pagos')
def pagos():

    lista_pagos = Pago.query.order_by(
        Pago.id.desc()
    ).all()

    return render_template(
        'pagos.html',
        pagos=lista_pagos
    )

# =========================
# REGISTRAR PAGO
# =========================
@app.route('/pagos/<int:id>', methods=['GET', 'POST'])
def registrar_pago(id):

    ticket = Ticket.query.get_or_404(id)

    if request.method == 'POST':

        metodo_pago = request.form['metodo_pago']

        pago = Pago(
            ticket_id=ticket.id,
            metodo_pago=metodo_pago,
            monto=ticket.total
        )

        db.session.add(pago)

        ticket.estado = 'pagado'

        db.session.commit()

        return redirect('/historial')

    return render_template(
        'pago.html',
        ticket=ticket
    )

# =========================
# MAIN
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)