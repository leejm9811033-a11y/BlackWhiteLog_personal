from flask import render_template, request, jsonify, session, redirect, url_for, flash
from db import fetch_categories
import routes.owner.owner_menu_db as owner_db
import routes.owner.owner_notices_db as owner_notice_db
import routes.owner.owner_board_db as owner_board_db
import routes.owner.owner_review_db as owner_review_db
import math


def register_owner_routes(app):

    def require_owner_approved():
        user_id = session.get("user_id")

        if not user_id:
            flash("로그인이 필요합니다.")
            return None, redirect(url_for("login.login"))

        if owner_db.has_approved_restaurant(user_id):
            return user_id, None

        if owner_db.has_pending_restaurant(user_id):
            flash("현재 판매자 승인 대기 중입니다.")
        else:
            flash("판매자 승인 후 이용할 수 있습니다.")

        return None, redirect(url_for("seller_register"))
    # -------------------------------------------------------------------------------------
    # 오너 보드 페이지
    # -------------------------------------------------------------------------------------
    @app.route("/owner/board", endpoint="owner_board")
    def owner_board():
        # -------------------------------------------------------------------------
        # 로그인 세션에서 현재 사용자 / 오너 정보 조회
        # - user_id: 로그인한 사용자
        # - owner_id: owners 테이블에서 조회 후 세션에 저장된 판매자 번호
        # -------------------------------------------------------------------------
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        
        #'''  승인 받으면 owner_board 화면이동 '''
        #owner_id, redirect_response = require_owner_approved()
        #if redirect_response:
        #    return redirect_response

        #total_menu_count = owner_db.get_menu_count_by_owner(owner_id)

        #return render_template(
        #    "owner/owner_board.html",
        #    total_menu_count=total_menu_count
        #)

        # -------------------------------------------------------------------------
        # 판매자 세션이 없으면 보드 진입 불가
        # - 일반 사용자이거나
        # - owner_id 세션이 아직 저장되지 않은 상태
        # -------------------------------------------------------------------------
        if not session_user_id or not session_owner_id:
            return redirect(url_for("index"))
        restaurant_menu_list = owner_db.get_menu_count_by_owner(session_owner_id)
        # -------------------------------------------------------------------------
        # 현재 로그인한 owner_id 기준으로 메뉴 수 요약 조회
        # -------------------------------------------------------------------------
        try:
            # ---------------------------------------------------------------------
            # 현재 로그인한 owner_id 기준으로 가게 목록 조회
            # ---------------------------------------------------------------------
            db_sidebar_restaurant_list = owner_board_db.get_restaurant_list_by_owner(session_owner_id)

            # ---------------------------------------------------------------------
            # 첫 번째 가게를 기본 선택값으로 사용
            # ---------------------------------------------------------------------
            if db_sidebar_restaurant_list:
                sidebar_selected_restaurant_id = db_sidebar_restaurant_list[0]["restaurant_id"]
                sidebar_selected_restaurant_name = db_sidebar_restaurant_list[0]["name"]
            else:
                sidebar_selected_restaurant_id = None
                sidebar_selected_restaurant_name = ""
                db_sidebar_restaurant_list = []

            # ---------------------------------------------------------------------
            # 공지 / 리뷰 / 방문자 차트 기본값
            # ---------------------------------------------------------------------
            sidebar_notice_current = None
            db_sidebar_notice_history_list = []
            sidebar_store_image_url = None
            board_review_data = {
                "march_review_count": 0,
                "review_list": []
            }
            visit_chart_data = []


            # ---------------------------------------------------------------------
            # 가게가 존재할 때만 공지 / 리뷰 데이터 조회
            # ---------------------------------------------------------------------
            if sidebar_selected_restaurant_id:
                sidebar_store_image_url = owner_board_db.get_store_image_url_by_restaurant(
                    sidebar_selected_restaurant_id
                )
                db_current_notice = owner_board_db.get_sidebar_current_notice_by_restaurant(
                    sidebar_selected_restaurant_id
                )

                if db_current_notice:
                    sidebar_notice_current = {
                        "notice_id": db_current_notice["notice_id"],
                        "restaurant_id": db_current_notice["restaurant_id"],
                        "notice_title": db_current_notice["notice_title"],
                        "notice_content": db_current_notice["notice_content"],
                        "updated_at": db_current_notice["updated_at"].strftime("%Y-%m-%d") if db_current_notice["updated_at"] else ""
                    }

                db_history_notice_list = owner_board_db.get_sidebar_history_notice_list_by_restaurant(
                    sidebar_selected_restaurant_id,
                    limit=3
                )

                for db_notice in db_history_notice_list:
                    db_sidebar_notice_history_list.append({
                        "notice_id": db_notice["notice_id"],
                        "restaurant_id": db_notice["restaurant_id"],
                        "notice_title": db_notice["notice_title"],
                        "notice_content": db_notice["notice_content"],
                        "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
                    })

                board_review_data = owner_review_db.get_board_review_summary_by_restaurant(
                    sidebar_selected_restaurant_id,
                    limit=3
                )
                # -----------------------------------------------------------------
                # 방문자 수 차트 데이터 조회
                # - 최근 10일
                # - 하루가 지나면 자동으로 1칸씩 밀리는 구조
                # -----------------------------------------------------------------
                visit_chart_data = owner_board_db.get_visit_chart_by_restaurant(
                    sidebar_selected_restaurant_id
                )

                
        except Exception as error:
            print("owner_board error =", error)

            db_sidebar_restaurant_list = []
            sidebar_selected_restaurant_id = None
            sidebar_selected_restaurant_name = ""
            sidebar_notice_current = None
            sidebar_store_image_url = None
            db_sidebar_notice_history_list = []
            board_review_data = {
                "march_review_count": 0,
                "review_list": []
            }
            visit_chart_data = []
        return render_template(
            "owner/owner_board.html",
            restaurant_menu_list=restaurant_menu_list,
            session_user_id=session_user_id,
            session_owner_id=session_owner_id,
            sidebar_restaurant_list=db_sidebar_restaurant_list,
            sidebar_selected_restaurant_id=sidebar_selected_restaurant_id,
            sidebar_selected_restaurant_name=sidebar_selected_restaurant_name,
            sidebar_notice_current=sidebar_notice_current,
            sidebar_notice_history_list=db_sidebar_notice_history_list,
            board_review_data=board_review_data,
            visit_chart_data=visit_chart_data,
            sidebar_store_image_url=sidebar_store_image_url
        )

    # -------------------------------------------------------------------------
    # 보드 공지사항 SPA API
    # -------------------------------------------------------------------------
    @app.route("/owner/board/api/notice_summary", methods=["GET"], endpoint="owner_board_api_notice_summary")
    def owner_board_api_notice_summary():
        session_user_id, session_owner_id = require_owner_session()

        if not session_user_id or not session_owner_id:
            return jsonify({
                "success": False,
                "message": "로그인이 필요합니다."
            }), 401

        client_restaurant_id = request.args.get("restaurant_id", type=int)

        try:
            selected_restaurant_id, restaurant_list = get_selected_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            current_notice = None
            history_notice_list = []

            db_current_notice = owner_board_db.get_sidebar_current_notice_by_restaurant(
                selected_restaurant_id
            )

            if db_current_notice:
                current_notice = {
                    "notice_id": db_current_notice["notice_id"],
                    "restaurant_id": db_current_notice["restaurant_id"],
                    "notice_title": db_current_notice["notice_title"],
                    "notice_content": db_current_notice["notice_content"],
                    "updated_at": db_current_notice["updated_at"].strftime("%Y-%m-%d") if db_current_notice["updated_at"] else ""
                }

            db_history_notice_list = owner_board_db.get_sidebar_history_notice_list_by_restaurant(
                selected_restaurant_id,
                limit=3
            )

            for db_notice in db_history_notice_list:
                history_notice_list.append({
                    "notice_id": db_notice["notice_id"],
                    "restaurant_id": db_notice["restaurant_id"],
                    "notice_title": db_notice["notice_title"],
                    "notice_content": db_notice["notice_content"],
                    "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
                })

            return jsonify({
                "success": True,
                "message": "사이드바 공지사항 조회 완료",
                "restaurant_id": selected_restaurant_id,
                "restaurant_list": restaurant_list,
                "current_notice": current_notice,
                "history_notice_list": history_notice_list
            })

        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500
        
    @app.route("/owner/board/api/store_image/upload", methods=["POST"], endpoint="owner_board_api_store_image_upload")
    def owner_board_api_store_image_upload():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            return jsonify({
                "success": False,
                "message": "로그인이 필요합니다."
            }), 401

        client_restaurant_id = request.form.get("restaurant_id", type=int)
        store_image = request.files.get("store_image")

        if not client_restaurant_id:
            return jsonify({
                "success": False,
                "message": "가게 정보가 올바르지 않습니다."
            }), 400

        if not store_image or not store_image.filename:
            return jsonify({
                "success": False,
                "message": "업로드할 이미지를 선택해주세요."
            }), 400

        if not owner_db.allowed_file(store_image.filename):
            return jsonify({
                "success": False,
                "message": "허용 확장자: jpg, jpeg, png, gif, webp"
            }), 400

        try:
            selected_restaurant_id, _ = get_selected_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            image_url = owner_board_db.save_store_image(
                restaurant_id=selected_restaurant_id,
                image_file=store_image
            )

            return jsonify({
                "success": True,
                "message": "가게 사진이 등록되었습니다.",
                "restaurant_id": selected_restaurant_id,
                "image_url": image_url
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500
# --------------------------------------------------------------------------------------
# 오너 메뉴 관리 페이지
# --------------------------------------------------------------------------------------
    # 수정: 메뉴 목록/개수 조회 기준이 owner_id 대신 restaurant_id가 되도록 함수 매개변수 변경
    def build_menu_list_payload(restaurant_id, page=1, per_page=5):
        # 수정: 총 메뉴 개수 조회도 restaurant_id 기준 함수로 변경
        total_menu_count = owner_db.get_menu_count_by_restaurant(restaurant_id)
        total_pages = math.ceil(total_menu_count / per_page) if total_menu_count > 0 else 1

        if page < 1:
            page = 1

        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        # 수정: 메뉴 목록 조회 시 owner_id 대신 restaurant_id 전달
        db_menu_list = owner_db.get_menu_list_by_owner(
            restaurant_id=restaurant_id,
            limit=per_page,
            offset=offset
        )

        menu_list = []
        for db_menu in db_menu_list:
            menu_list.append({
                "menu_id": db_menu["menu_id"],
                "menu_name": db_menu["menu_name"],
                "price": int(db_menu["price"]) if db_menu["price"] is not None else 0,
                "status": db_menu["status"],
                "menu_category_name": db_menu["menu_category_name"] or "",
                "menu_category_id": db_menu["menu_category_id"],
                "image_url": db_menu["image_url"],
                "thumb_url": db_menu["thumb_url"],
                "original_name": db_menu["original_name"]
            })

        return {
            "menu_list": menu_list,
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "total_menu_count": total_menu_count
        }

    # 수정: 오너가 가진 여러 가게 중 현재 선택된 restaurant_id를 결정하는 공통 함수 추가
    def get_selected_restaurant_id(session_owner_id, client_restaurant_id=None):
        restaurant_list = owner_db.get_restaurant_list_by_owner(session_owner_id)

        if not restaurant_list:
            raise ValueError("등록된 가게가 없습니다.")

        restaurant_id_list = [row["restaurant_id"] for row in restaurant_list]

        if client_restaurant_id is not None:
            try:
                selected_restaurant_id = int(client_restaurant_id)
            except (TypeError, ValueError):
                selected_restaurant_id = restaurant_id_list[0]

            if selected_restaurant_id not in restaurant_id_list:
                selected_restaurant_id = restaurant_id_list[0]
        else:
            selected_restaurant_id = restaurant_id_list[0]

        return selected_restaurant_id, restaurant_list

    @app.route("/owner/menu_management", methods=["GET"], endpoint="owner_menu_management")
    def owner_menu_management():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        db_owner = owner_db.get_owner_info(session_owner_id)
        db_categories = owner_db.get_menu_categories()

        selected_restaurant_id, restaurant_list = get_selected_restaurant_id(session_owner_id)

        initial_payload = build_menu_list_payload(
            restaurant_id=selected_restaurant_id,
            page=1,
            per_page=5
        )

        return render_template(
            "owner/owner_menu_management.html",
            owner=db_owner,
            restaurant_list=restaurant_list,
            selected_restaurant_id=selected_restaurant_id,
            categories=db_categories,
            initial_payload=initial_payload,
            session_user_id=session_user_id,
            session_owner_id=session_owner_id
        )

    @app.route("/owner/menu_management/api/list", methods=["GET"], endpoint="owner_menu_management_api_list")
    def owner_menu_management_api_list():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)
        page = request.args.get("page", default=1, type=int)

        selected_restaurant_id, restaurant_list = get_selected_restaurant_id(
            session_owner_id,
            client_restaurant_id
        )

        payload = build_menu_list_payload(
            restaurant_id=selected_restaurant_id,
            page=page,
            per_page=5
        )

        return jsonify({
            "success": True,
            "message": "메뉴 목록 조회 완료",
            "restaurant_id": selected_restaurant_id,
            "restaurant_list": restaurant_list,
            **payload
        })

    @app.route("/owner/menu_management/api/detail/<int:menu_id>", methods=["GET"], endpoint="owner_menu_management_api_detail")
    def owner_menu_management_api_detail(menu_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)

        selected_restaurant_id, _ = get_selected_restaurant_id(
            session_owner_id,
            client_restaurant_id
        )

        db_menu_detail = owner_db.get_menu_detail_by_id(selected_restaurant_id, menu_id)

        if not db_menu_detail:
            return jsonify({
                "success": False,
                "message": "메뉴 정보를 찾을 수 없습니다."
            }), 404

        return jsonify({
            "success": True,
            "message": "메뉴 상세 조회 완료",
            "menu_id": db_menu_detail["menu_id"],
            "restaurant_id": db_menu_detail["restaurant_id"],
            "menu_category_id": db_menu_detail["menu_category_id"],
            "menu_name": db_menu_detail["menu_name"],
            "price": int(db_menu_detail["price"]) if db_menu_detail["price"] is not None else 0,
            "status": db_menu_detail["status"],
            "image_url": db_menu_detail["image_url"],
            "thumb_url": db_menu_detail["thumb_url"],
            "original_name": db_menu_detail["original_name"]
        })

    @app.route("/owner/menu_management/api/save", methods=["POST"], endpoint="owner_menu_management_api_save")
    def owner_menu_management_api_save():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")
        print("request.form =", request.form)
        print("request.files =", request.files)

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_menu_id = request.form.get("client_menu_id", "").strip()
        client_menu_name = request.form.get("client_menu_name", "").strip()
        client_price = request.form.get("client_price", "").strip()
        client_menu_category_id = request.form.get("client_menu_category_id", "").strip()
        client_remove_image = request.form.get("client_remove_image", "").strip()
        client_soldout = request.form.get("client_soldout", "").strip()
        client_page = request.form.get("client_page", default="1").strip()
        client_menu_image = request.files.get("client_menu_image")

        if not client_menu_name or not client_price or not client_menu_category_id:
            return jsonify({
                "success": False,
                "message": "메뉴명, 가격, 카테고리는 필수입니다."
            }), 400

        if client_menu_image and client_menu_image.filename and not owner_db.allowed_file(client_menu_image.filename):
            return jsonify({
                "success": False,
                "message": "허용 확장자: jpg, jpeg, png, gif, webp"
            }), 400

        menu_status = "OFF" if client_soldout == "Y" else "ON"

        try:
            restaurant_id, _ = get_selected_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            if client_menu_id:
                owner_db.update_menu(
                    restaurant_id=restaurant_id,
                    menu_id=int(client_menu_id),
                    menu_category_id=int(client_menu_category_id),
                    menu_name=client_menu_name,
                    price=int(client_price),
                    status=menu_status,
                    image_file=client_menu_image,
                    remove_image=True if client_remove_image == "Y" else False
                )

                action_message = "메뉴가 수정되었습니다."
                saved_menu_id = int(client_menu_id)
            else:
                saved_menu_id = owner_db.insert_menu(
                    restaurant_id=restaurant_id,
                    menu_category_id=int(client_menu_category_id),
                    menu_name=client_menu_name,
                    price=int(client_price),
                    status=menu_status,
                    image_file=client_menu_image
                )
                action_message = "메뉴가 등록되었습니다."

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_menu_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": action_message,
                "menu_id": saved_menu_id,
                "restaurant_id": restaurant_id,
                "session_user_id": session_user_id,
                "session_owner_id": session_owner_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/menu_management/api/delete/<int:menu_id>", methods=["POST"], endpoint="owner_menu_management_api_delete")
    def owner_menu_management_api_delete(menu_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_page = request.form.get("client_page", default="1").strip()
        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()

        try:
            restaurant_id, _ = get_selected_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            owner_db.delete_menu(restaurant_id, menu_id)

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_menu_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": "메뉴가 삭제되었습니다.",
                "menu_id": menu_id,
                "restaurant_id": restaurant_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


    # 이종민 추가 레스트롱 추가 페이지 추가 S

    @app.route("/owner/additional", endpoint="owner_addtional_management")
    def owner_addtional_management():
        return redirect(url_for("seller_register"))

    # 이종민 추가 레스트롱 추가 페이지 추가 E













# -------------------------------------------------------------------------------------
# 오너 공지 관리 페이지
# -------------------------------------------------------------------------------------
    def build_notice_list_payload(restaurant_id, page=1, per_page=5):
        total_notice_count = owner_notice_db.get_notice_count_by_restaurant(restaurant_id)
        total_pages = math.ceil(total_notice_count / per_page) if total_notice_count > 0 else 1

        if page < 1:
            page = 1

        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        db_notice_list = owner_notice_db.get_notice_list_by_restaurant(
            restaurant_id=restaurant_id,
            limit=per_page,
            offset=offset
        )

        notice_list = []
        for db_notice in db_notice_list:
            notice_list.append({
                "notice_id": db_notice["notice_id"],
                "owner_id": db_notice["owner_id"],
                "restaurant_id": db_notice["restaurant_id"],
                "user_id": db_notice["user_id"],
                "notice_url": db_notice["notice_url"],
                "thumb_url": db_notice["thumb_url"],
                "notice_title": db_notice["notice_title"],
                "notice_content": db_notice["notice_content"],
                "is_pinned": int(db_notice["is_pinned"]) if db_notice["is_pinned"] is not None else 0,
                "created_at": db_notice["created_at"].strftime("%Y-%m-%d") if db_notice["created_at"] else "",
                "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
            })

        return {
            "notice_list": notice_list,
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "total_notice_count": total_notice_count
        }

    def get_selected_notice_restaurant_id(session_owner_id, client_restaurant_id=None):
        restaurant_list = owner_notice_db.get_restaurant_list_by_owner(session_owner_id)

        if not restaurant_list:
            raise ValueError("등록된 가게가 없습니다.")

        restaurant_id_list = [row["restaurant_id"] for row in restaurant_list]

        if client_restaurant_id is not None:
            try:
                selected_restaurant_id = int(client_restaurant_id)
            except (TypeError, ValueError):
                selected_restaurant_id = restaurant_id_list[0]

            if selected_restaurant_id not in restaurant_id_list:
                selected_restaurant_id = restaurant_id_list[0]
        else:
            selected_restaurant_id = restaurant_id_list[0]

        return selected_restaurant_id, restaurant_list

    @app.route("/owner/notice_management", methods=["GET"], endpoint="owner_notice_management")
    def owner_notice_management():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)

        selected_restaurant_id, restaurant_list = get_selected_notice_restaurant_id(
            session_owner_id,
            client_restaurant_id
        )

        initial_payload = build_notice_list_payload(
            restaurant_id=selected_restaurant_id,
            page=1,
            per_page=5
        )

        return render_template(
            "owner/owner_notice_management.html",
            restaurant_list=restaurant_list,
            selected_restaurant_id=selected_restaurant_id,
            initial_payload=initial_payload,
            session_user_id=session_user_id,
            session_owner_id=session_owner_id
        )

    @app.route("/owner/notice_management/api/list", methods=["GET"], endpoint="owner_notice_management_api_list")
    def owner_notice_management_api_list():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)
        page = request.args.get("page", default=1, type=int)

        try:
            selected_restaurant_id, restaurant_list = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            payload = build_notice_list_payload(
                restaurant_id=selected_restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": "공지사항 목록 조회 완료",
                "restaurant_id": selected_restaurant_id,
                "restaurant_list": restaurant_list,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/notice_management/api/detail/<int:notice_id>", methods=["GET"], endpoint="owner_notice_management_api_detail")
    def owner_notice_management_api_detail(notice_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)

        try:
            selected_restaurant_id, _ = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            db_notice = owner_notice_db.get_notice_detail_by_id(selected_restaurant_id, notice_id)

            if not db_notice:
                return jsonify({
                    "success": False,
                    "message": "공지사항 정보를 찾을 수 없습니다."
                }), 404

            return jsonify({
                "success": True,
                "message": "공지사항 상세 조회 완료",
                "notice_id": db_notice["notice_id"],
                "owner_id": db_notice["owner_id"],
                "restaurant_id": db_notice["restaurant_id"],
                "user_id": db_notice["user_id"],
                "notice_url": db_notice["notice_url"],
                "thumb_url": db_notice["thumb_url"],
                "notice_title": db_notice["notice_title"],
                "notice_content": db_notice["notice_content"],
                "is_pinned": int(db_notice["is_pinned"]) if db_notice["is_pinned"] is not None else 0,
                "created_at": db_notice["created_at"].strftime("%Y-%m-%d") if db_notice["created_at"] else "",
                "updated_at": db_notice["updated_at"].strftime("%Y-%m-%d") if db_notice["updated_at"] else ""
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/notice_management/api/save", methods=["POST"], endpoint="owner_notice_management_api_save")
    def owner_notice_management_api_save():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_notice_id = request.form.get("client_notice_id", "").strip()
        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_notice_title = request.form.get("client_notice_title", "").strip()
        client_notice_content = request.form.get("client_notice_content", "").strip()
        client_is_pinned = request.form.get("client_is_pinned", "").strip()
        client_remove_image = request.form.get("client_remove_image", "").strip()
        client_page = request.form.get("client_page", default="1").strip()
        client_notice_image = request.files.get("client_notice_image")

        if not client_notice_title or not client_notice_content:
            return jsonify({
                "success": False,
                "message": "공지사항 제목과 내용은 필수입니다."
            }), 400

        if client_notice_image and client_notice_image.filename and not owner_notice_db.allowed_file(client_notice_image.filename):
            return jsonify({
                "success": False,
                "message": "허용 확장자: jpg, jpeg, png, gif, webp"
            }), 400

        try:
            restaurant_id, _ = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            is_pinned = 1 if client_is_pinned == "Y" else 0

            if client_notice_id:
                owner_notice_db.update_notice(
                    restaurant_id=restaurant_id,
                    notice_id=int(client_notice_id),
                    notice_title=client_notice_title,
                    notice_content=client_notice_content,
                    is_pinned=is_pinned,
                    image_file=client_notice_image,
                    remove_image=True if client_remove_image == "Y" else False
                )
                saved_notice_id = int(client_notice_id)
                action_message = "공지사항이 수정되었습니다."
            else:
                saved_notice_id = owner_notice_db.insert_notice(
                    owner_id=session_owner_id,
                    restaurant_id=restaurant_id,
                    user_id=session_user_id,
                    notice_title=client_notice_title,
                    notice_content=client_notice_content,
                    is_pinned=is_pinned,
                    image_file=client_notice_image
                )
                action_message = "공지사항이 등록되었습니다."

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_notice_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": action_message,
                "notice_id": saved_notice_id,
                "restaurant_id": restaurant_id,
                "session_user_id": session_user_id,
                "session_owner_id": session_owner_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500

    @app.route("/owner/notice_management/api/delete/<int:notice_id>", methods=["POST"], endpoint="owner_notice_management_api_delete")
    def owner_notice_management_api_delete(notice_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_page = request.form.get("client_page", default="1").strip()

        try:
            restaurant_id, _ = get_selected_notice_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            owner_notice_db.delete_notice(restaurant_id, notice_id)

            page = int(client_page) if str(client_page).isdigit() else 1
            payload = build_notice_list_payload(
                restaurant_id=restaurant_id,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": "공지사항이 삭제되었습니다.",
                "notice_id": notice_id,
                "restaurant_id": restaurant_id,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


# ------------------------------------------------------------------------------------
# 오너 리뷰 관리 페이지
# ------------------------------------------------------------------------------------
    def get_selected_review_restaurant_id(session_owner_id, client_restaurant_id=None):
        db_restaurant_list = owner_review_db.get_restaurant_list_by_owner(session_owner_id)

        if not db_restaurant_list:
            raise ValueError("등록된 가게가 없습니다.")

        db_restaurant_id_list = [db_row["restaurant_id"] for db_row in db_restaurant_list]

        if client_restaurant_id is not None:
            try:
                selected_restaurant_id = int(client_restaurant_id)
            except (TypeError, ValueError):
                selected_restaurant_id = db_restaurant_id_list[0]

            if selected_restaurant_id not in db_restaurant_id_list:
                selected_restaurant_id = db_restaurant_id_list[0]
        else:
            selected_restaurant_id = db_restaurant_id_list[0]

        return selected_restaurant_id, db_restaurant_list


    def convert_review_row_to_payload(db_review):
        if not db_review:
            return None

        db_reply_is_active = int(db_review["is_active"]) if db_review["is_active"] is not None else 0
        db_reply_is_visible = int(db_review["is_visible"]) if db_review["is_visible"] is not None else 1

        if db_reply_is_visible == 0:
            review_status_text = "숨김"
        elif db_reply_is_active == 1:
            review_status_text = "답변완료"
        else:
            review_status_text = "미답변"

        review_content_preview = db_review["content"] or ""
        if len(review_content_preview) > 36:
            review_content_preview = review_content_preview[:36] + "..."

        return {
            "review_id": db_review["review_id"],
            "visit_id": db_review["visit_id"],
            "user_id": db_review["user_id"],
            "nickname": db_review["nickname"] or "",
            "rating": int(db_review["rating"]) if db_review["rating"] is not None else 0,
            "rating_text": "★" * int(db_review["rating"] or 0) + "☆" * (5 - int(db_review["rating"] or 0)),
            "content": db_review["content"] or "",
            "content_preview": review_content_preview,
            "created_at": db_review["created_at"].strftime("%Y-%m-%d") if db_review["created_at"] else "",
            "updated_at": db_review["updated_at"].strftime("%Y-%m-%d") if db_review["updated_at"] else "",
            "reply_id": db_review["reply_id"],
            "reply_content": db_review["reply_content"] or "",
            "is_active": db_reply_is_active,
            "is_visible": db_reply_is_visible,
            "review_status_text": review_status_text
        }


    def build_review_list_payload(
        db_restaurant_id,
        client_tab_status="all",
        client_sort_type="latest",
        client_search_keyword="",
        page=1,
        per_page=5
    ):
        total_review_count = owner_review_db.get_review_count_by_restaurant(
            db_restaurant_id=db_restaurant_id,
            client_tab_status=client_tab_status,
            client_search_keyword=client_search_keyword
        )

        total_pages = math.ceil(total_review_count / per_page) if total_review_count > 0 else 1

        if page < 1:
            page = 1

        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        db_review_list = owner_review_db.get_review_list_by_restaurant(
            db_restaurant_id=db_restaurant_id,
            client_tab_status=client_tab_status,
            client_sort_type=client_sort_type,
            client_search_keyword=client_search_keyword,
            limit=per_page,
            offset=offset
        )

        review_list = []
        for db_review in db_review_list:
            review_list.append(convert_review_row_to_payload(db_review))

        selected_review_id = review_list[0]["review_id"] if review_list else None

        return {
            "review_list": review_list,
            "selected_review_id": selected_review_id,
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "total_review_count": total_review_count,
            "tab_status": client_tab_status,
            "sort_type": client_sort_type,
            "search_keyword": client_search_keyword
        }


    @app.route("/owner/review_management", methods=["GET"], endpoint="owner_review_management")
    def owner_review_management():
        session_user_id = session.get("user_id")
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)
        client_tab_status = request.args.get("tab", default="all", type=str).strip().lower()
        client_sort_type = request.args.get("sort", default="latest", type=str).strip().lower()
        client_search_keyword = request.args.get("keyword", default="", type=str).strip()

        if client_tab_status not in ["all", "pending", "done", "hidden"]:
            client_tab_status = "all"

        if client_sort_type not in ["latest", "rating"]:
            client_sort_type = "latest"

        selected_restaurant_id, db_restaurant_list = get_selected_review_restaurant_id(
            session_owner_id,
            client_restaurant_id
        )

        db_owner = owner_review_db.get_owner_info(session_owner_id)
        db_summary = owner_review_db.get_review_summary_by_restaurant(selected_restaurant_id)

        initial_payload = build_review_list_payload(
            db_restaurant_id=selected_restaurant_id,
            client_tab_status=client_tab_status,
            client_sort_type=client_sort_type,
            client_search_keyword=client_search_keyword,
            page=1,
            per_page=5
        )

        db_detail_review = None
        if initial_payload["selected_review_id"]:
            db_detail_review = owner_review_db.get_review_detail_by_review_id(
                db_restaurant_id=selected_restaurant_id,
                db_review_id=initial_payload["selected_review_id"]
            )

        detail_review = convert_review_row_to_payload(db_detail_review)
        selected_restaurant_name = owner_review_db.get_restaurant_name_by_restaurant_id(selected_restaurant_id)

        return render_template(
            "owner/owner_review_management.html",
            owner=db_owner,
            restaurant_list=db_restaurant_list,
            selected_restaurant_id=selected_restaurant_id,
            selected_restaurant_name=selected_restaurant_name,
            summary_data=db_summary,
            initial_payload=initial_payload,
            detail_review=detail_review,
            session_user_id=session_user_id,
            session_owner_id=session_owner_id
        )


    @app.route("/owner/review_management/api/list", methods=["GET"], endpoint="owner_review_management_api_list")
    def owner_review_management_api_list():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)
        client_tab_status = request.args.get("tab", default="all", type=str).strip().lower()
        client_sort_type = request.args.get("sort", default="latest", type=str).strip().lower()
        client_search_keyword = request.args.get("keyword", default="", type=str).strip()
        page = request.args.get("page", default=1, type=int)

        if client_tab_status not in ["all", "pending", "done", "hidden"]:
            client_tab_status = "all"

        if client_sort_type not in ["latest", "rating"]:
            client_sort_type = "latest"

        try:
            selected_restaurant_id, db_restaurant_list = get_selected_review_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            db_summary = owner_review_db.get_review_summary_by_restaurant(selected_restaurant_id)

            payload = build_review_list_payload(
                db_restaurant_id=selected_restaurant_id,
                client_tab_status=client_tab_status,
                client_sort_type=client_sort_type,
                client_search_keyword=client_search_keyword,
                page=page,
                per_page=5
            )

            return jsonify({
                "success": True,
                "message": "리뷰 목록 조회 완료",
                "restaurant_id": selected_restaurant_id,
                "restaurant_list": db_restaurant_list,
                "summary_data": db_summary,
                **payload
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


    @app.route("/owner/review_management/api/detail/<int:review_id>", methods=["GET"], endpoint="owner_review_management_api_detail")
    def owner_review_management_api_detail(review_id):
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.args.get("restaurant_id", type=int)

        try:
            selected_restaurant_id, _ = get_selected_review_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            db_review = owner_review_db.get_review_detail_by_review_id(
                db_restaurant_id=selected_restaurant_id,
                db_review_id=review_id
            )

            if not db_review:
                return jsonify({
                    "success": False,
                    "message": "리뷰 정보를 찾을 수 없습니다."
                }), 404

            detail_review = convert_review_row_to_payload(db_review)

            return jsonify({
                "success": True,
                "message": "리뷰 상세 조회 완료",
                "detail_review": detail_review
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


    @app.route("/owner/review_management/api/reply/save", methods=["POST"], endpoint="owner_review_management_api_reply_save")
    def owner_review_management_api_reply_save():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_review_id = request.form.get("client_review_id", "").strip()
        client_reply_content = request.form.get("client_reply_content", "").strip()

        if not client_review_id:
            return jsonify({
                "success": False,
                "message": "리뷰 번호가 필요합니다."
            }), 400

        if not client_reply_content:
            return jsonify({
                "success": False,
                "message": "답변 내용을 입력해주세요."
            }), 400

        try:
            selected_restaurant_id, _ = get_selected_review_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            if owner_review_db.exists_owner_reply_by_review_id(int(client_review_id)):
                return jsonify({
                    "success": False,
                    "message": "이미 등록된 답변이 있습니다. 수정 기능을 사용해주세요."
                }), 400

            owner_review_db.insert_owner_reply(
                db_review_id=int(client_review_id),
                session_owner_id=session_owner_id,
                db_restaurant_id=selected_restaurant_id,
                client_reply_content=client_reply_content
            )

            db_summary = owner_review_db.get_review_summary_by_restaurant(selected_restaurant_id)
            db_review = owner_review_db.get_review_detail_by_review_id(
                db_restaurant_id=selected_restaurant_id,
                db_review_id=int(client_review_id)
            )

            return jsonify({
                "success": True,
                "message": "리뷰 답변이 등록되었습니다.",
                "summary_data": db_summary,
                "detail_review": convert_review_row_to_payload(db_review)
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


    @app.route("/owner/review_management/api/reply/update", methods=["POST"], endpoint="owner_review_management_api_reply_update")
    def owner_review_management_api_reply_update():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_review_id = request.form.get("client_review_id", "").strip()
        client_reply_content = request.form.get("client_reply_content", "").strip()

        if not client_review_id:
            return jsonify({
                "success": False,
                "message": "리뷰 번호가 필요합니다."
            }), 400

        if not client_reply_content:
            return jsonify({
                "success": False,
                "message": "수정할 답변 내용을 입력해주세요."
            }), 400

        try:
            selected_restaurant_id, _ = get_selected_review_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            if not owner_review_db.exists_owner_reply_by_review_id(int(client_review_id)):
                return jsonify({
                    "success": False,
                    "message": "기존 답변이 없습니다. 등록 기능을 먼저 사용해주세요."
                }), 400

            owner_review_db.update_owner_reply(
                db_review_id=int(client_review_id),
                session_owner_id=session_owner_id,
                db_restaurant_id=selected_restaurant_id,
                client_reply_content=client_reply_content
            )

            db_summary = owner_review_db.get_review_summary_by_restaurant(selected_restaurant_id)
            db_review = owner_review_db.get_review_detail_by_review_id(
                db_restaurant_id=selected_restaurant_id,
                db_review_id=int(client_review_id)
            )

            return jsonify({
                "success": True,
                "message": "리뷰 답변이 수정되었습니다.",
                "summary_data": db_summary,
                "detail_review": convert_review_row_to_payload(db_review)
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


    @app.route("/owner/review_management/api/reply/delete", methods=["POST"], endpoint="owner_review_management_api_reply_delete")
    def owner_review_management_api_reply_delete():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_review_id = request.form.get("client_review_id", "").strip()

        if not client_review_id:
            return jsonify({
                "success": False,
                "message": "리뷰 번호가 필요합니다."
            }), 400

        try:
            selected_restaurant_id, _ = get_selected_review_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            owner_review_db.delete_owner_reply(int(client_review_id))

            db_summary = owner_review_db.get_review_summary_by_restaurant(selected_restaurant_id)
            db_review = owner_review_db.get_review_detail_by_review_id(
                db_restaurant_id=selected_restaurant_id,
                db_review_id=int(client_review_id)
            )

            return jsonify({
                "success": True,
                "message": "리뷰 답변이 삭제되었습니다.",
                "summary_data": db_summary,
                "detail_review": convert_review_row_to_payload(db_review)
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500


    @app.route("/owner/review_management/api/reply/hide", methods=["POST"], endpoint="owner_review_management_api_reply_hide")
    def owner_review_management_api_reply_hide():
        session_owner_id = session.get("owner_id")

        if not session_owner_id:
            session_owner_id = 1

        client_restaurant_id = request.form.get("client_restaurant_id", "").strip()
        client_review_id = request.form.get("client_review_id", "").strip()

        if not client_review_id:
            return jsonify({
                "success": False,
                "message": "리뷰 번호가 필요합니다."
            }), 400

        try:
            selected_restaurant_id, _ = get_selected_review_restaurant_id(
                session_owner_id,
                client_restaurant_id
            )

            if not owner_review_db.exists_owner_reply_by_review_id(int(client_review_id)):
                owner_review_db.insert_owner_reply(
                    db_review_id=int(client_review_id),
                    session_owner_id=session_owner_id,
                    db_restaurant_id=selected_restaurant_id,
                    client_reply_content=""
                )

            owner_review_db.hide_review_reply(int(client_review_id))

            db_summary = owner_review_db.get_review_summary_by_restaurant(selected_restaurant_id)
            db_review = owner_review_db.get_review_detail_by_review_id(
                db_restaurant_id=selected_restaurant_id,
                db_review_id=int(client_review_id)
            )

            return jsonify({
                "success": True,
                "message": "리뷰가 숨김 처리되었습니다.",
                "summary_data": db_summary,
                "detail_review": convert_review_row_to_payload(db_review)
            })
        except Exception as error:
            return jsonify({
                "success": False,
                "message": str(error)
            }), 500