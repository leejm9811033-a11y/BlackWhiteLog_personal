import io
import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from flask import Blueprint, jsonify, request, session
from google import genai
from google.genai import types
from PIL import Image

from .visit_db import (
    create_visit_with_menus,
    find_menu_by_name,
    find_restaurant_id_by_store_name,
    exists_visit_same_day,
)

load_dotenv()

visit_bp = Blueprint("visit", __name__)
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL_ID = "models/gemini-flash-latest"

RECEIPT_PROMPT = """
이 영수증 이미지에서 다음 정보를 JSON 형식으로만 추출해줘.

반드시 아래 스키마를 지켜:
{
  "store_name": "가게 이름",
  "purchase_date": "YYYY-MM-DD",
  "items": [
    { "name": "메뉴명", "count": 숫자 }
  ]
}

규칙:
- 다른 설명, 마크다운, 코드블록 없이 순수 JSON만 응답
- 값이 확실하지 않으면 null 반환
- items가 없으면 빈 배열 반환
- count는 반드시 숫자
""".strip()


def analyze_receipt_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception as e:
        raise ValueError(f"이미지 로드 실패: {str(e)}")

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[image, RECEIPT_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            text = (response.text or "").strip()
            if not text:
                raise ValueError("모델 응답이 비어 있습니다.")

            return json.loads(text)

        except json.JSONDecodeError:
            raise ValueError("모델 응답이 JSON 형식이 아닙니다.")
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg and attempt < 2:
                time.sleep(10)
                continue
            raise ValueError(f"Gemini 호출 실패: {err_msg}")


def validate_receipt_payload(payload):
    if not isinstance(payload, dict):
        return False

    store_name = str(payload.get("store_name") or "").strip()
    purchase_date = str(payload.get("purchase_date") or "").strip()
    items = payload.get("items")

    if not store_name or store_name.lower() == "null":
        return False

    if not purchase_date or purchase_date.lower() == "null":
        return False

    try:
        datetime.strptime(purchase_date, "%Y-%m-%d")
    except ValueError:
        return False

    if not isinstance(items, list) or not items:
        return False

    for item in items:
        if not isinstance(item, dict):
            return False

        item_name = str(item.get("name") or "").strip()
        count = item.get("count")

        if not item_name or item_name.lower() == "null":
            return False

        if count in (None, "", "null"):
            return False

        try:
            if int(count) <= 0:
                return False
        except Exception:
            return False

    return True


@visit_bp.route("/api/visits/receipt", methods=["POST"])
def register_visit_by_receipt():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({
            "success": False,
            "message": "로그인 후 이용해 주세요."
        }), 401

    if "receipt_image" not in request.files:
        return jsonify({
            "success": False,
            "message": "영수증 사진을 업로드해 주세요."
        }), 400

    file = request.files["receipt_image"]
    if not file or file.filename == "":
        return jsonify({
            "success": False,
            "message": "영수증 사진을 업로드해 주세요."
        }), 400

    try:
        image_bytes = file.read()
        payload = analyze_receipt_image(image_bytes)

        if not validate_receipt_payload(payload):
            return jsonify({
                "success": False,
                "message": "영수증을 다시 찍어주세요!",
                "analysis": payload
            }), 422

        restaurant = find_restaurant_id_by_store_name(payload["store_name"])
        if not restaurant:
            return jsonify({
                "success": False,
                "message": "등록할 수 있는 음식점을 찾지 못했습니다.",
                "analysis": payload
            }), 404
        # 같은 날 같은 음식점 도장 중복 검사
        if exists_visit_same_day(
            user_id=user_id,
            restaurant_id=restaurant["restaurant_id"],
            purchase_date=payload["purchase_date"]
        ):
            return jsonify({
                "success": False,
                "message": "같은 날 같은 음식점에는 도장을 한 번만 찍을 수 있습니다."
            }), 409

        resolved_items = []
        unmatched_items = []

        for item in payload["items"]:
            menu = find_menu_by_name(restaurant["restaurant_id"], item["name"])
            if not menu:
                unmatched_items.append(item["name"])
                continue

            resolved_items.append({
                "menu_id": menu["menu_id"],
                "menu_name": menu["menu_name"],
                "quantity": int(item["count"]),
            })

        if not resolved_items:
            return jsonify({
                "success": False,
                "message": "영수증 메뉴를 확인할 수 없습니다. 영수증을 다시 찍어주세요!",
                "analysis": payload,
                "unmatched_items": unmatched_items
            }), 422

        visit_id = create_visit_with_menus(
            user_id=user_id,
            restaurant_id=restaurant["restaurant_id"],
            purchase_date=payload["purchase_date"],
            items=resolved_items
        )
        
        # 영수증 도장 찍히자마자 즉시 30점 지급 & 티어 검사
        try:
            from routes.ranking.user_ranking_db import process_mission, check_and_update_tier
            if process_mission(user_id, 'DAILY_VISIT', 30, is_weekly=False):
                check_and_update_tier(user_id)
        except Exception as e:
            print(f"방문 점수 즉시 지급 오류: {e}")

        return jsonify({
            "success": True,
            "message": "등록완료!",
            "visit_id": visit_id,
            "restaurant_id": restaurant["restaurant_id"],
            "restaurant_name": restaurant["name"],
            "unmatched_items": unmatched_items
        })

    except ValueError as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"등록 중 오류가 발생했습니다: {str(e)}"
        }), 500
