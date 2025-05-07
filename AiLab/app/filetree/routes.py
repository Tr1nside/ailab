from app.filetree import blueprint
from flask import (
    request,
    jsonify,
    send_file,
    Response,
)
import os
from flask_login import current_user
from app import UPLOAD_FOLDER, USER_FILES_PATH
from flask_login import login_required
from datetime import datetime
import shutil
from pathlib import Path
from typing import List, TypedDict, Union, Dict, Any, Optional
from werkzeug.wrappers import Response as WerkzeugResponse
import icecream as ic


class FileTreeItem(TypedDict):
    name: str
    path: str
    type: str
    size: int
    modified: str
    children: List["FileTreeItem"]


class FileActionElement(TypedDict, total=False):
    path: str
    old_path: str
    new_path: str
    src_path: str
    dest_path: str
    content: str


class FileActionRequest(TypedDict):
    action: str
    element: FileActionElement


# Константы для сообщений
ERROR_INVALID_PATH = "Недопустимый путь"
ERROR_EXISTS = "Элемент уже существует"
ERROR_NOT_FOUND = "Элемент не найден"
ERROR_NOT_FILE = "Файл не найден или это папка"
ERROR_UNKNOWN_ACTION = "Неизвестное действие"


def _file_exists(filename):
    """Проверяет, существует ли файл в папке uploads."""
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    return os.path.exists(file_path)


@blueprint.app_template_filter("file_exists")
def file_exists_filter(filename):
    return _file_exists(filename)


def _ensure_user_folder(user_id: int, base_path: str = USER_FILES_PATH) -> Path:
    """Создаёт папку пользователя, если она не существует."""
    user_folder = Path(base_path) / str(user_id)
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder


def _scan_directory(directory: Path, base_folder: Path) -> List[FileTreeItem]:
    """Рекурсивно сканирует директорию и возвращает список элементов."""
    result: List[FileTreeItem] = []
    try:
        for entry in directory.iterdir():
            stats = entry.stat()
            relative_path = entry.relative_to(base_folder).as_posix()
            item: FileTreeItem = {
                "name": entry.name,
                "path": relative_path,
                "type": "folder" if entry.is_dir() else "file",
                "size": stats.st_size if entry.is_file() else 0,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "children": [],
            }
            if entry.is_dir():
                item["children"] = _scan_directory(entry, base_folder)
            result.append(item)
        return sorted(result, key=lambda x: (x["type"] != "folder", x["name"].lower()))
    except PermissionError as e:
        raise PermissionError(f"Нет доступа к директории: {directory}") from e
    except OSError as e:
        raise OSError(
            f"Ошибка при сканировании директории {directory}: {str(e)}"
        ) from e


@blueprint.route("/api/filetree", methods=["GET"])
@login_required
def get_filetree() -> Union[Response, WerkzeugResponse]:
    """Возвращает структуру файлового дерева пользователя."""
    try:
        user_folder = _ensure_user_folder(current_user.id)
        filetree = _scan_directory(user_folder, user_folder)
        return jsonify({"success": True, "filetree": filetree})
    except (PermissionError, OSError) as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _ensure_safe_path(base_path: Path, target_path: Path) -> Optional[Path]:
    """Проверяет, что целевой путь находится внутри базовой папки."""
    try:
        resolved_path = target_path.resolve()
        if not str(resolved_path).startswith(str(base_path.resolve())):
            return None
        return resolved_path
    except Exception:
        return None


def _create_file(base_path: Path, element: FileActionElement) -> Dict[str, Any]:
    """Создаёт новый файл."""
    file_path = _ensure_safe_path(
        base_path, base_path / element.get("path", "new_file.py")
    )
    if not file_path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if file_path.exists():
        return {"status": "error", "message": ERROR_EXISTS, "code": 400}
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch()
    return {"status": "success", "message": "Файл создан"}


def _create_folder(base_path: Path, element: FileActionElement) -> Dict[str, Any]:
    """Создаёт новую папку."""
    folder_path = _ensure_safe_path(
        base_path, base_path / element.get("path", "new_folder")
    )
    if not folder_path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if folder_path.exists():
        return {"status": "error", "message": ERROR_EXISTS, "code": 400}
    folder_path.mkdir(parents=True, exist_ok=True)
    return {"status": "success", "message": "Папка создана"}


