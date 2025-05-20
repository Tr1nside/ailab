from flask import render_template, request
from flask_login import current_user, login_required
from app.ide import blueprint
from app import db, USER_FILES_PATH
import sqlalchemy as sa
from app.base.models import UserProfile
import importlib.util
import eventlet
import builtins
import contextlib
import io
import ast
import os
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

def register_socketio_events(socketio):
    """
    Функция, которая регистрирует все события SocketIO.
    Вызывается из server.py, чтобы избежать циклического импорта.
    """

    def find_local_module(module_name, user_path):
        """Ищет файл модуля в папке пользователя и подпапках."""
        for root, _, files in os.walk(user_path):
            if f"{module_name}.py" in files:
                return os.path.join(root, f"{module_name}.py")
        return None

    def load_local_module(module_name, file_path):
        """Загружает локальный модуль через importlib."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @socketio.on("execute")
    def execute_code(data):
        userId, filePath = data
        fullPath = f"{USER_FILES_PATH}/{userId}/{filePath}"
        user_dir = os.path.dirname(fullPath)

        # Читаем код
        with open(fullPath, 'r', encoding='utf-8') as file:
            code = file.read()

        # Анализируем импорты с помощью ast
        tree = ast.parse(code)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:  # Проверяем только импорты модулей
                    imports.append(node.module)

        # Подготавливаем среду
        sid = request.sid
        output_buffer = io.StringIO()
        exec_globals = {
            "__builtins__": builtins.__dict__.copy(),
            "input": lambda prompt="": custom_input(prompt, output_buffer, socketio, sid),
        }
        local_env = {}

        # Обрабатываем локальные импорты
        for module_name in imports:
            module_path = find_local_module(module_name, user_dir)
            if module_path:
                # Загружаем локальный модуль
                module = load_local_module(module_name, module_path)
                if module:
                    exec_globals[module_name] = module
                else:
                    output_buffer.write(f"Ошибка: Не удалось загрузить модуль {module_name}\n")
            # Если модуль не локальный, он будет обработан стандартным импортом в exec

        # Выполняем код
        try:
            with contextlib.redirect_stdout(output_buffer):
                exec(code, exec_globals, local_env)
            result = output_buffer.getvalue().strip()
            if not result:
                result = "Код выполнен, но вывода не было."
        except Exception as e:
            result = f"Ошибка: {e}"

        socketio.emit("console_output", result, room=sid)

    def custom_input(prompt, output_buffer, socketio, sid):
        result = output_buffer.getvalue().strip()
        output_buffer.truncate(0)
        output_buffer.seek(0)
        if result:
            socketio.emit("console_output", result, room=sid)
        socketio.emit("request_input", prompt, room=sid)
        ev = eventlet.Event()
        pending_inputs[sid] = ev
        return ev.wait()

    @socketio.on("console_input")
    def handle_console_input(data):
        sid = request.sid
        if sid in pending_inputs:
            pending_inputs[sid].send(data)
            del pending_inputs[sid]
        else:
            socketio.emit("console_output", f"\n(Ввод вне запроса: {data})\n", room=sid)
