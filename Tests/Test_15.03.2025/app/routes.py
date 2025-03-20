from flask import Blueprint, render_template, request, flash, redirect, url_for  # Импортируем необходимые модули из Flask
from urllib.parse import urlsplit
from flask_socketio import emit  # Импортируем emit для отправки сообщений через SocketIO
import eventlet  # Импортируем eventlet для работы с асинхронными событиями
import builtins  # Импортируем встроенные функции Python
import contextlib  # Импортируем contextlib для управления контекстами
import io  # Импортируем io для работы с потоками ввода-вывода
from .forms import LoginForm, RegistrationForm
from flask_login import current_user, login_user
from flask_login import logout_user
import sqlalchemy as sa
from .extensions import db
from .models import User
from flask_login import login_required

main_bp = Blueprint('main_bp', __name__) # Создаём Blueprint для организации маршрутов


@main_bp.route('/') # Определяем маршрут для главной страницы, доступной по адресу http://127.0.0.1:5000/
@main_bp.route('/index')
def index():
    return render_template('index.html')  # Возвращаем HTML-шаблон index.html

@main_bp.route('/ide') # Определяем маршрут для главной страницы, доступной по адресу http://127.0.0.1:5000/
@login_required
def ide():
    return render_template('ide.html')  # Возвращаем HTML-шаблон index.html

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.ide'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('main_bp.login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main_bp.ide')
        return redirect(next_page)
    # Если запрос GET или форма не прошла валидацию, возвращаем страницу входа
    return render_template('login.html', title='Sign In', form=form)

@main_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main_bp.login'))

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.ide'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(last_name=form.last_name.data, first_name=form.first_name.data, middle_name=form.middle_name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('main_bp.login'))
    return render_template('register.html', title='Register', form=form)

pending_inputs = {}  # Общий словарь для хранения событий ожидания ввода
#извините, пусть оно просто тут полежит иначе все крашится) (пусть это будет дань уважения генеративному ИИ)


def register_socketio_events(socketio):
    """
    Функция, которая регистрирует все события SocketIO.
    Вызывается из server.py, чтобы избежать циклического импорта.
    """


    @socketio.on('execute')  # Обработчик события 'execute'
    def execute_code(code):
        sid = request.sid  # Получаем идентификатор сессии клиента
        def custom_input(prompt=""):
            result = output_buffer.getvalue().strip()
            output_buffer.truncate(0)
            output_buffer.seek(0)
            if result:
                socketio.emit('console_output', result, room=sid)
            # Отправляем запрос на ввод через отдельное событие
            socketio.emit("request_input", prompt, room=sid)
            ev = eventlet.Event()
            pending_inputs[sid] = ev
            return ev.wait()


        local_env = {}  # Локальная среда для выполнения кода
        exec_globals = {"__builtins__": builtins.__dict__.copy(),
                        "input": custom_input}  # Глобальная среда с копией встроенных функций
        output_buffer = io.StringIO()  # Создаём буфер для захвата вывода
        try:
            with contextlib.redirect_stdout(output_buffer):  # Перенаправляем стандартный вывод в буфер
                exec(code, exec_globals, local_env)  # Выполняем код в заданной среде
            result = output_buffer.getvalue().strip()  # Получаем вывод из буфера и убираем лишние пробелы
            if not result:  # Если вывод пустой
                result = "Код выполнен, но вывода не было."  # Указываем, что вывод отсутствует
        except Exception as e:  # Обрабатываем исключения
            result = f"Ошибка: {e}"  # Сохраняем сообщение об ошибке

        socketio.emit('console_output', result, room=sid)  # Отправляем результат выполнения кода обратно клиенту


    @socketio.on('console_input')  # Обработчик события 'console_input'
    def handle_console_input(data):
        sid = request.sid  # Получаем идентификатор сессии клиента
        if sid in pending_inputs:  # Проверяем, есть ли ожидающий ввод для этой сессии
            pending_inputs[sid].send(data)  # Отправляем введённые данные в ожидающее событие
            del pending_inputs[sid]  # Удаляем событие из словаря
        else:  # Если нет ожидающего ввода
            socketio.emit('console_output', f"\n(Ввод вне запроса: {data})\n", room=sid)  # Уведомляем клиента о вводе вне запроса
    