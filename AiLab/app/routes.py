from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify,
    abort,
)  # Импортируем необходимые модули из Flask
from urllib.parse import urlsplit
import eventlet  # Импортируем eventlet для работы с асинхронными событиями
import builtins  # Импортируем встроенные функции Python
import contextlib  # Импортируем contextlib для управления контекстами
import io  # Импортируем io для работы с потоками ввода-вывода
from .forms import LoginForm, RegistrationForm, ProfileEditForm
from flask_login import current_user, login_user
from flask_login import logout_user
import sqlalchemy as sa
from .extensions import db
from .models import User, UserProfile, Friendship, Message
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
from .funcs import generate_qr_code
from datetime import datetime
from .extensions import socketio
from flask_socketio import join_room, leave_room, emit


main_bp = Blueprint("main_bp", __name__)  # Создаём Blueprint для организации маршрутов
appdir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(appdir, '../static/uploads')

@main_bp.route(
    "/"
)  # Определяем маршрут для главной страницы, доступной по адресу http://127.0.0.1:5000/
@main_bp.route("/index")
def index():
    return render_template("index.html")  # Возвращаем HTML-шаблон index.html

@main_bp.route('/profile/<int:id>', methods=['GET', 'POST'])
@login_required
def profile(id):
    profile = db.first_or_404(sa.select(UserProfile).where(UserProfile.user_id == id))
    form = ProfileEditForm()
    
    if form.validate_on_submit():
        try:
            # Обновляем текстовые поля
            profile.full_name = form.full_name.data
            profile.email = form.email.data
            profile.phone = form.phone.data
            profile.position = form.position.data
            profile.telegram_link = form.telegram_link.data
            profile.github_link = form.github_link.data
            profile.vk_link = form.vk_link.data

            # Обрабатываем файл
            if form.profile_media.data:
                file = form.profile_media.data
                filename = secure_filename(f"{id}_{file.filename}")
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                profile.profile_photo = filename

            db.session.commit()
            flash('Данные успешно сохранены!', 'success')
            return redirect(url_for('main_bp.profile', id=id))  # Редирект с ID

        except Exception as e:
            db.session.rollback()
            print(e)

    elif request.method == 'GET':
        # Заполняем форму данными из БД
        form.full_name.data = profile.full_name
        form.email.data = profile.email
        form.phone.data = profile.phone
        form.position.data = profile.position
        form.telegram_link.data = profile.telegram_link
        form.github_link.data = profile.github_link
        form.vk_link.data = profile.vk_link

    return render_template('profile.html', profile=profile, id=id, current_endpoint=request.endpoint, form=form)

@main_bp.route("/ide")  # Определяем маршрут для главной страницы, доступной по адресу http://127.0.0.1:5000/
@login_required
def ide():
    profile = db.first_or_404(sa.select(UserProfile).where(UserProfile.user_id == current_user.id))
    return render_template("ide.html", current_endpoint=request.endpoint, profile=profile)  # Возвращаем HTML-шаблон index.html


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main_bp.ide"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password")
            return redirect(url_for("main_bp.login"))
        login_user(user)
        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = url_for("main_bp.ide")
        return redirect(next_page)
    # Если запрос GET или форма не прошла валидацию, возвращаем страницу входа
    return render_template("login.html", title="Sign In", form=form)


@main_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main_bp.login"))


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main_bp.ide"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            last_name=form.last_name.data,
            first_name=form.first_name.data,
            middle_name=form.middle_name.data,
            email=form.email.data,
        )
        full_name = " ".join(filter(None, [form.last_name.data, form.first_name.data, form.middle_name.data]))
        user.profile = UserProfile(email=form.email.data, full_name=full_name)
        user.set_password(form.password.data)
        user.profile.profile_photo = 'standart.png'

        qr_filename = generate_qr_code(user.id, user.email, False)
        user.profile.qr_photo = qr_filename

        db.session.add(user)
        db.session.commit()
        qr_filename = generate_qr_code(user.id, user.email, True)
        
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("main_bp.login"))
    return render_template("register.html", title="Register", form=form)


@main_bp.route('/add_friend', methods=['POST'])
@login_required
def add_friend():
    friend_id = request.form.get('friend_id')
    
    # Проверка: нельзя добавить себя
    if current_user.id == int(friend_id):
        flash("Нельзя добавить себя в друзья", "error")
        return redirect(url_for('main_bp.profile', id=friend_id))
    
    # Проверка существующего запроса
    existing = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if existing:
        flash("Запрос на дружбу уже существует", "info")
        return redirect(url_for('main_bp.profile', id=friend_id))
    
    # Создание нового запроса
    new_request = Friendship(
        user_id=current_user.id,
        friend_id=friend_id,
        status='pending'
    )
    db.session.add(new_request)
    db.session.commit()
    
    flash("Запрос на дружбу отправлен!", "success")
    return redirect(url_for('main_bp.profile', id=friend_id))

# routes.py
@main_bp.route('/friend_requests')
@login_required
def friend_requests():
    # Входящие запросы
    incoming = Friendship.query.filter(
        Friendship.friend_id == current_user.id,
        Friendship.status == 'pending'
    ).all()

    # Исходящие запросы
    outgoing = Friendship.query.filter(
        Friendship.user_id == current_user.id,
        Friendship.status == 'pending'
    ).all()

    # Список друзей
    friends = current_user.get_friends()
    profile = db.first_or_404(sa.select(UserProfile).where(UserProfile.user_id == current_user.id))
    return render_template('friend_requests.html', incoming=incoming, outgoing=outgoing, friends=friends, profile=profile)

