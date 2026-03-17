# =========================
# 관리자 음식점 관리용 더미 데이터
# 나중에 DB 연결 전까지 임시로 사용
# =========================

# 카테고리 더미 데이터
DUMMY_CATEGORIES = [
    {"restaurant_category_id": 1, "restaurant_category_name": "한식"},
    {"restaurant_category_id": 2, "restaurant_category_name": "중식"},
    {"restaurant_category_id": 3, "restaurant_category_name": "일식"},
    {"restaurant_category_id": 4, "restaurant_category_name": "양식"},
    {"restaurant_category_id": 5, "restaurant_category_name": "카페"},
]

# 음식점 더미 데이터
DUMMY_RESTAURANTS = [
    {
        "restaurant_id": 1,
        "restaurant_name": "혜성식당",
        "restaurant_category_id": 1,
        "region_sigungu": "수원시",
        "address": "경기도 수원시 팔달구 어딘가 12",
        "phone": "031-111-2222",
    },
    {
        "restaurant_id": 2,
        "restaurant_name": "블랙라멘",
        "restaurant_category_id": 3,
        "region_sigungu": "성남시",
        "address": "경기도 성남시 분당구 어딘가 45",
        "phone": "031-333-4444",
    },
    {
        "restaurant_id": 3,
        "restaurant_name": "화이트카페",
        "restaurant_category_id": 5,
        "region_sigungu": "용인시",
        "address": "경기도 용인시 수지구 어딘가 78",
        "phone": "031-555-6666",
    },
]


# =========================
# 카테고리 id로 카테고리명 찾기
# =========================
def get_category_name(category_id):
    for category in DUMMY_CATEGORIES:
        if category["restaurant_category_id"] == category_id:
            return category["restaurant_category_name"]
    return "-"


# =========================
# 음식점 id로 음식점 1개 찾기
# =========================
def get_restaurant_by_id(restaurant_id):
    for restaurant in DUMMY_RESTAURANTS:
        if restaurant["restaurant_id"] == restaurant_id:
            return restaurant
    return None


# =========================
# 새 음식점 등록 시 다음 id 만들기
# =========================
def get_next_restaurant_id():
    if not DUMMY_RESTAURANTS:
        return 1
    return max(r["restaurant_id"] for r in DUMMY_RESTAURANTS) + 1