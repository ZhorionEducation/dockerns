from app import create_app
from flask import render_template
from flask_talisman import Talisman  # Importa Flask-Talisman
from ldap3 import Server, Connection, ALL, SIMPLE
import socket

app = create_app()

# Configuración de modo de mantenimiento de forma centralizada
app.config['MAINTENANCE_MODE'] = False


@app.before_request
def check_for_maintenance():
    if app.config.get('MAINTENANCE_MODE'):
        return render_template('maintenance.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)