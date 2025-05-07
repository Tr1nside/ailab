from flask import render_template, request
from flask_login import current_user, login_required
from app.ide import blueprint
from app import db
import sqlalchemy as sa
from app.base.models import UserProfile
import eventlet
from flask_socketio import SocketIO
from pathlib import Path
import subprocess

@blueprint.route("/ide")
@login_required
def ide():
    profile = db.first_or_404(
        sa.select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    return render_template(
        "ide.html", current_endpoint=request.endpoint, profile=profile
    )


# Глобальный словарь для хранения ожидающих событий ввода
pending_inputs = {}

# Базовый путь к папкам пользователей
USERS_DIR = "Q:/Code/00 - Projects/ailab/AiLab/app/base/user_files/"


def register_socketio_events(socketio: SocketIO):
    """
    Регистрирует события SocketIO для выполнения пользовательских файлов через subprocess.
    Вызывается из server.py, чтобы избежать циклического импорта.
    """

    @socketio.on("execute")
    def execute_file(data):
        """
        Обрабатывает событие 'execute'. Запускает файл пользователя через subprocess.
        
        Args:
            data: Массив [userId, filePath], где userId — ID пользователя, filePath — путь к файлу.
        """
        sid = request.sid  # Идентификатор сессии клиента
        
        # Проверяем формат данных
        if not isinstance(data, list) or len(data) != 2:
            socketio.emit("console_output", "Ошибка: неверный формат данных", room=sid)
            return
        
        user_id, file_path = data
        
        # Формируем путь к файлу
        user_dir = Path(USERS_DIR) / user_id
        full_path = user_dir / file_path
        
        # Проверяем, что файл существует и находится в папке пользователя
        if not full_path.exists() or not str(full_path).startswith(str(user_dir)):
            socketio.emit("console_output", "Ошибка: файл не найден или доступ запрещён", room=sid)
            return
        
        try:
            # Запускаем процесс с поддержкой интерактивного ввода
            process = subprocess.Popen(
                ["python", str(full_path)],
                cwd=str(user_dir),  # Рабочая директория — папка пользователя
                stdout=subprocess.PIPE,  # Перехватываем stdout
                stderr=subprocess.PIPE,  # Перехватываем stderr
                stdin=subprocess.PIPE,  # Открываем stdin для ввода
                text=True,  # Вывод как строки
                bufsize=1,  # Построчная буферизация
                universal_newlines=True
            )
            
            # Запускаем асинхронный процесс для чтения вывода
            def handle_output():
                while True:
                    stdout_line = process.stdout.readline().strip()
                    stderr_line = process.stderr.readline().strip()
                    if stdout_line:
                        socketio.emit("console_output", stdout_line, room=sid)
                    if stderr_line:
                        socketio.emit("console_output", f"Ошибка: {stderr_line}", room=sid)
                    if process.poll() is not None:  # Процесс завершился
                        break
                # Читаем остатки вывода
                stdout, stderr = process.communicate()
                if stdout.strip():
                    socketio.emit("console_output", stdout.strip(), room=sid)
                if stderr.strip():
                    socketio.emit("console_output", f"Ошибка: {stderr.strip()}", room=sid)
            
            # Запускаем поток для обработки вывода
            eventlet.spawn(handle_output)
            
            # Обрабатываем интерактивный ввод
            def handle_input(prompt=""):
                socketio.emit("request_input", prompt, room=sid)
                ev = eventlet.Event()
                pending_inputs[sid] = ev
                user_input = ev.wait()
                process.stdin.write(user_input + "\n")  # Отправляем ввод в stdin
                process.stdin.flush()  # Принудительно отправляем
                return user_input
            
            # Ждём завершения процесса или таймаута
            try:
                process.wait(timeout=2)  # Максимум 10 секунд
                socketio.emit("console_output", "Выполнение завершено", room=sid)
            except subprocess.TimeoutExpired:
                process.terminate()  # Завершаем процесс
                socketio.emit("console_output", "Ошибка: превышено время выполнения", room=sid)
            
        except subprocess.SubprocessError as e:
            socketio.emit("console_output", f"Ошибка выполнения: {str(e)}", room=sid)
        finally:
            # Убедимся, что процесс завершён
            if process.poll() is None:
                process.terminate()
            # Удаляем ожидающий ввод, если он есть
            if sid in pending_inputs:
                del pending_inputs[sid]
    
    @socketio.on("console_input")
    def handle_console_input(data):
        """
        Обрабатывает событие 'console_input'. Передаёт пользовательский ввод в процесс.
        
        Args:
            data: Данные, введённые пользователем.
        """
        sid = request.sid
        if sid in pending_inputs:
            pending_inputs[sid].send(data)  # Отправляем ввод в ожидающее событие
            del pending_inputs[sid]
        else:
            socketio.emit("console_output", f"\n(Ввод вне запроса: {data})\n", room=sid)
