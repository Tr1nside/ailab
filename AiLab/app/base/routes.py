from flask import render_template
from flask_login import current_user
from flask_socketio import join_room, leave_room
from app.base import blueprint
from app import socketio


@blueprint.route("/")
@blueprint.route("/index")
def index():
    return render_template("index.html")


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
