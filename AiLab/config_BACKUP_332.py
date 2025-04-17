import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")
    UPLOAD_FOLDER = os.path.join(basedir, "app/static/uploads")
<<<<<<< HEAD
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
=======
    
>>>>>>> 01b837417345405b7bddd7a24800897d95a1a8bf
