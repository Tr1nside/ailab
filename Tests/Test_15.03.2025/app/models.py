from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as so
from .extensions import db, login

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    last_name = db.Column(db.String(50), nullable=False)  # Фамилия
    first_name = db.Column(db.String(50), nullable=False)  # Имя
    middle_name = db.Column(db.String(50), nullable=False)  # Отчество (может быть пустым)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        print(check_password_hash(self.password_hash, password))
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.email)

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))