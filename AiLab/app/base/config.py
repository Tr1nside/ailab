import os
from icecream import ic

basedir = os.path.abspath(os.path.dirname(__file__))

USER_FILES_PATH = os.path.join(basedir, "user_files")
UPLOAD_FOLDER = os.path.join(basedir, "static/uploads")
QR_FOLDER = os.path.join(basedir, "static/qrcodes")

ic(USER_FILES_PATH, UPLOAD_FOLDER)
