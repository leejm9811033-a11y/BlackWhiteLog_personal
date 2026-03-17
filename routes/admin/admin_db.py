from db import get_connection
import random

# =========================
# 관리자용 전체 회원 목록 조회
# =========================
def fetch_all_users():
    sql = """
        SELECT user_id, email, nickname, role, status, provider, created_at
        FROM users
        ORDER BY created_at DESC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 관리자용 회원 비활성화
# =========================
def admin_deactivate_user(user_id):
    sql = """
        UPDATE users
        SET status = 'DELETED'
        WHERE user_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
        conn.commit()
    finally:
        conn.close()


# =========================
# 관리자용 회원 복구
# =========================
def admin_restore_user(user_id):
    sql = """
        UPDATE users
        SET status = 'ACTIVE'
        WHERE user_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
        conn.commit()
    finally:
        conn.close()


# =========================
# 관리자 신고 관리용 더미 데이터
# 실제 신고 테이블 연결 전 임시 사용
# =========================
_dummy_reports = [
    {
        "report_id": 201,
        "review_id": 101,
        "reported_user_nickname": "혜성",
        "report_user_nickname": "민수",
        "restaurant_name": "흑백식당",
        "reason": "욕설/비방",
        "review_content": "분위기도 좋고 음식도 깔끔해서 재방문 의사 있어요.",
        "status": "PENDING",
        "created_at": "2026-03-13 16:10:00",
    },
    {
        "report_id": 202,
        "review_id": 102,
        "reported_user_nickname": "테스트유저",
        "report_user_nickname": "가나다",
        "restaurant_name": "서울김밥",
        "reason": "허위 리뷰",
        "review_content": "광고 같은 느낌이 들었고 사진이 실제와 달랐어요.",
        "status": "RESOLVED",
        "created_at": "2026-03-13 16:35:00",
    },
    {
        "report_id": 203,
        "review_id": 104,
        "reported_user_nickname": "가나다",
        "report_user_nickname": "혜성",
        "restaurant_name": "한강분식",
        "reason": "도배",
        "review_content": "반복적인 도배성 내용입니다.",
        "status": "REJECTED",
        "created_at": "2026-03-13 17:05:00",
    },
]


# =========================
# 관리자 제재 관리용 더미 데이터
# 실제 제재 테이블 연결 전 임시 사용
# =========================
_dummy_sanctions = [
    {
        "sanction_id": 301,
        "user_nickname": "테스트유저",
        "sanction_type": "WARNING",
        "reason": "광고성 리뷰 작성",
        "status": "ACTIVE",
        "created_at": "2026-03-13 17:20:00",
        "expire_at": "-",
    },
    {
        "sanction_id": 302,
        "user_nickname": "가나다",
        "sanction_type": "SUSPEND_3D",
        "reason": "도배성 리뷰 반복 작성",
        "status": "ACTIVE",
        "created_at": "2026-03-13 17:40:00",
        "expire_at": "2026-03-16 17:40:00",
    },
]


# =========================
# 관리자 신고 목록 조회
# keyword: 신고ID / 리뷰ID / 닉네임 / 음식점명 / 사유 검색
# status: PENDING / RESOLVED / REJECTED
# =========================
def fetch_admin_reports(keyword="", status=""):
    keyword = (keyword or "").strip().lower()
    status = (status or "").strip().upper()

    filtered = []

    for report in _dummy_reports:
        matches_keyword = True
        matches_status = True

        if keyword:
            searchable_text = " ".join([
                str(report["report_id"]),
                str(report["review_id"]),
                report["reported_user_nickname"],
                report["report_user_nickname"],
                report["restaurant_name"],
                report["reason"],
                report["review_content"],
            ]).lower()
            matches_keyword = keyword in searchable_text

        if status:
            matches_status = report["status"] == status

        if matches_keyword and matches_status:
            filtered.append(report)

    return filtered


# =========================
# 신고 단건 조회
# =========================
def get_admin_report_by_id(report_id):
    for report in _dummy_reports:
        if report["report_id"] == report_id:
            return report
    return None


# =========================
# 신고 상태 변경
# PENDING / RESOLVED / REJECTED
# =========================
def update_admin_report_status(report_id, new_status):
    report = get_admin_report_by_id(report_id)
    if not report:
        return False

    report["status"] = new_status
    return True


# =========================
# 관리자 제재 목록 조회
# keyword: 제재ID / 닉네임 / 사유 / 제재종류 검색
# status: ACTIVE / RELEASED
# =========================
def fetch_admin_sanctions(keyword="", status=""):
    keyword = (keyword or "").strip().lower()
    status = (status or "").strip().upper()

    filtered = []

    for sanction in _dummy_sanctions:
        matches_keyword = True
        matches_status = True

        if keyword:
            searchable_text = " ".join([
                str(sanction["sanction_id"]),
                sanction["user_nickname"],
                sanction["sanction_type"],
                sanction["reason"],
            ]).lower()
            matches_keyword = keyword in searchable_text

        if status:
            matches_status = sanction["status"] == status

        if matches_keyword and matches_status:
            filtered.append(sanction)

    return filtered


# =========================
# 제재 등록
# sanction_type 예:
# WARNING / SUSPEND_3D / SUSPEND_7D / BAN
# =========================
def create_admin_sanction(user_nickname, sanction_type, reason, expire_at="-"):
    new_id = 301
    if _dummy_sanctions:
        new_id = max(item["sanction_id"] for item in _dummy_sanctions) + 1

    new_item = {
        "sanction_id": new_id,
        "user_nickname": user_nickname,
        "sanction_type": sanction_type,
        "reason": reason,
        "status": "ACTIVE",
        "created_at": "2026-03-13 18:00:00",
        "expire_at": expire_at if expire_at else "-",
    }

    _dummy_sanctions.insert(0, new_item)
    return True


# =========================
# 제재 해제
# =========================
def release_admin_sanction(sanction_id):
    for sanction in _dummy_sanctions:
        if sanction["sanction_id"] == sanction_id:
            sanction["status"] = "RELEASED"
            return True
    return False

# =========================
# 관리자 리뷰 관리 - 전체 리뷰 목록 조회
# 설명:
# - 필요 시 app.py나 다른 화면에서 써도 되도록 유지
# - keyword, status 필터 지원
# =========================
def fetch_admin_reviews(keyword="", status=""):
    sql = """
        SELECT
            rv.review_id,
            rv.visit_id,
            r.restaurant_id,
            r.name AS restaurant_name,
            u.user_id,
            u.nickname AS user_nickname,
            rv.rating,
            rv.content,
            rv.created_at,
            rv.updated_at,
            rv.status
        FROM reviews rv
        INNER JOIN visits v
            ON rv.visit_id = v.visit_id
        INNER JOIN users u
            ON v.user_id = u.user_id
        INNER JOIN restaurants r
            ON v.restaurant_id = r.restaurant_id
        WHERE 1=1
    """

    params = []

    if keyword:
        sql += """
            AND (
                CAST(rv.review_id AS CHAR) LIKE %s
                OR u.nickname LIKE %s
                OR r.name LIKE %s
                OR rv.content LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    if status:
        sql += " AND rv.status = %s "
        params.append(status)

    sql += " ORDER BY rv.created_at DESC "

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 관리자 리뷰 관리 - 리뷰가 등록된 가게 목록 조회
# =========================
def fetch_admin_review_restaurants(keyword=""):
    sql = """
        SELECT
            r.restaurant_id,
            r.name AS restaurant_name,
            COUNT(rv.review_id) AS review_count
        FROM reviews rv
        INNER JOIN visits v
            ON rv.visit_id = v.visit_id
        INNER JOIN restaurants r
            ON v.restaurant_id = r.restaurant_id
        WHERE (%s = '' OR r.name LIKE CONCAT('%%', %s, '%%'))
        GROUP BY r.restaurant_id, r.name
        ORDER BY review_count DESC, r.name ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (keyword, keyword))
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 관리자 리뷰 관리 - 특정 가게의 리뷰 목록 조회
# =========================
def fetch_admin_reviews_by_restaurant(restaurant_id, status=""):
    sql = """
        SELECT
            rv.review_id,
            rv.visit_id,
            r.restaurant_id,
            r.name AS restaurant_name,
            u.user_id,
            u.nickname AS user_nickname,
            rv.rating,
            rv.content,
            rv.created_at,
            rv.updated_at,
            rv.status
        FROM reviews rv
        INNER JOIN visits v
            ON rv.visit_id = v.visit_id
        INNER JOIN users u
            ON v.user_id = u.user_id
        INNER JOIN restaurants r
            ON v.restaurant_id = r.restaurant_id
        WHERE r.restaurant_id = %s
    """

    params = [restaurant_id]

    if status:
        sql += " AND rv.status = %s "
        params.append(status)

    sql += " ORDER BY rv.created_at DESC "

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 관리자 리뷰 관리 - 리뷰 단건 조회
# =========================
def get_admin_review_by_id(review_id):
    sql = """
        SELECT
            rv.review_id,
            rv.visit_id,
            r.restaurant_id,
            r.name AS restaurant_name,
            u.user_id,
            u.nickname AS user_nickname,
            rv.rating,
            rv.content,
            rv.created_at,
            rv.updated_at,
            rv.status
        FROM reviews rv
        INNER JOIN visits v
            ON rv.visit_id = v.visit_id
        INNER JOIN users u
            ON v.user_id = u.user_id
        INNER JOIN restaurants r
            ON v.restaurant_id = r.restaurant_id
        WHERE rv.review_id = %s
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (review_id,))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 관리자 리뷰 관리 - 리뷰 수정
# =========================
def update_admin_review(review_id, rating, content):
    sql = """
        UPDATE reviews
        SET rating = %s,
            content = %s,
            updated_at = NOW()
        WHERE review_id = %s
          AND status <> 'DELETED'
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (rating, content, review_id))
            return cursor.rowcount > 0
    finally:
        conn.close()


# =========================
# 관리자 리뷰 관리 - 리뷰 상태 변경 공통 함수
# =========================
def update_admin_review_status(review_id, new_status):
    sql = """
        UPDATE reviews
        SET status = %s,
            updated_at = NOW()
        WHERE review_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (new_status, review_id))
            updated = cursor.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()


