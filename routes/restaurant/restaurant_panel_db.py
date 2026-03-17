import os
from db import get_connection, is_favorite_restaurant

def get_restaurant_detail(restaurant_id, user_id=None):
    sql = """
        SELECT
            r.restaurant_id,
            r.name,
            r.description,
            r.road_address,
            r.phone,
            r.business_hours,
            r.status,
            (
                SELECT image_url
                FROM restaurant_images
                WHERE restaurant_id = r.restaurant_id
                ORDER BY sort_order ASC
                LIMIT 1
            ) AS image_url
        FROM restaurants r
        WHERE r.restaurant_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            row = cursor.fetchone()

            if not row:
                return None

            row["is_favorite"] = False
            row["has_visited"] = False
            row["has_reviewed_latest_visit"] = False
            
            if user_id:
                row["is_favorite"] = is_favorite_restaurant(user_id, restaurant_id)

                cursor.execute(
                    "SELECT visit_id FROM visits WHERE user_id=%s AND restaurant_id=%s ORDER BY visited_at DESC LIMIT 1",
                    (user_id, restaurant_id)
                )
                visit_row = cursor.fetchone()

                if visit_row:
                    row["has_visited"] = True
                    latest_visit_id = visit_row["visit_id"]

                    cursor.execute("""
                        SELECT 1
                        FROM reviews
                        WHERE visit_id = %s
                          AND COALESCE(status, 'ACTIVE') = 'ACTIVE'
                        LIMIT 1
                    """, (latest_visit_id,))
                    if cursor.fetchone():
                        row["has_reviewed_latest_visit"] = True
                    
            return row
    finally:
        conn.close()


def get_restaurant_menus(restaurant_id, user_id=None):
    """특정 음식점의 메뉴 목록 + 현재 유저가 먹은 메뉴 여부를 가져오는 함수"""
    effective_user_id = user_id if user_id else 0

    sql = """
        SELECT
            rm.menu_id,
            rm.menu_name,
            rm.price,
            COALESCE(uvm.eaten_count, 0) AS eaten_count,
            CASE
                WHEN uvm.menu_id IS NULL THEN 0
                ELSE 1
            END AS has_eaten
        FROM restaurant_menus rm
        LEFT JOIN (
            SELECT
                vm.menu_id,
                SUM(vm.quantity) AS eaten_count
            FROM visit_menus vm
            INNER JOIN visits v
                ON vm.visit_id = v.visit_id
            WHERE v.user_id = %s
              AND v.restaurant_id = %s
            GROUP BY vm.menu_id
        ) uvm
            ON rm.menu_id = uvm.menu_id
        WHERE rm.restaurant_id = %s
        ORDER BY rm.menu_id ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (effective_user_id, restaurant_id, restaurant_id))
            rows = cursor.fetchall()

            for row in rows:
                row["price"] = int(row["price"] or 0)
                row["eaten_count"] = int(row.get("eaten_count") or 0)
                row["has_eaten"] = bool(row.get("has_eaten", 0))

            return rows
    finally:
        conn.close()

