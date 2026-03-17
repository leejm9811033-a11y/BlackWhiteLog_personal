from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

from .mypage_db import fetch_my_reviews, fetch_my_favorites, fetch_my_visits, fetch_my_achievements, delete_my_favorite
from routes.login.login_db import update_user_nickname, find_user_by_nickname

mypage_bp = Blueprint("mypage", __name__)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("로그인이 필요합니다.")
            return redirect(url_for("login.login"))
        return view_func(*args, **kwargs)
    return wrapper


@mypage_bp.route("/mypage")
@login_required
def mypage():
    return render_template(
        "mypage/mypage.html",
        user_nickname=session.get("user_nickname"),
        user_email=session.get("user_email"),
    )


@mypage_bp.route("/mypage/nickname", methods=["POST"])
@login_required
def update_nickname():
    user_id = session["user_id"]
    current_nickname = session.get("user_nickname", "")
    new_nickname = request.form.get("nickname", "").strip()

    if not new_nickname:
        flash("닉네임을 입력해주세요.")
        return redirect(url_for("mypage.mypage"))
    if len(new_nickname) < 2 or len(new_nickname) > 12:
        flash("닉네임은 2자 이상 12자 이하로 입력해주세요.")
        return redirect(url_for("mypage.mypage"))
    if new_nickname == current_nickname:
        flash("현재 사용 중인 닉네임입니다.")
        return redirect(url_for("mypage.mypage"))

    existing_user = find_user_by_nickname(new_nickname)
    if existing_user and existing_user["user_id"] != user_id:
        flash("이미 사용 중인 닉네임입니다.")
        return redirect(url_for("mypage.mypage"))

    success = update_user_nickname(user_id, new_nickname)
    if success:
        session["user_nickname"] = new_nickname
        flash("닉네임이 변경되었습니다.")
    else:
        flash("닉네임 변경에 실패했습니다.")

    return redirect(url_for("mypage.mypage"))


@mypage_bp.route("/mypage/reviews")
@login_required
def mypage_reviews():
    user_id = session["user_id"]
    reviews = fetch_my_reviews(user_id)
    return render_template("mypage/mypage_reviews.html", reviews=reviews, user_nickname=session.get("user_nickname"))


# ==================================================
# 내 즐겨찾기 목록 삭제 실행
# ==================================================
@mypage_bp.route("/mypage/favorites")
@login_required
def mypage_favorites():
    user_id = session["user_id"]
    favorites = fetch_my_favorites(user_id)
    return render_template("mypage/mypage_favorites.html", favorites=favorites, user_nickname=session.get("user_nickname"))


@mypage_bp.route("/favorites/delete", methods=["POST"])
@login_required
def delete_favorite():
    user_id = session["user_id"]
    favorite_id = request.form.get("favorite_id", type=int)

    if not favorite_id:
        flash("잘못된 요청입니다.")
        return redirect(url_for("mypage.mypage_favorites"))

    delete_my_favorite(user_id, favorite_id)
    flash("즐겨찾기가 삭제되었습니다.")
    return redirect(url_for("mypage.mypage_favorites"))


@mypage_bp.route("/mypage/visits")
@login_required
def mypage_visits():
    user_id = session["user_id"]
    visits = fetch_my_visits(user_id)
    return render_template("mypage/mypage_visits.html", visits=visits, user_nickname=session.get("user_nickname"))


@mypage_bp.route("/mypage/achievements")
@login_required
def mypage_achievements():
    user_id = session["user_id"]
    achievements = fetch_my_achievements(user_id)
    return render_template("mypage/mypage_achievements.html", achievements=achievements, user_nickname=session.get("user_nickname"))
