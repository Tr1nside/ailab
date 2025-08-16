from flask import render_template, send_from_directory
from flask_login import current_user
from flask_socketio import join_room, leave_room
from app.base import blueprint
from app import socketio
from pathlib import Path
from app.base.config import USER_FILES_PATH
from urllib.parse import unquote
import os

@blueprint.route("/")
@blueprint.route("/index")
def index():
    return render_template("index.html")



@blueprint.route('/user_files/<user_id>/<path:filename>')
def get_user_file(user_id, filename):
    parse_filename = unquote(filename)
    path = os.path.join(USER_FILES_PATH, user_id)
    return send_from_directory(path, parse_filename)



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
