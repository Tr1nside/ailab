import qrcode
import os
from qrcode.image.svg import SvgPathImage
from typing import NamedTuple


class QrPathData(NamedTuple):
    save_path: str
    filename: str


def _generate_qr_obj(profile_url: str) -> qrcode.QRCode:
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(profile_url)
        qr.make(fit=True)
        return qr
    except Exception as e:
        print(f"Error in generate qr object: {e}")
        return None


def _create_qr_path(email: str) -> QrPathData:
    appdir = os.path.abspath(os.path.dirname(__file__))
    QR_FOLDER = os.path.join(appdir, "../static/qrcodes")
    filename = f"qr_{email}.svg"
    save_path = os.path.join(QR_FOLDER, filename)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    return QrPathData(save_path, filename)


def generate_qr_code(user_id: int, email: str, flag: bool) -> str:
    """Генерация и сохранение qr кода пользователя"""
    try:
        if flag:
            profile_url = f"http://localhost:5000/profile/{user_id}"
            qr = _generate_qr_obj(profile_url)

            img = qr.make_image(
                image_factory=SvgPathImage,
                fill_color="currentColor",  # Используем текущий цвет CSS
                back_color="transparent",  # Прозрачный фон
            )

            save_path, filename = _create_qr_path(email)

            img.save(save_path)

            return filename
        else:
            filename = _create_qr_path(email).filename
            return filename
    except Exception as e:
        print(f"Error in generate qr code: {e}")
        return None
