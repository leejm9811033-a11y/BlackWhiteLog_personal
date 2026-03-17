import os
import uuid
import pymysql
from PIL import Image
from dotenv import load_dotenv



load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

MENU_IMAGE_DIR = os.path.join(PROJECT_DIR, "static", "img", "owner")
MENU_THUMB_DIR = os.path.join(PROJECT_DIR, "static", "img", "owner", "thumbs")

os.makedirs(MENU_IMAGE_DIR, exist_ok=True)
os.makedirs(MENU_THUMB_DIR, exist_ok=True)

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


#====================================================================================
# owner_menu_management.html
#-------------------------------------------------------------------------------------
# 이미지 파일 처리 - menu_management
#-------------------------------------------------------------------------------------

# 전달받는 값   : filename: 클라이언트가 업로드한 파일명
# 반환값        :  허용 확장자면 True, 아니면 False
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# 전달받는 값   : stored_name: 서버에 저장된 실제 파일명
# 반환값        : static 기준 원본 이미지 상대경로
def build_menu_image_rel_path(stored_name):
    return f"img/owner/{stored_name}"


# 전달받는 값   : stored_name: 서버에 저장된 실제 파일명
# 반환값        :  static 기준 썸네일 이미지 상대경로
def build_menu_thumb_rel_path(stored_name):
    return f"img/owner/thumbs/{stored_name}"


# 전달받는 값
# - src_abs: 원본 이미지 절대경로
# - thumb_abs: 썸네일 저장 절대경로
# 반환값 :   없음
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


# 전달받는 값   : image_file: 클라이언트가 업로드한 이미지 파일 객체
# 반환값        : original_name, stored_name, image_url, thumb_url 딕셔너리
def save_menu_image_file(image_file):
    raw_name = (image_file.filename or "").strip()

    if not raw_name or "." not in raw_name:
        raise ValueError("확장자가 있는 이미지 파일만 업로드할 수 있습니다.")

    ext = raw_name.rsplit(".", 1)[1].lower()

    if ext not in ALLOWED_EXT:
        raise ValueError("허용되지 않은 이미지 확장자입니다.")

    original_name = raw_name
    stored_name = f"{uuid.uuid4().hex}.{ext}"

    image_abs_path = os.path.join(MENU_IMAGE_DIR, stored_name)
    thumb_abs_path = os.path.join(MENU_THUMB_DIR, stored_name)

    image_file.save(image_abs_path)
    make_thumbnail(image_abs_path, thumb_abs_path)
    # 저장경로 확인
    print("image_abs_path =", image_abs_path)
    print("thumb_abs_path =", thumb_abs_path)

    return {
        "original_name": original_name,
        "stored_name": stored_name,
        "image_url": build_menu_image_rel_path(stored_name),
        "thumb_url": build_menu_thumb_rel_path(stored_name)
    }


# 전달받는 값   : rel_path: static 기준 상대경로
# 반환값        : 없음
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
# - cursor: conn.cursor()
# - restaurant_id: DB의 식당 번호
# - menu_id: DB의 메뉴 번호
# 반환값 : restaurant_images 테이블의 대표 이미지 1건
def get_menu_image_by_menu_id(cursor, restaurant_id, menu_id):
    sql = """
        SELECT
            image_id,
            restaurant_id,
            menu_id,
            image_url,
            thumb_url,
            original_name,
            stored_name,
            sort_order,
            created_at
        FROM restaurant_images
        WHERE restaurant_id = %s
        AND menu_id = %s
        ORDER BY sort_order ASC, image_id ASC
        LIMIT 1
    """
    cursor.execute(sql, (restaurant_id, menu_id))
    return cursor.fetchone()


# 전달받는 값
# - cursor: conn.cursor()
# - restaurant_id: DB의 식당 번호
# - menu_id: DB의 메뉴 번호
# - image_data: 저장된 이미지 메타데이터 딕셔너리
# - sort_order: 이미지 정렬 순서
# 반환값 : 없음
def insert_menu_image(cursor, restaurant_id, menu_id, image_data, sort_order=1):
    sql = """
        INSERT INTO restaurant_images
        (
            restaurant_id,
            menu_id,
            image_url,
            thumb_url,
            original_name,
            stored_name,
            sort_order
        )
        VALUES
        (
            %s, %s, %s, %s, %s, %s, %s
        )
    """
    cursor.execute(
        sql,
        (
            restaurant_id,
            menu_id,
            image_data["image_url"],
            image_data["thumb_url"],
            image_data["original_name"],
            image_data["stored_name"],
            sort_order
        )
    )


