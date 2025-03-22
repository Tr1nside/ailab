from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import uuid
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage (for demonstration purposes)
users = {}  # {session_id: {id, name, online, avatar}}
messages = {}  # {room_id: [{text, sender, timestamp}]}

# Random name generation
first_names = ["Alex", "Sam", "Jordan", "Casey", "Taylor", "Morgan", "Riley", "Quinn", "Avery", "Dakota"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson"]

def generate_random_name():
    return f"{random.choice(first_names)} {random.choice(last_names)}"

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    session_id = request.sid

    # Create a new user with random name
    user_id = str(uuid.uuid4())
    user_name = generate_random_name()
    user_avatar = f"https://placehold.co/44/random?text={user_name[0]}"

    users[session_id] = {
        'id': user_id,
        'name': user_name,
        'online': True,
        'avatar': user_avatar,
        'session_id': session_id
    }

    # Broadcast new user to everyone
    emit('user_list', list(users.values()), broadcast=True)

    # Send existing users to the new user
    emit('user_list', list(users.values()))

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in users:
        users[session_id]['online'] = False
        emit('user_list', list(users.values()), broadcast=True)
        # For a real application, you might want to remove users after some time

@socketio.on('send_message')
def handle_message(data):
    session_id = request.sid
    sender = users[session_id]
    recipient_id = data['recipient_id']
    message_text = data['text']

    # Create a unique room ID for this conversation (sorted to ensure consistency)
    user_ids = sorted([sender['id'], recipient_id])
    room_id = f"{user_ids[0]}_{user_ids[1]}"

    # Initialize message list for this room if it doesn't exist
    if room_id not in messages:
        messages[room_id] = []

    # Add message to the room
    message = {
        'text': message_text,
        'sender': sender['id'],
        'timestamp': datetime.now().isoformat()
    }
    messages[room_id].append(message)

    # Find recipient's session ID
    recipient_session_id = None
    for sid, user in users.items():
        if user['id'] == recipient_id:
            recipient_session_id = sid
            break

    # Send message to both sender and recipient
    emit('new_message', {
        'room_id': room_id,
        'message': message
    }, room=session_id)

    if recipient_session_id:
        emit('new_message', {
            'room_id': room_id,
            'message': message
        }, room=recipient_session_id)

@socketio.on('get_messages')
def handle_get_messages(data):
    recipient_id = data['recipient_id']
    session_id = request.sid
    sender_id = users[session_id]['id']

    # Create a unique room ID for this conversation (sorted to ensure consistency)
    user_ids = sorted([sender_id, recipient_id])
    room_id = f"{user_ids[0]}_{user_ids[1]}"

    # Return existing messages or empty list
    room_messages = messages.get(room_id, [])
    emit('message_history', {
        'room_id': room_id,
        'messages': room_messages
    })

if __name__ == '__main__':
    socketio.run(app, debug=True)