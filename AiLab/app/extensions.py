# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_login import LoginManager


db = SQLAlchemy()
socketio = SocketIO(cors_allowed_origins="*", engineio_logger=True, logger=True)
login = LoginManager()
