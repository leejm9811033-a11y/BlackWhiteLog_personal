# user_ranking_db.py
from db import get_connection
import datetime
import pymysql

TIER_THRESHOLDS = {
    'BRONZE': 0,
    'SILVER': 500,
    'GOLD': 1500,
    'PLATINUM': 3000,
    'DIAMOND': 6000
}

def get_all_user_rankings():
    """전체 유저 랭킹 리스트 (점수순)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # SQL 실행 전, DB에 users 테이블과 아래 컬럼들이 있는지 꼭 확인하세요!
            sql = """
                SELECT user_id, nickname, point, tier, profile_image_url 
                FROM users 
                ORDER BY point DESC
            """
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        print(f"❌ DB Error (get_all_user_rankings): {e}")
        return []
    finally:
        conn.close()

def get_user_dashboard_data(user_id):
    """특정 유저 상세 데이터"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ DB Error (get_user_dashboard_data): {e}")
        return None
    finally:
        conn.close()

def get_user_achievements_data(user_id):
    """전체 업적 목록과 특정 유저가 획득한 업적 목록을 반환"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 모든 업적 목록
            cursor.execute("SELECT achievement_id, name, icon_url FROM achievements")
            all_achievements = cursor.fetchall()

            # 2. 유저가 획득한 업적 목록
            cursor.execute("""
                SELECT a.achievement_id, a.name, a.icon_url 
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                WHERE ua.user_id = %s
            """, (user_id,))
            user_achievements = cursor.fetchall()

            return {
                "all_achievements": all_achievements,
                "user_achievements": user_achievements
            }
    except Exception as e:
        print(f"❌ DB Error (get_user_achievements_data): {e}")
        return {"all_achievements": [], "user_achievements": []}
    finally:
        conn.close()

def get_ranking_summary(user_id):
    """랭킹 요약 카드용 데이터 (게이지, 방문수, 내 랭킹, 최근 뱃지) 반환"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 내 포인트 조회 (게이지 렌더링 및 등수 계산용)
            cursor.execute("SELECT point FROM users WHERE user_id = %s", (user_id,))
            user_info = cursor.fetchone()
            my_point = user_info['point'] if user_info and user_info['point'] else 0

            # 2. 방문 도장 개수 (visits 테이블에서 내 user_id 카운트)
            cursor.execute("SELECT COUNT(*) AS visit_count FROM visits WHERE user_id = %s", (user_id,))
            visit_count = cursor.fetchone()['visit_count']

            # 3. 내 랭킹 (나보다 점수가 높은 사람의 수 + 1)
            cursor.execute("SELECT COUNT(*) + 1 AS my_rank FROM users WHERE point > %s", (my_point,))
            my_rank = cursor.fetchone()['my_rank']

            # 4. 최근 획득 뱃지 이미지 (시간순 내림차순 정렬 후 1개 추출)
            cursor.execute("""
                SELECT a.icon_url 
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                WHERE ua.user_id = %s
                ORDER BY ua.earned_at DESC, ua.user_achievement_id DESC
                LIMIT 1
            """, (user_id,))
            latest_badge_row = cursor.fetchone()
            latest_badge_img = latest_badge_row['icon_url'] if latest_badge_row else None

            return {
                "point": my_point,
                "visit_count": visit_count,
                "my_rank": my_rank,
                "latest_badge_img": latest_badge_img
            }
    except Exception as e:
        print(f"❌ DB Error (get_ranking_summary): {e}")
        return None
    finally:
        conn.close()

