from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Email,
    EqualTo,
    Length,
    Regexp,
    Optional,
)
from flask_wtf.file import FileField, FileAllowed
from werkzeug.security import check_password_hash
import sqlalchemy as sa
from .extensions import db
from .models import User


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(message="Это поле обязательно для заполнения")],
    )
    password = PasswordField(
        "Пароль",
        validators=[DataRequired(message="Это поле обязательно для заполнения")],
    )
    submit = SubmitField("Войти")

    def validate_email(self, email):
        # Поиск пользователя в базе данных по email
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError("Пользователь с таким email не зарегистрирован")

    def validate_password(self, password):
        # Поиск пользователя в базе данных по email
        user = User.query.filter_by(email=self.email.data).first()
        if user and not check_password_hash(user.password_hash, password.data):
            raise ValidationError("Неверный пароль")


def must_accept(form, field):
    if not field.data:
        raise ValidationError("Вы должны согласиться с условиями")


class RegistrationForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(message="Это поле обязательно для заполнения"),
            # Email(),
        ],
    )
    last_name = StringField(
        "Фамилия",
        validators=[
            DataRequired(message="Это поле обязательно для заполнения"),
            Length(max=50),
        ],
    )
    first_name = StringField(
        "Имя",
        validators=[
            DataRequired(message="Это поле обязательно для заполнения"),
            Length(max=50),
        ],
    )
    middle_name = StringField(
        "Отчество", validators=[Length(max=50)]
    )  # Может быть пустым
    password = PasswordField(
        "Пароль",
        validators=[
            DataRequired(message="Это поле обязательно для заполнения"),
            Length(min=6, max=100),
            Regexp(
                r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@!#%&?]+$",
                message="Пароль должен содержать буквы и цифры",
            ),
        ],
    )
    password2 = PasswordField(
        "Повторите пароль",
        validators=[
            DataRequired(message="Это поле обязательно для заполнения"),
            EqualTo("password", message="Пароли должны совпадать"),
        ],
    )
    terms_accepted = BooleanField(
        "Нажимая на кнопку, вы соглашаетесь с политикой приложения и условиями пользования.",
        validators=[must_accept],
    )
    submit = SubmitField("Регистрация")

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError("Данная почта уже используется")


class ProfileEditForm(FlaskForm):
    profile_media = FileField(
        "Медиа профиля",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png", "gif", "mp4", "webm"],
                "Разрешены только изображения и видео",
            )
        ],
    )
    full_name = StringField("Полное имя", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField(
        "Телефон",
        validators=[
            Optional(),
            Regexp(r"^\+?[1-9]\d{1,14}$", message="Неверный формат телефона"),
        ],
    )
    position = StringField("Должность", validators=[Optional()])
    telegram_link = StringField(
        "Telegram",
        validators=[
            Optional(),
            Regexp(r"^https://t\.me/\w+", message="Формат: https://t.me/username"),
        ],
    )
    github_link = StringField(
        "GitHub",
        validators=[
            Optional(),
            Regexp(
                r"^https://github\.com/\w+",
                message="Формат: https://github.com/username",
            ),
        ],
    )
    vk_link = StringField(
        "VK",
        validators=[
            Optional(),
            Regexp(r"^https://vk\.com/\w+", message="Формат: https://vk.com/username"),
        ],
    )
    submit = SubmitField("Сохранить")
