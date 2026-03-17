from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mail import Message
from extensions import mail
import os
import requests
import secrets
import random
import time

from .login_db import (
    verify_user_login,
    create_user,
    find_user_by_email,
    find_user_by_social,
    create_social_user_with_form,
    withdraw_user,
    find_user_by_nickname,
    find_email_by_nickname,
    link_social_account,
    update_user_password_by_email,
)

login_bp = Blueprint("login", __name__)


def login_user_session(user, provider_name):
    session["user_email"] = user["email"]
    session["user_nickname"] = user["nickname"]
    session["user_id"] = user["user_id"]
    session["role"] = user.get("role", "USER")
    session["login_provider"] = provider_name


def handle_social_login_or_link(provider, social_id, email, nickname, profile_image_url):
    user = find_user_by_social(provider, social_id)

    if user:
        login_user_session(user, provider.lower())
        flash("로그인되었습니다.")
        return redirect(url_for("index"))

# ==================================================
# 카카오 소셜 로그인 시 값을 이상하게 받아옴, 이메일 강제로 비우기
# ==================================================
    signup_email = email
    if provider.upper() == "KAKAO":
        signup_email = ""

    session["pending_social_link"] = {
        "provider": provider.upper(),
        "social_id": social_id,
        "email": signup_email,
        "nickname": nickname,
        "profile_image_url": profile_image_url,
    }
    session["show_social_link_modal"] = True
    session.pop("social_signup_data", None)

    flash("연결된 계정이 없습니다. 기존 회원이면 계정 연결, 처음이라면 회원가입을 진행해주세요.")
    return redirect(url_for("login.login"))


# =========================
# 일반 로그인
# =========================
@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = verify_user_login(email, password)

        if user:
            pending_social_link = session.get("pending_social_link")

            if pending_social_link:
                provider = pending_social_link.get("provider")
                social_id = pending_social_link.get("social_id")

                if not provider or not social_id:
                    session.pop("pending_social_link", None)
                    session.pop("show_social_link_modal", None)
                    flash("소셜 연동 정보가 올바르지 않습니다. 다시 시도해주세요.")
                    return redirect(url_for("login.login"))

                try:
                    link_social_account(user["user_id"], provider, social_id)
                except ValueError as e:
                    session.pop("pending_social_link", None)
                    session.pop("show_social_link_modal", None)
                    flash(str(e))
                    return redirect(url_for("login.login"))
                except Exception:
                    session.pop("pending_social_link", None)
                    session.pop("show_social_link_modal", None)
                    flash("소셜 계정 연결 중 오류가 발생했습니다.")
                    return redirect(url_for("login.login"))

                session.pop("pending_social_link", None)
                session.pop("show_social_link_modal", None)
                flash("기존 계정과 소셜 계정이 연결되었습니다.")

            login_user_session(user, "local")
            return redirect(url_for("index"))

        flash("이메일 또는 비밀번호가 올바르지 않거나 탈퇴한 계정입니다.")
        return redirect(url_for("login.login"))

    show_social_link_modal = session.pop("show_social_link_modal", False)
    pending_social_link = session.get("pending_social_link")

    return render_template(
        "login/login.html",
        show_social_link_modal=show_social_link_modal,
        pending_social_link=pending_social_link,
    )


