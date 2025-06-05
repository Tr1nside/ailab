from flask import render_template
from flask_login import current_user
from flask_socketio import join_room, leave_room
from app.base import blueprint
from app import socketio
from pathlib import Path


@blueprint.route("/")
@blueprint.route("/index")
def index():
    return render_template("index.html")

@blueprint.route("/get_user_files_path")
def get_user_files_path():
    try:
        current_dir = Path(__file__).resolve().parent
        user_files_path = current_dir / "user_files" / str(current_user.id)
        
        # Создаем директорию, если ее нет
        user_files_path.mkdir(exist_ok=True, parents=True)
        
        # Явно преобразуем WindowsPath в строку перед возвратом
        return str(user_files_path)  # Или используйте jsonify({"path": str(user_files_path)})
    except Exception as e:
        print(f"ERROR ERROR ERROR ERROR ERROR ERROR ERROR ERROR \n{e}")
        return ""


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
