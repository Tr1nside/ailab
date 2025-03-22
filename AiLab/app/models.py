from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as so
from .extensions import db, login


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    last_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    first_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    middle_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    
    # Двусторонняя связь с моделью UserProfile (один к одному)
    profile: so.Mapped[Optional["UserProfile"]] = db.relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

class UserProfile(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    full_name: so.Mapped[Optional[str]] = so.mapped_column(sa.String(100))
    email: so.Mapped[Optional[str]] = so.mapped_column(sa.String(120))
    phone: so.Mapped[Optional[str]] = so.mapped_column(sa.String(20))
    position: so.Mapped[Optional[str]] = so.mapped_column(sa.String(200))
    profile_photo: so.Mapped[Optional[str]] = so.mapped_column(sa.String(200))
    qr_photo: so.Mapped[Optional[str]] = so.mapped_column(sa.String(200))
    github_link: so.Mapped[Optional[str]] = so.mapped_column(sa.String(100))
    telegram_link: so.Mapped[Optional[str]] = so.mapped_column(sa.String(100))
    vk_link: so.Mapped[Optional[str]] = so.mapped_column(sa.String(100))
    

    # Обратная связь, позволяющая получить пользователя, которому принадлежит профиль
    user: so.Mapped["User"] = db.relationship('User', back_populates='profile')