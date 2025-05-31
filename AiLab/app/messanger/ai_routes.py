from app.messanger import blueprint
from flask import (
    render_template,
    request,
    url_for,
    jsonify,
)  # Импортируем необходимые модули из Flask
import os
from flask_login import current_user
from sqlalchemy.orm import joinedload
from app import db, socketio
from app.base.config import UPLOAD_FOLDER, USER_FILES_PATH
from app.base.models import Message, Attachment, AIChat
from flask_login import login_required
from werkzeug.utils import secure_filename
from app.AI import AI_BOT_V3


bot = AI_BOT_V3()


@blueprint.route("/messenger/ai/contacts")
@login_required
def messenger_ai_contacts():
    chats = AIChat.query.filter_by(user_id=current_user.id).all()
    return render_template("messenger_ai_contacts.html", chats=chats)


@blueprint.route("/messenger/ai/chat/<int:ai_chat_id>")
@login_required
def messenger_ai_chat(ai_chat_id):
    messages = (
        Message.query.options(joinedload(Message.attachments))
        .filter(Message.ai_chat_id == ai_chat_id)  # <-- фильтр по значению переменной
        .order_by(Message.timestamp.asc())
        .all()
    )
    ai_chat = db.session.get(AIChat, ai_chat_id)

    return render_template("messenger_ai_chat.html", chat=ai_chat, messages=messages)


@blueprint.route("/messenger/ai/send", methods=["POST"])
@login_required
def send_ai_message():
    try:
        # 1) Текстовые сообщения в формате JSON
        if request.content_type.startswith("application/json"):
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "Invalid JSON data"}), 400

            ai_chat_id = data.get("ai_chat_id")
            text = data.get("text", "").replace("\n", "<br>")

            if not ai_chat_id or not text:
                return jsonify(
                    {"success": False, "error": "Missing ai_chat_id or text"}
                ), 400

            ai_chat = db.session.get(AIChat, ai_chat_id)
            if not ai_chat or ai_chat.user_id != current_user.id:
                return jsonify({"success": False, "error": "AI chat not found"}), 404

            # Создаём сообщение пользователя
            message = Message(
                sender_id=current_user.id,
                ai_chat_id=ai_chat_id,
                text=text,
                is_read=True,  # Сообщения в чате с ИИ считаются прочитанными
            )
            db.session.add(message)
            db.session.commit()

            # Заглушка: создаём ответное сообщение "Сообщение прочитано"
            ai_response = _ai_response(text, ai_chat_id)
            ai_message = Message(
                ai_chat_id=ai_chat_id,
                text=ai_response.replace("\n", "<br>"),
                is_read=True,
            )
            db.session.add(ai_message)
            db.session.commit()

            # Формируем данные сообщения пользователя
            message_data = {
                "id": message.id,
                "sender_id": message.sender_id,
                "ai_chat_id": message.ai_chat_id,
                "text": message.text,
                "attachments": [],
                "timestamp": message.timestamp.isoformat(),
                "is_read": message.is_read,
            }

            # Отправляем сообщение пользователя через Socket.IO
            socketio.emit("new_message", message_data, room=f"user_{current_user.id}")

            # Отправляем ответное сообщение "Сообщение прочитано"
            ai_message_data = {
                "id": ai_message.id,
                "sender_id": None,
                "ai_chat_id": ai_message.ai_chat_id,
                "text": ai_message.text,
                "attachments": [],
                "timestamp": ai_message.timestamp.isoformat(),
                "is_read": ai_message.is_read,
            }
            socketio.emit(
                "new_message", ai_message_data, room=f"user_{current_user.id}"
            )

            return jsonify({"success": True, "message": message_data})

        # 2) Form-data с текстом и/или файлами
        ai_chat_id = request.form.get("ai_chat_id", type=int)
        text = request.form.get("text", "").replace("\n", "<br>")

        if not ai_chat_id or (not text and "files" not in request.files):
            return jsonify(
                {"success": False, "error": "Missing ai_chat_id or content"}
            ), 400

        ai_chat = db.session.get(AIChat, ai_chat_id)
        if not ai_chat or ai_chat.user_id != current_user.id:
            return jsonify({"success": False, "error": "AI chat not found"}), 404

        # Создаём сообщение пользователя
        message = Message(
            sender_id=current_user.id,
            ai_chat_id=ai_chat_id,
            text=text or None,
            is_read=True,
        )
        db.session.add(message)
        db.session.flush()  # Чтобы получить message.id для вложений

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

        # Заглушка: создаём ответное сообщение "Сообщение прочитано", если есть текст
        if text:
            ai_response = _ai_response(text, ai_chat_id)
            ai_message = Message(
                ai_chat_id=ai_chat_id,
                text=ai_response.replace("\n", "<br>"),
                is_read=True,
            )
            db.session.add(ai_message)
            db.session.commit()

        # Формируем данные сообщения пользователя
        message_data = {
            "id": message.id,
            "sender_id": message.sender_id,
            "ai_chat_id": message.ai_chat_id,
            "text": message.text,
            "attachments": attachments_data,
            "timestamp": message.timestamp.isoformat(),
            "is_read": message.is_read,
        }

        # Отправляем сообщение пользователя через Socket.IO
        socketio.emit("new_message", message_data, room=f"user_{current_user.id}")

        # Если есть текст и ответ "Сообщение прочитано", отправляем его
        if text:
            ai_message_data = {
                "id": ai_message.id,
                "sender_id": None,
                "ai_chat_id": ai_message.ai_chat_id,
                "text": ai_message.text,
                "attachments": [],
                "timestamp": ai_message.timestamp.isoformat(),
                "is_read": ai_message.is_read,
            }
            socketio.emit(
                "new_message", ai_message_data, room=f"user_{current_user.id}"
            )

        return jsonify({"success": True, "message": message_data})

    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Internal server error"}), 500