# =========================
# 일반 회원가입 / 소셜 회원가입
# =========================
@login_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        mode = request.args.get("mode", "").strip()
        if mode == "local":
            session.pop("social_signup_data", None)
            session.pop("pending_social_link", None)
            session.pop("show_social_link_modal", None)

    social_data = session.get("social_signup_data", {})

    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()

        gender = request.form.get("gender", "").strip()
        birth_year = request.form.get("birth_year", "").strip()
        birth_month = request.form.get("birth_month", "").strip()
        birth_day = request.form.get("birth_day", "").strip()

        postcode = request.form.get("postcode", "").strip()
        road_address = request.form.get("roadAddress", "").strip()
        jibun_address = request.form.get("jibunAddress", "").strip()
        detail_address = request.form.get("detailAddress", "").strip()
        extra_address = request.form.get("extraAddress", "").strip()

        ad_agree = request.form.get("ad_agree", "")
        email_checked = request.form.get("email_checked", "false")
        checked_email_value = request.form.get("checked_email_value", "").strip()
        nickname_checked = request.form.get("nickname_checked", "false")
        checked_nickname_value = request.form.get("checked_nickname_value", "").strip()

        form_data = {
            "email": email,
            "nickname": nickname,
            "gender": gender,
            "birth_year": birth_year,
            "birth_month": birth_month,
            "birth_day": birth_day,
            "postcode": postcode,
            "roadAddress": road_address,
            "jibunAddress": jibun_address,
            "detailAddress": detail_address,
            "extraAddress": extra_address,
            "ad_agree": ad_agree,
        }

        def render_signup_with_error(message):
            flash(message)
            return render_template("login/signup.html", social_data=social_data, form_data=form_data)

        if not nickname or not email:
            return render_signup_with_error("이메일과 닉네임을 입력해주세요.")
        if not gender:
            return render_signup_with_error("성별을 선택해주세요.")
        if not birth_year or not birth_month or not birth_day:
            return render_signup_with_error("생년월일을 입력해주세요.")
        if not postcode or not road_address:
            return render_signup_with_error("주소 검색을 통해 주소를 입력해주세요.")

        existing_user = find_user_by_email(email)
        if existing_user:
            if not social_data or existing_user["email"] != social_data.get("email"):
                return render_signup_with_error("이미 가입된 이메일입니다.")

        existing_nickname = find_user_by_nickname(nickname)
        if existing_nickname:
            if not social_data or existing_nickname["nickname"] != social_data.get("nickname"):
                return render_signup_with_error("이미 사용 중인 닉네임입니다.")

        # 소셜 신규 회원가입
        if social_data:
            provider = social_data.get("provider")
            social_id = social_data.get("social_id")
            profile_image_url = social_data.get("profile_image_url")

            if not provider or not social_id:
                flash("소셜 회원가입 정보가 올바르지 않습니다. 다시 시도해주세요.")
                session.pop("social_signup_data", None)
                session.pop("pending_social_link", None)
                return redirect(url_for("login.login"))

            if not password or not password_confirm:
                return render_signup_with_error("비밀번호와 비밀번호 확인을 입력해주세요.")
            if password != password_confirm:
                return render_signup_with_error("비밀번호와 비밀번호 확인이 일치하지 않습니다.")

            if provider.upper() == "KAKAO":
                if not email:
                    return render_signup_with_error("카카오 회원가입은 이메일을 직접 입력해주세요.")
                if email_checked != "true" or checked_email_value != email:
                    return render_signup_with_error("이메일 중복 확인을 해주세요.")

            if nickname_checked != "true" or checked_nickname_value != nickname:
                return render_signup_with_error("닉네임 중복 확인을 해주세요.")

            create_social_user_with_form(
                nickname=nickname,
                email=email,
                password=password,
                provider=provider,
                social_id=social_id,
                profile_image_url=profile_image_url,
            )

            user = find_user_by_social(provider, social_id)
            if not user:
                return render_signup_with_error("소셜 회원가입 후 사용자 조회에 실패했습니다.")

            login_user_session(user, provider.lower())
            session.pop("social_signup_data", None)
            session.pop("pending_social_link", None)
            session.pop("show_social_link_modal", None)

            flash("간편 회원가입이 완료되었습니다.")
            return redirect(url_for("index"))

        # 일반 회원가입
        if not password or not password_confirm:
            return render_signup_with_error("비밀번호와 비밀번호 확인을 입력해주세요.")
        if password != password_confirm:
            return render_signup_with_error("비밀번호와 비밀번호 확인이 일치하지 않습니다.")
        if email_checked != "true" or checked_email_value != email:
            return render_signup_with_error("이메일 중복 확인을 해주세요.")
        if nickname_checked != "true" or checked_nickname_value != nickname:
            return render_signup_with_error("닉네임 중복 확인을 해주세요.")

        create_user(nickname, email, password)
        flash("회원가입이 완료되었습니다. 로그인해주세요.")
        return redirect(url_for("login.login"))

    return render_template("login/signup.html", social_data=social_data, form_data={})


@login_bp.route("/signup/reset")
def signup_reset():
    session.pop("social_signup_data", None)
    session.pop("pending_social_link", None)
    session.pop("show_social_link_modal", None)
    return redirect(url_for("login.signup", mode="local"))


