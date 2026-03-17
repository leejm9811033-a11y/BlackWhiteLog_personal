from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps

from .admin_db import (
    fetch_all_users,
    admin_deactivate_user,
    admin_restore_user,
    fetch_admin_reports,
    update_admin_report_status,
    fetch_admin_sanctions,
    create_admin_sanction,
    release_admin_sanction,
    fetch_admin_review_restaurants,
    fetch_admin_reviews_by_restaurant,
    get_admin_review_by_id,
    update_admin_review,
    hide_admin_review,
    soft_delete_admin_review,
    restore_admin_review,
    get_restaurant_by_id,
    update_restaurant,
    delete_restaurant,
    create_restaurant,
    fetch_admin_restaurant_requests,
    approve_restaurant_request,
    reject_restaurant_request,
    fetch_admin_owners,
)

admin_bp = Blueprint("admin", __name__)


# =========================
# 관리자 권한 체크 데코레이터
# =========================
def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # 로그인 안 했으면 로그인 페이지로 이동
        if "user_id" not in session:
            flash("로그인이 필요합니다.")
            return redirect(url_for("login.login"))

        # 관리자만 접근 가능
        if session.get("role") != "ADMIN":
            flash("관리자만 접근할 수 있습니다.")
            return redirect(url_for("index"))

        return view_func(*args, **kwargs)
    return wrapper


# =========================
# 관리자 음식점 등록
# =========================
@admin_bp.route("/admin/restaurants/create", methods=["GET", "POST"])
@admin_required
def admin_restaurant_create():
    # GET 요청이면 등록 폼 보여주기
    if request.method == "GET":
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="create",
            restaurant=None,
        )

    # POST 요청이면 폼 데이터 받기
    restaurant_name = request.form.get("restaurant_name", "").strip()
    restaurant_category_id = request.form.get("restaurant_category_id", "").strip()
    region_sigungu = request.form.get("region_sigungu", "").strip()
    address = request.form.get("address", "").strip()
    phone = request.form.get("phone", "").strip()

    # 이름은 필수 입력
    if not restaurant_name:
        flash("음식점 이름을 입력해주세요.")
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="create",
            restaurant=None,
        )

    create_restaurant(
        restaurant_name,
        restaurant_category_id,
        region_sigungu,
        address,
        phone
    )

    flash("음식점이 등록되었습니다.")
    return redirect(url_for("admin.admin_restaurants"))


# =========================
# 관리자 음식점 수정
# =========================
@admin_bp.route("/admin/restaurants/<int:restaurant_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_restaurant_edit(restaurant_id):
    # 수정할 음식점 찾기
    restaurant = get_restaurant_by_id(restaurant_id)

    # 없는 음식점이면 목록으로 이동
    if not restaurant:
        flash("해당 음식점을 찾을 수 없습니다.")
        return redirect(url_for("admin.admin_restaurants"))

    # GET 요청이면 수정 폼 보여주기
    if request.method == "GET":
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="edit",
            restaurant=restaurant,
        )

    # POST 요청이면 수정값 받기
    restaurant_name = request.form.get("restaurant_name", "").strip()
    restaurant_category_id = request.form.get("restaurant_category_id", "").strip()
    region_sigungu = request.form.get("region_sigungu", "").strip()
    address = request.form.get("address", "").strip()
    phone = request.form.get("phone", "").strip()

    # 이름은 필수 입력
    if not restaurant_name:
        flash("음식점 이름을 입력해주세요.")
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="edit",
            restaurant=restaurant,
        )

    update_restaurant(
        restaurant_id,
        restaurant_name,
        address,
        phone
    )

    flash("음식점 정보가 수정되었습니다.")
    return redirect(url_for("admin.admin_restaurants"))


# =========================
# 관리자 음식점 삭제  이종민 수정 s
# =========================