def get_restaurant_reviews(restaurant_id):
    """특정 음식점의 리뷰(댓글) 목록을 가져오는 함수"""
    # reviews, visits, users, review_image 4개 테이블 조인
    # 자바스크립트가 시간 오해하지 못하게 텍스트로 가져옴
    sql = """
        SELECT 
            r.review_id, 
            r.rating, 
            r.content, 
            DATE_FORMAT(r.created_at, '%%Y. %%m. %%d.') AS created_at,
            u.nickname, 
            u.profile_image_url AS user_image,
            v.user_id,
            GROUP_CONCAT(ri.image_url ORDER BY ri.sort_order ASC) AS review_images
        FROM reviews r
        JOIN visits v ON r.visit_id = v.visit_id
        JOIN users u ON v.user_id = u.user_id
        LEFT JOIN review_images ri ON r.review_id = ri.review_id
        WHERE v.restaurant_id = %s
        GROUP BY r.review_id
        ORDER BY r.created_at DESC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            return cursor.fetchall()
    finally:
        conn.close()
        
def save_restaurant_review(restaurant_id, user_id, rating, content, image_urls=None):
    """
    visits는 필수 외래키만, reviews는 created_at 포함하여 저장
    """
    from db import get_connection
    # 티어 업데이트 함수를 안에서 임포트 (순환 참조 방지)
    from routes.ranking.user_ranking_db import check_and_update_tier, process_mission

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 이 유저가 영수증으로 찍은 도장(방문 기록)이 있는지 가장 최근 것 찾기
            check_visit_sql = """
                SELECT visit_id FROM visits
                WHERE user_id = %s AND restaurant_id = %s
                ORDER BY visited_at DESC LIMIT 1
            """
            cursor.execute(check_visit_sql, (user_id, restaurant_id))
            visit_row = cursor.fetchone()
            
            if not visit_row:
                return False # 도장 없으면 리뷰 저장 실패 (어뷰징 차단)
                
            visit_id = visit_row['visit_id']

            # 찾은 visit_id에 리뷰를 연결하여 저장
            review_sql = """
                INSERT INTO reviews (visit_id, rating, content, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(review_sql, (visit_id, rating, content))
            review_id = cursor.lastrowid  
            
            # 리뷰 이미지 저장
            if image_urls:
                image_sql = """
                    INSERT INTO review_images (review_id, image_url, sort_order)
                    VALUES (%s, %s, %s)
                """
                for idx, url in enumerate(image_urls):
                    cursor.execute(image_sql, (review_id, url, idx + 1))

            conn.commit()

        review_point = 50
        process_mission(user_id, 'DAILY_REVIEW', review_point, is_weekly=False)
        # 티어 검사 실행
        check_and_update_tier(user_id)
        return True
    
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_review_transaction(review_id, user_id):
    """리뷰 삭제 및 AUTO_INCREMENT 정리"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 소유권 확인 및 visit_id 추출
            check_sql = """
                SELECT v.visit_id FROM reviews r 
                JOIN visits v ON r.visit_id = v.visit_id 
                WHERE r.review_id = %s AND v.user_id = %s
            """
            cursor.execute(check_sql,(review_id, user_id))
            res = cursor.fetchone()
            if not res: return False # 소유권 없음

            visit_id = res['visit_id']

            # 2. 삭제할 이미지 경로 미리 조회 (DB 지우기 전에 백업)
            cursor.execute("SELECT image_url FROM review_images WHERE review_id = %s", (review_id,))
            image_rows = cursor.fetchall()
            image_paths_to_delete = []
            
            for row in image_rows:
                img_url = row.get('image_url')
                if img_url:
                    # DB에는 '/static/img/...' 로 저장되어 있으므로 앞의 '/'를 제거하여 실제 상대 경로로 변환
                    file_path = img_url.lstrip('/')
                    image_paths_to_delete.append(file_path)
            
            # 리뷰이미지 아이디 데이터 삭제
            cursor.execute("DELETE FROM review_images WHERE review_id = %s", (review_id,))
            # 리뷰 삭제
            cursor.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))    
            # review_images 테이블 초기화
            cursor.execute("SELECT MAX(review_image_id) AS max_id FROM review_images")
            row_img = cursor.fetchone()
            max_img_id = row_img['max_id'] if row_img['max_id'] is not None else 0
            cursor.execute(f"ALTER TABLE review_images AUTO_INCREMENT = {max_img_id + 1}")
            # reviews 테이블 AUTO_INCREMENT 초기화
            cursor.execute("SELECT MAX(review_id) AS max_id FROM reviews")
            row_rev = cursor.fetchone()
            max_rev_id = row_rev['max_id'] if row_rev['max_id'] is not None else 0
            cursor.execute(f"ALTER TABLE reviews AUTO_INCREMENT = {max_rev_id + 1}")
            # visits 테이블 AUTO_INCREMENT 초기화

            conn.commit()
            
            # 물리적 이미지 파일 삭제 (DB 삭제가 완벽히 성공한 후에만 실행)
            for file_path in image_paths_to_delete:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as file_e:
                        print(f"⚠️ 파일 삭제 권한 없음/실패: {file_path} - {file_e}")
            
            return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()