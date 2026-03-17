import os
import pymysql
from dotenv import load_dotenv
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import uuid

load_dotenv()


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database="bwlog",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


# ====================================================================================
# owner_board.html
# ------------------------------------------------------------------------------------
# 오너보드 공지사항 DB 처리 요약
# ------------------------------------------------------------------------------------
# 1. 오너가 여러 식당을 가질 수 있으므로 restaurant_id 기준으로 사이드 공지 카드를 조회한다.
# 2. 현재 공지 카드는 is_pinned = 1 인 공지 중 updated_at 이 가장 최근인 1건을 조회한다.
# 3. 이전 공지 카드는 is_pinned = 0 인 공지 중 updated_at 최신순 3건만 조회한다.
# 4. 날짜 출력은 보드 카드에서 바로 쓰기 쉽게 문자열로 가공한다.
# ====================================================================================

# 전달받는 값
# - owner_id: 오너 번호
# 반환값
# - 해당 오너가 가진 식당 목록
def get_restaurant_list_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    restaurant_id,
                    name,
                    status
                FROM restaurants
                WHERE owner_id = %s
                ORDER BY restaurant_id ASC
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchall()
    finally:
        conn.close()


# 전달받는 값
# - restaurant_id: 식당 번호
# 반환값
# - 현재 고정 공지 1건
def get_sidebar_current_notice_by_restaurant(restaurant_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    notice_id,
                    owner_id,
                    restaurant_id,
                    user_id,
                    notice_url,
                    thumb_url,
                    notice_title,
                    notice_content,
                    is_pinned,
                    created_at,
                    updated_at
                FROM owner_notices
                WHERE restaurant_id = %s
                  AND is_pinned = 1
                ORDER BY updated_at DESC, notice_id DESC
                LIMIT 1
            """
            cursor.execute(sql, (restaurant_id,))
            return cursor.fetchone()
    finally:
        conn.close()


# 전달받는 값
# - restaurant_id: 식당 번호
# 반환값
# - 이전 공지 3건
def get_sidebar_history_notice_list_by_restaurant(restaurant_id, limit=3):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    notice_id,
                    owner_id,
                    restaurant_id,
                    user_id,
                    notice_url,
                    thumb_url,
                    notice_title,
                    notice_content,
                    is_pinned,
                    created_at,
                    updated_at
                FROM owner_notices
                WHERE restaurant_id = %s
                  AND is_pinned = 0
                ORDER BY updated_at DESC, notice_id DESC
                LIMIT %s
            """
            cursor.execute(sql, (restaurant_id, limit))
            return cursor.fetchall()
    finally:
        conn.close()


# 전달받는 값
# - restaurant_id: 식당 번호
# 반환값
# - 최근 10일 방문자 차트 데이터
def get_visit_chart_by_restaurant(restaurant_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    DATE(visited_at) AS visit_date,
                    COUNT(*) AS visit_count
                FROM visits
                WHERE restaurant_id = %s
                  AND visited_at >= DATE_SUB(CURDATE(), INTERVAL 9 DAY)
                  AND visited_at < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
                GROUP BY DATE(visited_at)
                ORDER BY visit_date ASC
            """
            cursor.execute(sql, (restaurant_id,))
            db_rows = cursor.fetchall()
    finally:
        conn.close()

    db_map = {}
    for row in db_rows:
        visit_date = row["visit_date"]
        if hasattr(visit_date, "strftime"):
            visit_date = visit_date.strftime("%Y-%m-%d")
        db_map[visit_date] = int(row["visit_count"])

    today = datetime.now().date()
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

    chart_list = []
    for diff in range(9, -1, -1):
        target_date = today - timedelta(days=diff)
        target_date_str = target_date.strftime("%Y-%m-%d")

        chart_list.append({
            "date": target_date_str,
            "label": target_date.strftime("%m/%d"),
            "weekday": weekday_names[target_date.weekday()],
            "visit_count": db_map.get(target_date_str, 0)
        })

    return chart_list

def allowed_file(filename):
    if "." not in filename:
        return False

    ext = filename.rsplit(".", 1)[1].lower()
    return ext in {"jpg", "jpeg", "png", "gif", "webp"}


def get_store_image_url_by_restaurant(restaurant_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT image_url
                FROM restaurant_images
                WHERE restaurant_id = %s
                ORDER BY sort_order ASC, image_id DESC
                LIMIT 1
            """
            cursor.execute(sql, (restaurant_id,))
            row = cursor.fetchone()
            return row["image_url"] if row and row.get("image_url") else None
    finally:
        conn.close()


def save_store_image(restaurant_id, image_file):
    if not image_file or not image_file.filename:
        raise ValueError("이미지 파일이 없습니다.")

    if not allowed_file(image_file.filename):
        raise ValueError("허용 확장자: jpg, jpeg, png, gif, webp")

    upload_dir = os.path.join("static", "uploads", "restaurant")
    os.makedirs(upload_dir, exist_ok=True)

    original_name = secure_filename(image_file.filename)
    ext = original_name.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"

    save_path = os.path.join(upload_dir, stored_name)
    image_file.save(save_path)

    image_url = f"/static/uploads/restaurant/{stored_name}"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_sort
                FROM restaurant_images
                WHERE restaurant_id = %s
            """, (restaurant_id,))
            row = cursor.fetchone()
            next_sort_order = int(row["next_sort"]) if row and row["next_sort"] is not None else 1

            cursor.execute("""
                INSERT INTO restaurant_images (
                    restaurant_id,
                    image_url,
                    thumb_url,
                    original_name,
                    stored_name,
                    sort_order,
                    created_at,
                    menu_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NULL)
            """, (
                restaurant_id,
                image_url,
                image_url,
                original_name,
                stored_name,
                next_sort_order
            ))

        conn.commit()
        return image_url

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()