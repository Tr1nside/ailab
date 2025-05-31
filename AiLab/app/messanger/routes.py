from app.messanger import blueprint
from flask import (
    render_template,
    request,
    url_for,
    jsonify,
    abort,
)  # Импортируем необходимые модули из Flask
import os
from flask_login import current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_
from app import db, socketio
from app.base.config import UPLOAD_FOLDER
from app.base.models import User, Message, Attachment, AIChat
from flask_login import login_required
from werkzeug.utils import secure_filename
from datetime import datetime
from app.messanger.ai_routes import get_started_context


CONTEXT_MENU_ITEMS = {
    "message": [
        {"label": "Редактировать", "action": "edit"},
        {"label": "Удалить", "action": "delete"},
    ],
    "media": [{"label": "Скачать", "action": "download"}],
    "ai_chat": [{"label": "Удалить", "action": "delete_chat"}],
}


@blueprint.route("/messenger/contacts")
@login_required
def messenger_contacts():
    friends = current_user.get_friends()
    return render_template("messenger_contacts.html", friends=friends)


@blueprint.route("/messenger/chat/<int:user_id>")
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


@blueprint.route("/messenger/send", methods=["POST"])
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

    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Internal server error"}), 500


@blueprint.route("/messenger/check_new")
@login_required
def check_new_messages():
    count = Message.query.filter(
        Message.recipient_id == current_user.id, Message.is_read is False
    ).count()
    return jsonify({"count": count})


@blueprint.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@blueprint.route("/messenger/mark_as_read/<int:sender_id>", methods=["POST"])
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


@blueprint.route("/messenger/mark_message_read/<int:message_id>", methods=["POST"])
@login_required
def mark_message_read(message_id):
    message = Message.query.get_or_404(message_id)
    if message.recipient_id != current_user.id:
        abort(403)

    message.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@blueprint.route("/api/context-menu", methods=["GET"])
def get_context_menu():
    context_type = request.args.get("type")  # file, folder и т. д.
    menu_items = CONTEXT_MENU_ITEMS.get(context_type, [])
    return jsonify({"items": menu_items})


@blueprint.route("/api/execute-action", methods=["POST"])
def execute_action():
    try:
        data = request.get_json()
        action = data.get("action")
        element_data = data.get("element")

        if action == "delete_chat":
            # Обработка удаления чата ИИ
            ai_chat_id = element_data.get("ai_chat_id")
            if not ai_chat_id:
                return jsonify(
                    {"status": "error", "message": "Не указан ai_chat_id"}
                ), 400

            ai_chat = db.session.get(AIChat, ai_chat_id)
            if not ai_chat or ai_chat.user_id != current_user.id:
                return jsonify(
                    {"status": "error", "message": "Чат с ИИ не найден"}
                ), 404

            # Удаляем все сообщения и вложения чата
            messages = Message.query.filter_by(ai_chat_id=ai_chat_id).all()
            for msg in messages:
                for attachment in msg.attachments:
                    db.session.delete(attachment)
                db.session.delete(msg)

            # Удаляем сам чат
            db.session.delete(ai_chat)
            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "message": "Чат с ИИ удален",
                    "ai_chat_id": ai_chat_id,
                }
            )

        elif action == "delete":
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
            # Обработка clear_history
            recipient_id = element_data.get("recipient_id")
            ai_chat_id = element_data.get("ai_chat_id")

            if ai_chat_id:
                # Очистка истории чата с ИИ
                ai_chat = db.session.get(AIChat, ai_chat_id)
                if not ai_chat or ai_chat.user_id != current_user.id:
                    return jsonify(
                        {"status": "error", "message": "Чат с ИИ не найден"}
                    ), 404
                ai_chat.context = get_started_context(ai_chat.id)
                messages = Message.query.filter_by(ai_chat_id=ai_chat_id).all()
                for msg in messages:
                    for attachment in msg.attachments:
                        db.session.delete(attachment)
                    db.session.delete(msg)
                db.session.commit()
                return jsonify(
                    {
                        "status": "success",
                        "message": "История чата с ИИ очищена",
                        "ai_chat_id": ai_chat_id,
                    }
                )

            elif recipient_id:
                # Очистка истории обычного чата
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

            return jsonify(
                {"status": "error", "message": "Не указан recipient_id или ai_chat_id"}
            ), 400
        elif action == "download":
            return jsonify({"status": "success", "message": "Скаченно медиа"})
        else:
            return jsonify({"status": "error", "message": "Неизвестное действие"}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