# =========================
# 소셜 연결 선택 페이지
# =========================
@login_bp.route("/social/connect-choice")
def social_connect_choice():
    pending_social_link = session.get("pending_social_link")
    if not pending_social_link:
        flash("소셜 연동 정보가 없습니다. 다시 시도해주세요.")
        return redirect(url_for("login.login"))

    return render_template(
        "login/social_connect_choice.html",
        social_data=pending_social_link
    )


# =========================
# 기존 회원 계정과 연결하러 로그인 페이지로 이동
# =========================

#@login_bp.route("/social/connect-existing")
#def social_connect_existing():
#    pending_social_link = session.get("pending_social_link")
#    if not pending_social_link:
#        flash("소셜 연동 정보가 없습니다. 다시 시도해주세요.")
#        return redirect(url_for("login.login"))
#
#    session["show_social_link_modal"] = True
#    flash("기존 계정으로 로그인하면 소셜 계정이 연결됩니다.")
#    return redirect(url_for("login.login"))


@login_bp.route("/social/signup")
def social_signup():
    pending_social_link = session.get("pending_social_link")
    if not pending_social_link:
        flash("소셜 회원가입 정보가 없습니다. 다시 시도해주세요.")
        return redirect(url_for("login.login"))

    session["social_signup_data"] = pending_social_link
    session.pop("show_social_link_modal", None)
    flash("추가 회원정보를 입력해주세요.")
    return redirect(url_for("login.signup"))


@login_bp.route("/social/cancel")
def social_cancel():
    session.pop("pending_social_link", None)
    session.pop("social_signup_data", None)
    session.pop("show_social_link_modal", None)
    flash("소셜 로그인 연결이 취소되었습니다.")
    return redirect(url_for("login.login"))


@login_bp.route("/api/check-duplicate")
def check_duplicate():
    check_type = request.args.get("type", "").strip()
    value = request.args.get("value", "").strip()

    if not value:
        return jsonify({"available": False, "message": "값을 입력해주세요."})

    if check_type == "email":
        user = find_user_by_email(value)
        return jsonify({
            "available": not bool(user),
            "message": "사용 가능한 이메일입니다." if not user else "이미 사용 중인 이메일입니다."
        })
    elif check_type == "nickname":
        user = find_user_by_nickname(value)
        return jsonify({
            "available": not bool(user),
            "message": "사용 가능한 닉네임입니다." if not user else "이미 사용 중인 닉네임입니다."
        })

    return jsonify({"available": False, "message": "잘못된 요청입니다."})


@login_bp.route("/find-id", methods=["GET", "POST"])
def find_id():
    found_email = None
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        if not nickname:
            flash("닉네임을 입력해주세요.")
            return redirect(url_for("login.find_id"))

        user = find_email_by_nickname(nickname)
        if not user:
            flash("일치하는 회원 정보를 찾을 수 없습니다.")
            return redirect(url_for("login.find_id"))
        found_email = user["email"]

    return render_template("login/find_id.html", found_email=found_email)


@login_bp.route("/find-password", methods=["GET"])
def find_password():
    clear_password_reset_session()
    return render_template("login/find_password.html")


@login_bp.route("/logout")
def logout():
    provider = session.get("login_provider")
    session.clear()

    if provider == "kakao":
        kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY")
        kakao_logout_redirect_uri = os.getenv("KAKAO_LOGOUT_REDIRECT_URI")
        logout_url = (
            "https://kauth.kakao.com/oauth/logout"
            f"?client_id={kakao_rest_api_key}"
            f"&logout_redirect_uri={kakao_logout_redirect_uri}"
        )
        return redirect(logout_url)

    if provider in ["naver", "google", "local", None]:
        flash("로그아웃되었습니다.")
        return redirect(url_for("index"))


@login_bp.route("/logout/kakao/callback")
def logout_kakao_callback():
    flash("로그아웃되었습니다.")
    return redirect(url_for("index"))


@login_bp.route("/login/kakao")
def login_kakao():
    kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY")
    redirect_uri = os.getenv("KAKAO_REDIRECT_URI")
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={kakao_rest_api_key}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&state={state}"
    )
    return redirect(auth_url)


