from flask import render_template, request, jsonify
from flask_login import current_user, login_required
from app.ide import blueprint
from app import db
import sqlalchemy as sa
from app.base.models import UserProfile
import eventlet
import subprocess
import os
import io
import contextlib
from pathlib import Path
from app import USER_FILES_PATH
import venv
import sys

@blueprint.route("/ide")
@login_required
def ide():
    profile = db.first_or_404(
        sa.select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    return render_template(
        "ide.html", current_endpoint=request.endpoint, profile=profile
    )

pending_inputs = {}

def _ensure_user_folder(user_id: int) -> Path:
    """Создаёт папку пользователя, если она не существует."""
    user_folder = Path(USER_FILES_PATH) / str(user_id)
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder

def _create_venv(user_folder: Path, venv_name: str) -> dict:
    """Создаёт виртуальное окружение в папке пользователя."""
    venv_path = user_folder / venv_name
    if venv_path.exists():
        return {"status": "error", "message": "Виртуальное окружение уже существует"}
    try:
        venv.create(venv_path, with_pip=True)
        return {"status": "success", "message": f"Виртуальное окружение '{venv_name}' создано"}
    except Exception as e:
        return {"status": "error", "message": f"Ошибка создания окружения: {str(e)}"}

def _get_venv_python(venv_path: Path) -> Path:
    """Возвращает путь к исполняемому файлу Python в виртуальном окружении."""
    path = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
    if not path.exists():
        raise FileNotFoundError(f"Python interpreter not found at: {path}")
    return path

@blueprint.route("/api/venv", methods=["POST"])
@login_required
def manage_venv():
    """Обрабатывает создание и управление виртуальными окружениями."""
    data = request.get_json()
    action = data.get("action")
    venv_name = data.get("venv_name")
    user_folder = _ensure_user_folder(current_user.id)

    if action == "create":
        result = _create_venv(user_folder, venv_name)
        return jsonify(result)
    else:
        return jsonify({"status": "error", "message": "Неизвестное действие"}), 400

def register_socketio_events(socketio):
    """
    Регистрирует события SocketIO для выполнения кода и обработки ввода.
    """
    @socketio.on("execute")
    def execute_code(data):
        sid = request.sid
        file_path = data.get("file_path")
        language = data.get("language", "python")
        venv_name = data.get("venv_name")  # Опционально: имя виртуального окружения

        user_folder = _ensure_user_folder(current_user.id)
        abs_file_path = user_folder / file_path

        if not abs_file_path.exists() or abs_file_path.is_dir():
            socketio.emit("console_output", "Ошибка: файл не найден или это папка", room=sid)
            return

        output_buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_buffer):
                if language == "python":
                    try:
                        python_exec = _get_venv_python(user_folder / venv_name) if venv_name else sys.executable
                        if not os.path.exists(python_exec):
                            socketio.emit("console_output", f"Ошибка: интерпретатор Python не найден: {python_exec}", room=sid)
                            return
                        cmd = [python_exec, str(abs_file_path)]
                    except FileNotFoundError as e:
                        socketio.emit("console_output", str(e), room=sid)
                        return

                    process = subprocess.Popen(
                        cmd,
                        cwd=str(user_folder),  # Рабочая директория — папка пользователя
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8"
                    )

                    def handle_input(prompt=""):
                        result = output_buffer.getvalue().strip()
                        output_buffer.truncate(0)
                        output_buffer.seek(0)
                        if result:
                            socketio.emit("console_output", result, room=sid)
                        socketio.emit("request_input", prompt, room=sid)
                        ev = eventlet.Event()
                        pending_inputs[sid] = ev
                        return ev.wait()

                    # Поток для чтения вывода процесса
                    def stream_output():
                        while process.poll() is None:
                            line = process.stdout.readline()
                            if line:
                                socketio.emit("console_output", line.strip(), room=sid)
                            err_line = process.stderr.readline()
                            if err_line:
                                socketio.emit("console_output", f"Ошибка: {err_line.strip()}", room=sid)
                        # Читаем остатки после завершения
                        stdout, stderr = process.communicate()
                        if stdout:
                            socketio.emit("console_output", stdout.strip(), room=sid)
                        if stderr:
                            socketio.emit("console_output", f"Ошибка: {stderr.strip()}", room=sid)

                    eventlet.spawn(stream_output)
                    process.wait()

                elif language == "cpp":
                    # Компиляция C++ кода
                    output_path = abs_file_path.with_suffix("")
                    compile_cmd = ["g++", str(abs_file_path), "-o", str(output_path)]
                    compile_process = subprocess.run(
                        compile_cmd,
                        cwd=str(user_folder),
                        capture_output=True,
                        text=True
                    )
                    if compile_process.returncode != 0:
                        socketio.emit("console_output", f"Ошибка компиляции: {compile_process.stderr}", room=sid)
                        return

                    # Запуск скомпилированного файла
                    run_cmd = [str(output_path)] if sys.platform != "win32" else [f"{output_path}.exe"]
                    process = subprocess.run(
                        run_cmd,
                        cwd=str(user_folder),
                        capture_output=True,
                        text=True
                    )
                    output = process.stdout or process.stderr or "Код выполнен, но вывода не было."
                    socketio.emit("console_output", output.strip(), room=sid)

                else:
                    socketio.emit("console_output", "Ошибка: неподдерживаемый язык", room=sid)

        except Exception as e:
            socketio.emit("console_output", f"Ошибка выполнения: {str(e)}", room=sid)

    @socketio.on("console_input")
    def handle_console_input(data):
        sid = request.sid
        if sid in pending_inputs:
            pending_inputs[sid].send(data)
            del pending_inputs[sid]
        else:
            socketio.emit("console_output", f"\n(Ввод вне запроса: {data})\n", room=sid)