# =========================
# 관리자 리뷰 관리 - 리뷰 숨김
# =========================
def hide_admin_review(review_id):
    return update_admin_review_status(review_id, "HIDDEN")


# =========================
# 관리자 리뷰 관리 - 리뷰 삭제(실제 삭제)
# =========================
def soft_delete_admin_review(review_id):
    sql = """
        DELETE FROM reviews
        WHERE review_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (review_id,))
            deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()


# =========================
# 관리자 리뷰 관리 - 리뷰 복구
# =========================
def restore_admin_review(review_id):
    return update_admin_review_status(review_id, "ACTIVE")

# (관리자가 음식점 등록 신청을 관리) S

def fetch_all_restaurants(keyword=None):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                r.restaurant_id,
                r.name,
                r.road_address,
                r.phone,
                r.status,
                r.user_id,
                r.owner_id
            FROM restaurants r
            """

            params = []

            if keyword:
                sql += " WHERE r.name LIKE %s"
                params.append(f"%{keyword}%")

            sql += " ORDER BY r.restaurant_id DESC"

            cursor.execute(sql, params)
            return cursor.fetchall()

    finally:
        conn.close()

def get_restaurant_by_id(restaurant_id):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                restaurant_id,
                owner_id,
                user_id,
                name,
                address,
                road_address,
                phone,
                status
            FROM restaurants
            WHERE restaurant_id = %s
            """

            cursor.execute(sql, (restaurant_id,))
            return cursor.fetchone()

    finally:
        conn.close()

def update_restaurant(restaurant_id, restaurant_name, address, phone):
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
    UPDATE restaurants
    SET
        name = %s,
        address = %s,
        phone = %s
    WHERE restaurant_id = %s
    """

    cursor.execute(sql, (restaurant_name, address, phone, restaurant_id))
    conn.commit()

    cursor.close()
    conn.close()