# 전달받는 값
# - cursor: conn.cursor()
# - image_id: 수정할 이미지 번호
# - image_data: 저장된 이미지 딕셔너리
# 반환값    : 없음
def update_menu_image(cursor, image_id, image_data):
    sql = """
        UPDATE restaurant_images
        SET
            image_url = %s,
            thumb_url = %s,
            original_name = %s,
            stored_name = %s
        WHERE image_id = %s
    """
    cursor.execute(
        sql,
        (
            image_data["image_url"],
            image_data["thumb_url"],
            image_data["original_name"],
            image_data["stored_name"],
            image_id
        )
    )


# 전달받는 값
# - cursor: conn.cursor()
# - restaurant_id: DB의 식당 번호
# - menu_id: DB의 메뉴 번호
# 반환값    : 없음
def delete_menu_image_by_menu_id(cursor, restaurant_id, menu_id):
    current_image = get_menu_image_by_menu_id(cursor, restaurant_id, menu_id)

    if current_image:
        safe_remove_file(current_image.get("image_url"))
        safe_remove_file(current_image.get("thumb_url"))

        sql = """
            DELETE FROM restaurant_images
            WHERE restaurant_id = %s
            AND menu_id = %s
        """
        cursor.execute(sql, (restaurant_id, menu_id))