def check_and_update_tier(user_id):
    """
    유저의 현재 점수를 확인하고, 기준점을 넘었으면 티어를 승급(DB 업데이트)시키는 함수
    (나중에 점수가 부여되는 액션이 발생할 때마다 호출할 예정입니다.)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 유저의 현재 점수와 티어 확인
            cursor.execute("SELECT point, tier FROM users WHERE user_id = %s", (user_id,))
            user_info = cursor.fetchone()
            if not user_info:
                return False

            current_point = user_info['point'] or 0
            current_tier = user_info['tier'] or 'BRONZE'

            # 2. 점수에 따른 새로운 랭크(티어) 계산
            new_tier = 'BRONZE'
            if current_point >= TIER_THRESHOLDS['DIAMOND']:
                new_tier = 'DIAMOND'
            elif current_point >= TIER_THRESHOLDS['PLATINUM']:
                new_tier = 'PLATINUM'
            elif current_point >= TIER_THRESHOLDS['GOLD']:
                new_tier = 'GOLD'
            elif current_point >= TIER_THRESHOLDS['SILVER']:
                new_tier = 'SILVER'

            # 3. 만약 새로 달성한 티어가 기존 티어와 다르면 DB 업데이트
            if new_tier != current_tier:
                cursor.execute("UPDATE users SET tier = %s WHERE user_id = %s", (new_tier, user_id))
                conn.commit()
                return True # 승급이 발생했음을 반환 
            
            return False # 승급하지 않음
    except Exception as e:
        conn.rollback()
        print(f"❌ DB Error (check_and_update_tier): {e}")
        return False
    finally:
        conn.close()

def process_mission(user_id, mission_type, points, is_weekly=False):
    """
    미션 달성 여부를 확인하고, 오늘(또는 이번 주) 처음 달성했다면 점수를 지급합니다.
    """
    
    now = datetime.datetime.now()
    
    if is_weekly:
        # ISO 달력 기준으로 '2026-W12' 형태로 주간 키 생성 (월요일 기준 갱신)
        year, week, _ = now.isocalendar()
        mission_key = f"{year}-W{week:02d}"
    else:
        # 일일 미션은 '2026-03-16' 형태로 생성
        mission_key = now.strftime("%Y-%m-%d")
        
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # SELECT로 미리 확인 PK 증발 차단
            check_sql = "SELECT 1 FROM user_missions WHERE user_id=%s AND mission_type=%s AND mission_key=%s"
            cursor.execute(check_sql, (user_id, mission_type, mission_key))
            if cursor.fetchone():
                return False # 이미 달성했으면 번호표 안 뽑고 조용히 종료
            
            # 미션 테이블에 Insert 시도 (UNIQUE 제약조건 덕분에 이미 받았으면 여기서 예외 발생!)
            insert_sql = """
                INSERT INTO user_missions (user_id, mission_type, mission_key, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(insert_sql, (user_id, mission_type, mission_key))
            
            # Insert가 무사히 통과되었다면 = 오늘 처음 달성한 것! -> 점수 지급
            update_sql = "UPDATE users SET point = point + %s WHERE user_id = %s"
            cursor.execute(update_sql, (points, user_id))
            
            conn.commit()
            return True # 보상 지급 완료!
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Mission Error: {e}")
        return False
    finally:
        conn.close()

def get_user_missions_status(user_id):
    from db import get_connection
    from routes.ranking.user_ranking_db import process_mission
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # --- 일일 통계 체크 ---
            # 일일 출석 횟수 (직접 출석체크 버튼을 눌렀는지 user_missions 확인)
            cursor.execute("SELECT COUNT(*) as cnt FROM user_missions WHERE user_id=%s AND mission_type='DAILY_ATTENDANCE' AND DATE(created_at) = CURDATE()", (user_id,))
            daily_attendance = cursor.fetchone()['cnt']
            
            # 영수증 도장(Visit) 횟수 (visits 테이블 확인)
            cursor.execute("""
                SELECT COUNT(DISTINCT v.visit_id) as cnt 
                FROM visits v
                JOIN visit_menus vm ON v.visit_id = vm.visit_id
                WHERE v.user_id=%s AND DATE(vm.created_at) = CURDATE()
            """, (user_id,))
            daily_visits = cursor.fetchone()['cnt']
            
            # 리뷰 횟수 (오늘 작성한 리뷰)
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM reviews r 
                JOIN visits v ON r.visit_id = v.visit_id 
                WHERE v.user_id=%s AND DATE(r.created_at) = CURDATE()
            """, (user_id,))
            daily_reviews = cursor.fetchone()['cnt']
            
            # --- 주간 통계 체크 ---
            cursor.execute("SELECT COUNT(*) as cnt FROM user_missions WHERE user_id=%s AND mission_type='DAILY_ATTENDANCE' AND YEARWEEK(created_at, 1) = YEARWEEK(NOW(), 1)", (user_id,))
            weekly_attendance = cursor.fetchone()['cnt']
            
            cursor.execute("""
                SELECT COUNT(DISTINCT v.visit_id) as cnt 
                FROM visits v
                JOIN visit_menus vm ON v.visit_id = vm.visit_id
                WHERE v.user_id=%s AND YEARWEEK(vm.created_at, 1) = YEARWEEK(NOW(), 1)
            """, (user_id,))
            weekly_visits = cursor.fetchone()['cnt']
            
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM reviews r 
                JOIN visits v ON r.visit_id = v.visit_id 
                WHERE v.user_id=%s AND YEARWEEK(r.created_at, 1) = YEARWEEK(NOW(), 1)
            """, (user_id,))
            weekly_reviews = cursor.fetchone()['cnt']
            
            # 일일 보상 조건 달성 시 자동 지급 (랭킹 탭을 여는 순간 못 받은 30점을 챙겨줍니다!)
            if daily_visits >= 1: 
                process_mission(user_id, 'DAILY_VISIT', 30, is_weekly=False)

            # 주간 보상 조건 달성 시 자동 지급 검사
            if weekly_attendance >= 5: process_mission(user_id, 'WEEKLY_ATTENDANCE', 100, is_weekly=True)
            if weekly_visits >= 5: process_mission(user_id, 'WEEKLY_VISIT', 50, is_weekly=True)
            if weekly_reviews >= 5: process_mission(user_id, 'WEEKLY_REVIEW', 20, is_weekly=True)

            # 프론트엔드로 보낼 JSON (즐겨찾기 제거, visit 추가)
            return {
                "daily": {
                    "attendance": {"count": daily_attendance, "target": 1, "reward": 10},
                    "visit": {"count": min(daily_visits, 1), "target": 1, "reward": 30},
                    "review": {"count": min(daily_reviews, 1), "target": 1, "reward": 50}
                },
                "weekly": {
                    "attendance": {"count": min(weekly_attendance, 5), "target": 5, "reward": 100},
                    "visit": {"count": min(weekly_visits, 5), "target": 5, "reward": 50},
                    "review": {"count": min(weekly_reviews, 5), "target": 5, "reward": 20}
                }
            }
    except Exception as e:
        print(f"❌ Mission Status Error: {e}")
        return None
    finally:
        conn.close()