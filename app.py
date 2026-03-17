# Flask 기본 기능들 import
from flask import Flask, jsonify, render_template, request, session, url_for, flash, redirect
# .env 파일에 저장한 환경변수 불러오기
from extensions import mail
from dotenv import load_dotenv
# 운영체제 환경변수 접근용
import os

from routes.admin.admin_db import create_restaurant_request
from routes.owner.owner_routes import register_owner_routes
from routes.admin.admin_routes import admin_bp
from routes.login.login_routes import login_bp
from routes.mypage.mypage_routes import mypage_bp
from routes.restaurant.restaurant_panel import restaurant_panel_bp
from routes.ranking.user_ranking import user_ranking_bp
from routes.visit.visit_routes import visit_bp

from db import (
    fetch_categories,
    fetch_regions,
    fetch_restaurants,
    fetch_favorite_restaurants,
    toggle_favorite_restaurant,
    get_owner_by_user_id
)

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# =========================
# 메일 설정
# =========================
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USE_SSL"] = os.getenv("MAIL_USE_SSL", "False") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

mail.init_app(app)

app.register_blueprint(admin_bp)
app.register_blueprint(login_bp)
app.register_blueprint(mypage_bp)
app.register_blueprint(restaurant_panel_bp)
app.register_blueprint(user_ranking_bp)
app.register_blueprint(visit_bp)
register_owner_routes(app)


# =========================
# 메인 페이지
# =========================
@app.route("/")
def index():
    regions = ["전체"] + fetch_regions()
    categories = fetch_categories()
    user_email = session.get("user_email")
    user_nickname = session.get("user_nickname")
    user_id = session.get("user_id")
    
    # owner_id 유무 판단후 판매자 페이지 이동
    owner_id = None
    is_owner = False

    if user_id:
        owner_id = get_owner_by_user_id(user_id)
        is_owner = owner_id is not None

        if owner_id is not None:
            session["owner_id"] = owner_id
        else:
            session.pop("owner_id", None)
    else:
        session.pop("owner_id", None)

        
    return render_template(
        "index.html",
        regions=regions,
        categories=categories,
        user_email=user_email,
        user_nickname=user_nickname,
        user_id=user_id,
        is_owner=is_owner, # owner_id True 일때
        owner_id=owner_id # owner_id 반환
    )


# =========================
# 음식점 API
# =========================
@app.route("/api/restaurants")
def api_restaurants():
    region = request.args.get("region", default="전체", type=str)
    keyword = request.args.get("keyword", default="", type=str).strip()
    category_id = request.args.get("category_id", default="", type=str).strip()
    sort_by = request.args.get("sort_by", default="visits", type=str)
    user_id = session.get("user_id")

    items = fetch_restaurants(
        region=region,
        keyword=keyword,
        category_id=category_id if category_id else None,
        user_id=user_id,
        sort_by=sort_by,
    )

    return jsonify(items)

# =========================
# 즐겨찾기 API
# =========================
@app.route("/api/favorites")
def api_favorites():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "message": "로그인 후 이용해 주세요.",
            "login_url": url_for("login.login")
        }), 401

    region = request.args.get("region", default="전체", type=str)
    category_id = request.args.get("category_id", default="", type=str).strip()

    items = fetch_favorite_restaurants(
        user_id=user_id,
        region=region,
        category_id=category_id if category_id else None,
    )

    return jsonify(items)

@app.route("/api/favorites/<int:restaurant_id>/toggle", methods=["POST"])
def api_toggle_favorite(restaurant_id):
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "message": "로그인 후 이용해 주세요.",
            "login_url": url_for("login.login")
        }), 401

    is_favorite = toggle_favorite_restaurant(user_id, restaurant_id)

    return jsonify({
        "restaurant_id": restaurant_id,
        "is_favorite": is_favorite
    })

@app.route("/seller/register", methods=["GET", "POST"])
def seller_register():
    user_id = session.get("user_id")
    if not user_id:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login.login"))

    categories = fetch_categories()

    if request.method == "GET":
        return render_template("owner/owner_register.html", categories=categories)

    store_name = request.form.get("store_name", "").strip()
    owner_name = request.form.get("owner_name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    category_id = request.form.get("category_id", "").strip()
    description = request.form.get("description", "").strip()

    if not store_name:
        flash("가게명을 입력해주세요.")
        return render_template("owner/owner_register.html", categories=categories)

    if not category_id:
        flash("카테고리를 선택해주세요.")
        return render_template("owner/owner_register.html", categories=categories)

    category_name = ""
    for c in categories:
        if str(c["restaurant_category_id"]) == str(category_id):
            category_name = c["restaurant_category_name"]
            break

    if not category_name:
        flash("올바른 카테고리를 선택해주세요.")
        return render_template("owner/owner_register.html", categories=categories)

    success, result = create_restaurant_request(
        owner_name=str(user_id),
        store_name=store_name,
        phone=phone,
        road_address=address,
        category_name=category_name,
        description=description
    )

    if success:
        flash("판매자 등록 신청이 완료되었습니다.")
        return redirect(url_for("seller_register"))

    flash(f"판매자 등록 신청에 실패했습니다: {result}")
    return render_template("owner/owner_register.html", categories=categories)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "True") == "True") # asdffadsfdasadf