# 전달받는 값
# - owner_id: DB의 owner_id
# 반환값
# - owners 테이블 1건
def get_owner_info(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT owner_id, owner_name, email, status
                FROM owners
                WHERE owner_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchone()
    finally:
        conn.close()


# 전달받는 값
# - owner_id: DB의 owner_id
# 반환값
# - restaurants 테이블 1건
def get_restaurant_id_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT restaurant_id, name, status
                FROM restaurants
                WHERE owner_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchone()
    finally:
        conn.close()


# 전달받는 값
# - owner_id: DB의 owner_id
# 반환값
# - 해당 owner의 restaurants 목록
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


# -------------------------------------------------------------------------------------
# 메뉴 카테고리 조회
# -------------------------------------------------------------------------------------
# 반환값    : menu_categories 전체 목록
def get_menu_categories():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT menu_category_id, menu_category_name
                FROM menu_categories
                ORDER BY menu_category_id ASC
            """
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


#------------------------------------------------------------------------------------
# 등록된 메뉴 출력 (페이징)- menu_management
#------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# 등록된 메뉴 목록 조회
# -------------------------------------------------------------------------------------
# 전달받는 값
# - restaurant_id: DB의 restaurant_id
# - limit: 페이지당 조회 개수
# - offset: 시작 위치
# 반환값 : 해당 restaurant의 메뉴 목록
# 수정: owner_id 대신 restaurant_id를 직접 받아 해당 식당 메뉴만 조회하도록 변경
def get_menu_list_by_owner(restaurant_id, limit=None, offset=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    r.owner_id,
                    r.restaurant_id,
                    rm.menu_id,
                    rm.menu_category_id,
                    rm.menu_name,
                    rm.price,
                    rm.status,
                    mc.menu_category_name,
                    ri.image_url,
                    ri.thumb_url,
                    ri.original_name
                FROM restaurant_menus rm
                INNER JOIN restaurants r
                    ON rm.restaurant_id = r.restaurant_id
                LEFT JOIN menu_categories mc
                    ON rm.menu_category_id = mc.menu_category_id
                LEFT JOIN restaurant_images ri
                    ON ri.restaurant_id = rm.restaurant_id
                    AND ri.menu_id = rm.menu_id
                WHERE r.restaurant_id = %s
                ORDER BY rm.menu_id DESC
            """

            # 수정: 하드코딩 params = [1] 제거 후 전달받은 restaurant_id 사용
            params = [restaurant_id]

            if limit is not None and offset is not None:
                sql += " LIMIT %s OFFSET %s"
                params.extend([limit, offset])

            cursor.execute(sql, tuple(params))
            return cursor.fetchall()
    finally:
        conn.close()


# -------------------------------------------------------------------------------------
# 등록된 메뉴 총 개수 조회
# -------------------------------------------------------------------------------------
# 전달받는 값
# - restaurant_id: DB의 restaurant_id
# 반환값
# - 해당 restaurant의 메뉴 총 개수
def get_menu_count_by_restaurant(restaurant_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT COUNT(*) AS cnt
                FROM restaurant_menus
                WHERE restaurant_id = %s
            """
            cursor.execute(sql, (restaurant_id,))
            row = cursor.fetchone()
            return row["cnt"] if row else 0
    finally:
        conn.close()


# 전달받는 값
# - owner_id: DB의 owner_id
# 반환값
# - 해당 owner의 메뉴 총 개수
def get_menu_count_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    r.restaurant_id,
                    r.name,
                    COUNT(rm.menu_id) AS cnt
                FROM restaurants r
                LEFT JOIN restaurant_menus rm
                    ON rm.restaurant_id = r.restaurant_id
                WHERE r.owner_id = %s
                GROUP BY r.restaurant_id, r.name
                ORDER BY r.restaurant_id ASC
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchall()
    finally:
        conn.close()


# -------------------------------------------------------------------------------------
# 메뉴 상세 조회
# -------------------------------------------------------------------------------------
# 전달받는 값
# - restaurant_id: DB의 restaurant_id
# - menu_id: DB의 menu_id
# 반환값
# - 해당 메뉴 1건 상세정보
def get_menu_detail_by_id(restaurant_id, menu_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    rm.menu_id,
                    rm.restaurant_id,
                    rm.menu_category_id,
                    rm.menu_name,
                    rm.price,
                    rm.status,
                    ri.image_url,
                    ri.thumb_url,
                    ri.original_name,
                    ri.stored_name
                FROM restaurant_menus rm
                LEFT JOIN restaurant_images ri
                    ON ri.restaurant_id = rm.restaurant_id
                    AND ri.menu_id = rm.menu_id
                    AND ri.image_id = (
                        SELECT image_id
                        FROM restaurant_images
                        WHERE restaurant_id = rm.restaurant_id
                        AND menu_id = rm.menu_id
                        ORDER BY sort_order ASC, image_id ASC
                        LIMIT 1
                    )
                WHERE rm.restaurant_id = %s
                AND rm.menu_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (restaurant_id, menu_id))
            return cursor.fetchone()
    finally:
        conn.close()


#------------------------------------------------------------------------------------
# 메뉴 등록 (insert) - menu_management
#------------------------------------------------------------------------------------
# 전달받는 값
# - restaurant_id: 등록할 restaurant_id
# - menu_category_id: 카테고리 번호
# - menu_name: 메뉴명
# - price: 가격
# - status: 판매 상태
# - image_file: 업로드 파일 객체
# 반환값
# - 새로 등록된 menu_id
def insert_menu(restaurant_id, menu_category_id, menu_name, price, status="ON", image_file=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO restaurant_menus
                (
                    restaurant_id,
                    menu_category_id,
                    menu_name,
                    price,
                    status
                )
                VALUES
                (
                    %s, %s, %s, %s, %s
                )
            """
            cursor.execute(
                sql,
                (restaurant_id, menu_category_id, menu_name, price, status)
            )
            menu_id = cursor.lastrowid

            if image_file and image_file.filename:
                image_data = save_menu_image_file(image_file)
                insert_menu_image(cursor, restaurant_id, menu_id, image_data, sort_order=1)

        conn.commit()
        return menu_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


#------------------------------------------------------------------------------------
# 메뉴 수정 (update) - menu_management
#------------------------------------------------------------------------------------
# 전달받는 값
# - restaurant_id: 수정할 메뉴의 restaurant_id
# - menu_id: 수정할 menu_id
# - menu_category_id: 카테고리 번호
# - menu_name: 메뉴명
# - price: 가격
# - status: 판매 상태
# - image_file: 새 업로드 파일 객체
# - remove_image: 기존 이미지 삭제 여부
# 반환값
# - 없음
def update_menu(
    restaurant_id,
    menu_id,
    menu_category_id,
    menu_name,
    price,
    status="ON",
    image_file=None,
    remove_image=False
):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE restaurant_menus
                SET
                    menu_category_id = %s,
                    menu_name = %s,
                    price = %s,
                    status = %s
                WHERE restaurant_id = %s
                AND menu_id = %s
            """
            cursor.execute(
                sql,
                (menu_category_id, menu_name, price, status, restaurant_id, menu_id)
            )

            current_image = get_menu_image_by_menu_id(cursor, restaurant_id, menu_id)

            if remove_image:
                delete_menu_image_by_menu_id(cursor, restaurant_id, menu_id)
                current_image = None

            if image_file and image_file.filename:
                image_data = save_menu_image_file(image_file)

                if current_image:
                    safe_remove_file(current_image.get("image_url"))
                    safe_remove_file(current_image.get("thumb_url"))
                    update_menu_image(cursor, current_image["image_id"], image_data)
                else:
                    insert_menu_image(cursor, restaurant_id, menu_id, image_data, sort_order=1)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


#------------------------------------------------------------------------------------
# 메뉴 삭제 (delete) - menu_management
#------------------------------------------------------------------------------------
# 전달받는 값
# - restaurant_id: 삭제할 메뉴의 restaurant_id
# - menu_id: 삭제할 menu_id
# 반환값
# - 없음
def delete_menu(restaurant_id, menu_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            delete_menu_image_by_menu_id(cursor, restaurant_id, menu_id)

            sql = """
                DELETE FROM restaurant_menus
                WHERE restaurant_id = %s
                AND menu_id = %s
            """
            cursor.execute(sql, (restaurant_id, menu_id))

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

#------------------------------------------------------------------------------------
# 레스토랑 요청 테이블 관리 함수 - owner_register.html
#------------------------------------------------------------------------------------

# 이종민 레스토랑 요청 테이블 관리 함수 S
def insert_pending_restaurant(store_name, owner_name, phone, road_address, category_name, description):
    owner = get_owner_info()

    owner_name = owner["owner_name"] if owner else "UNKNOWN"

    sql = """
        INSERT INTO restaurants_request
        (
            store_name,
            owner_name,            
            phone,
            road_address,
            category_name,
            description
        )
        VALUES
        (%s, %s, %s, %s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (
                owner_name,
                store_name,
                phone,
                road_address,
                category_name,
                description
            ))
        conn.commit()
    finally:
        conn.close()
# 이종민 레스토랑 요청 테이블 관리 함수 E
        
# 이종민 레스토랑 요청 테이블 관리 함수 S
def fetch_pending_restaurants():

    sql = """
        SELECT
            request_id,
            owner_name,
            store_name,
            phone,
            road_address,
            category_name,
            description,
            status,
            created_at
        FROM restaurants_request
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    finally:
        conn.close()
# 이종민 레스토랑 요청 테이블 관리 함수 E


# 이종민 추가된 함수 레스토랑 요청 관리  S
def approve_restaurant(request_id):

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # 요청 정보 가져오기
            sql = """
                SELECT *
                FROM restaurants_request
                WHERE request_id = %s
            """
            cursor.execute(sql, (request_id,))
            request_data = cursor.fetchone()

            if not request_data:
                return

            category_id = get_category_id_by_name(request_data["category_name"])

            if category_id is None:
                category_id = 1

            # restaurants 테이블에 등록
            sql = """
                INSERT INTO restaurants
                (
                    restaurant_category_id,
                    name,
                    address,
                    road_address,
                    latitude,
                    longitude,
                    phone,
                    business_hours,
                    description,
                    owner_id,
                    status
                )
                VALUES (%s,%s,%s,%s,37.5665,126.9780,%s,NULL,%s,%s,'OPEN')
            """

            cursor.execute(sql, (
                category_id,
                request_data["store_name"],
                request_data["road_address"],
                request_data["road_address"],
                request_data["phone"],
                request_data["description"],
                request_data["owner_id"]
            ))

            # 요청 상태 변경
            sql = """
                UPDATE restaurants_request
                SET status='APPROVED'
                WHERE request_id=%s
            """

            cursor.execute(sql, (request_id,))

        conn.commit()

    finally:
        conn.close()

def reject_restaurant(restaurant_id):
    sql = """
        UPDATE restaurants
        SET status = 'REJECTED'
        WHERE restaurant_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
    finally:
        conn.close()

# 이종민 추가된 함수 레스토랑 요청 관리  E