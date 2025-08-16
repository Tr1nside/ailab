import os

basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(basedir, "./app/base/static/uploads")
USER_FILES_FOLDER = os.path.join(basedir, "./app/base/user_files")

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")
    UPLOAD_FOLDER = UPLOAD_FOLDER
    USER_FILES_FOLDER = USER_FILES_FOLDER
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
    SEND_FILE_MAX_AGE_DEFAULT = 0