@blueprint.route("/messenger/ai/mark_as_read/<int:ai_chat_id>", methods=["POST"])
@login_required
def ai_mark_as_read(ai_chat_id):
    # Помечаем все непрочитанные сообщения от этого пользователя как прочитанные
    Message.query.filter(
        Message.ai_chat_id == ai_chat_id,
        Message.is_read is False,
    ).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})


@blueprint.route("/messenger/ai/mark_message_read/<int:message_id>", methods=["POST"])
@login_required
def ai_mark_message_read(message_id):
    message = Message.query.get_or_404(message_id)

    message.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@blueprint.route("/messenger/ai/create_chat", methods=["POST"])
@login_required
def create_ai_chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Invalid JSON data"}), 400

        chat_name = data.get("name")
        if (
            not chat_name
            or not isinstance(chat_name, str)
            or len(chat_name.strip()) == 0
        ):
            return jsonify({"success": False, "error": "Chat name is required"}), 400

        # Создаём новый чат ИИ
        ai_chat = AIChat(
            user_id=current_user.id,
            name=chat_name.strip(),  # Значение по умолчанию
        )
        ai_chat.context = get_started_context(ai_chat.id)
        db.session.add(ai_chat)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "ai_chat": {
                    "id": ai_chat.id,
                    "name": ai_chat.name,
                    "created_at": ai_chat.created_at.isoformat(),
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


def _ai_response(text, ai_chat_id):
    try:
        # Получаем чат ИИ
        ai_chat = AIChat.query.filter_by(
            id=ai_chat_id, user_id=current_user.id
        ).first_or_404()

        context_path = ai_chat.context

        ai_response = bot.ask(prompt=text, context_path=context_path, file_context=[])

        # updated_context = f"{current_context}\n\n[{text}"
        # for_ai_context = f"{current_context}\n\n{text}"
        # ai_response = f"Контекст:\n {for_ai_context}"
        # updated_context = f"{updated_context}\n\nИИ:{ai_response} ]"

        return ai_response
    except Exception as e:
        print(str(e))


def get_started_context(ai_chat_id):
    return os.path.join(
        USER_FILES_PATH, "context", f"{current_user.id}-{ai_chat_id}.json"
    )
