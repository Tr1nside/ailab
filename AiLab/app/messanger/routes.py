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
from app import db, socketio, UPLOAD_FOLDER
from app.base.models import User, Message, Attachment
from flask_login import login_required
from werkzeug.utils import secure_filename
from datetime import datetime


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
