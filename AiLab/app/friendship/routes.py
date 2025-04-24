from flask import (
    render_template,
    request,
    flash,
    redirect,
    url_for,
)
import sqlalchemy as sa
from flask_login import current_user
from app import db
from app.base.models import UserProfile, Friendship
from flask_login import login_required
from app.friendship import blueprint


@blueprint.route("/add_friend", methods=["POST"])
@login_required
def add_friend():
    friend_id = request.form.get("friend_id")

    # Проверка: нельзя добавить себя
    if current_user.id == int(friend_id):
        flash("Нельзя добавить себя в друзья", "error")
        return redirect(url_for("profile_blueprint.profile", id=friend_id))

    # Проверка существующего запроса
    existing = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id))
        | (
            (Friendship.user_id == friend_id)
            & (Friendship.friend_id == current_user.id)
        )
    ).first()

    if existing:
        flash("Запрос на дружбу уже существует", "info")
        return redirect(url_for("profile_blueprint.profile", id=friend_id))

    # Создание нового запроса
    new_request = Friendship(
        user_id=current_user.id, friend_id=friend_id, status="pending"
    )
    db.session.add(new_request)
    db.session.commit()

    flash("Запрос на дружбу отправлен!", "success")
    return redirect(url_for("profile_blueprint.profile", id=friend_id))


@blueprint.route("/friend_requests")
@login_required
def friend_requests():
    # Входящие запросы
    incoming = Friendship.query.filter(
        Friendship.friend_id == current_user.id, Friendship.status == "pending"
    ).all()

    # Исходящие запросы
    outgoing = Friendship.query.filter(
        Friendship.user_id == current_user.id, Friendship.status == "pending"
    ).all()

    # Список друзей
    friends = current_user.get_friends()
    profile = db.first_or_404(
        sa.select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    return render_template(
        "friend_requests.html",
        incoming=incoming,
        outgoing=outgoing,
        friends=friends,
        profile=profile,
    )


@blueprint.route("/accept_request/<int:request_id>", methods=["POST"])
@login_required
def accept_request(request_id):
    request = Friendship.query.get_or_404(request_id)

    if request.friend_id != current_user.id:
        flash("Вы не можете подтвердить этот запрос", "error")
        return redirect(url_for("friendship_blueprint.friend_requests"))

    request.status = "accepted"
    db.session.commit()

    flash("Запрос на дружбу подтвержден!", "success")
    return redirect(url_for("friendship_blueprint.friend_requests"))


@blueprint.route("/decline_request/<int:request_id>", methods=["POST"])
@login_required
def decline_request(request_id):
    request = Friendship.query.get_or_404(request_id)

    if request.friend_id != current_user.id:
        flash("Вы не можете отклонить этот запрос", "error")
        return redirect(url_for("friendship_blueprint.friend_requests"))

    db.session.delete(request)
    db.session.commit()

    flash("Запрос на дружбу отклонен", "info")
    return redirect(url_for("friendship_blueprint.friend_requests"))


@blueprint.route("/cancel_request/<int:request_id>", methods=["POST"])
@login_required
def cancel_request(request_id):
    request = Friendship.query.get_or_404(request_id)

    if request.user_id != current_user.id:
        flash("Вы не можете отменить этот запрос", "error")
        return redirect(url_for("friendship_blueprint.friend_requests"))

    db.session.delete(request)
    db.session.commit()

    flash("Запрос на дружбу отменен", "info")
    return redirect(url_for("friendship_blueprint.friend_requests"))


@blueprint.route("/remove_friend/<int:friend_id>", methods=["POST"])
@login_required
def remove_friend(friend_id):
    # Находим дружескую связь
    friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id))
        | (
            (Friendship.user_id == friend_id)
            & (Friendship.friend_id == current_user.id)
        ),
        Friendship.status == "accepted",
    ).first()

    if not friendship:
        flash("Пользователь не найден в списке друзей", "error")
        return redirect(url_for("friendship_blueprint.friend_requests"))

    # Удаляем дружескую связь
    db.session.delete(friendship)
    db.session.commit()

    flash("Пользователь удален из друзей", "success")
    return redirect(url_for("friendship_blueprint.friend_requests"))
