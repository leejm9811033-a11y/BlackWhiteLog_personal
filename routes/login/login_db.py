from db import get_connection
from werkzeug.security import generate_password_hash, check_password_hash


# =========================
# 일반 로그인 검증
# =========================
def verify_user_login(email, password):
    sql = """
        SELECT *
        FROM users
        WHERE email = %s
          AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                return user
            return None
    finally:
        conn.close()


# =========================
# 이메일로 회원 조회
# =========================
def find_user_by_email(email):
    sql = """
        SELECT user_id, email, nickname, password_hash, status
        FROM users
        WHERE email = %s
          AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 닉네임으로 회원 조회
# =========================
def find_user_by_nickname(nickname):
    sql = """
        SELECT user_id, email, nickname, status
        FROM users
        WHERE nickname = %s
          AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (nickname,))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 일반 회원가입
# =========================
def create_user(nickname, email, password):
    password_hash = generate_password_hash(password)

    sql = """
        INSERT INTO users (email, password_hash, nickname, role)
        VALUES (%s, %s, %s, 'USER')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email, password_hash, nickname))
        conn.commit()
    finally:
        conn.close()


# =========================
# 소셜 로그인용 사용자 조회
# provider + social_id 기준 조회
# =========================
def find_user_by_social(provider, social_id):
    sql = """
        SELECT
            u.user_id,
            u.email,
            u.nickname,
            u.profile_image_url,
            u.status,
            u.role,
            usa.provider,
            usa.provider_user_id
        FROM user_social_accounts usa
        INNER JOIN users u
            ON usa.user_id = u.user_id
        WHERE usa.provider = %s
          AND usa.provider_user_id = %s
          AND (u.status IS NULL OR u.status <> 'DELETED')
        LIMIT 1
    """

    provider = provider.upper()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 특정 유저에 특정 provider가 이미 연결되어 있는지 조회
# 예: 같은 user가 이미 KAKAO를 연결했는지
# =========================
def find_social_account_by_user(user_id, provider):
    sql = """
        SELECT social_account_id, user_id, provider, provider_user_id
        FROM user_social_accounts
        WHERE user_id = %s
          AND provider = %s
        LIMIT 1
    """

    provider = provider.upper()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id, provider))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 해당 소셜 계정이 이미 다른 계정에 연결되어 있는지 조회
# =========================
def is_social_account_already_linked(provider, social_id):
    sql = """
        SELECT social_account_id, user_id, provider, provider_user_id
        FROM user_social_accounts
        WHERE provider = %s
          AND provider_user_id = %s
        LIMIT 1
    """

    provider = provider.upper()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 기존 회원 계정에 소셜 계정 연결
# =========================
def link_social_account(user_id, provider, social_id):
    provider = provider.upper()

    existing_social = is_social_account_already_linked(provider, social_id)
    if existing_social:
        raise ValueError("이미 다른 계정에 연결된 소셜 계정입니다.")

    existing_provider_for_user = find_social_account_by_user(user_id, provider)
    if existing_provider_for_user:
        raise ValueError("이미 해당 소셜 계정이 연결되어 있습니다.")

    sql = """
        INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
        VALUES (%s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id, provider, social_id))
        conn.commit()
    finally:
        conn.close()


# =========================
# 소셜 회원가입
# 회원가입 폼을 거친 뒤 users + user_social_accounts 저장
# =========================
def create_social_user_with_form(nickname, email, password, provider, social_id, profile_image_url=None):
    provider = provider.upper()
    password_hash = generate_password_hash(password)

    user_sql = """
        INSERT INTO users (email, password_hash, nickname, profile_image_url, role)
        VALUES (%s, %s, %s, %s, 'USER')
    """

    social_sql = """
        INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
        VALUES (%s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(user_sql, (email, password_hash, nickname, profile_image_url))
            user_id = cursor.lastrowid

            cursor.execute(social_sql, (user_id, provider, social_id))

        conn.commit()
        return user_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =========================
# 닉네임으로 이메일 찾기
# =========================
def find_email_by_nickname(nickname):
    sql = """
        SELECT user_id, nickname, email
        FROM users
        WHERE nickname = %s
          AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (nickname,))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 이메일로 비밀번호 변경
# 이메일 인증 완료 후 사용
# =========================
def update_user_password_by_email(email, new_password):
    new_password_hash = generate_password_hash(new_password)

    sql = """
        UPDATE users
        SET password_hash = %s
        WHERE email = %s
          AND (status IS NULL OR status <> 'DELETED')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (new_password_hash, email))
            changed = cursor.rowcount > 0
        conn.commit()
        return changed
    finally:
        conn.close()


# =========================
# 비밀번호 재설정
# 이메일 + 닉네임 일치하는 회원의 비밀번호 변경
# 기존 방식 유지용
# =========================
def reset_user_password(email, nickname, new_password):
    new_password_hash = generate_password_hash(new_password)

    sql = """
        UPDATE users
        SET password_hash = %s
        WHERE email = %s
          AND nickname = %s
          AND (status IS NULL OR status <> 'DELETED')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (new_password_hash, email, nickname))
            changed = cursor.rowcount > 0
        conn.commit()
        return changed
    finally:
        conn.close()


# =========================
# 일반 회원 탈퇴 처리
# =========================
def withdraw_user(user_id):
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
# 탈퇴 회원 복구
# =========================
def restore_user(user_id):
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
# 닉네임 변경
# =========================
def update_user_nickname(user_id, new_nickname):
    sql = """
        UPDATE users
        SET nickname = %s
        WHERE user_id = %s
          AND (status IS NULL OR status <> 'DELETED')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (new_nickname, user_id))
            changed = cursor.rowcount > 0
        conn.commit()
        return changed
    finally:
        conn.close()