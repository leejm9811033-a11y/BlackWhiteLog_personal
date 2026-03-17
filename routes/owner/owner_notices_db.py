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
# owner_notice_management.html
# ------------------------------------------------------------------------------------
# 공지사항 관리 DB 처리 요약
# ------------------------------------------------------------------------------------
# 1. 공지사항은 owner_id 단독이 아니라 restaurant_id 기준으로 조회/수정/삭제한다.
# 2. 오너는 여러 식당을 가질 수 있으므로, 라우트에서 선택된 restaurant_id를 받아 사용한다.
# 3. 이미지 파일은 static/img/owner_notic_img 에 저장하고 DB에는 경로만 저장한다.
# 4. 썸네일은 static/img/owner_notic_img/thumbs 에 저장한다.
# 5. 목록/상세/등록/수정/삭제에 필요한 DB 함수를 분리해서 중복 쿼리를 줄인다.
# ====================================================================================


# 전달받는 값
# - filename: 업로드한 파일명
# 반환값
# - 허용 확장자 여부
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# 전달받는 값
# - stored_name: 서버에 저장된 실제 파일명
# 반환값
# - static 기준 원본 이미지 상대경로
def build_notice_image_rel_path(stored_name):
    return f"img/owner_notic_img/{stored_name}"


# 전달받는 값
# - stored_name: 서버에 저장된 실제 파일명
# 반환값
# - static 기준 썸네일 이미지 상대경로
def build_notice_thumb_rel_path(stored_name):
    return f"img/owner_notic_img/thumbs/{stored_name}"


# 전달받는 값
# - src_abs: 원본 이미지 절대경로
# - thumb_abs: 썸네일 저장 절대경로
# 반환값
# - 없음
def make_thumbnail(src_abs, thumb_abs):
    ext = os.path.splitext(thumb_abs)[1].lower()

    with Image.open(src_abs) as image:
        image.thumbnail(THUMB_MAX_SIZE)

        if ext in [".jpg", ".jpeg"]:
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode == "P":
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            image.save(thumb_abs, format="JPEG", quality=90)
        else:
            image.save(thumb_abs)


# 전달받는 값
# - image_file: 업로드 이미지 파일 객체
# 반환값
# - notice_url, thumb_url 딕셔너리
def save_notice_image_file(image_file):
    raw_name = (image_file.filename or "").strip()

    if not raw_name or "." not in raw_name:
        raise ValueError("확장자가 있는 이미지 파일만 업로드할 수 있습니다.")

    ext = raw_name.rsplit(".", 1)[1].lower()

    if ext not in ALLOWED_EXT:
        raise ValueError("허용되지 않은 이미지 확장자입니다.")

    stored_name = f"{uuid.uuid4().hex}.{ext}"

    image_abs_path = os.path.join(NOTICE_IMAGE_DIR, stored_name)
    thumb_abs_path = os.path.join(NOTICE_THUMB_DIR, stored_name)

    image_file.save(image_abs_path)
    make_thumbnail(image_abs_path, thumb_abs_path)

    print("notice_image_abs_path =", image_abs_path)
    print("notice_thumb_abs_path =", thumb_abs_path)

    return {
        "notice_url": build_notice_image_rel_path(stored_name),
        "thumb_url": build_notice_thumb_rel_path(stored_name)
    }


# 전달받는 값
# - rel_path: static 기준 상대경로
# 반환값
# - 없음
def safe_remove_file(rel_path):
    if not rel_path:
        return

    abs_path = os.path.join(PROJECT_DIR, "static", rel_path)

    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except Exception:
        pass


# 전달받는 값
# - owner_id: 오너 번호
# 반환값
# - 해당 오너가 가진 식당 목록
def get_restaurant_list_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT restaurant_id, name, status
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
# - 공지 개수
def get_notice_count_by_restaurant(restaurant_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT COUNT(*) AS cnt
                FROM owner_notices
                WHERE restaurant_id = %s
            """
            cursor.execute(sql, (restaurant_id,))
            row = cursor.fetchone()
            return row["cnt"] if row else 0
    finally:
        conn.close()


# 전달받는 값
# - restaurant_id: 식당 번호
# - limit: 페이지당 개수
# - offset: 시작 위치
# 반환값
# - 공지 목록
def get_notice_list_by_restaurant(restaurant_id, limit=None, offset=None):
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
                ORDER BY is_pinned DESC, notice_id DESC
            """
            params = [restaurant_id]

            if limit is not None and offset is not None:
                sql += " LIMIT %s OFFSET %s"
                params.extend([limit, offset])

            cursor.execute(sql, tuple(params))
            return cursor.fetchall()
    finally:
        conn.close()


# 전달받는 값
# - restaurant_id: 식당 번호
# - notice_id: 공지 번호
# 반환값
# - 공지 1건
def get_notice_detail_by_id(restaurant_id, notice_id):
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
                AND notice_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (restaurant_id, notice_id))
            return cursor.fetchone()
    finally:
        conn.close()


