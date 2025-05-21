from app import USER_FILES_PATH
from flask import request
from threading import Thread
import importlib.util
import eventlet
import subprocess
import io
import ast
import os
import sys
import json
import shutil

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

    def run_user_code_in_subprocess(
        user_id, file_path, preset_name, python_version, sid
    ):
        """Запускает пользовательский код в subprocess с выбранным пресетом и версией Python."""
        full_path = os.path.join(USER_FILES_PATH, user_id, file_path)
        user_dir = os.path.normpath(os.path.dirname(full_path))
        preset_path = os.path.join(
            USER_FILES_PATH, "presets", user_id, f"{preset_name}.json"
        )

        # Проверяем существование пресета и пользовательского файла
        if not os.path.exists(preset_path):
            socketio.emit(
                "console_output",
                f"Ошибка: Пресет '{preset_name}' не существует по пути {preset_path}",
                room=sid,
            )
            return
        if not os.path.exists(full_path):
            socketio.emit(
                "console_output", f"Ошибка: Файл {full_path} не существует", room=sid
            )
            return

        # Читаем пресет
        try:
            with open(preset_path, "r", encoding="utf-8") as f:
                preset_data = json.load(f)
            allowed_libraries = set(preset_data.get("libraries", []))
            preset_python_version = preset_data.get("python_version", "3.12")
            if preset_python_version != python_version:
                socketio.emit(
                    "console_output",
                    f"Ошибка: Пресет '{preset_name}' привязан к Python {preset_python_version}, но выбрана версия {python_version}",
                    room=sid,
                )
                return
        except Exception as e:
            socketio.emit("console_output", f"Ошибка чтения пресета: {e}", room=sid)
            return

        # Читаем код
        try:
            with open(full_path, "r", encoding="utf-8") as file:
                code = file.read()
        except Exception as e:
            socketio.emit("console_output", f"Ошибка чтения файла: {e}", room=sid)
            return

        # Анализируем импорты с помощью ast
        try:
            tree = ast.parse(code)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except Exception as e:
            socketio.emit("console_output", f"Ошибка анализа кода: {e}", room=sid)
            return

        # Проверяем, что используются только разрешенные библиотеки
        invalid_imports = [
            imp
            for imp in imports
            if imp not in allowed_libraries and find_local_module(imp, user_dir) is None
        ]
        if invalid_imports:
            socketio.emit(
                "console_output",
                f"Ошибка: Используются недопустимые библиотеки: {', '.join(invalid_imports)}",
                room=sid,
            )
            return

        # Проверяем доступность интерпретатора Python
        version_map = {"3.6": "python36", "3.9": "python39", "3.12": "python3"}
        python_executable = shutil.which(version_map.get(python_version, "python3"))
        if not python_executable:
            socketio.emit(
                "console_output",
                f"Ошибка: Интерпретатор Python {python_version} ({version_map.get(python_version)}) не найден",
                room=sid,
            )
            return

        # Подготавливаем словарь с информацией о локальных модулях
        local_modules = {}
        for module_name in imports:
            module_path = find_local_module(module_name, user_dir)
            if module_path:
                local_modules[module_name] = module_path

        # Экранируем путь для Windows
        escaped_user_dir = repr(user_dir)[1:-1].replace("\\", "\\\\")

        # Создаем временный файл для выполнения в subprocess
        wrapper_code = """
import sys
import json
import builtins

# Устанавливаем кодировку ввода-вывода
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

# Перенаправляем ввод/вывод
def custom_input(prompt=""):
    print(json.dumps({{"type": "input_request", "prompt": prompt}}))
    sys.stdout.flush()
    line = sys.stdin.readline().strip()
    data = json.loads(line)
    if data["type"] == "input_response":
        return data["value"]
    return ""

# Заменяем встроенный input
builtins.input = custom_input

# Устанавливаем путь для локальных модулей
sys.path.insert(0, "{}")

# Пользовательский код
{}
"""
        temp_file_path = os.path.join(user_dir, f"temp_{sid}.py")
        try:
            wrapper_code = wrapper_code.format(escaped_user_dir, code)
            with open(temp_file_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(wrapper_code)
        except Exception as e:
            socketio.emit(
                "console_output", f"Ошибка создания временного файла: {e}", room=sid
            )
            return

        # Запускаем subprocess
        try:
            process = subprocess.Popen(
                [python_executable, temp_file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

            def handle_process():
                output_buffer = io.StringIO()
                while True:
                    try:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        if line:
                            line = line.rstrip("\n").replace("\ufeff", "")
                            try:
                                data = json.loads(line)
                                if (
                                    isinstance(data, dict)
                                    and data.get("type") == "input_request"
                                ):
                                    socketio.emit(
                                        "request_input", data["prompt"], room=sid
                                    )
                                    ev = eventlet.Event()
                                    pending_inputs[sid] = ev
                                    user_input = ev.wait()
                                    process.stdin.write(
                                        json.dumps(
                                            {
                                                "type": "input_response",
                                                "value": user_input,
                                            }
                                        )
                                        + "\n"
                                    )
                                    process.stdin.flush()
                                else:
                                    output_buffer.write(str(data) + "\n")
                            except json.JSONDecodeError:
                                output_buffer.write(line + "\n")
                    except Exception as e:
                        output_buffer.write(f"Ошибка обработки вывода: {e}\n")

                # Собираем ошибки, если есть
                stderr_output = process.stderr.read()
                if stderr_output:
                    output_buffer.write(stderr_output)

                result = output_buffer.getvalue().rstrip()
                if not result:
                    result = "Код выполнен, но вывода не было."
                socketio.emit("console_output", result, room=sid)
                output_buffer.close()

                # Удаляем временный файл
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except Exception as e:
                        socketio.emit(
                            "console_output",
                            f"Ошибка удаления временного файла: {e}",
                            room=sid,
                        )

            Thread(target=handle_process).start()

        except Exception as e:
            socketio.emit("console_output", f"Ошибка запуска процесса: {e}", room=sid)
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    socketio.emit(
                        "console_output",
                        f"Ошибка удаления временного файла: {e}",
                        room=sid,
                    )

    @socketio.on("execute")
    def execute_code(data):
        user_id, file_path, preset_name, python_version = data
        sid = request.sid
        run_user_code_in_subprocess(
            user_id, file_path, preset_name, python_version, sid
        )

    @socketio.on("console_input")
    def handle_console_input(data):
        sid = request.sid
        if sid in pending_inputs:
            pending_inputs[sid].send(data)
            del pending_inputs[sid]
        else:
            socketio.emit("console_output", f"\n(Ввод вне запроса: {data})\n", room=sid)
