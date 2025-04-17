# manage.py

import eventlet
eventlet.monkey_patch()  # Очень важно: это должно быть самым первым!

from flask_migrate import Migrate, upgrade, migrate, init, stamp
from flask.cli import FlaskGroup
from app import create_app
from app.extensions import db
import click

app = create_app()
cli = FlaskGroup(app)

@cli.command("db_init")
def db_init():
    """Инициализация миграций"""
    with app.app_context():
        init()

@cli.command("db_migrate")
def db_migrate():
    """Создание новой миграции"""
    with app.app_context():
        migrate()

@cli.command("db_upgrade")
def db_upgrade():
    """Применение миграций"""
    with app.app_context():
        upgrade()

@cli.command("db_stamp")
def db_stamp():
    """Проставить текущую версию без миграции"""
    with app.app_context():
        stamp()

if __name__ == "__main__":
    cli()