@login_bp.route("/login/kakao/callback")
def login_kakao_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("카카오 로그인에 실패했습니다.")
        return redirect(url_for("login.login"))
    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login.login"))

    token_data = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("KAKAO_REST_API_KEY"),
        "redirect_uri": os.getenv("KAKAO_REDIRECT_URI"),
        "code": code,
    }
    client_secret = os.getenv("KAKAO_CLIENT_SECRET")
    if client_secret:
        token_data["client_secret"] = client_secret

    token_res = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=token_data,
        headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
    )
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"카카오 토큰 발급 실패: {token_json}")
        return redirect(url_for("login.login"))

    user_res = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
        },
    )
    user_json = user_res.json()
    social_id = str(user_json.get("id"))
    kakao_account = user_json.get("kakao_account", {})
    profile = kakao_account.get("profile", {})
    email = kakao_account.get("email") or f"kakao_{social_id}@kakao.local"
    nickname = profile.get("nickname") or f"kakao_{social_id}"
    profile_image_url = profile.get("profile_image_url")

    if not social_id:
        flash("카카오 사용자 정보를 불러오지 못했습니다.")
        return redirect(url_for("login.login"))

    return handle_social_login_or_link(
        provider="KAKAO",
        social_id=social_id,
        email=email,
        nickname=nickname,
        profile_image_url=profile_image_url,
    )


@login_bp.route("/login/naver")
def login_naver():
    naver_client_id = os.getenv("NAVER_CLIENT_ID")
    redirect_uri = os.getenv("NAVER_REDIRECT_URI")
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    auth_url = (
        "https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={naver_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )
    return redirect(auth_url)


@login_bp.route("/login/naver/callback")
def login_naver_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("네이버 로그인에 실패했습니다.")
        return redirect(url_for("login.login"))
    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login.login"))

    token_data = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("NAVER_CLIENT_ID"),
        "client_secret": os.getenv("NAVER_CLIENT_SECRET"),
        "code": code,
        "state": state,
    }
    token_res = requests.post("https://nid.naver.com/oauth2.0/token", params=token_data)
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"네이버 토큰 발급 실패: {token_json}")
        return redirect(url_for("login.login"))

    user_res = requests.get(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_json = user_res.json().get("response", {})
    social_id = user_json.get("id")
    email = user_json.get("email") or f"naver_{social_id}@naver.local"
    nickname = user_json.get("nickname") or f"naver_{social_id}"
    profile_image_url = user_json.get("profile_image")

    if not social_id:
        flash("네이버 사용자 정보를 불러오지 못했습니다.")
        return redirect(url_for("login.login"))

    return handle_social_login_or_link(
        provider="NAVER",
        social_id=social_id,
        email=email,
        nickname=nickname,
        profile_image_url=profile_image_url,
    )


@login_bp.route("/login/google")
def login_google():
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={google_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
    )
    return redirect(auth_url)


@login_bp.route("/login/google/callback")
def login_google_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("구글 로그인에 실패했습니다.")
        return redirect(url_for("login.login"))
    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login.login"))

    token_data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }
    token_res = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"구글 토큰 발급 실패: {token_json}")
        return redirect(url_for("login.login"))

    user_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_json = user_res.json()
    social_id = user_json.get("id")
    email = user_json.get("email") or f"google_{social_id}@google.local"
    nickname = user_json.get("name") or f"google_{social_id}"
    profile_image_url = user_json.get("picture")

    if not social_id:
        flash("구글 사용자 정보를 불러오지 못했습니다.")
        return redirect(url_for("login.login"))

    return handle_social_login_or_link(
        provider="GOOGLE",
        social_id=social_id,
        email=email,
        nickname=nickname,
        profile_image_url=profile_image_url,
    )


@login_bp.route("/withdraw", methods=["POST"])
def withdraw():
    user_id = session.get("user_id")
    if not user_id:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login.login"))

    withdraw_user(user_id)
    session.clear()
    flash("회원 탈퇴가 완료되었습니다.")
    return redirect(url_for("index"))


# =========================
# 비밀번호 재설정 세션 초기화
# =========================
def clear_password_reset_session():
    session.pop("pw_reset_email", None)
    session.pop("pw_reset_code", None)
    session.pop("pw_reset_expire", None)
    session.pop("pw_reset_verified", None)


# =========================
# 비밀번호 재설정 페이지
# /password-reset 접근 시 기존 find-password로 연결
# =========================
@login_bp.route("/password-reset", methods=["GET"])
def password_reset_page():
    return redirect(url_for("login.find_password"))


