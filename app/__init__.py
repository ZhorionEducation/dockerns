from flask import Flask
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'you-will-never-guess'  # Asegúrate de usar una clave secreta segura
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)

# Importar y registrar blueprints
from app.routes import main as main_blueprint
app.register_blueprint(main_blueprint)

def create_app():
    app = Flask(__name__)
    app.secret_key = 'clave_secreta_segura'

    # Registrar Blueprints
    from .routes import main
    app.register_blueprint(main)

    return app