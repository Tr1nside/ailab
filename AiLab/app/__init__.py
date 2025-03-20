import eventlet

eventlet.monkey_patch()
from .routes import (
    main_bp,
    register_socketio_events,
)  # Импортируем наш Blueprint и функцию, где регистрируются события
from config import Config
import os
from flask_migrate import Migrate
from flask import Flask
from .extensions import socketio, db, login


MAIN_FOLDER = os.path.dirname(os.path.abspath(__file__))


def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(MAIN_FOLDER, "..", "static"),
        template_folder=os.path.join(MAIN_FOLDER, "..", "templates"),
    )  # Создаём Flask-приложение

    app.config.from_object(Config)
    db.init_app(app)
    socketio.init_app(app)
    login.login_view = "main_bp.login"  # Указываем правильный endpoint
    login.init_app(app)

    migrate = Migrate(app, db)

    from .models import User

    app.register_blueprint(main_bp)  # Регистрируем Blueprint
    register_socketio_events(
        socketio
    )  # Регистрируем события для SocketIO (обработчики on('execute'), on('console_input'), и т.д.)

    return app
