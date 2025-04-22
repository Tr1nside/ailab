from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify,
    abort,
    send_file,
)  # Импортируем необходимые модули из Flask
import eventlet  # Импортируем eventlet для работы с асинхронными событиями
import builtins  # Импортируем встроенные функции Python
import contextlib  # Импортируем contextlib для управления контекстами
import io  # Импортируем io для работы с потоками ввода-вывода
import sqlalchemy as sa
import os
from urllib.parse import urlsplit
from .forms import LoginForm, RegistrationForm, ProfileEditForm
from flask_login import current_user, login_user
from flask_login import logout_user
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
from .extensions import db
from .models import User, UserProfile, Friendship, Message, Attachment
from flask_login import login_required
from werkzeug.utils import secure_filename
from .funcs import generate_qr_code
from datetime import datetime
from .extensions import socketio
from flask_socketio import join_room, leave_room
import shutil
from pathlib import Path


main_bp = Blueprint("main_bp", __name__)  # Создаём Blueprint для организации маршрутов
appdir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(appdir, "../static/uploads")
USER_FILES_PATH = os.path.join(appdir, "../user_files")

CONTEXT_MENU_ITEMS = {
    "message": [
        {"label": "Редактировать", "action": "edit"},
        {"label": "Удалить", "action": "delete"},
    ],
    "media": [{"label": "Скачать", "action": "download"}],
}


@main_bp.route(
    "/"
)  # Определяем маршрут для главной страницы, доступной по адресу http://127.0.0.1:5000/
@main_bp.route("/index")
def index():
    return render_template("index.html")  # Возвращаем HTML-шаблон index.html


@main_bp.route("/profile/<int:id>", methods=["GET", "POST"])
@login_required
def profile(id):
    profile = db.first_or_404(sa.select(UserProfile).where(UserProfile.user_id == id))
    form = ProfileEditForm()

    if form.validate_on_submit():
        try:
            # Обновляем текстовые поля
            profile.full_name = form.full_name.data
            profile.email = form.email.data
            profile.phone = form.phone.data
            profile.position = form.position.data
            profile.telegram_link = form.telegram_link.data
            profile.github_link = form.github_link.data
            profile.vk_link = form.vk_link.data

            # Обрабатываем файл
            if form.profile_media.data:
                file = form.profile_media.data
                filename = secure_filename(f"{id}_{file.filename}")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                profile.profile_photo = filename

            db.session.commit()
            flash("Данные успешно сохранены!", "success")
            return redirect(url_for("main_bp.profile", id=id))  # Редирект с ID

        except Exception as e:
            db.session.rollback()
            print(e)

    elif request.method == "GET":
        # Заполняем форму данными из БД
        form.full_name.data = profile.full_name
        form.email.data = profile.email
        form.phone.data = profile.phone
        form.position.data = profile.position
        form.telegram_link.data = profile.telegram_link
        form.github_link.data = profile.github_link
        form.vk_link.data = profile.vk_link

    return render_template(
        "profile.html",
        profile=profile,
        id=id,
        current_endpoint=request.endpoint,
        form=form,
    )


@main_bp.route(
    "/ide"
)  # Определяем маршрут для главной страницы, доступной по адресу http://127.0.0.1:5000/
@login_required
def ide():
    profile = db.first_or_404(
        sa.select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    return render_template(
        "ide.html", current_endpoint=request.endpoint, profile=profile
    )  # Возвращаем HTML-шаблон index.html


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main_bp.ide"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for("main_bp.login"))
        login_user(user)
        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("main_bp.ide")
        return redirect(next_page)
    # Если запрос GET или форма не прошла валидацию, возвращаем страницу входа
    return render_template("login.html", title="Sign In", form=form)


@main_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main_bp.login"))


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main_bp.ide"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            last_name=form.last_name.data,
            first_name=form.first_name.data,
            middle_name=form.middle_name.data,
            email=form.email.data,
        )
        full_name = " ".join(
            filter(
                None, [form.last_name.data, form.first_name.data, form.middle_name.data]
            )
        )
        user.profile = UserProfile(email=form.email.data, full_name=full_name)
        user.set_password(form.password.data)
        user.profile.profile_photo = "standart.png"

        qr_filename = generate_qr_code(user.id, user.email, False)
        user.profile.qr_photo = qr_filename

        db.session.add(user)
        db.session.commit()
        qr_filename = generate_qr_code(user.id, user.email, True)
        
        filename = secure_filename("main.py")
        save_path = os.path.join(USER_FILES_PATH, f"/{current_user.id}" + filename)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w') as f:
            f.write("# Your content here\n")  # Пример записи в файлё
            f.close

        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("main_bp.login"))
    return render_template("register.html", title="Register", form=form)