# =========================
# 인증번호 메일 발송
# =========================
@login_bp.route("/password-reset/send-code", methods=["POST"])
def send_password_reset_code():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({
            "ok": False,
            "message": "이메일을 입력해주세요."
        }), 400

    user = find_user_by_email(email)
    if not user:
        return jsonify({
            "ok": False,
            "message": "해당 이메일의 회원이 없습니다."
        }), 404

    code = str(random.randint(100000, 999999))
    expire_at = int(time.time()) + 180

    session["pw_reset_email"] = email
    session["pw_reset_code"] = code
    session["pw_reset_expire"] = expire_at
    session["pw_reset_verified"] = False

    try:
        msg = Message(
            subject="[흑백로그] 비밀번호 재설정 인증번호",
            recipients=[email],
            body=f"""안녕하세요.

흑백로그 비밀번호 재설정 인증번호는 [{code}] 입니다.

이 인증번호는 3분 동안만 유효합니다.
감사합니다.
"""
        )
        mail.send(msg)

        return jsonify({
            "ok": True,
            "message": "인증번호를 이메일로 전송했습니다.",
            "expire_at": expire_at
        })
    except Exception as e:
        clear_password_reset_session()
        return jsonify({
            "ok": False,
            "message": f"메일 전송 실패: {str(e)}"
        }), 500


# =========================
# 인증번호 확인
# =========================
@login_bp.route("/password-reset/verify-code", methods=["POST"])
def verify_password_reset_code():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()

    saved_email = session.get("pw_reset_email")
    saved_code = session.get("pw_reset_code")
    expire_at = session.get("pw_reset_expire")

    if not saved_email or not saved_code or not expire_at:
        return jsonify({
            "ok": False,
            "message": "인증정보가 없습니다. 다시 인증번호를 요청해주세요."
        }), 400

    if int(time.time()) > int(expire_at):
        clear_password_reset_session()
        return jsonify({
            "ok": False,
            "message": "인증시간이 만료되었습니다. 다시 인증번호를 요청해주세요."
        }), 400

    if email != saved_email:
        return jsonify({
            "ok": False,
            "message": "인증 요청한 이메일과 일치하지 않습니다."
        }), 400

    if code != saved_code:
        return jsonify({
            "ok": False,
            "message": "인증번호가 올바르지 않습니다."
        }), 400

    session["pw_reset_verified"] = True

    return jsonify({
        "ok": True,
        "message": "이메일 인증이 완료되었습니다."
    })


# =========================
# 새 비밀번호로 변경
# =========================
@login_bp.route("/password-reset/change", methods=["POST"])
def change_password_after_email_verify():
    data = request.get_json() or {}

    email = (data.get("email") or "").strip().lower()
    new_password = (data.get("new_password") or "").strip()
    new_password_confirm = (data.get("new_password_confirm") or "").strip()

    saved_email = session.get("pw_reset_email")
    expire_at = session.get("pw_reset_expire")
    verified = session.get("pw_reset_verified", False)

    if not saved_email or not expire_at:
        return jsonify({
            "ok": False,
            "message": "인증정보가 없습니다. 처음부터 다시 진행해주세요."
        }), 400

    if int(time.time()) > int(expire_at):
        clear_password_reset_session()
        return jsonify({
            "ok": False,
            "message": "인증시간이 만료되었습니다. 다시 진행해주세요."
        }), 400

    if not verified:
        return jsonify({
            "ok": False,
            "message": "먼저 인증번호 확인을 완료해주세요."
        }), 400

    if email != saved_email:
        return jsonify({
            "ok": False,
            "message": "인증한 이메일과 일치하지 않습니다."
        }), 400

    if not new_password or not new_password_confirm:
        return jsonify({
            "ok": False,
            "message": "새 비밀번호와 비밀번호 확인을 입력해주세요."
        }), 400

    if new_password != new_password_confirm:
        return jsonify({
            "ok": False,
            "message": "새 비밀번호와 비밀번호 확인이 일치하지 않습니다."
        }), 400

    if len(new_password) < 8:
        return jsonify({
            "ok": False,
            "message": "비밀번호는 8자 이상이어야 합니다."
        }), 400

    changed = update_user_password_by_email(email, new_password)

    if not changed:
        return jsonify({
            "ok": False,
            "message": "비밀번호 변경에 실패했습니다."
        }), 500

    clear_password_reset_session()

    return jsonify({
        "ok": True,
        "message": "비밀번호가 성공적으로 변경되었습니다."
    })