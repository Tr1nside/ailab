from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional
from flask_login import UserMixin
import sqlalchemy as sa
import sqlalchemy.orm as so
from .extensions import db, login
from datetime import datetime


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    last_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    first_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    middle_name: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        sa.DateTime, default=datetime.utcnow
    )

    # Двусторонняя связь с моделью UserProfile (один к одному)
    profile: so.Mapped[Optional["UserProfile"]] = db.relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def is_online(self):
        if self.last_seen:
            return (datetime.utcnow() - self.last_seen).total_seconds() < 300  # 5 минут
        return False

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"

    def is_friend(self, friend_id):
        return (
            Friendship.query.filter(
                ((Friendship.user_id == self.id) & (Friendship.friend_id == friend_id))
                | (
                    (Friendship.user_id == friend_id)
                    & (Friendship.friend_id == self.id)
                ),
                Friendship.status == "accepted",
            ).first()
            is not None
        )

    def get_friends(self):
        # Получаем подтвержденные дружеские связи
        friendships = Friendship.query.filter(
            ((Friendship.user_id == self.id) | (Friendship.friend_id == self.id)),
            Friendship.status == "accepted",
        ).all()

        friends = []
        for fs in friendships:
            if fs.user_id == self.id:
                friend = User.query.get(fs.friend_id)
            else:
                friend = User.query.get(fs.user_id)
            friends.append(friend)

        return friends

    @classmethod
    def get_friendship_status(cls, user_id, friend_id):
        """
        Возвращает статус дружбы между двумя пользователями.
        Возможные значения:
        - 'accepted': Пользователи друзья.
        - 'pending': Запрос на дружбу ожидает подтверждения.
        - None: Нет активной дружбы или запроса.
        """
        friendshipU_F = Friendship.query.filter(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id))
        ).first()

        friendshipF_U = Friendship.query.filter(
            ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
        ).first()

        if friendshipU_F:
            if friendshipU_F.status == "accepted":
                return "accepted"
            elif friendshipU_F.status == "pending":
                return "U_F"
        elif friendshipF_U:
            if friendshipF_U.status == "accepted":
                return "accepted"
            elif friendshipF_U.status == "pending":
                return "F_U"
        return None


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


class UserProfile(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(
        sa.Integer, db.ForeignKey("user.id"), unique=True, nullable=False
    )
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
    user: so.Mapped["User"] = db.relationship("User", back_populates="profile")


# models.py
class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending/accepted/declined
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Отношение к пользователям
    user = db.relationship("User", foreign_keys=[user_id], backref="sent_requests")
    friend = db.relationship(
        "User", foreign_keys=[friend_id], backref="received_requests"
    )


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("message.id"), nullable=False)
    url = db.Column(db.String(512), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)

    message = db.relationship("Message", back_populates="attachments")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    recipient = db.relationship(
        "User", foreign_keys=[recipient_id], backref="received_messages"
    )
    attachments = db.relationship(
        "Attachment", back_populates="message", cascade="all, delete-orphan"
    )