@admin_bp.route("/admin/restaurants")
@admin_required
def admin_restaurants():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    items = fetch_admin_restaurant_requests(keyword=keyword, status=status)

    return render_template(
        "admin/admin_seller_requests.html",
        items=items,
        keyword=keyword,
        status=status,
    )




@admin_bp.route("/admin/restaurants/<int:restaurant_id>/delete", methods=["POST"])
@admin_required
def admin_restaurant_delete(restaurant_id):

    delete_restaurant(restaurant_id)

    flash("음식점이 삭제되었습니다.")

    return redirect(url_for("admin.admin_restaurants"))



# =========================
# 관리자 리뷰 관리 - 리뷰가 등록된 가게 목록
# 템플릿:
# - templates/admin/admin_reviews.html
# =========================
@admin_bp.route("/admin/reviews")
@admin_required
def admin_review_restaurants():
    keyword = request.args.get("keyword", "").strip()

    restaurants = fetch_admin_review_restaurants(keyword)

    return render_template(
        "admin/admin_reviews.html",
        restaurants=restaurants,
        keyword=keyword,
    )


# =========================
# 관리자 리뷰 관리 - 특정 가게의 리뷰 목록
# 템플릿:
# - templates/admin/admin_reviews_detail.html
# =========================
@admin_bp.route("/admin/reviews/<int:restaurant_id>")
@admin_required
def admin_review_manage(restaurant_id):
    status = request.args.get("status", "").strip()

    reviews = fetch_admin_reviews_by_restaurant(restaurant_id, status)

    # 기본 제목
    restaurant_name = "리뷰 관리"

    # 리뷰가 있으면 첫 번째 리뷰에서 가게명 꺼내기
    if reviews:
        restaurant_name = reviews[0]["restaurant_name"]

    return render_template(
        "admin/admin_reviews_detail.html",
        reviews=reviews,
        restaurant_id=restaurant_id,
        restaurant_name=restaurant_name,
        selected_status=status,
    )


