import os
import uuid
from flask import Blueprint, jsonify, request, session
from .restaurant_panel_db import get_restaurant_detail, get_restaurant_menus
from ..review.review_db import get_restaurant_reviews, save_restaurant_review, delete_review_transaction
restaurant_panel_bp = Blueprint('restaurant_panel_bp', __name__)

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>")
def api_restaurant_detail(restaurant_id):
    """특정 음식점 상세 정보 반환 API"""
    user_id = session.get("user_id")
    detail = get_restaurant_detail(restaurant_id, user_id=user_id)

    if detail:
        return jsonify(detail)
    return jsonify({"error": "Restaurant not found"}), 404

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>/menus")
def api_restaurant_menus(restaurant_id):
    """특정 음식점의 메뉴 목록 반환 API"""
    user_id = session.get("user_id")
    menus = get_restaurant_menus(restaurant_id, user_id=user_id)
    return jsonify(menus)

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>/reviews")
def api_restaurant_reviews(restaurant_id):
    """특정 음식점의 리뷰 목록 반환 API"""
    reviews = get_restaurant_reviews(restaurant_id)

    current_user_id = session.get('user_id')

    for review in reviews:
        review['is_mine'] = (current_user_id == review['user_id'])

    return jsonify(reviews)

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>/reviews", methods=["POST"])
def api_add_review(restaurant_id):
    try:
        rating = request.form.get("rating")
        content = request.form.get("content")
        images = request.files.getlist("images")

        if not rating or not content:
            return jsonify({"success": False, "message": "데이터가 부족합니다."}), 400

        user_id = session.get('user_id')

        if not user_id:
            return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

        image_urls = []
        if images and images[0].filename != '':
            upload_dir = os.path.join("static", "img", "review_img")
            os.makedirs(upload_dir, exist_ok=True)

            for img in images:
                if img and img.filename:
                    ext = img.filename.rsplit('.', 1)[-1].lower() if '.' in img.filename else 'jpg'
                    unique_filename = f"{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join(upload_dir, unique_filename)

                    img.save(filepath)

                    web_path = f"/{filepath.replace(os.sep, '/')}"
                    image_urls.append(web_path)

        success = save_restaurant_review(restaurant_id, user_id, int(rating), content, image_urls)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "DB 저장 실패 (함수 반환값 False)"})

    except Exception as e:
        print(f"서버 에러 발생: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500


@restaurant_panel_bp.route("/api/reviews/<int:review_id>", methods=["DELETE"])
def api_delete_review(review_id):
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    from .restaurant_panel_db import delete_review_transaction
    if delete_review_transaction(review_id, user_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "삭제 권한이 없거나 오류가 발생했습니다."}), 403