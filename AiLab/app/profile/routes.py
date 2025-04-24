from flask import (
    render_template,
    request,
    flash,
    redirect,
    url_for,
)
from app.profile import blueprint
from flask_login import login_required
from app import db
import sqlalchemy as sa
from app.base.models import UserProfile
from app.base.forms import ProfileEditForm
from werkzeug.utils import secure_filename
from os import path
from app import UPLOAD_FOLDER


@blueprint.route("/profile/<int:id>", methods=["GET", "POST"])
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
                file_path = path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                profile.profile_photo = filename

            db.session.commit()
            flash("Данные успешно сохранены!", "success")
            return redirect(url_for("main_bp.profile", id=id))  # Редирект с ID

        except Exception as e:
            db.session.rollback()
            print(e)

    elif request.method == "GET":
        # Заполняем форму данными из БД
        form.full_name.data = profile.full_name
        form.email.data = profile.email
        form.phone.data = profile.phone
        form.position.data = profile.position
        form.telegram_link.data = profile.telegram_link
        form.github_link.data = profile.github_link
        form.vk_link.data = profile.vk_link

    return render_template(
        "profile.html",
        profile=profile,
        id=id,
        current_endpoint=request.endpoint,
        form=form,
    )
