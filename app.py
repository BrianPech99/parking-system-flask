from flask import Flask, render_template, request, redirect, flash
from dotenv import load_dotenv
import os
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from math import ceil
from sqlalchemy import inspect, text

from models import (
    db,
    Usuario,
    Espacio,
    Vehiculo,
    Ticket,
    Pago,
    Tarifa
)

# =========================
# CARGAR VARIABLES
# =========================
load_dotenv()

# =========================
# CONFIGURAR APP
# =========================
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

PLACA_REGEX = re.compile(r'^[A-Z]{3}[0-9]{3}[A-Z]$')

# =========================
# INICIALIZAR DB
# =========================
db.init_app(app)


def asegurar_columna_archivado():
    inspector = inspect(db.engine)
    columnas = [
        columna['name']
        for columna in inspector.get_columns('vehiculos')
    ]

    if 'archivado' in columnas:
        return False

    db.session.execute(
        text(
            'ALTER TABLE vehiculos '
            'ADD COLUMN archivado BOOLEAN NOT NULL DEFAULT FALSE'
        )
    )
    db.session.commit()
    return True

# =========================
# CREAR TABLAS
# =========================
with app.app_context():
    db.create_all()
    columna_archivado_creada = asegurar_columna_archivado()

        # Crear espacios iniciales
    if Espacio.query.count() == 0:
        for i in range(1, 11):
            espacio = Espacio(
                numero=i,
                estado='disponible'
            )
            db.session.add(espacio)

        db.session.commit()

    # Crear tarifas iniciales
    if Tarifa.query.count() == 0:
        tarifas = [
            Tarifa(tipo_vehiculo='automovil', precio_hora=25),
            Tarifa(tipo_vehiculo='motocicleta', precio_hora=15),
            Tarifa(tipo_vehiculo='camioneta', precio_hora=30),
            Tarifa(tipo_vehiculo='otro', precio_hora=20)
        ]

        db.session.add_all(tarifas)
        db.session.commit()

    if columna_archivado_creada:
        vehiculos_pagados = Vehiculo.query.join(Ticket).filter(
            Ticket.estado == 'pagado'
        ).all()

        for vehiculo in vehiculos_pagados:
            vehiculo.archivado = True

        db.session.commit()

# =========================
# RUTA PRINCIPAL
# =========================
from flask import render_template


def calcular_total_ticket(ticket, ahora=None):
    ahora = ahora or datetime.utcnow()
    segundos = max(
        0,
        (ahora - ticket.hora_entrada).total_seconds()
    )
    minutos = max(1, ceil(segundos / 60))

    tarifa = Tarifa.query.filter_by(
        tipo_vehiculo=ticket.vehiculo.tipo
    ).first()

    precio_minuto = Decimal(tarifa.precio_hora if tarifa else 0)
    total = (precio_minuto * minutos).quantize(
        Decimal('0.01'),
        rounding=ROUND_HALF_UP
    )

    return total, minutos


def normalizar_placa(placa):
    placa_limpia = re.sub(r'[^A-Za-z0-9]', '', placa).upper()

    if len(placa_limpia) == 7:
        return (
            f'{placa_limpia[:3]}-'
            f'{placa_limpia[3:6]}-'
            f'{placa_limpia[6]}'
        )

    return placa_limpia


def placa_valida(placa):
    placa_limpia = re.sub(r'[^A-Za-z0-9]', '', placa).upper()
    return bool(PLACA_REGEX.match(placa_limpia))


def obtener_mapa_espacios():
    espacios = Espacio.query.order_by(Espacio.numero).all()
    tickets_activos = Ticket.query.filter_by(
        estado='activo'
    ).all()
    tickets_por_espacio = {
        ticket.espacio_id: ticket
        for ticket in tickets_activos
    }

    return [
        {
            'espacio': espacio,
            'ticket': tickets_por_espacio.get(espacio.id)
        }
        for espacio in espacios
    ]


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

    tickets_en_curso = Ticket.query.filter_by(
        estado='activo'
    ).all()
    ingresos_en_curso = sum(
        float(calcular_total_ticket(ticket)[0])
        for ticket in tickets_en_curso
    )

    return render_template(
        'dashboard.html',

        total_espacios=total_espacios,
        disponibles=disponibles,
        ocupados=ocupados,

        tickets_activos=tickets_activos,
        tickets_finalizados=tickets_finalizados,

        ingresos=ingresos,
        ingresos_en_curso=ingresos_en_curso,
        mapa_espacios=obtener_mapa_espacios()
    )


@app.route('/espacios')
def espacios():

    mapa_espacios = obtener_mapa_espacios()

    total_espacios = len(mapa_espacios)
    disponibles = sum(
        1
        for item in mapa_espacios
        if item['espacio'].estado == 'disponible'
    )
    ocupados = sum(
        1
        for item in mapa_espacios
        if item['espacio'].estado == 'ocupado'
    )

    return render_template(
        'espacios.html',
        mapa_espacios=mapa_espacios,
        total_espacios=total_espacios,
        disponibles=disponibles,
        ocupados=ocupados
    )
