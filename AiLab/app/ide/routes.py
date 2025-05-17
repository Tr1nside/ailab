from flask import render_template, request
from flask_login import current_user, login_required
from flask_socketio import SocketIO
from pathlib import Path
import docker
import ast
import sqlalchemy as sa
import threading
import queue
import uuid
import os
from app import db, USER_FILES_PATH
from app.base.models import UserProfile
from app.ide import blueprint

# Глобальные словари для хранения состояния
pending_inputs = {}  # Очереди ввода для каждого sid
execution_context = {}  # Контекст выполнения (file_path, user_dir, container, language)

# Настройки Docker (локальный сокет)
docker_client = docker.DockerClient(base_url="unix:///var/run/docker.sock")

def count_input_calls(file_path, user_dir):
    """
    Рекурсивно подсчитывает количество вызовов input() в файле и импортируемых модулях.
    
    Args:
        file_path: Путь к файлу для анализа.
        user_dir: Директория пользователя для проверки импортов.
    
    Returns:
        Количество вызовов input().
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        tree = ast.parse(code, filename=str(file_path))
        input_count = 0
        
        # Подсчёт вызовов input()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'input':
                input_count += 1
        
        # Проверка импортов
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    module_path = user_dir / f"{module_name}.py"
                    if module_path.exists() and str(module_path).startswith(str(user_dir)):
                        input_count += count_input_calls(module_path, user_dir)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module
                if module_name:
                    module_path = user_dir / f"{module_name}.py"
                    if module_path.exists() and str(module_path).startswith(str(user_dir)):
                        input_count += count_input_calls(module_path, user_dir)
        
        return input_count
    except Exception as e:
        print(f"Ошибка анализа файла {file_path}: {str(e)}")
        return 0

def stream_container_output(container, sid, socketio, input_queue, language):
    """
    Потоковая передача вывода контейнера и обработка интерактивного ввода.
    
    Args:
        container: Docker контейнер.
        sid: SocketIO session ID.
        socketio: SocketIO instance.
        input_queue: Очередь для пользовательских вводов.
        language: Язык программирования ('python' или 'cpp').
    """
    try:
        for line in container.logs(stream=True, stdout=True, stderr=True):
            line = line.decode('utf-8').strip()
            if line:
                socketio.emit("console_output", line, room=sid)
                # Проверяем, ожидает ли программа ввод
                if "input" in line.lower() or line.endswith(":") or "cin" in line.lower():
                    socketio.emit("request_input", "Введите данные: ", room=sid)
            # Передаем ввод из очереди
            try:
                input_data = input_queue.get_nowait()
                container.exec_run(f"echo '{input_data}' > /proc/1/fd/0", detach=True)
            except queue.Empty:
                pass
    except Exception as e:
        socketio.emit("console_output", f"Ошибка: {str(e)}", room=sid)
    finally:
        socketio.emit("console_output", "Выполнение завершено", room=sid)
        container.remove(force=True)
        if sid in pending_inputs:
            del pending_inputs[sid]
        if sid in execution_context:
            temp_dir = execution_context[sid].get('temp_dir')
            if temp_dir and os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
            del execution_context[sid]

def register_socketio_events(socketio: SocketIO):
    """
    Регистрирует события SocketIO для выполнения пользовательских файлов через Docker.
    """
    @socketio.on("execute")
    def execute_file(data):
        """
        Обрабатывает событие 'execute'. Запускает файл пользователя через Docker.
        
        Args:
            data: Массив [userId, filePath, language], где userId — ID пользователя, 
                  filePath — путь к файлу, language — 'python' или 'cpp'.
        """
        sid = request.sid
        
        if not isinstance(data, list) or len(data) != 3:
            socketio.emit("console_output", "Ошибка: неверный формат данных", room=sid)
            return
        
        user_id, file_path, language = data
        if language not in ['python', 'cpp']:
            socketio.emit("console_output", "Ошибка: неподдерживаемый язык", room=sid)
            return
        
        user_dir = Path(USER_FILES_PATH) / user_id
        full_path = user_dir / file_path
        
        if not full_path.exists() or not str(full_path).startswith(str(user_dir)):
            socketio.emit("console_output", "Ошибка: файл не найден или доступ запрещён", room=sid)
            return
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            socketio.emit("console_output", f"Ошибка чтения файла: {str(e)}", room=sid)
            return
        
        # Подсчитываем вызовы input() для Python
        input_count = count_input_calls(full_path, user_dir) if language == 'python' else 0
        
        # Создаем временную директорию
        temp_dir = f"/tmp/{uuid.uuid4()}"
        os.makedirs(temp_dir)
        temp_file = f"{temp_dir}/main.py" if language == 'python' else f"{temp_dir}/main.cpp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # Собираем дополнительные файлы (импорты для Python)
        additional_files = []
        if language == 'python':
            for node in ast.walk(ast.parse(code)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        module_path = user_dir / f"{module_name}.py"
                        if module_path.exists() and str(module_path).startswith(str(user_dir)):
                            with open(module_path, 'r', encoding='utf-8') as f:
                                additional_files.append((f"{temp_dir}/{module_name}.py", f.read()))
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module
                    if module_name:
                        module_path = user_dir / f"{module_name}.py"
                        if module_path.exists() and str(module_path).startswith(str(user_dir)):
                            with open(module_path, 'r', encoding='utf-8') as f:
                                additional_files.append((f"{temp_dir}/{module_name}.py", f.read()))
        
        for file_path, content in additional_files:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Инициализируем очередь для интерактивного ввода
        input_queue = queue.Queue()
        pending_inputs[sid] = input_queue
        
        # Сохраняем контекст
        execution_context[sid] = {
            'file_path': file_path,
            'user_dir': user_dir,
            'temp_dir': temp_dir,
            'language': language
        }
        
        try:
            # Запускаем контейнер
            if language == 'python':
                container = docker_client.containers.run(
                    image='python:3.10-slim',
                    command=['python', '/code/main.py'],
                    volumes={temp_dir: {'bind': '/code', 'mode': 'rw'}},
                    mem_limit='256m',
                    cpu_period=100000,
                    cpu_quota=50000,
                    detach=True,
                    tty=True,
                    stdin_open=True
                )
            else:  # cpp
                container = docker_client.containers.run(
                    image='gcc:latest',
                    command=['sh', '-c', 'g++ /code/main.cpp -o /code/main && /code/main'],
                    volumes={temp_dir: {'bind': '/code', 'mode': 'rw'}},
                    mem_limit='256m',
                    cpu_period=100000,
                    cpu_quota=50000,
                    detach=True,
                    tty=True,
                    stdin_open=True
                )
            
            # Запускаем поток для обработки вывода и ввода
            threading.Thread(
                target=stream_container_output,
                args=(container, sid, socketio, input_queue, language),
                daemon=True
            ).start()
        
        except docker.errors.DockerException as e:
            socketio.emit("console_output", f"Ошибка выполнения: {str(e)}", room=sid)
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
            if sid in pending_inputs:
                del pending_inputs[sid]
            if sid in execution_context:
                del execution_context[sid]

    @socketio.on("console_input")
    def handle_console_input(data):
        """
        Обрабатывает событие 'console_input'. Передает ввод в контейнер.
        
        Args:
            data: Данные, введённые пользователем.
        """
        sid = request.sid
        if sid not in pending_inputs or sid not in execution_context:
            socketio.emit("console_output", f"\n(Ввод вне запроса: {data})\n", room=sid)
            return
        
        # Добавляем ввод в очередь
        pending_inputs[sid].put(data)
        print(f"sid={sid}: Получен ввод: {data}")

@blueprint.route("/ide")
@login_required
def ide():
    profile = db.first_or_404(
        sa.select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    return render_template(
        "ide.html", current_endpoint=request.endpoint, profile=profile
    )