@main_bp.route("/add_friend", methods=["POST"])
@login_required
def add_friend():
    friend_id = request.form.get("friend_id")

    # Проверка: нельзя добавить себя
    if current_user.id == int(friend_id):
        flash("Нельзя добавить себя в друзья", "error")
        return redirect(url_for("main_bp.profile", id=friend_id))

    # Проверка существующего запроса
    existing = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id))
        | (
            (Friendship.user_id == friend_id)
            & (Friendship.friend_id == current_user.id)
        )
    ).first()

    if existing:
        flash("Запрос на дружбу уже существует", "info")
        return redirect(url_for("main_bp.profile", id=friend_id))

    # Создание нового запроса
    new_request = Friendship(
        user_id=current_user.id, friend_id=friend_id, status="pending"
    )
    db.session.add(new_request)
    db.session.commit()

    flash("Запрос на дружбу отправлен!", "success")
    return redirect(url_for("main_bp.profile", id=friend_id))


# routes.py
@main_bp.route("/friend_requests")
@login_required
def friend_requests():
    # Входящие запросы
    incoming = Friendship.query.filter(
        Friendship.friend_id == current_user.id, Friendship.status == "pending"
    ).all()

    # Исходящие запросы
    outgoing = Friendship.query.filter(
        Friendship.user_id == current_user.id, Friendship.status == "pending"
    ).all()

    # Список друзей
    friends = current_user.get_friends()
    profile = db.first_or_404(
        sa.select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    return render_template(
        "friend_requests.html",
        incoming=incoming,
        outgoing=outgoing,
        friends=friends,
        profile=profile,
    )


# routes.py
@main_bp.route("/accept_request/<int:request_id>", methods=["POST"])
@login_required
def accept_request(request_id):
    request = Friendship.query.get_or_404(request_id)

    if request.friend_id != current_user.id:
        flash("Вы не можете подтвердить этот запрос", "error")
        return redirect(url_for("main_bp.friend_requests"))

    request.status = "accepted"
    db.session.commit()

    flash("Запрос на дружбу подтвержден!", "success")
    return redirect(url_for("main_bp.friend_requests"))


# routes.py
@main_bp.route("/decline_request/<int:request_id>", methods=["POST"])
@login_required
def decline_request(request_id):
    request = Friendship.query.get_or_404(request_id)

    if request.friend_id != current_user.id:
        flash("Вы не можете отклонить этот запрос", "error")
        return redirect(url_for("main_bp.friend_requests"))

    db.session.delete(request)
    db.session.commit()

    flash("Запрос на дружбу отклонен", "info")
    return redirect(url_for("main_bp.friend_requests"))


# routes.py
@main_bp.route("/cancel_request/<int:request_id>", methods=["POST"])
@login_required
def cancel_request(request_id):
    request = Friendship.query.get_or_404(request_id)

    if request.user_id != current_user.id:
        flash("Вы не можете отменить этот запрос", "error")
        return redirect(url_for("main_bp.friend_requests"))

    db.session.delete(request)
    db.session.commit()

    flash("Запрос на дружбу отменен", "info")
    return redirect(url_for("main_bp.friend_requests"))


# routes.py
@main_bp.route("/remove_friend/<int:friend_id>", methods=["POST"])
@login_required
def remove_friend(friend_id):
    # Находим дружескую связь
    friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id))
        | (
            (Friendship.user_id == friend_id)
            & (Friendship.friend_id == current_user.id)
        ),
        Friendship.status == "accepted",
    ).first()

    if not friendship:
        flash("Пользователь не найден в списке друзей", "error")
        return redirect(url_for("main_bp.friend_requests"))

    # Удаляем дружескую связь
    db.session.delete(friendship)
    db.session.commit()

    flash("Пользователь удален из друзей", "success")
    return redirect(url_for("main_bp.friend_requests"))


