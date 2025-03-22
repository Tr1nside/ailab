import qrcode
import os
from qrcode.image.svg import SvgPathImage

def generate_qr_code(user_id, email, flag):
    if flag:
        # Создаем URL профиля
        profile_url = f"http://localhost:5000/profile/{user_id}"
        
        # Генерируем QR-код
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(profile_url)
        qr.make(fit=True)
        
        # Создаем изображение
        
        img = qr.make_image(
        image_factory=SvgPathImage,
        fill_color="currentColor",  # Используем текущий цвет CSS
        back_color="transparent"    # Прозрачный фон
    )

        # Сохраняем в папку static/qrcodes
        appdir = os.path.abspath(os.path.dirname(__file__))
        QR_FOLDER = os.path.join(appdir, '../static/qrcodes')
        filename = f"qr_{email}.svg"
        save_path = os.path.join(QR_FOLDER, filename)
        
        # Создаем папку если не существует
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        img.save(save_path)
        return filename
    else: 
        return f"qr_{email}.png"
