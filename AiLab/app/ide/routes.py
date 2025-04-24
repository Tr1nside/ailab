from flask import render_template, request
from flask_login import current_user, login_required
from app.ide import blueprint
from app import db
import sqlalchemy as sa
from app.base.models import UserProfile
import eventlet
import builtins
import contextlib
import io


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

    @socketio.on("execute")  # Обработчик события 'execute'
    def execute_code(code):
        sid = request.sid  # Получаем идентификатор сессии клиента

        def custom_input(prompt=""):
            result = output_buffer.getvalue().strip()
            output_buffer.truncate(0)
            output_buffer.seek(0)
            if result:
                socketio.emit("console_output", result, room=sid)
            # Отправляем запрос на ввод через отдельное событие
            socketio.emit("request_input", prompt, room=sid)
            ev = eventlet.Event()
            pending_inputs[sid] = ev
            return ev.wait()

        local_env = {}  # Локальная среда для выполнения кода
        exec_globals = {
            "__builtins__": builtins.__dict__.copy(),
            "input": custom_input,
        }  # Глобальная среда с копией встроенных функций
        output_buffer = io.StringIO()  # Создаём буфер для захвата вывода
        try:
            with contextlib.redirect_stdout(
                output_buffer
            ):  # Перенаправляем стандартный вывод в буфер
                exec(code, exec_globals, local_env)  # Выполняем код в заданной среде
            result = (
                output_buffer.getvalue().strip()
            )  # Получаем вывод из буфера и убираем лишние пробелы
            if not result:  # Если вывод пустой
                result = "Код выполнен, но вывода не было."  # Указываем, что вывод отсутствует
        except Exception as e:  # Обрабатываем исключения
            result = f"Ошибка: {e}"  # Сохраняем сообщение об ошибке

        socketio.emit(
            "console_output", result, room=sid
        )  # Отправляем результат выполнения кода обратно клиенту

    @socketio.on("console_input")  # Обработчик события 'console_input'
    def handle_console_input(data):
        sid = request.sid  # Получаем идентификатор сессии клиента
        if sid in pending_inputs:  # Проверяем, есть ли ожидающий ввод для этой сессии
            pending_inputs[sid].send(
                data
            )  # Отправляем введённые данные в ожидающее событие
            del pending_inputs[sid]  # Удаляем событие из словаря
        else:  # Если нет ожидающего ввода
            socketio.emit(
                "console_output", f"\n(Ввод вне запроса: {data})\n", room=sid
            )  # Уведомляем клиента о вводе вне запроса
