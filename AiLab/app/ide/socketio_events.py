from app.base.config import USER_FILES_PATH
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
from icecream import ic

pending_inputs = {}
active_processes = {}  # Словарь для хранения активных процессов по sid

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
            
            allowed_libraries.add('cv2')
            allowed_libraries.add('matplotlib.pyplot')
            allowed_libraries.add('matplotlib.image')
            allowed_libraries.add('tensorflow.keras.layers')
            allowed_libraries.add('tensorflow.keras.datasets')
            
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
        version_map = {"3.6": "python36", "3.9": "python39", "3.12": "python312"}
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

# Устанавливаем текущую рабочую директорию
os.chdir("{}")

# Перенаправляем ввод/вывод
def custom_input(prompt=""):
    print(json.dumps({{"type": "input_request", "prompt": prompt}}))
    sys.stdout.flush()
    line = sys.stdin.readline().strip()
    try:
        data = json.loads(line)
        if data["type"] == "input_response":
            return data["value"]
        return ""
    except json.JSONDecodeError:
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
            wrapper_code = wrapper_code.format(escaped_user_dir, escaped_user_dir, code)
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
                bufsize=1,  # Построчная буферизация
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

            # Сохраняем процесс в active_processes
            active_processes[sid] = (process, temp_file_path)

            def handle_process():
                output_buffer = []
                BATCH_SIZE = 50  # Количество строк в одном пакете
                BATCH_INTERVAL = 0.1  # Интервал между отправками пакетов (в секундах)

                def send_buffer():
                    if output_buffer:
                        socketio.emit("console_output", "\n".join(output_buffer), room=sid)
                        output_buffer.clear()
                        eventlet.sleep(BATCH_INTERVAL)  # Задержка для обработки клиентом

                while True:
                    try:
                        # Читаем вывод построчно
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
                                    # Отправляем запрос ввода клиенту
                                    send_buffer()  # Отправляем накопленный буфер перед запросом ввода
                                    socketio.emit(
                                        "request_input", data["prompt"], room=sid
                                    )
                                    ev = eventlet.Event()
                                    pending_inputs[sid] = ev
                                    user_input = ev.wait()
                                    # Отправляем ввод в процесс
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
                                    # Добавляем в буфер
                                    output_buffer.append(str(data))
                                    if len(output_buffer) >= BATCH_SIZE:
                                        send_buffer()
                            except json.JSONDecodeError:
                                # Обычный вывод, не JSON
                                output_buffer.append(line)
                                if len(output_buffer) >= BATCH_SIZE:
                                    send_buffer()
                    except Exception as e:
                        output_buffer.append(f"Ошибка обработки вывода: {e}")
                        send_buffer()
                        break

                # Отправляем оставшийся буфер
                send_buffer()

                # Собираем ошибки, если есть
                stderr_output = process.stderr.read()
                if stderr_output:
                    socketio.emit("console_output", stderr_output, room=sid)

                # Очищаем процесс и временный файл
                if sid in active_processes:
                    del active_processes[sid]
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except Exception as e:
                        socketio.emit(
                            "console_output",
                            f"Ошибка удаления временного файла: {e}",
                            room=sid,
                        )

            # Запускаем обработку в отдельном потоке
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

    @socketio.on("stop_execution")
    def stop_execution():
        sid = request.sid
        if sid in active_processes:
            process, temp_file_path = active_processes[sid]
            try:
                # Завершаем процесс
                process.terminate()
                process.wait(timeout=1)  # Даём процессу 1 секунду на завершение
            except subprocess.TimeoutExpired:
                # Если процесс не завершился, убиваем его
                process.kill()
            except Exception as e:
                socketio.emit("console_output", f"Ошибка при остановке процесса: {e}", room=sid)

            # Очищаем ресурсы
            del active_processes[sid]
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    socketio.emit(
                        "console_output",
                        f"Ошибка удаления временного файла: {e}",
                        room=sid,
                    )
            socketio.emit("console_output", "", room=sid)
        else:
            socketio.emit("console_output", "", room=sid)
