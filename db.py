import os
import pymysql
from dotenv import load_dotenv


# 비밀번호 해시 생성 / 비밀번호 검사용
from werkzeug.security import generate_password_hash, check_password_hash

# .env 파일 로드
load_dotenv()


# =========================
# DB 연결 함수
# =========================
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "heukbaeklog"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


# =========================
# 지역 목록 조회
# =========================
def fetch_regions():
    sql = """
        SELECT DISTINCT region_sigungu
        FROM restaurants
        WHERE region_sigungu IS NOT NULL
          AND region_sigungu <> ''
        ORDER BY region_sigungu ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [row["region_sigungu"] for row in rows]
    finally:
        conn.close()


# =========================
# 카테고리 목록 조회
# =========================
def fetch_categories():
    sql = """
        SELECT restaurant_category_id, restaurant_category_name
        FROM restaurant_categories
        ORDER BY restaurant_category_name ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 음식점 목록 조회
# =========================
def fetch_restaurants(region=None, keyword=None, category_id=None, user_id=None, sort_by="visits"):
    """
    sort_by:
      - visits   : 방문수순
      - rating   : 평점순
      - latest   : 최신등록순
    """

    order_by_map = {
        "visits": "visit_count DESC, avg_rating DESC, review_count DESC, r.created_at DESC",
        "rating": "avg_rating DESC, review_count DESC, visit_count DESC, r.created_at DESC",
        "latest": "r.created_at DESC, visit_count DESC, avg_rating DESC",
    }

    order_by = order_by_map.get(sort_by, order_by_map["visits"])

    sql = f"""
        SELECT
            r.restaurant_id,
            r.name,
            r.address,
            r.road_address,
            r.latitude,
            r.longitude,
            r.phone,
            r.business_hours,
            r.description,
            r.region_sido,
            r.region_sigungu,
            r.region_dong,
            r.status,
            r.created_at,
            rc.restaurant_category_name AS category_name,

            COALESCE(vs.visit_count, 0) AS visit_count,
            COALESCE(rv.review_count, 0) AS review_count,
            COALESCE(rv.avg_rating, 0) AS avg_rating,

            CASE
                WHEN uf.favorite_id IS NULL THEN 0
                ELSE 1
            END AS is_favorite,

            CASE
                WHEN uv.restaurant_id IS NULL THEN 0
                ELSE 1
            END AS has_visited,

            (
                SELECT COALESCE(ri.thumb_url, ri.image_url)
                FROM restaurant_images ri
                WHERE ri.restaurant_id = r.restaurant_id
                ORDER BY ri.sort_order ASC, ri.image_id ASC
                LIMIT 1
            ) AS image_url

            FROM restaurants r
            LEFT JOIN user_favorites uf
                ON uf.restaurant_id = r.restaurant_id
            AND uf.user_id = %s

            LEFT JOIN (
                SELECT DISTINCT restaurant_id
                FROM visits
                WHERE user_id = %s
            ) uv
                ON uv.restaurant_id = r.restaurant_id

            LEFT JOIN restaurant_categories rc
                ON r.restaurant_category_id = rc.restaurant_category_id

        LEFT JOIN (
            SELECT restaurant_id, COUNT(*) AS visit_count
            FROM visits
            GROUP BY restaurant_id
        ) vs
            ON r.restaurant_id = vs.restaurant_id

        LEFT JOIN (
            SELECT
                v.restaurant_id,
                COUNT(rv.review_id) AS review_count,
                ROUND(AVG(rv.rating), 1) AS avg_rating
            FROM reviews rv
            INNER JOIN visits v
                ON rv.visit_id = v.visit_id
            WHERE COALESCE(rv.status, 'ACTIVE') = 'ACTIVE'
            GROUP BY v.restaurant_id
        ) rv
            ON r.restaurant_id = rv.restaurant_id

        WHERE 1=1
    """

    effective_user_id = user_id if user_id else 0
    params = [effective_user_id, effective_user_id]

    # 운영 가능한 음식점만 보이게 하는 조건
    sql += " AND (r.status IS NULL OR r.status IN ('OPEN', 'ACTIVE')) "

    # 지역 필터
    if region and region != "전체":
        sql += " AND r.region_sigungu = %s "
        params.append(region)

    # 검색어 필터
    if keyword:
        sql += """
            AND (
                r.name LIKE %s
                OR r.address LIKE %s
                OR r.road_address LIKE %s
                OR r.description LIKE %s
                OR rc.restaurant_category_name LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword] * 5)

    # 카테고리 필터
    if category_id and str(category_id).strip():
        sql += " AND r.restaurant_category_id = %s "
        params.append(category_id)

    # 정렬 + 최대 100개 제한
    sql += f" ORDER BY {order_by} LIMIT 100 "

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            for row in rows:
                row["image_url"] = row["image_url"] or "https://placehold.co/160x120?text=No+Image"
                row["avg_rating"] = float(row["avg_rating"] or 0)
                row["visit_count"] = int(row["visit_count"] or 0)
                row["review_count"] = int(row["review_count"] or 0)
                row["is_favorite"] = bool(row.get("is_favorite", 0))
                row["has_visited"] = bool(row.get("has_visited", 0))

            return rows
    finally:
        conn.close()

## 가게 즐겨찾기 추가 ##
def fetch_favorite_restaurants(user_id, region=None, category_id=None):
    sql = """
        SELECT
            r.restaurant_id,
            r.name,
            r.address,
            r.road_address,
            r.latitude,
            r.longitude,
            r.phone,
            r.business_hours,
            r.description,
            r.region_sido,
            r.region_sigungu,
            r.region_dong,
            r.status,
            r.created_at,
            rc.restaurant_category_name AS category_name,
            uf.created_at AS favorite_created_at,

            COALESCE(vs.visit_count, 0) AS visit_count,
            COALESCE(rv.review_count, 0) AS review_count,
            COALESCE(rv.avg_rating, 0) AS avg_rating,

            CASE
                WHEN uv.restaurant_id IS NULL THEN 0
                ELSE 1
            END AS has_visited,

            (
                SELECT COALESCE(ri.thumb_url, ri.image_url)
                FROM restaurant_images ri
                WHERE ri.restaurant_id = r.restaurant_id
                ORDER BY ri.sort_order ASC, ri.image_id ASC
                LIMIT 1
            ) AS image_url

        FROM user_favorites uf
        INNER JOIN restaurants r
            ON uf.restaurant_id = r.restaurant_id
        LEFT JOIN restaurant_categories rc
            ON r.restaurant_category_id = rc.restaurant_category_id

        LEFT JOIN (
            SELECT DISTINCT restaurant_id
            FROM visits
            WHERE user_id = %s
        ) uv
            ON uv.restaurant_id = r.restaurant_id

        LEFT JOIN (
            SELECT restaurant_id, COUNT(*) AS visit_count
            FROM visits
            GROUP BY restaurant_id
        ) vs
            ON r.restaurant_id = vs.restaurant_id

        LEFT JOIN (
            SELECT
                v.restaurant_id,
                COUNT(rv.review_id) AS review_count,
                ROUND(AVG(rv.rating), 1) AS avg_rating
            FROM reviews rv
            INNER JOIN visits v
                ON rv.visit_id = v.visit_id
            WHERE COALESCE(rv.status, 'ACTIVE') = 'ACTIVE'
            GROUP BY v.restaurant_id
        ) rv
            ON r.restaurant_id = rv.restaurant_id

        WHERE uf.user_id = %s
          AND (r.status IS NULL OR r.status IN ('OPEN', 'ACTIVE'))
    """

    params = [user_id, user_id]

    if region and region != "전체":
        sql += " AND r.region_sigungu = %s "
        params.append(region)

    if category_id and str(category_id).strip():
        sql += " AND r.restaurant_category_id = %s "
        params.append(category_id)

    sql += """
        ORDER BY
            r.region_sigungu ASC,
            rc.restaurant_category_name ASC,
            r.name ASC
        LIMIT 100
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            for row in rows:
                row["image_url"] = row["image_url"] or "https://placehold.co/160x120?text=No+Image"
                row["avg_rating"] = float(row["avg_rating"] or 0)
                row["visit_count"] = int(row["visit_count"] or 0)
                row["review_count"] = int(row["review_count"] or 0)
                row["has_visited"] = bool(row.get("has_visited", 0))

            return rows
    finally:
        conn.close()

