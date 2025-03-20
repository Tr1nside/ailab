from app import create_app
from app.extensions import socketio, db
from app.models import User
import sqlalchemy as sa
import sqlalchemy.orm as so

app = create_app()

# Создание таблиц при запуске
with app.app_context():
    db.create_all()


@app.shell_context_processor
def make_shell_context():
    return {"sa": sa, "so": so, "db": db, "User": User}


if __name__ == "__main__":
    socketio.run(app, debug=True, host="127.0.0.1", port=5000)
