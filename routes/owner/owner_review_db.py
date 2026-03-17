# routes/owner/owner_review_db.py

import os
import uuid
import pymysql
from dotenv import load_dotenv
from PIL import Image


load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

NOTICE_IMAGE_DIR = os.path.join(PROJECT_DIR, "static", "img", "owner_notic_img")
NOTICE_THUMB_DIR = os.path.join(PROJECT_DIR, "static", "img", "owner_notic_img", "thumbs")

os.makedirs(NOTICE_IMAGE_DIR, exist_ok=True)
os.makedirs(NOTICE_THUMB_DIR, exist_ok=True)

ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
THUMB_MAX_SIZE = (300, 300)


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
# owner_review_management.html
# ===================================================================================

# ====================================================================================
# 공통 조회
# ====================================================================================
def get_restaurant_list_by_owner(session_owner_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            restaurant_id,
            name
        FROM restaurants
        WHERE owner_id = %s
          AND status != 'DELETED'
        ORDER BY restaurant_id ASC
    """
    db_cursor.execute(sql, (session_owner_id,))
    db_restaurant_list = db_cursor.fetchall()

    db_cursor.close()
    db_conn.close()
    return db_restaurant_list


def get_owner_info(session_owner_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            owner_id,
            email,
            owner_name,
            phone,
            business_number,
            status,
            created_at,
            updated_at
        FROM owners
        WHERE owner_id = %s
        LIMIT 1
    """
    db_cursor.execute(sql, (session_owner_id,))
    db_owner = db_cursor.fetchone()

    db_cursor.close()
    db_conn.close()
    return db_owner


def get_restaurant_name_by_restaurant_id(db_restaurant_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            name
        FROM restaurants
        WHERE restaurant_id = %s
        LIMIT 1
    """
    db_cursor.execute(sql, (db_restaurant_id,))
    db_row = db_cursor.fetchone()

    db_cursor.close()
    db_conn.close()

    if db_row:
        return db_row["name"]
    return ""


# ====================================================================================
# 리뷰 요약 카드
# ====================================================================================
def get_review_summary_by_restaurant(db_restaurant_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            COUNT(rv.review_id) AS total_review_count,
            SUM(
                CASE
                    WHEN IFNULL(ror.is_active, 0) = 0
                     AND IFNULL(ror.is_visible, 1) = 1
                    THEN 1
                    ELSE 0
                END
            ) AS pending_review_count,
            SUM(
                CASE
                    WHEN ror.is_active = 1
                     AND ror.is_visible = 1
                    THEN 1
                    ELSE 0
                END
            ) AS done_review_count,
            SUM(
                CASE
                    WHEN IFNULL(ror.is_visible, 1) = 0
                    THEN 1
                    ELSE 0
                END
            ) AS hidden_review_count
        FROM reviews rv
        INNER JOIN visits vs
            ON rv.visit_id = vs.visit_id
        LEFT JOIN review_owner_replies ror
            ON rv.review_id = ror.review_id
        WHERE vs.restaurant_id = %s
          AND rv.status = 'ACTIVE'
          AND rv.deleted_at IS NULL
    """
    db_cursor.execute(sql, (db_restaurant_id,))
    db_summary = db_cursor.fetchone()

    db_cursor.close()
    db_conn.close()

    if not db_summary:
        return {
            "total_review_count": 0,
            "pending_review_count": 0,
            "done_review_count": 0,
            "hidden_review_count": 0
        }

    return {
        "total_review_count": int(db_summary["total_review_count"] or 0),
        "pending_review_count": int(db_summary["pending_review_count"] or 0),
        "done_review_count": int(db_summary["done_review_count"] or 0),
        "hidden_review_count": int(db_summary["hidden_review_count"] or 0)
    }


# - 추가: 오너보드 mini-stat-card에서 3월 리뷰 수만 count(*) 조회
def get_march_review_count_by_restaurant(db_restaurant_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            COUNT(rv.review_id) AS march_review_count
        FROM reviews rv
        INNER JOIN visits vs
            ON rv.visit_id = vs.visit_id
        WHERE vs.restaurant_id = %s
          AND rv.status = 'ACTIVE'
          AND rv.deleted_at IS NULL
          AND MONTH(rv.created_at) = 3
    """
    db_cursor.execute(sql, (db_restaurant_id,))
    db_row = db_cursor.fetchone()

    db_cursor.close()
    db_conn.close()

    if not db_row:
        return 0
    return int(db_row["march_review_count"] or 0)


# - 추가: 오너보드 review-card에서 restaurant_id 기준 리뷰 5개 미리보기 조회
# - users.profile_image_url, users.nickname, reviews.rating, reviews.content 사용
def get_board_review_list_by_restaurant(db_restaurant_id, limit=5):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            rv.review_id,
            rv.rating,
            rv.content,
            rv.created_at,
            rv.updated_at,
            vs.restaurant_id,
            us.user_id,
            us.nickname,
            us.profile_image_url
        FROM reviews rv
        INNER JOIN visits vs
            ON rv.visit_id = vs.visit_id
        INNER JOIN users us
            ON rv.user_id = us.user_id
        WHERE vs.restaurant_id = %s
          AND rv.status = 'ACTIVE'
          AND rv.deleted_at IS NULL
        ORDER BY rv.updated_at DESC, rv.review_id DESC
        LIMIT %s
    """
    db_cursor.execute(sql, (db_restaurant_id, limit))
    db_review_list = db_cursor.fetchall()

    db_cursor.close()
    db_conn.close()
    return db_review_list


# - 추가: 오너보드 리뷰 카드용 데이터 조합
def get_board_review_summary_by_restaurant(db_restaurant_id, limit=5):
    db_review_list = get_board_review_list_by_restaurant(db_restaurant_id, limit=limit)

    review_list = []
    for db_review in db_review_list:
        db_review_id = int(db_review["review_id"])

        review_list.append({
            "review_id": db_review_id,
            "restaurant_id": int(db_review["restaurant_id"]),
            "nickname": db_review["nickname"] or "",
            "profile_image_url": db_review["profile_image_url"] or "",
            "rating": int(db_review["rating"]) if db_review["rating"] is not None else 0,
            "rating_text": "★" * int(db_review["rating"] or 0) + "☆" * (5 - int(db_review["rating"] or 0)),
            "content": db_review["content"] or "",
            "created_at": db_review["created_at"].strftime("%Y-%m-%d") if db_review["created_at"] else "",
            "updated_at": db_review["updated_at"].strftime("%Y-%m-%d") if db_review["updated_at"] else "",
            "review_page": get_review_page_by_review_id(
                db_restaurant_id=db_restaurant_id,
                db_review_id=db_review_id,
                client_tab_status="all",
                client_sort_type="latest",
                client_search_keyword="",
                per_page=5
            )
        })

    return {
        "march_review_count": get_march_review_count_by_restaurant(db_restaurant_id),
        "review_list": review_list
    }

# ====================================================================================
# 리뷰 목록 조건
# ====================================================================================
def build_review_where_sql(client_tab_status, client_search_keyword):
    db_where_sql = """
        WHERE vs.restaurant_id = %s
          AND rv.status = 'ACTIVE'
          AND rv.deleted_at IS NULL
    """
    db_where_params = []

    if client_tab_status == "pending":
        db_where_sql += """
          AND IFNULL(ror.is_active, 0) = 0
          AND IFNULL(ror.is_visible, 1) = 1
        """
    elif client_tab_status == "done":
        db_where_sql += """
          AND ror.is_active = 1
          AND ror.is_visible = 1
        """
    elif client_tab_status == "hidden":
        db_where_sql += """
          AND IFNULL(ror.is_visible, 1) = 0
        """

    if client_search_keyword:
        db_where_sql += """
          AND (
                us.nickname LIKE %s
             OR rv.content LIKE %s
             OR IFNULL(ror.reply_content, '') LIKE %s
          )
        """
        db_like_keyword = f"%{client_search_keyword}%"
        db_where_params.extend([db_like_keyword, db_like_keyword, db_like_keyword])

    return db_where_sql, db_where_params


def build_review_order_sql(client_sort_type):
    if client_sort_type == "rating":
        return " ORDER BY rv.rating DESC, rv.updated_at DESC, rv.review_id DESC "
    return " ORDER BY rv.updated_at DESC, rv.review_id DESC "


# ====================================================================================
# 리뷰 목록 개수
# ====================================================================================
def get_review_count_by_restaurant(
    db_restaurant_id,
    client_tab_status="all",
    client_search_keyword=""
):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    db_where_sql, db_where_params = build_review_where_sql(
        client_tab_status,
        client_search_keyword
    )

    sql = f"""
        SELECT
            COUNT(rv.review_id) AS total_count
        FROM reviews rv
        INNER JOIN visits vs
            ON rv.visit_id = vs.visit_id
        INNER JOIN users us
            ON rv.user_id = us.user_id
        LEFT JOIN review_owner_replies ror
            ON rv.review_id = ror.review_id
        {db_where_sql}
    """

    db_params = [db_restaurant_id] + db_where_params
    db_cursor.execute(sql, tuple(db_params))
    db_row = db_cursor.fetchone()

    db_cursor.close()
    db_conn.close()

    if not db_row:
        return 0
    return int(db_row["total_count"] or 0)


# ====================================================================================
# 리뷰 목록 조회
# ====================================================================================
def get_review_list_by_restaurant(
    db_restaurant_id,
    client_tab_status="all",
    client_sort_type="latest",
    client_search_keyword="",
    limit=5,
    offset=0
):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    db_where_sql, db_where_params = build_review_where_sql(
        client_tab_status,
        client_search_keyword
    )
    db_order_sql = build_review_order_sql(client_sort_type)

    sql = f"""
        SELECT
            rv.review_id,
            rv.visit_id,
            rv.rating,
            rv.content,
            rv.created_at,
            rv.updated_at,
            rv.user_id,
            us.nickname,
            us.profile_image_url,
            ror.reply_id,
            ror.reply_content,
            ror.is_active,
            ror.is_visible,
            ror.created_at AS reply_created_at,
            ror.updated_at AS reply_updated_at
        FROM reviews rv
        INNER JOIN visits vs
            ON rv.visit_id = vs.visit_id
        INNER JOIN users us
            ON rv.user_id = us.user_id
        LEFT JOIN review_owner_replies ror
            ON rv.review_id = ror.review_id
        {db_where_sql}
        {db_order_sql}
        LIMIT %s OFFSET %s
    """

    db_params = [db_restaurant_id] + db_where_params + [limit, offset]
    db_cursor.execute(sql, tuple(db_params))
    db_review_list = db_cursor.fetchall()

    db_cursor.close()
    db_conn.close()
    return db_review_list


# - 추가: 오너보드 review-card 클릭 시 리뷰관리페이지에서 해당 리뷰가 있는 페이지 계산
def get_review_page_by_review_id(
    db_restaurant_id,
    db_review_id,
    client_tab_status="all",
    client_sort_type="latest",
    client_search_keyword="",
    per_page=5
):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    db_where_sql, db_where_params = build_review_where_sql(
        client_tab_status,
        client_search_keyword
    )
    db_order_sql = build_review_order_sql(client_sort_type)

    sql = f"""
        SELECT
            rv.review_id
        FROM reviews rv
        INNER JOIN visits vs
            ON rv.visit_id = vs.visit_id
        INNER JOIN users us
            ON rv.user_id = us.user_id
        LEFT JOIN review_owner_replies ror
            ON rv.review_id = ror.review_id
        {db_where_sql}
        {db_order_sql}
    """

    db_params = [db_restaurant_id] + db_where_params
    db_cursor.execute(sql, tuple(db_params))
    db_review_id_list = [int(row["review_id"]) for row in db_cursor.fetchall()]

    db_cursor.close()
    db_conn.close()

    if int(db_review_id) not in db_review_id_list:
        return 1

    db_index = db_review_id_list.index(int(db_review_id))
    return (db_index // per_page) + 1


# ====================================================================================
# 리뷰 상세 조회
# ====================================================================================
def get_review_detail_by_review_id(db_restaurant_id, db_review_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            rv.review_id,
            rv.visit_id,
            rv.rating,
            rv.content,
            rv.created_at,
            rv.updated_at,
            rv.user_id,
            us.nickname,
            us.profile_image_url,
            vs.restaurant_id,
            ror.reply_id,
            ror.owner_id,
            ror.reply_content,
            ror.is_active,
            ror.is_visible,
            ror.created_at AS reply_created_at,
            ror.updated_at AS reply_updated_at
        FROM reviews rv
        INNER JOIN visits vs
            ON rv.visit_id = vs.visit_id
        INNER JOIN users us
            ON rv.user_id = us.user_id
        LEFT JOIN review_owner_replies ror
            ON rv.review_id = ror.review_id
        WHERE vs.restaurant_id = %s
          AND rv.review_id = %s
          AND rv.status = 'ACTIVE'
          AND rv.deleted_at IS NULL
        LIMIT 1
    """
    db_cursor.execute(sql, (db_restaurant_id, db_review_id))
    db_review = db_cursor.fetchone()

    db_cursor.close()
    db_conn.close()
    return db_review


# ====================================================================================
# 답변 존재 여부
# ====================================================================================
def exists_owner_reply_by_review_id(db_review_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    sql = """
        SELECT
            reply_id
        FROM review_owner_replies
        WHERE review_id = %s
        LIMIT 1
    """
    db_cursor.execute(sql, (db_review_id,))
    db_row = db_cursor.fetchone()

    db_cursor.close()
    db_conn.close()
    return db_row is not None


# ====================================================================================
# 답변 등록
# ====================================================================================
def insert_owner_reply(db_review_id, session_owner_id, db_restaurant_id, client_reply_content):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    try:
        sql = """
            INSERT INTO review_owner_replies (
                review_id,
                owner_id,
                restaurant_id,
                reply_content,
                is_active,
                is_visible
            )
            VALUES (%s, %s, %s, %s, 1, 1)
        """
        db_cursor.execute(
            sql,
            (db_review_id, session_owner_id, db_restaurant_id, client_reply_content)
        )
        db_conn.commit()
        db_reply_id = db_cursor.lastrowid

        db_cursor.close()
        db_conn.close()
        return db_reply_id
    except Exception:
        db_conn.rollback()
        db_cursor.close()
        db_conn.close()
        raise


# ====================================================================================
# 답변 수정
# ====================================================================================
def update_owner_reply(db_review_id, session_owner_id, db_restaurant_id, client_reply_content):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    try:
        sql = """
            UPDATE review_owner_replies
            SET reply_content = %s,
                owner_id = %s,
                restaurant_id = %s,
                is_active = 1,
                is_visible = 1
            WHERE review_id = %s
        """
        db_cursor.execute(
            sql,
            (client_reply_content, session_owner_id, db_restaurant_id, db_review_id)
        )
        db_conn.commit()

        db_cursor.close()
        db_conn.close()
    except Exception:
        db_conn.rollback()
        db_cursor.close()
        db_conn.close()
        raise


# ====================================================================================
# 답변 삭제
# ====================================================================================
def delete_owner_reply(db_review_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    try:
        sql = """
            UPDATE review_owner_replies
            SET reply_content = '',
                is_active = 0,
                is_visible = 1
            WHERE review_id = %s
        """
        db_cursor.execute(sql, (db_review_id,))
        db_conn.commit()

        db_cursor.close()
        db_conn.close()
    except Exception:
        db_conn.rollback()
        db_cursor.close()
        db_conn.close()
        raise


# ====================================================================================
# 리뷰 숨김
# ====================================================================================
def hide_review_reply(db_review_id):
    db_conn = get_connection()
    db_cursor = db_conn.cursor()

    try:
        sql = """
            UPDATE review_owner_replies
            SET is_visible = 0,
                is_active = 0
            WHERE review_id = %s
        """
        db_cursor.execute(sql, (db_review_id,))
        db_conn.commit()

        db_cursor.close()
        db_conn.close()
    except Exception:
        db_conn.rollback()
        db_cursor.close()
        db_conn.close()
        raise