from db import get_connection
from routes.ranking.user_ranking_db import check_and_update_tier, process_mission


def get_restaurant_reviews(restaurant_id):
    """특정 음식점의 리뷰(댓글) 목록을 가져오는 함수 - 메인에는 ACTIVE만 표시"""
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
          AND COALESCE(r.status, 'ACTIVE') = 'ACTIVE'
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
    리뷰 저장
    - 가장 최근 방문 기록(visit_id)에 연결
    - 새 리뷰는 ACTIVE 상태로 저장
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            check_visit_sql = """
                SELECT visit_id
                FROM visits
                WHERE user_id = %s AND restaurant_id = %s
                ORDER BY visited_at DESC
                LIMIT 1
            """
            cursor.execute(check_visit_sql, (user_id, restaurant_id))
            visit_row = cursor.fetchone()

            if not visit_row:
                return False

            visit_id = visit_row["visit_id"]

            review_sql = """
                INSERT INTO reviews (visit_id, rating, content, created_at, status)
                VALUES (%s, %s, %s, NOW(), 'ACTIVE')
            """
            cursor.execute(review_sql, (visit_id, rating, content))
            review_id = cursor.lastrowid

            if image_urls:
                image_sql = """
                    INSERT INTO review_images (review_id, image_url, sort_order)
                    VALUES (%s, %s, %s)
                """
                for idx, url in enumerate(image_urls):
                    cursor.execute(image_sql, (review_id, url, idx + 1))

            conn.commit()

        review_point = 50
        process_mission(user_id, "DAILY_REVIEW", review_point, is_weekly=False)
        check_and_update_tier(user_id)
        return True

    except Exception as e:
        conn.rollback()
        print("save_restaurant_review error:", e)
        return False
    finally:
        conn.close()


def delete_review_transaction(review_id, user_id):
    """
    리뷰 소프트 삭제
    - 실제 DELETE 하지 않고 status='DELETED' 로 변경
    - 메인에서는 ACTIVE만 보이므로 삭제 후 바로 안 보이게 됨
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            check_sql = """
                SELECT r.review_id
                FROM reviews r
                JOIN visits v ON r.visit_id = v.visit_id
                WHERE r.review_id = %s
                  AND v.user_id = %s
                  AND COALESCE(r.status, 'ACTIVE') = 'ACTIVE'
            """
            cursor.execute(check_sql, (review_id, user_id))
            res = cursor.fetchone()

            if not res:
                return False

            delete_sql = """
                UPDATE reviews
                SET status = 'DELETED'
                WHERE review_id = %s
            """
            cursor.execute(delete_sql, (review_id,))
            conn.commit()
            return True

    except Exception as e:
        conn.rollback()
        print("delete_review_transaction error:", e)
        return False
    finally:
        conn.close()