# =========================
# 관리자 리뷰 관리 - 리뷰 수정
# 템플릿:
# - templates/admin/admin_review_edit.html
# =========================
@admin_bp.route("/admin/reviews/edit/<int:review_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_review(review_id):
    review = get_admin_review_by_id(review_id)

    # 없는 리뷰면 목록으로 이동
    if not review:
        flash("리뷰를 찾을 수 없습니다.")
        return redirect(url_for("admin.admin_review_restaurants"))

    # 수정 저장
    if request.method == "POST":
        rating = request.form.get("rating", "").strip()
        content = request.form.get("content", "").strip()

        # 입력값 검증
        if not rating or not content:
            flash("평점과 내용을 모두 입력해주세요.")
            return render_template("admin/admin_review_edit.html", review=review)

        # 평점 숫자 변환
        try:
            rating = int(rating)
        except ValueError:
            flash("평점은 숫자로 입력해주세요.")
            return render_template("admin/admin_review_edit.html", review=review)

        # 평점 범위 체크
        if rating < 1 or rating > 5:
            flash("평점은 1점부터 5점까지 입력할 수 있습니다.")
            return render_template("admin/admin_review_edit.html", review=review)

        success = update_admin_review(review_id, rating, content)

        if success:
            flash("리뷰가 수정되었습니다.")
        else:
            flash("리뷰 수정에 실패했습니다.")

        return redirect(url_for("admin.admin_review_manage", restaurant_id=review["restaurant_id"]))

    # GET 요청이면 수정 화면
    return render_template("admin/admin_review_edit.html", review=review)


# =========================
# 관리자 리뷰 관리 - 리뷰 숨김
# 설명:
# - status를 HIDDEN으로 변경
# =========================
@admin_bp.route("/admin/reviews/hide/<int:review_id>", methods=["POST"])
@admin_required
def admin_hide_review(review_id):
    review = get_admin_review_by_id(review_id)

    if not review:
        flash("리뷰를 찾을 수 없습니다.")
        return redirect(url_for("admin.admin_review_restaurants"))

    success = hide_admin_review(review_id)

    if success:
        flash("리뷰를 숨김 처리했습니다.")
    else:
        flash("리뷰 숨김 처리에 실패했습니다.")

    return redirect(url_for("admin.admin_review_manage", restaurant_id=review["restaurant_id"]))


# =========================
# 관리자 리뷰 관리 - 리뷰 삭제(소프트 삭제)
# 설명:
# - 실제 DELETE가 아니라 status를 DELETED로 변경
# =========================
@admin_bp.route("/admin/reviews/delete/<int:review_id>", methods=["POST"])
@admin_required
def admin_delete_review(review_id):
    review = get_admin_review_by_id(review_id)

    if not review:
        flash("리뷰를 찾을 수 없습니다.")
        return redirect(url_for("admin.admin_review_restaurants"))

    success = soft_delete_admin_review(review_id)

    if success:
        flash("리뷰를 삭제 처리했습니다.")
    else:
        flash("리뷰 삭제 처리에 실패했습니다.")

    return redirect(url_for("admin.admin_review_manage", restaurant_id=review["restaurant_id"]))


# =========================
# 관리자 리뷰 관리 - 리뷰 복구
# 설명:
# - HIDDEN / DELETED -> ACTIVE
# =========================
@admin_bp.route("/admin/reviews/restore/<int:review_id>", methods=["POST"])
@admin_required
def admin_restore_review(review_id):
    review = get_admin_review_by_id(review_id)

    if not review:
        flash("리뷰를 찾을 수 없습니다.")
        return redirect(url_for("admin.admin_review_restaurants"))

    success = restore_admin_review(review_id)

    if success:
        flash("리뷰를 복구했습니다.")
    else:
        flash("리뷰 복구에 실패했습니다.")

    return redirect(url_for("admin.admin_review_manage", restaurant_id=review["restaurant_id"]))

# =========================
# 관리자 페이지
# =========================
@admin_bp.route("/admin")
@admin_required
def admin_page():
    return render_template("admin/admin_dashboard.html")


# =========================
# 관리자 회원 관리
# =========================
@admin_bp.route("/admin/users")
@admin_required
def admin_users():
    users = fetch_all_users()
    return render_template("admin/admin_users.html", users=users)


# =========================
# 관리자 회원 비활성화
# =========================
@admin_bp.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def admin_user_deactivate(user_id):
    admin_deactivate_user(user_id)
    flash("회원 상태를 DELETED로 변경했습니다.")
    return redirect(url_for("admin.admin_users"))


# =========================
# 관리자 회원 복구
# =========================
@admin_bp.route("/admin/users/<int:user_id>/restore", methods=["POST"])
@admin_required
def admin_user_restore(user_id):
    admin_restore_user(user_id)
    flash("회원 상태를 ACTIVE로 복구했습니다.")
    return redirect(url_for("admin.admin_users"))


# =========================
# 관리자 신고 / 제재 통합 관리
# =========================
@admin_bp.route("/admin/moderation", methods=["GET", "POST"])
@admin_required
def admin_moderation():
    if request.method == "POST":
        user_nickname = request.form.get("user_nickname", "").strip()
        sanction_type = request.form.get("sanction_type", "").strip()
        reason = request.form.get("reason", "").strip()
        expire_at = request.form.get("expire_at", "").strip()

        if not user_nickname or not sanction_type or not reason:
            flash("대상 닉네임, 제재 종류, 사유를 입력해주세요.")
            return redirect(url_for("admin.admin_moderation"))

        create_admin_sanction(
            user_nickname=user_nickname,
            sanction_type=sanction_type,
            reason=reason,
            expire_at=expire_at if expire_at else "-"
        )
        flash("제재가 등록되었습니다.")
        return redirect(url_for("admin.admin_moderation"))

    report_keyword = request.args.get("report_keyword", "").strip()
    report_status = request.args.get("report_status", "").strip()

    sanction_keyword = request.args.get("sanction_keyword", "").strip()
    sanction_status = request.args.get("sanction_status", "").strip()

    reports = fetch_admin_reports(keyword=report_keyword, status=report_status)
    sanctions = fetch_admin_sanctions(keyword=sanction_keyword, status=sanction_status)

    return render_template(
        "admin/admin_moderation.html",
        reports=reports,
        sanctions=sanctions,
        report_keyword=report_keyword,
        report_status=report_status,
        sanction_keyword=sanction_keyword,
        sanction_status=sanction_status,
    )


# =========================
# 관리자 신고 관리 목록
# =========================
@admin_bp.route("/admin/reports")
@admin_required
def admin_reports():
    return redirect(url_for("admin.admin_moderation"))


# =========================
# 신고 승인 처리
# =========================
@admin_bp.route("/admin/reports/<int:report_id>/resolve", methods=["POST"])
@admin_required
def admin_resolve_report(report_id):
    success = update_admin_report_status(report_id, "RESOLVED")
    if success:
        flash("신고를 처리 완료 상태로 변경했습니다.")
    else:
        flash("신고 내역을 찾을 수 없습니다.")
    return redirect(url_for("admin.admin_moderation"))


# =========================
# 신고 반려 처리
# =========================
@admin_bp.route("/admin/reports/<int:report_id>/reject", methods=["POST"])
@admin_required
def admin_reject_report(report_id):
    success = update_admin_report_status(report_id, "REJECTED")
    if success:
        flash("신고를 반려 처리했습니다.")
    else:
        flash("신고 내역을 찾을 수 없습니다.")
    return redirect(url_for("admin.admin_moderation"))


# =========================
# 관리자 제재 관리
# =========================
@admin_bp.route("/admin/sanctions", methods=["GET", "POST"])
@admin_required
def admin_sanctions():
    return redirect(url_for("admin.admin_moderation"))


# =========================
# 제재 해제
# =========================
@admin_bp.route("/admin/sanctions/<int:sanction_id>/release", methods=["POST"])
@admin_required
def admin_release_sanction(sanction_id):
    success = release_admin_sanction(sanction_id)
    if success:
        flash("제재를 해제했습니다.")
    else:
        flash("제재 내역을 찾을 수 없습니다.")
    return redirect(url_for("admin.admin_moderation"))

# =========================
# 관리자 판매자 신청 목록
# - restaurants_request 기준
# - user_id, restaurant_id 같이 화면에 전달
# =========================
# =========================
# 관리자 판매자 신청 목록
# - restaurants_request 기준
# =========================
@admin_bp.route("/admin/seller-requests", methods=["GET"])
@admin_required
def admin_seller_requests():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "PENDING").strip()

    items = fetch_admin_restaurant_requests(keyword=keyword, status=status)

    return render_template(
        "admin/admin_seller_requests.html",
        items=items,
        keyword=keyword,
        status=status,
    )

# =========================
# 관리자 판매자 신청 승인
# - request_id 기준으로 승인
# =========================

@admin_bp.route("/admin/seller-requests/<int:request_id>/approve", methods=["POST"])
@admin_required
def approve_seller_request(request_id):
    success, message = approve_restaurant_request(request_id)
    flash(message)
    return redirect(url_for("admin.admin_seller_requests"))

# =========================
# 관리자 판매자 신청 반려
# - request_id 기준으로 반려
# =========================
@admin_bp.route("/admin/seller-requests/<int:request_id>/reject", methods=["POST"])
@admin_required
def reject_seller_request(request_id):
    success, message = reject_restaurant_request(request_id)
    flash(message)
    return redirect(url_for("admin.admin_seller_requests"))


# =========================
# 관리자 오너 목록
# =========================
@admin_bp.route("/admin/owners", methods=["GET"])
@admin_required
def admin_owners():
    keyword = request.args.get("keyword", "").strip()
    owners = fetch_admin_owners(keyword=keyword)

    return render_template(
        "admin/admin_owners.html",
        owners=owners,
        keyword=keyword,
    )