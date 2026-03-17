from db import get_connection


def find_restaurant_id_by_store_name(store_name):
    """영수증 가게명으로 restaurants.restaurant_id를 찾는다."""
    sql = """
        SELECT restaurant_id, name
        FROM restaurants
        WHERE REPLACE(LOWER(name), ' ', '') = REPLACE(LOWER(%s), ' ', '')
        ORDER BY restaurant_id ASC
        LIMIT 1
    """

    fallback_sql = """
        SELECT restaurant_id, name
        FROM restaurants
        WHERE REPLACE(LOWER(name), ' ', '') LIKE CONCAT('%%', REPLACE(LOWER(%s), ' ', ''), '%%')
           OR REPLACE(LOWER(%s), ' ', '') LIKE CONCAT('%%', REPLACE(LOWER(name), ' ', ''), '%%')
        ORDER BY CHAR_LENGTH(name) ASC, restaurant_id ASC
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (store_name,))
            row = cursor.fetchone()
            if row:
                return row

            cursor.execute(fallback_sql, (store_name, store_name))
            return cursor.fetchone()
    finally:
        conn.close()



def find_menu_by_name(restaurant_id, menu_name):
    """음식점 내 메뉴명을 찾아 menu_id를 반환한다."""
    exact_sql = """
        SELECT menu_id, menu_name
        FROM restaurant_menus
        WHERE restaurant_id = %s
          AND REPLACE(LOWER(menu_name), ' ', '') = REPLACE(LOWER(%s), ' ', '')
        ORDER BY menu_id ASC
        LIMIT 1
    """

    fallback_sql = """
        SELECT menu_id, menu_name
        FROM restaurant_menus
        WHERE restaurant_id = %s
          AND (
                REPLACE(LOWER(menu_name), ' ', '') LIKE CONCAT('%%', REPLACE(LOWER(%s), ' ', ''), '%%')
             OR REPLACE(LOWER(%s), ' ', '') LIKE CONCAT('%%', REPLACE(LOWER(menu_name), ' ', ''), '%%')
          )
        ORDER BY CHAR_LENGTH(menu_name) ASC, menu_id ASC
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(exact_sql, (restaurant_id, menu_name))
            row = cursor.fetchone()
            if row:
                return row

            cursor.execute(fallback_sql, (restaurant_id, menu_name, menu_name))
            return cursor.fetchone()
    finally:
        conn.close()



def create_visit_with_menus(user_id, restaurant_id, purchase_date, items):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            visit_sql = """
                INSERT INTO visits (user_id, restaurant_id, visited_at)
                VALUES (%s, %s, %s)
            """
            cursor.execute(visit_sql, (user_id, restaurant_id, purchase_date))
            visit_id = cursor.lastrowid

            visit_menu_sql = """
                INSERT INTO visit_menus (visit_id, menu_id, quantity, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            for item in items:
                cursor.execute(
                    visit_menu_sql,
                    (visit_id, item["menu_id"], item["quantity"])
                )

            conn.commit()
            return visit_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def exists_visit_same_day(user_id, restaurant_id, purchase_date):
    conn = get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT visit_id
        FROM visits
        WHERE user_id = %s
          AND restaurant_id = %s
          AND DATE(visited_at) = %s
        LIMIT 1
    """
    cursor.execute(sql, (user_id, restaurant_id, purchase_date))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row is not None