# routes.py
@main_bp.route('/accept_request/<int:request_id>', methods=['POST'])
@login_required
def accept_request(request_id):
    request = Friendship.query.get_or_404(request_id)
    
    if request.friend_id != current_user.id:
        flash("Вы не можете подтвердить этот запрос", "error")
        return redirect(url_for('main_bp.friend_requests'))
    
    request.status = 'accepted'
    db.session.commit()
    
    flash("Запрос на дружбу подтвержден!", "success")
    return redirect(url_for('main_bp.friend_requests'))

# routes.py
@main_bp.route('/decline_request/<int:request_id>', methods=['POST'])
@login_required
def decline_request(request_id):
    request = Friendship.query.get_or_404(request_id)
    
    if request.friend_id != current_user.id:
        flash("Вы не можете отклонить этот запрос", "error")
        return redirect(url_for('main_bp.friend_requests'))
    
    db.session.delete(request)
    db.session.commit()
    
    flash("Запрос на дружбу отклонен", "info")
    return redirect(url_for('main_bp.friend_requests'))

# routes.py
@main_bp.route('/cancel_request/<int:request_id>', methods=['POST'])
@login_required
def cancel_request(request_id):
    request = Friendship.query.get_or_404(request_id)
    
    if request.user_id != current_user.id:
        flash("Вы не можете отменить этот запрос", "error")
        return redirect(url_for('main_bp.friend_requests'))
    
    db.session.delete(request)
    db.session.commit()
    
    flash("Запрос на дружбу отменен", "info")
    return redirect(url_for('main_bp.friend_requests'))

# routes.py
@main_bp.route('/remove_friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    # Находим дружескую связь
    friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id)),
        Friendship.status == 'accepted'
    ).first()

    if not friendship:
        flash("Пользователь не найден в списке друзей", "error")
        return redirect(url_for('main_bp.friend_requests'))

    # Удаляем дружескую связь
    db.session.delete(friendship)
    db.session.commit()

    flash("Пользователь удален из друзей", "success")
    return redirect(url_for('main_bp.friend_requests'))
@main_bp.route('/messenger/contacts')
@login_required
def messenger_contacts():
    friends = current_user.get_friends()
    return render_template('messenger_contacts.html', friends=friends)

@main_bp.route('/messenger/chat/<int:user_id>')
@login_required
def messenger_chat(user_id):
    friend = User.query.get_or_404(user_id)
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    return render_template('messenger_chat.html', friend=friend, messages=messages)

@main_bp.route('/messenger/send', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400

        recipient_id = data.get('recipient_id')
        
        text = data.get('text')
        
        text = text.replace('\n', '<br>')

        print(text)

        if not recipient_id or not text:
            return jsonify({'success': False, 'error': 'Missing recipient_id or text'}), 400

        # Проверяем существование получателя
        recipient = db.session.get(User, recipient_id)
        if not recipient:
            return jsonify({'success': False, 'error': 'Recipient not found'}), 404

        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            text=text,
            is_read=False
        )
        db.session.add(message)
        db.session.commit()

        message_data = {
            'id': message.id,
            'sender_id': message.sender_id,
            'recipient_id': message.recipient_id,
            'text': message.text,
            'timestamp': message.timestamp.isoformat(),
            'is_read': message.is_read
        }
        
        socketio.emit('new_message', message_data, room=f'user_{recipient_id}')
        socketio.emit('new_message', message_data, room=f'user_{current_user.id}')
        
        return jsonify({'success': True, 'message': message_data})

    except Exception as e:
        db.session.rollback()
        print(f"Error sending message: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@main_bp.route('/messenger/check_new')
@login_required
def check_new_messages():
    count = Message.query.filter(
        Message.recipient_id == current_user.id,
        Message.is_read is False
    ).count()
    return jsonify({'count': count})

@main_bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
@main_bp.route('/messenger/mark_as_read/<int:sender_id>', methods=['POST'])
@login_required
def mark_as_read(sender_id):
    # Помечаем все непрочитанные сообщения от этого пользователя как прочитанные
    Message.query.filter(
        Message.sender_id == sender_id,
        Message.recipient_id == current_user.id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})

@main_bp.route('/messenger/mark_message_read/<int:message_id>', methods=['POST'])
@login_required
def mark_message_read(message_id):
    message = Message.query.get_or_404(message_id)
    if message.recipient_id != current_user.id:
        abort(403)
    
    message.is_read = True
    db.session.commit()
    return jsonify({'success': True})

pending_inputs = {}  # Общий словарь для хранения событий ожидания ввода
# извините, пусть оно просто тут полежит иначе все крашится) (пусть это будет дань уважения генеративному ИИ)


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

@socketio.on('join_user_room')
def handle_join_user_room():
    if current_user.is_authenticated:
        room = f'user_{current_user.id}'
        join_room(room)

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        print(f"User {current_user.id} joined room user_{current_user.id}")

@socketio.on('disconnect')
def handle_disconnect():
    leave_room(f'user_{current_user.id}')