def _rename_element(base_path: Path, element: FileActionElement) -> Dict[str, Any]:
    """Переименовывает файл или папку."""
    old_path = _ensure_safe_path(base_path, base_path / element.get("old_path", ""))
    new_path = _ensure_safe_path(base_path, base_path / element.get("new_path", ""))
    if not old_path or not new_path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if not old_path.exists():
        return {"status": "error", "message": ERROR_NOT_FOUND, "code": 404}
    if new_path.exists():
        return {"status": "error", "message": ERROR_EXISTS, "code": 400}
    old_path.rename(new_path)
    return {"status": "success", "message": "Элемент переименован"}


def _delete_element(base_path: Path, element: FileActionElement) -> Dict[str, Any]:
    """Удаляет файл или папку."""
    path = _ensure_safe_path(base_path, base_path / element.get("path", ""))
    if not path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if not path.exists():
        return {"status": "error", "message": ERROR_NOT_FOUND, "code": 404}
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return {"status": "success", "message": "Элемент удалён"}


def _copy_element(base_path: Path, element: FileActionElement) -> Dict[str, Any]:
    """Копирует файл или папку."""
    src_path = _ensure_safe_path(base_path, base_path / element.get("src_path", ""))
    dest_path = _ensure_safe_path(base_path, base_path / element.get("dest_path", ""))
    if not src_path or not dest_path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if not src_path.exists():
        return {"status": "error", "message": ERROR_NOT_FOUND, "code": 404}
    if dest_path.exists():
        return {"status": "error", "message": ERROR_EXISTS, "code": 400}
    if src_path.is_dir():
        shutil.copytree(src_path, dest_path)
    else:
        shutil.copy2(src_path, dest_path)
    return {"status": "success", "message": "Элемент скопирован"}


def _read_file(base_path: Path, element: FileActionElement) -> Dict[str, Any]:
    """Читает содержимое файла."""
    file_path = _ensure_safe_path(base_path, base_path / element.get("path", ""))
    if not file_path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if not file_path.exists() or file_path.is_dir():
        return {"status": "error", "message": ERROR_NOT_FILE, "code": 404}
    try:
        with file_path.open("r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "message": "Файл прочитан", "content": content}
    except UnicodeDecodeError:
        return {"status": "error", "message": "Файл не является текстовым"}, 400


def _write_file(base_path: Path, element: FileActionElement) -> Dict[str, Any]:
    """Записывает содержимое в файл."""
    file_path = _ensure_safe_path(base_path, base_path / element.get("path", ""))
    content = element.get("content", "")
    if not file_path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if not file_path.exists() or file_path.is_dir():
        return {"status": "error", "message": ERROR_NOT_FILE, "code": 404}
    with file_path.open("w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "success", "message": "Файл обновлён"}


def _download_file(
    base_path: Path, element: FileActionElement
) -> Union[Response, Dict[str, Any]]:
    """Отправляет файл для скачивания."""
    file_path = _ensure_safe_path(base_path, base_path / element.get("path", ""))
    if not file_path:
        return {"status": "error", "message": ERROR_INVALID_PATH, "code": 403}
    if not file_path.exists() or file_path.is_dir():
        return {"status": "error", "message": ERROR_NOT_FILE, "code": 404}
    return send_file(file_path, as_attachment=True)


@blueprint.route("/api/file-action", methods=["POST"])
@login_required
def file_action() -> Union[Response, WerkzeugResponse]:
    """Обрабатывает действия с файлами и папками."""
    try:
        data: FileActionRequest = request.get_json()
        action = data.get("action", "")
        element = data.get("element", {})
        user_folder = Path(os.path.join(USER_FILES_PATH, str(current_user.id)))
        actions = {
            "create_file": _create_file,
            "create_folder": _create_folder,
            "rename": _rename_element,
            "delete": _delete_element,
            "copy": _copy_element,
            "read_file": _read_file,
            "write_file": _write_file,
            "download_file": _download_file,
        }

        if action in actions:
            result = actions[action](user_folder, element)
            if isinstance(result, dict):
                return jsonify(result), result.get("code", 200)
            return result  # Для download_file
        return jsonify({"status": "error", "message": ERROR_UNKNOWN_ACTION}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
