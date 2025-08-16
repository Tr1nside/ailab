from flask import Flask
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from importlib import import_module


# Инициализация расширений
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*", engineio_logger=True, logger=True)
migrate = Migrate()


def _register_socketio(app):
    """Инициализация SocketIO"""
    from app.ide.socketio_events import register_socketio_events

    socketio.init_app(app)
    register_socketio_events(socketio)


def _register_extensions(app):
    """Инициализация всех расширений (SQLAlchemy, LoginManager, SocketIO, Migrate)"""
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # Инициализация Flask-Migrate
    _register_socketio(app)


def _register_blueprints(app):
    """Регистрация blueprints"""
    for module_name in (
        "base",
        "auth",
        "ide",
        "profile",
        "friendship",
        "messanger",
        "filetree",
    ):
        print(f"Регистрируем blueprint: app.{module_name}.routes")  # Для отладки
        module = import_module(f"app.{module_name}.routes")
        app.register_blueprint(module.blueprint)


def _configure_database(app):
    """Настройка базы данных"""
    # Инициализация базы данных и создание таблиц
    with app.app_context():
        db.create_all()  # Создаём таблицы, если их нет

    # Очистка сессии после каждого запроса
    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def create_app(config):
    """Создание приложения Flask"""
    app = Flask(
        __name__,
        static_folder="base/static",
        template_folder="base/templates",
    )
    app.config.from_object(config)

    from app.base import models

    # Инициализация расширений и blueprints
    _register_extensions(app)
    _register_blueprints(app)
    _configure_database(app)

    return app