@main_bp.route("/messenger/contacts")
@login_required
def messenger_contacts():
    friends = current_user.get_friends()
    return render_template("messenger_contacts.html", friends=friends)


@main_bp.route("/messenger/chat/<int:user_id>")
@login_required
def messenger_chat(user_id):
    friend = User.query.get_or_404(user_id)

    messages = (
        Message.query.options(
            joinedload(Message.attachments)
        )  # <-- заранее подгружаем attachments
        .filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id))
            | (
                (Message.sender_id == user_id)
                & (Message.recipient_id == current_user.id)
            )
        )
        .order_by(Message.timestamp.asc())
        .all()
    )

    return render_template("messenger_chat.html", friend=friend, messages=messages)


@main_bp.route("/messenger/send", methods=["POST"])
@login_required
def send_message():
    try:
        # 1) Текстовые сообщения в формате JSON
        if request.content_type.startswith("application/json"):
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "Invalid JSON data"}), 400

            recipient_id = data.get("recipient_id")
            text = data.get("text", "").replace("\n", "<br>")

            if not recipient_id or not text:
                return jsonify(
                    {"success": False, "error": "Missing recipient_id or text"}
                ), 400

            recipient = db.session.get(User, recipient_id)
            if not recipient:
                return jsonify({"success": False, "error": "Recipient not found"}), 404

            message = Message(
                sender_id=current_user.id,
                recipient_id=recipient_id,
                text=text,
                is_read=False,
            )
            db.session.add(message)
            db.session.commit()

            message_data = {
                "id": message.id,
                "sender_id": message.sender_id,
                "recipient_id": message.recipient_id,
                "text": message.text,
                "attachments": [],
                "timestamp": message.timestamp.isoformat(),
                "is_read": message.is_read,
            }

            socketio.emit("new_message", message_data, room=f"user_{recipient_id}")
            socketio.emit("new_message", message_data, room=f"user_{current_user.id}")
            return jsonify({"success": True, "message": message_data})

        # 2) Form-data с текстом и/или файлами
        recipient_id = request.form.get("recipient_id", type=int)
        text = request.form.get("text", "").replace("\n", "<br>")

        if not recipient_id or (not text and "files" not in request.files):
            return jsonify(
                {"success": False, "error": "Missing recipient_id or content"}
            ), 400

        recipient = db.session.get(User, recipient_id)
        if not recipient:
            return jsonify({"success": False, "error": "Recipient not found"}), 404

        # Создаём сообщение
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            text=text or None,
            is_read=False,
        )
        db.session.add(message)
        db.session.flush()  # чтобы получить message.id для вложений

        # Обрабатываем вложения
        files = request.files.getlist("files")
        allowed_ext = {
            "png",
            "jpg", 
            "jpeg",
            "gif",
            "mp4",
            "mov",
            "pdf",
            "doc",
            "docx",
            "cpp",
            "py",
            "html",
            "js",
        }
        attachments_data = []

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        for f in files:
            if f and f.filename:
                ext = f.filename.rsplit(".", 1)[-1].lower()
                if ext not in allowed_ext:
                    continue
                filename = secure_filename(f"{message.id}_{f.filename}")
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                f.save(save_path)
                file_url = url_for(
                    "static", filename=f"uploads/{filename}", _external=True
                )
                attach = Attachment(
                    message_id=message.id, url=file_url, mime_type=f.mimetype
                )
                db.session.add(attach)
                attachments_data.append({"url": file_url, "mime_type": f.mimetype})

        db.session.commit()

        # Ответ клиенту
        message_data = {
            "id": message.id,
            "sender_id": message.sender_id,
            "recipient_id": message.recipient_id,
            "text": message.text,
            "attachments": attachments_data,
            "timestamp": message.timestamp.isoformat(),
            "is_read": message.is_read,
        }

        socketio.emit("new_message", message_data, room=f"user_{recipient_id}")
        socketio.emit("new_message", message_data, room=f"user_{current_user.id}")
        return jsonify({"success": True, "message": message_data})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": "Internal server error"}), 500