# =========================
# 관리자 음식점 삭제
# =========================
def delete_restaurant(restaurant_id):

    sql = """
        DELETE FROM restaurants
        WHERE restaurant_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
        conn.commit()
    finally:
        conn.close()

# =========================
# 관리자 음식점 등록
# =========================
def create_restaurant(name, category_id, region_sigungu, address, phone):
    sql = """
        INSERT INTO restaurants
        (name, restaurant_category_id, region_sigungu, address, phone, status)
        VALUES (%s, %s, %s, %s, %s, 'OPEN')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (name, category_id, region_sigungu, address, phone))
        conn.commit()
    finally:
        conn.close()

# =========================
# 관리자 판매 신청 목록 조회
# keyword: 유저ID / 닉네임 / 이메일 / 식당ID / 식당명 검색
# status: PENDING / APPROVED / REJECTED
# ========================= 이종민 판매자 등록 페이지.
def fetch_admin_restaurant_requests(keyword="", status="PENDING"):
    sql = """
        SELECT
            rr.request_id,
            rr.owner_id,
            rr.owner_name,   -- 실제로는 user_id 문자열
            rr.store_name,
            rr.phone,
            rr.road_address,
            rr.category_name,
            rr.description,
            rr.status,
            rr.created_at
        FROM restaurants_request rr
        WHERE 1=1
    """

    params = []

    if keyword:
        sql += """
            AND (
                CAST(rr.request_id AS CHAR) LIKE %s
                OR CAST(rr.owner_name AS CHAR) LIKE %s
                OR rr.store_name LIKE %s
                OR rr.phone LIKE %s
                OR rr.road_address LIKE %s
                OR rr.category_name LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword] * 6)

    if status:
        sql += " AND rr.status = %s "
        params.append(status)

    sql += " ORDER BY rr.created_at DESC "

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()
# =========================
# 관리자 판매 신청 단건 조회
# =========================
def get_admin_restaurant_request_by_id(request_id):
    sql = """
        SELECT
            rr.request_id,
            rr.owner_id,
            o.owner_name,
            rr.store_name,
            rr.phone,
            rr.road_address,
            rr.category_name,
            rr.description,
            rr.status,
            rr.created_at,
            o.user_id
        FROM restaurants_request rr
        LEFT JOIN owners o
            ON rr.owner_id = o.owner_id
        WHERE rr.request_id = %s
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (request_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def insert_owner_p(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 이미 owner가 있으면 기존 owner_id 반환
            cursor.execute("""
                SELECT owner_id
                FROM owners
                WHERE user_id = %s
                LIMIT 1
            """, (user_id,))
            existing_owner = cursor.fetchone()

            if existing_owner:
                return True, existing_owner["owner_id"]

            # users 테이블에서 owner 생성에 필요한 정보 조회
            cursor.execute("""
                SELECT
                    user_id,
                    nickname,
                    email
                FROM users
                WHERE user_id = %s
                LIMIT 1
            """, (user_id,))
            user = cursor.fetchone()

            if not user:
                return False, "해당 유저를 찾을 수 없습니다."

            # owners 테이블에 신규 등록
            cursor.execute("""
                INSERT INTO owners
                (
                    user_id,
                    owner_name,
                    email,
                    phone,
                    business_number,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, 'ACTIVE')
            """, (
                user["user_id"],
                user["nickname"],
                user["email"],
                None,
                None
            ))

            new_owner_id = cursor.lastrowid
            conn.commit()
            return True, new_owner_id

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        conn.close()

# =========================
# 관리자 판매 신청 승인
# - 신청한 user_id 기준으로 owners 생성 또는 조회
# - restaurants.owner_id 연결
# - restaurants_request 상태 APPROVED 처리
# ========================= 이종민 승인/반려 함수 수정

def get_random_gangnam_location():
    base_lat = 37.497958
    base_lng = 127.027539
    lat = base_lat + random.uniform(-0.0045, 0.0045)
    lng = base_lng + random.uniform(-0.0045, 0.0045)
    return round(lat, 7), round(lng, 7)


def approve_restaurant_request(request_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            conn.begin()

            random_lat, random_lng = get_random_gangnam_location()

            cur.execute("""
                SELECT
                    rr.request_id,
                    CAST(rr.owner_name AS UNSIGNED) AS user_id,
                    rr.owner_name,
                    rr.store_name,
                    rr.phone,
                    rr.road_address,
                    rr.category_name,
                    rr.description,
                    rr.status
                FROM restaurants_request rr
                WHERE rr.request_id = %s
                  AND rr.status = 'PENDING'
            """, (request_id,))
            req = cur.fetchone()

            if not req:
                raise Exception("승인할 신청 데이터가 없습니다.")

            if not req["user_id"]:
                raise Exception("user_id 값을 읽을 수 없습니다.")

            # 1. 기존 owner 조회
            cur.execute("""
                SELECT owner_id
                FROM owners
                WHERE user_id = %s
                LIMIT 1
            """, (req["user_id"],))
            owner_row = cur.fetchone()

            # 2. owner가 없으면 생성
            if owner_row:
                owner_id = owner_row["owner_id"]
            else:
                cur.execute("""
                    SELECT
                        user_id,
                        nickname,
                        email
                    FROM users
                    WHERE user_id = %s
                    LIMIT 1
                """, (req["user_id"],))
                user_row = cur.fetchone()

                if not user_row:
                    raise Exception("신청한 유저 정보를 찾을 수 없습니다.")

                cur.execute("""
                    INSERT INTO owners
                    (
                        user_id,
                        owner_name,
                        email,
                        phone,
                        business_number,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, 'ACTIVE')
                """, (
                    user_row["user_id"],
                    user_row["nickname"],
                    user_row["email"],
                    req["phone"],
                    None
                ))
                owner_id = cur.lastrowid

            # 3. restaurant 생성
            cur.execute("""
                INSERT INTO restaurants (
                    restaurant_category_id,
                    name,
                    address,
                    road_address,
                    latitude,
                    longitude,
                    phone,
                    business_hours,
                    description,
                    region_sido,
                    region_sigungu,
                    region_dong,
                    owner_id,
                    user_id,
                    status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPEN'
                )
            """, (
                None,
                req["store_name"],
                req["road_address"],
                req["road_address"],
                random_lat,
                random_lng,
                req["phone"],
                None,
                req["description"],
                "서울특별시",
                "강남구",
                "역삼동",
                owner_id,         # 여기 중요: user_id가 아니라 owner_id
                req["user_id"]    # user_id는 그대로 user_id 칼럼에 저장
            ))

            # 4. 신청 내역 삭제
            cur.execute("""
                DELETE FROM restaurants_request
                WHERE request_id = %s
            """, (request_id,))

            conn.commit()
            return True, "승인 완료"

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        conn.close()

# =========================
# 관리자 판매 신청 반려
# =========================  이종민 수정
def reject_restaurant_request(request_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM restaurants_request
                WHERE request_id = %s
                  AND status = 'PENDING'
            """, (request_id,))
            deleted = cursor.rowcount > 0

        conn.commit()

        if deleted:
            return True, "거절 완료: 요청 목록에서 제거했습니다."
        return False, "처리 가능한 신청 정보가 없습니다."

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        conn.close()


# =========================
# 관리자 오너 목록 조회
# - 어떤 user가 실제 owner인지 확인
# - owner가 가진 레스토랑 수까지 확인
# =========================
def fetch_admin_owners(keyword=""):
    sql = """
        SELECT
            o.owner_id,
            o.user_id,
            u.email,
            u.nickname,
            o.business_number,
            COUNT(r.restaurant_id) AS restaurant_count
        FROM owners o
        INNER JOIN users u
            ON o.user_id = u.user_id
        LEFT JOIN restaurants r
            ON r.owner_id = o.owner_id
        WHERE 1=1
    """

    params = []

    if keyword:
        sql += """
            AND (
                CAST(o.owner_id AS CHAR) LIKE %s
                OR CAST(o.user_id AS CHAR) LIKE %s
                OR u.email LIKE %s
                OR u.nickname LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    sql += """
        GROUP BY o.owner_id, o.user_id, u.email, u.nickname, o.business_number
        ORDER BY o.owner_id DESC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 유저가 판매자 신청
# - restaurants에 owner_id NULL로 등록
# - restaurants_request에 신청 내역 생성
# =========================
def create_restaurant_request(owner_name, store_name, phone, road_address, category_name, description):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO restaurants_request
                (
                    owner_id,
                    owner_name,
                    store_name,
                    phone,
                    road_address,
                    category_name,
                    description,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING')
            """
            cursor.execute(sql, (
                None,               # 아직 owner_id 없음
                str(owner_name),    # 여기에 user_id 문자열 저장
                store_name,
                phone,
                road_address,
                category_name,
                description
            ))
            new_request_id = cursor.lastrowid

        conn.commit()
        return True, new_request_id

    except Exception as e:
        conn.rollback()
        return False, str(e)

    finally:
        conn.close()

