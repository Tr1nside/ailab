from flask import render_template, request, jsonify
from flask_login import current_user, login_required
from app.ide import blueprint
from app import db, USER_FILES_PATH
import sqlalchemy as sa
from app.base.models import UserProfile
import subprocess
import json
import os
import shutil

# Список стандартных библиотек Python
STANDARD_LIBRARIES = [
    "argparse",
    "array",
    "base64",
    "bisect",
    "calendar",
    "cmath",
    "collections",
    "contextlib",
    "copy",
    "csv",
    "datetime",
    "decimal",
    "difflib",
    "enum",
    "functools",
    "hashlib",
    "heapq",
    "io",
    "itertools",
    "json",
    "logging",
    "math",
    "operator",
    "os",
    "pathlib",
    "pickle",
    "random",
    "re",
    "shutil",
    "socket",
    "sqlite3",
    "statistics",
    "string",
    "subprocess",
    "sys",
    "tempfile",
    "threading",
    "time",
    "traceback",
    "types",
    "urllib",
    "uuid",
    "warnings",
    "weakref",
    "zlib",
]

# Системные библиотеки
SYSTEM_LIBRARIES = ["pip", "setuptools", "wheel"]


@blueprint.route("/ide")
@login_required
def ide():
    profile = db.first_or_404(
        sa.select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    return render_template(
        "ide.html", current_endpoint=request.endpoint, profile=profile
    )


@blueprint.route("/libraries/<python_version>", methods=["GET"])
@login_required
def get_libraries(python_version):
    """Возвращает список сторонних библиотек, установленных в интерпретаторе."""
    version_map = {"3.6": "python36", "3.9": "python39", "3.12": "python3"}
    python_executable = shutil.which(version_map.get(python_version, "python3"))
    if not python_executable:
        return jsonify(
            {
                "error": f"Интерпретатор Python {python_version} ({version_map.get(python_version)}) не найден"
            }
        ), 404

    try:
        result = subprocess.run(
            [python_executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        pip_data = json.loads(result.stdout)

        # Проверяем формат данных
        if isinstance(pip_data, dict) and "packages" in pip_data:
            libraries = pip_data["packages"]
        elif isinstance(pip_data, list):
            libraries = pip_data
        else:
            return jsonify(
                {"error": f"Некорректный формат данных от pip list: {type(pip_data)}"}
            ), 500

        # Формируем список сторонних библиотек
        formatted_libraries = []
        for lib in libraries:
            if isinstance(lib, dict) and "name" in lib and "version" in lib:
                if (
                    lib["name"] not in STANDARD_LIBRARIES
                    and lib["name"] not in SYSTEM_LIBRARIES
                ):
                    formatted_libraries.append(
                        {"name": lib["name"], "version": lib["version"]}
                    )
            else: 
                print()
                
        # Сортируем по имени
        formatted_libraries.sort(key=lambda x: x["name"])
        return jsonify(formatted_libraries)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Ошибка выполнения pip list: {e.stderr}"}), 500
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Ошибка декодирования JSON: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Ошибка получения библиотек: {str(e)}"}), 500


@blueprint.route("/presets", methods=["GET"])
@login_required
def get_presets():
    """Возвращает список пресетов пользователя."""
    user_id = current_user.id
    presets_dir = os.path.join(USER_FILES_PATH, "presets", str(user_id))
    os.makedirs(presets_dir, exist_ok=True)
    presets = []
    for preset_file in os.listdir(presets_dir):
        if preset_file.endswith(".json"):
            preset_name = preset_file[:-5]
            preset_path = os.path.join(presets_dir, preset_file)
            try:
                with open(preset_path, "r", encoding="utf-8") as f:
                    preset_data = json.load(f)
                presets.append(
                    {
                        "name": preset_name,
                        "libraries": preset_data.get("libraries", []),
                        "python_version": preset_data.get("python_version", "3.12"),
                    }
                )
            except:
                continue
    return jsonify(presets)


@blueprint.route("/create_preset", methods=["POST"])
@login_required
def create_preset():
    """Создает или обновляет пресет с указанными библиотеками и версией Python."""
    data = request.get_json()
    preset_name = data.get("name")
    libraries = data.get("libraries", [])
    python_version = data.get("python_version", "3.12")
    user_id = current_user.id
    presets_dir = os.path.join(USER_FILES_PATH, "presets", str(user_id))
    preset_path = os.path.join(presets_dir, f"{preset_name}.json")

    # Валидация имени пресета
    if not preset_name or not preset_name.replace(" ", "").isalnum():
        return jsonify(
            {"error": "Имя пресета должно содержать только буквы, цифры и пробелы"}
        ), 400

    # Проверяем, что библиотеки существуют в указанном интерпретаторе
    version_map = {"3.6": "python36", "3.9": "python39", "3.12": "python3"}
    python_executable = shutil.which(version_map.get(python_version, "python3"))
    if not python_executable:
        return jsonify(
            {
                "error": f"Интерпретатор Python {python_version} ({version_map.get(python_version)}) не найден"
            }
        ), 404

    try:
        result = subprocess.run(
            [python_executable, "-m", "pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        pip_data = json.loads(result.stdout)
        if isinstance(pip_data, dict) and "packages" in pip_data:
            installed_libraries = {lib["name"] for lib in pip_data["packages"]}
        elif isinstance(pip_data, list):
            installed_libraries = {lib["name"] for lib in pip_data}
        else:
            return jsonify({"error": "Некорректный формат данных от pip list"}), 500

        # Добавляем стандартные и системные библиотеки в список допустимых
        installed_libraries.update(STANDARD_LIBRARIES)
        installed_libraries.update(SYSTEM_LIBRARIES)
        invalid_libraries = [lib for lib in libraries if lib not in installed_libraries]
        if invalid_libraries:
            return jsonify(
                {"error": f"Библиотеки не найдены: {', '.join(invalid_libraries)}"}
            ), 400
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Ошибка проверки библиотек: {e.stderr}"}), 500
    except Exception as e:
        return jsonify({"error": f"Ошибка проверки библиотек: {str(e)}"}), 500

    # Автоматически добавляем стандартные и системные библиотеки
    libraries = list(set(libraries).union(STANDARD_LIBRARIES, SYSTEM_LIBRARIES))

    try:
        os.makedirs(presets_dir, exist_ok=True)
        with open(preset_path, "w", encoding="utf-8") as f:
            json.dump({"libraries": libraries, "python_version": python_version}, f)
        return jsonify({"message": f"Пресет '{preset_name}' сохранен"})
    except Exception as e:
        return jsonify({"error": f"Ошибка сохранения пресета: {str(e)}"}), 500


@blueprint.route("/delete_preset/<preset_name>", methods=["DELETE"])
@login_required
def delete_preset(preset_name):
    """Удаляет пресет."""
    user_id = current_user.id
    preset_path = os.path.join(
        USER_FILES_PATH, "presets", str(user_id), f"{preset_name}.json"
    )
    if not os.path.exists(preset_path):
        return jsonify({"error": f"Пресет '{preset_name}' не найден"}), 404
    try:
        os.remove(preset_path)
        return jsonify({"message": f"Пресет '{preset_name}' удален"})
    except Exception as e:
        return jsonify({"error": f"Ошибка удаления пресета: {str(e)}"}), 500


@blueprint.route("/save_code", methods=["POST"])
@login_required
def save_code():
    """Сохраняет код в файл."""
    data = request.get_json()
    code = data.get("code")
    file_path = data.get("file_path")
    user_id = current_user.id
    full_path = os.path.join(USER_FILES_PATH, str(user_id), file_path)
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(code)
        return jsonify({"message": "Код сохранен"})
    except Exception as e:
        return jsonify({"error": f"Ошибка сохранения кода: {str(e)}"}), 500