def is_favorite_restaurant(user_id, restaurant_id):
    sql = """
        SELECT 1
        FROM user_favorites
        WHERE user_id = %s
          AND restaurant_id = %s
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id, restaurant_id))
            return cursor.fetchone() is not None
    finally:
        conn.close()


def add_favorite_restaurant(user_id, restaurant_id):
    sql = """
        INSERT IGNORE INTO user_favorites (user_id, restaurant_id)
        VALUES (%s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id, restaurant_id))
        conn.commit()
    finally:
        conn.close()


def remove_favorite_restaurant(user_id, restaurant_id):
    sql = """
        DELETE FROM user_favorites
        WHERE user_id = %s
          AND restaurant_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id, restaurant_id))
        conn.commit()
    finally:
        conn.close()


def toggle_favorite_restaurant(user_id, restaurant_id):
    if is_favorite_restaurant(user_id, restaurant_id):
        remove_favorite_restaurant(user_id, restaurant_id)
        return False

    add_favorite_restaurant(user_id, restaurant_id)
    return True

# 판매자 페이지를 이동하는 조건문.
def get_owner_by_user_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT owner_id
        FROM owners
        WHERE user_id = %s
        LIMIT 1
    """
    cursor.execute(sql, (user_id,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row:
        return row["owner_id"]
    return None