# =========================
# LISTAR VEHICULOS
# =========================
@app.route('/vehiculos')
def vehiculos():

    lista_vehiculos = Vehiculo.query.filter_by(
        archivado=False
    ).all()

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
        placa = normalizar_placa(placa)

        if not placa_valida(placa):
            flash(
                'La placa debe tener el formato ABC-123-A.',
                'warning'
            )
            return redirect('/vehiculos/agregar')

        vehiculo_existente = Vehiculo.query.filter_by(
            placa=placa
        ).first()

        if vehiculo_existente and not vehiculo_existente.archivado:
            flash(
                'Esa placa ya esta registrada y disponible en el sistema.',
                'warning'
            )
            return redirect('/vehiculos/agregar')

        if vehiculo_existente and vehiculo_existente.archivado:
            vehiculo_existente.conductor = conductor
            vehiculo_existente.tipo = tipo
            vehiculo_existente.archivado = False
            db.session.commit()

            flash(
                'Vehiculo registrado nuevamente. Ya puede crear una nueva entrada.',
                'success'
            )
            return redirect('/vehiculos')

        nuevo_vehiculo = Vehiculo(
            placa=placa,
            conductor=conductor,
            tipo=tipo
        )

        db.session.add(nuevo_vehiculo)
        db.session.commit()

        flash(
            'Vehiculo registrado correctamente.',
            'success'
        )

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

    ticket_activo = Ticket.query.filter_by(
        vehiculo_id=vehiculo.id,
        estado='activo'
    ).first()

    if ticket_activo:
        flash(
            'No se puede eliminar el vehiculo porque tiene un ticket activo. Registra su salida primero.',
            'warning'
        )
        return redirect('/vehiculos')

    tiene_historial = Ticket.query.filter_by(
        vehiculo_id=vehiculo.id
    ).first()

    if tiene_historial:
        flash(
            'El vehiculo tiene historial de tickets y no se elimino para conservar los registros.',
            'info'
        )
        return redirect('/vehiculos')

    db.session.delete(vehiculo)
    db.session.commit()

    flash(
        'Vehiculo eliminado correctamente.',
        'success'
    )

    return redirect('/vehiculos')


# =========================
# LISTAR TICKETS
# =========================
@app.route('/tickets')
def tickets():

    lista_tickets = Ticket.query.filter_by(
        estado='activo'
    ).all()

    for ticket in lista_tickets:
        total_actual, minutos_actuales = calcular_total_ticket(ticket)
        ticket.total_actual = total_actual
        ticket.minutos_actuales = minutos_actuales

    return render_template(
        'tickets.html',
        tickets=lista_tickets
    )

# =========================
# NUEVO TICKET
# =========================
@app.route('/tickets/nuevo', methods=['GET', 'POST'])
def nuevo_ticket():

    vehiculos_ocupados = [
        ticket.vehiculo_id
        for ticket in Ticket.query.filter_by(
            estado='activo'
        ).all()
    ]

    vehiculos = Vehiculo.query.filter(
        Vehiculo.archivado == False,
        ~Vehiculo.id.in_(vehiculos_ocupados)
    ).all()

    espacios = Espacio.query.filter_by(
        estado='disponible'
    ).all()

    if request.method == 'POST':

        vehiculo_id = request.form['vehiculo_id']
        espacio_id = request.form['espacio_id']

        ticket_existente = Ticket.query.filter_by(
            vehiculo_id=vehiculo_id,
            estado='activo'
        ).first()

        if ticket_existente:
            flash(
                'Ese vehiculo ya tiene un ticket activo y no puede registrarse de nuevo.',
                'warning'
            )
            return redirect('/tickets/nuevo')

        vehiculo = Vehiculo.query.get(vehiculo_id)

        if not vehiculo or vehiculo.archivado:
            flash(
                'Ese vehiculo ya fue pagado o no esta disponible. Registralo nuevamente para crear otra entrada.',
                'warning'
            )
            return redirect('/tickets/nuevo')

        # Crear ticket
        ticket = Ticket(
            vehiculo_id=vehiculo_id,
            espacio_id=espacio_id,
            estado='activo'
        )

        db.session.add(ticket)

        # Cambiar espacio a ocupado
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

    total, minutos = calcular_total_ticket(
        ticket,
        ticket.hora_salida
    )

    ticket.total = total
    ticket.estado = 'finalizado'

    # Liberar espacio
    ticket.espacio.estado = 'disponible'

    db.session.commit()

    flash(
        f'Salida registrada. Tiempo cobrado: {minutos} minuto(s).',
        'success'
    )

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
        ticket.vehiculo.archivado = True

        db.session.commit()

        return redirect('/historial')

    return render_template(
        'pago.html',
        ticket=ticket
    )

# =========================
# LISTAR PAGOS
# =========================
@app.route('/pagos')
def pagos():

    lista_pagos = Pago.query.order_by(
        Pago.id.desc()
    ).all()

    total_pagado = sum(
        float(pago.monto)
        for pago in lista_pagos
    )

    return render_template(
        'pagos.html',
        pagos=lista_pagos,
        total_pagado=total_pagado
    )
# =========================
# EJECUTAR APP
# =========================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