@main_bp.route("/messenger/check_new")
@login_required
def check_new_messages():
    count = Message.query.filter(
        Message.recipient_id == current_user.id, Message.is_read is False
    ).count()
    return jsonify({"count": count})


@main_bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@main_bp.route("/messenger/mark_as_read/<int:sender_id>", methods=["POST"])
@login_required
def mark_as_read(sender_id):
    # Помечаем все непрочитанные сообщения от этого пользователя как прочитанные
    Message.query.filter(
        Message.sender_id == sender_id,
        Message.recipient_id == current_user.id,
        Message.is_read is False,
    ).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})


@main_bp.route("/messenger/mark_message_read/<int:message_id>", methods=["POST"])
@login_required
def mark_message_read(message_id):
    message = Message.query.get_or_404(message_id)
    if message.recipient_id != current_user.id:
        abort(403)

    message.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@main_bp.route("/api/context-menu", methods=["GET"])
def get_context_menu():
    context_type = request.args.get("type")  # file, folder и т. д.
    menu_items = CONTEXT_MENU_ITEMS.get(context_type, [])
    return jsonify({"items": menu_items})


@main_bp.route("/api/execute-action", methods=["POST"])
def execute_action():
    try:
        data = request.get_json()
        action = data.get("action")
        element_data = data.get("element")

        if action == "delete":
            item_id = element_data.get("id")
            item = Message.query.get_or_404(item_id)
            if item.sender_id != current_user.id:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Вы можете удалять только свои сообщения",
                    }
                ), 403
            recipient_id = item.recipient_id
            db.session.delete(item)
            db.session.commit()
            return jsonify(
                {
                    "status": "success",
                    "message": f"Сообщение {item_id} удалено",
                    "recipient_id": recipient_id,
                }
            )

        elif action == "edit":
            item_id = element_data.get("id")
            new_text = element_data.get("content")
            item = Message.query.get_or_404(item_id)
            if item.sender_id != current_user.id:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Вы можете редактировать только свои сообщения",
                    }
                ), 403
            if not new_text.strip():
                return jsonify(
                    {
                        "status": "error",
                        "message": "Текст сообщения не может быть пустым",
                    }
                ), 400
            item.text = new_text.strip()
            db.session.commit()
            return jsonify(
                {
                    "status": "success",
                    "message": f"Сообщение {item_id} отредактировано",
                    "recipient_id": item.recipient_id,
                }
            )

        elif action == "clear_history":
            recipient_id = element_data.get("recipient_id")
            messages = Message.query.filter(
                or_(
                    and_(
                        Message.sender_id == current_user.id,
                        Message.recipient_id == recipient_id,
                    ),
                    and_(
                        Message.sender_id == recipient_id,
                        Message.recipient_id == current_user.id,
                    ),
                )
            ).all()

            for msg in messages:
                for attachment in msg.attachments:
                    db.session.delete(attachment)
                db.session.delete(msg)

            db.session.commit()
            return jsonify(
                {
                    "status": "success",
                    "message": "История чата очищена",
                    "recipient_id": recipient_id,
                }
            )
        elif action == "download":
            return jsonify({"status": "success", "message": "Скаченно медиа"})
        else:
            return jsonify({"status": "error", "message": "Неизвестное действие"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


def file_exists(filename):
    """Проверяет, существует ли файл в папке uploads."""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    return os.path.exists(file_path)


# Регистрируем функцию как фильтр для Jinja2
@main_bp.app_template_filter("file_exists")
def file_exists_filter(filename):
    return file_exists(filename)

@main_bp.route("/api/filetree", methods=["GET"])
@login_required
def get_filetree():
    user_folder = os.path.join(USER_FILES_PATH, str(current_user.id))
    os.makedirs(user_folder, exist_ok=True)

    def scan_directory(path):
        result = []
        for entry in os.scandir(path):
            stats = entry.stat()
            item = {
                "name": entry.name,
                "path": os.path.relpath(entry.path, user_folder).replace(os.sep, "/"),
                "type": "folder" if entry.is_dir() else "file",
                "size": stats.st_size,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            }
            if entry.is_dir():
                item["children"] = scan_directory(entry.path)
            result.append(item)
        return result

    try:
        filetree = scan_directory(user_folder)
        return jsonify({"success": True, "filetree": filetree})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route("/api/file-action", methods=["POST"])
@login_required
def file_action():
    try:
        data = request.get_json()
        action = data.get("action")
        element = data.get("element", {})
        user_folder = os.path.join(USER_FILES_PATH, str(current_user.id))
        base_path = Path(user_folder).resolve()

        if action == "create_file":
            file_path = (base_path / element.get("path", "new_file.py")).resolve()
            if str(file_path).startswith(str(base_path)):
                if file_path.exists():
                    return jsonify({"status": "error", "message": "Файл уже существует"}), 400
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.touch()
                return jsonify({"status": "success", "message": "Файл создан"})

        elif action == "create_folder":
            folder_path = (base_path / element.get("path", "new_folder")).resolve()
            if str(folder_path).startswith(str(base_path)):
                if folder_path.exists():
                    return jsonify({"status": "error", "message": "Папка уже существует"}), 400
                folder_path.mkdir(parents=True, exist_ok=True)
                return jsonify({"status": "success", "message": "Папка создана"})

        elif action == "rename":
            old_path = (base_path / element.get("old_path")).resolve()
            new_path = (base_path / element.get("new_path")).resolve()
            if not str(old_path).startswith(str(base_path)) or not str(new_path).startswith(str(base_path)):
                return jsonify({"status": "error", "message": "Недопустимый путь"}), 403
            if not old_path.exists():
                return jsonify({"status": "error", "message": "Элемент не найден"}), 404
            if new_path.exists():
                return jsonify({"status": "error", "message": "Элемент с таким именем уже существует"}), 400
            old_path.rename(new_path)
            return jsonify({"status": "success", "message": "Элемент переименован"})

        elif action == "delete":
            path = (base_path / element.get("path")).resolve()
            if not str(path).startswith(str(base_path)):
                return jsonify({"status": "error", "message": "Недопустимый путь"}), 403
            if not path.exists():
                return jsonify({"status": "error", "message": "Элемент не найден"}), 404
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return jsonify({"status": "success", "message": "Элемент удален"})

        elif action == "move":
            src_path = (base_path / element.get("src_path")).resolve()
            dest_path = (base_path / element.get("dest_path")).resolve()
            if not str(src_path).startswith(str(base_path)) or not str(dest_path).startswith(str(base_path)):
                return jsonify({"status": "error", "message": "Недопустимый путь"}), 403
            if not src_path.exists():
                return jsonify({"status": "error", "message": "Исходный элемент не найден"}), 404
            if dest_path.exists():
                return jsonify({"status": "error", "message": "Целевой элемент уже существует"}), 400
            shutil.move(str(src_path), str(dest_path))
            return jsonify({"status": "success", "message": "Элемент перемещен"})

        elif action == "copy":
            src_path = (base_path / element.get("src_path")).resolve()
            dest_path = (base_path / element.get("dest_path")).resolve()
            if not str(src_path).startswith(str(base_path)) or not str(dest_path).startswith(str(base_path)):
                return jsonify({"status": "error", "message": "Недопустимый путь"}), 403
            if not src_path.exists():
                return jsonify({"status": "error", "message": "Исходный элемент не найден"}), 404
            if dest_path.exists():
                return jsonify({"status": "error", "message": "Целевой элемент уже существует"}), 400
            if src_path.is_dir():
                shutil.copytree(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)
            return jsonify({"status": "success", "message": "Элемент скопирован"})

        elif action == "read_file":
            file_path = (base_path / element.get("path")).resolve()
            if not str(file_path).startswith(str(base_path)):
                return jsonify({"status": "error", "message": "Недопустимый путь"}), 403
            if not file_path.exists() or file_path.is_dir():
                return jsonify({"status": "error", "message": "Файл не найден или это папка"}), 404
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({"status": "success", "message": "Файл прочитан", "content": content})

        elif action == "write_file":
            file_path = (base_path / element.get("path")).resolve()
            content = element.get("content", "")
            if not str(file_path).startswith(str(base_path)):
                return jsonify({"status": "error", "message": "Недопустимый путь"}), 403
            if not file_path.exists() or file_path.is_dir():
                return jsonify({"status": "error", "message": "Файл не найден или это папка"}), 404
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return jsonify({"status": "success", "message": "Файл обновлён"})

        elif action == "download_file":
            file_path = (base_path / element.get("path")).resolve()
            if not str(file_path).startswith(str(base_path)):
                return jsonify({"status": "error", "message": "Недопустимый путь"}), 403
            if not file_path.exists() or file_path.is_dir():
                return jsonify({"status": "error", "message": "Файл не найден или это папка"}), 404
            return send_file(file_path, as_attachment=True)

        return jsonify({"status": "error", "message": "Неизвестное действие"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

pending_inputs = {}  # Общий словарь для хранения событий ожидания ввода


def register_socketio_events(socketio):
    """
    Функция, которая регистрирует все события SocketIO.
    Вызывается из server.py, чтобы избежать циклического импорта.
    """

    @socketio.on("execute")  # Обработчик события 'execute'
    def execute_code(code):
        sid = request.sid  # Получаем идентификатор сессии клиента

        def custom_input(prompt=""):
            result = output_buffer.getvalue().strip()
            output_buffer.truncate(0)
            output_buffer.seek(0)
            if result:
                socketio.emit("console_output", result, room=sid)
            # Отправляем запрос на ввод через отдельное событие
            socketio.emit("request_input", prompt, room=sid)
            ev = eventlet.Event()
            pending_inputs[sid] = ev
            return ev.wait()

        local_env = {}  # Локальная среда для выполнения кода
        exec_globals = {
            "__builtins__": builtins.__dict__.copy(),
            "input": custom_input,
        }  # Глобальная среда с копией встроенных функций
        output_buffer = io.StringIO()  # Создаём буфер для захвата вывода
        try:
            with contextlib.redirect_stdout(
                output_buffer
            ):  # Перенаправляем стандартный вывод в буфер
                exec(code, exec_globals, local_env)  # Выполняем код в заданной среде
            result = (
                output_buffer.getvalue().strip()
            )  # Получаем вывод из буфера и убираем лишние пробелы
            if not result:  # Если вывод пустой
                result = "Код выполнен, но вывода не было."  # Указываем, что вывод отсутствует
        except Exception as e:  # Обрабатываем исключения
            result = f"Ошибка: {e}"  # Сохраняем сообщение об ошибке

        socketio.emit(
            "console_output", result, room=sid
        )  # Отправляем результат выполнения кода обратно клиенту

    @socketio.on("console_input")  # Обработчик события 'console_input'
    def handle_console_input(data):
        sid = request.sid  # Получаем идентификатор сессии клиента
        if sid in pending_inputs:  # Проверяем, есть ли ожидающий ввод для этой сессии
            pending_inputs[sid].send(
                data
            )  # Отправляем введённые данные в ожидающее событие
            del pending_inputs[sid]  # Удаляем событие из словаря
        else:  # Если нет ожидающего ввода
            socketio.emit(
                "console_output", f"\n(Ввод вне запроса: {data})\n", room=sid
            )  # Уведомляем клиента о вводе вне запроса


@socketio.on("join_user_room")
def handle_join_user_room():
    if current_user.is_authenticated:
        room = f"user_{current_user.id}"
        join_room(room)


@socketio.on("connect")
def handle_connect():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")


@socketio.on("disconnect")
def handle_disconnect():
    leave_room(f"user_{current_user.id}")