# 전달받는 값
# - cursor: 현재 DB 커서
# - restaurant_id: 식당 번호
# - exclude_notice_id: 제외할 공지 번호
# 반환값
# - 없음
def clear_pinned_notice_by_restaurant(cursor, restaurant_id, exclude_notice_id=None):
    sql = """
        UPDATE owner_notices
        SET is_pinned = 0
        WHERE restaurant_id = %s
        AND is_pinned = 1
    """
    params = [restaurant_id]

    if exclude_notice_id is not None:
        sql += " AND notice_id <> %s"
        params.append(exclude_notice_id)

    cursor.execute(sql, tuple(params))


# 전달받는 값
# - owner_id: 오너 번호
# - restaurant_id: 식당 번호
# - user_id: 작성자 유저 번호
# - notice_title: 공지 제목
# - notice_content: 공지 내용
# - is_pinned: 상단 고정 여부
# - image_file: 업로드 파일
# 반환값
# - 저장된 notice_id
def insert_notice(
    owner_id,
    restaurant_id,
    user_id,
    notice_title,
    notice_content,
    is_pinned=0,
    image_file=None
):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            notice_url = None
            thumb_url = None

            if image_file and image_file.filename:
                image_data = save_notice_image_file(image_file)
                notice_url = image_data["notice_url"]
                thumb_url = image_data["thumb_url"]

            if int(is_pinned) == 1:
                clear_pinned_notice_by_restaurant(cursor, restaurant_id)

            sql = """
                INSERT INTO owner_notices
                (
                    owner_id,
                    restaurant_id,
                    user_id,
                    notice_url,
                    thumb_url,
                    notice_title,
                    notice_content,
                    is_pinned
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            cursor.execute(
                sql,
                (
                    owner_id,
                    restaurant_id,
                    user_id,
                    notice_url,
                    thumb_url,
                    notice_title,
                    notice_content,
                    is_pinned
                )
            )
            notice_id = cursor.lastrowid

        conn.commit()
        return notice_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# 전달받는 값
# - restaurant_id: 식당 번호
# - notice_id: 공지 번호
# - notice_title: 수정 제목
# - notice_content: 수정 내용
# - is_pinned: 상단 고정 여부
# - image_file: 새 이미지 파일
# - remove_image: 기존 이미지 삭제 여부
def update_notice(
    restaurant_id,
    notice_id,
    notice_title,
    notice_content,
    is_pinned=0,
    image_file=None,
    remove_image=False
):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            db_notice = get_notice_detail_by_id(restaurant_id, notice_id)

            if not db_notice:
                raise ValueError("공지사항 정보를 찾을 수 없습니다.")

            notice_url = db_notice["notice_url"]
            thumb_url = db_notice["thumb_url"]

            if remove_image:
                safe_remove_file(notice_url)
                safe_remove_file(thumb_url)
                notice_url = None
                thumb_url = None

            if image_file and image_file.filename:
                image_data = save_notice_image_file(image_file)

                if notice_url:
                    safe_remove_file(notice_url)
                if thumb_url:
                    safe_remove_file(thumb_url)

                notice_url = image_data["notice_url"]
                thumb_url = image_data["thumb_url"]

            if int(is_pinned) == 1:
                clear_pinned_notice_by_restaurant(
                    cursor,
                    restaurant_id,
                    exclude_notice_id=notice_id
                )

            sql = """
                UPDATE owner_notices
                SET
                    notice_url = %s,
                    thumb_url = %s,
                    notice_title = %s,
                    notice_content = %s,
                    is_pinned = %s
                WHERE restaurant_id = %s
                AND notice_id = %s
            """
            cursor.execute(
                sql,
                (
                    notice_url,
                    thumb_url,
                    notice_title,
                    notice_content,
                    is_pinned,
                    restaurant_id,
                    notice_id
                )
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# 전달받는 값
# - restaurant_id: 식당 번호
# - notice_id: 공지 번호
def delete_notice(restaurant_id, notice_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            db_notice = get_notice_detail_by_id(restaurant_id, notice_id)

            if not db_notice:
                raise ValueError("삭제할 공지사항 정보를 찾을 수 없습니다.")

            safe_remove_file(db_notice.get("notice_url"))
            safe_remove_file(db_notice.get("thumb_url"))

            sql = """
                DELETE FROM owner_notices
                WHERE restaurant_id = %s
                AND notice_id = %s
            """
            cursor.execute(sql, (restaurant_id, notice_id))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()