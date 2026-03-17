document.addEventListener("DOMContentLoaded", function () {
    // =========================
    // 화면 상태값 관리
    // - currentPage : 현재 페이지 번호
    // - totalPages  : 전체 페이지 수
    // - editMenuId  : 수정중인 메뉴 id
    // - initialData : 서버가 최초 렌더링 시 내려준 목록 데이터
    // =========================
    const state = {
        currentPage: 1,
        totalPages: 1,
        editMenuId: null,
        selectedRestaurantId: window.ownerMenuSelectedRestaurantId || null,
        initialData: window.ownerMenuInitialData || {
            menu_list: [],
            current_page: 1,
            total_pages: 1,
            has_prev: false,
            has_next: false,
            total_menu_count: 0
        }
    };

    // Ajax 요청 경로
    const menuApi = window.ownerMenuApi || {};

    // =========================
    // 자주 사용하는 DOM 요소 캐싱
    // =========================
    const menuForm = document.getElementById("menuForm");
    const formTitle = document.getElementById("formTitle");
    const submitBtn = document.getElementById("submitBtn");
    const cancelEditBtn = document.getElementById("cancelEditBtn");

    const clientMenuIdInput = document.getElementById("client-menu-id");
    const clientPageInput = document.getElementById("client-page");
    const clientRestaurantIdInput = document.getElementById("client-restaurant-id");
    const clientMenuNameInput = document.getElementById("menu-name");
    const clientPriceInput = document.getElementById("menu-price");
    const clientMenuCategoryInput = document.getElementById("menu-category");
    const clientMenuImageInput = document.getElementById("menu-image-input");
    const clientRemoveImageInput = document.getElementById("remove-image-input");
    const clientSoldoutInput = document.getElementById("soldout-input");

    const previewImage = document.getElementById("previewImage");
    const previewEmpty = document.getElementById("previewEmpty");
    const imageGuideText = document.getElementById("imageGuideText");
    const removeImageLabel = document.getElementById("removeImageLabel");

    const registeredMenuList = document.getElementById("registeredMenuList");
    const paginationWrap = document.getElementById("paginationWrap");
    const registeredMenuCount = document.getElementById("registeredMenuCount");
    const formMessageList = document.getElementById("formMessageList");
    const restaurantToggleGroup = document.getElementById("restaurantToggleGroup");

    // =========================
    // HTML 특수문자 이스케이프
    // - 사용자 입력값을 그대로 innerHTML에 넣을 때 안전하게 처리
    // =========================
    function escapeHtml(value) {
        return String(value ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    // =========================
    // 가격 세자리 콤마 처리
    // =========================
    function numberWithComma(value) {
        return Number(value || 0).toLocaleString("ko-KR");
    }

    // =========================
    // 상단 메시지 출력
    // - Ajax 성공/실패 안내
    // =========================
    function showMessage(message, type = "success") {
        formMessageList.hidden = false;
        formMessageList.innerHTML = `
            <p class="form-message-item ${type === "error" ? "is-error" : "is-success"}">
                ${escapeHtml(message)}
            </p>
        `;
    }

    // 메시지 초기화
    function clearMessage() {
        formMessageList.hidden = true;
        formMessageList.innerHTML = "";
    }

    // =========================
    // 이미지 미리보기 갱신
    // - 등록/수정 시 현재 이미지 상태를 화면에 반영
    // =========================
    function updatePreview(imageUrl = "", originalName = "") {
        if (imageUrl) {
            previewImage.src = imageUrl;
            previewImage.style.display = "block";
            previewEmpty.style.display = "none";
            imageGuideText.textContent = originalName ? `현재 파일: ${originalName}` : "현재 이미지가 등록되어 있습니다.";
        } else {
            previewImage.src = "";
            previewImage.style.display = "none";
            previewEmpty.style.display = "block";
            imageGuideText.textContent = "이미지 미등록";
        }
    }

    // =========================
    // 폼 초기화
    // - 등록 모드로 되돌림
    // =========================
    function resetForm() {
        state.editMenuId = null;
        clientMenuIdInput.value = "";
        clientRestaurantIdInput.value = state.selectedRestaurantId || "";
        clientMenuNameInput.value = "";
        clientPriceInput.value = "";
        clientMenuCategoryInput.selectedIndex = 0;
        clientMenuImageInput.value = "";
        clientRemoveImageInput.checked = false;
        clientSoldoutInput.checked = false;
        formTitle.textContent = "메뉴 등록";
        submitBtn.textContent = "등록완료";
        removeImageLabel.style.display = "inline-flex";
        updatePreview("", "");
        clearMessage();
    }

    // =========================
    // 메뉴 목록 Ajax 조회
    // - 페이지 이동 없이 목록만 다시 그림
    // - SPA 방식 페이지네이션 핵심
    // =========================
    async function fetchMenuList(page = 1) {
        const response = await fetch(`${menuApi.listUrl}?page=${page}&restaurant_id=${state.selectedRestaurantId}`, {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "메뉴 목록을 불러오지 못했습니다.");
        }

        state.currentPage = result.current_page;
        state.totalPages = result.total_pages;
        state.selectedRestaurantId = result.restaurant_id;
        clientPageInput.value = result.current_page;
        clientRestaurantIdInput.value = result.restaurant_id;

        renderMenuList(result);
        renderPagination(result);
        registeredMenuCount.textContent = `총 ${numberWithComma(result.total_menu_count)}개`;
    }

    // =========================
    // 메뉴 목록 렌더링
    // - 서버에서 받은 JSON을 카드 목록으로 그림
    // - 수정/삭제 버튼은 말풍선 확인 UI와 연결
    // =========================
    function renderMenuList(result) {
        const menuList = result.menu_list || [];

        if (!menuList.length) {
            registeredMenuList.innerHTML = `<p class="empty-menu-message">등록된 메뉴가 없습니다.</p>`;
            return;
        }

        registeredMenuList.innerHTML = menuList.map((menu) => {
            const imageHtml = menu.thumb_url
                ? `<img src="/static/${escapeHtml(menu.thumb_url)}" alt="${escapeHtml(menu.menu_name)} 이미지">`
                : menu.image_url
                    ? `<img src="/static/${escapeHtml(menu.image_url)}" alt="${escapeHtml(menu.menu_name)} 이미지">`
                    : `<div class="registered-menu-thumb-empty"></div>`;

            const fileHtml = menu.original_name
                ? `<p class="registered-menu-file">파일명: ${escapeHtml(menu.original_name)}</p>`
                : "";

            const statusText = menu.status === "OFF" ? "품절" : "판매중";

            return `
                <article class="registered-menu-item" data-menu-id="${menu.menu_id}">
                    <div class="registered-menu-thumb">
                        ${imageHtml}
                    </div>

                    <div class="registered-menu-info">
                        <p class="registered-menu-name">${escapeHtml(menu.menu_name)}</p>
                        <p class="registered-menu-price">${numberWithComma(menu.price)}원</p>
                        <p class="registered-menu-category">${escapeHtml(menu.menu_category_name || "")}</p>
                        <p class="registered-menu-status">${statusText}</p>
                        ${fileHtml}
                    </div>

                    <div class="registered-menu-actions">
                        <div class="action-bubble-wrap">
                            <button
                                type="button"
                                class="menu-edit-btn js-open-confirm"
                                data-action="edit"
                                data-menu-id="${menu.menu_id}"
                            >
                                수정
                            </button>
                        </div>

                        <div class="action-bubble-wrap">
                            <button
                                type="button"
                                class="menu-delete-btn js-open-confirm"
                                data-action="delete"
                                data-menu-id="${menu.menu_id}"
                            >
                                삭제
                            </button>
                        </div>
                    </div>
                </article>
            `;
        }).join("");
    }

    // =========================
    // 페이지네이션 렌더링
    // - 링크 이동이 아닌 버튼 클릭으로 Ajax 조회
    // =========================
    function renderPagination(result) {
        if (!result.total_pages || result.total_pages <= 1) {
            paginationWrap.innerHTML = "";
            return;
        }

        const pages = [];
        for (let pageNumber = 1; pageNumber <= result.total_pages; pageNumber += 1) {
            pages.push(`
                <button
                    type="button"
                    class="pagination-btn ${pageNumber === result.current_page ? "is-active" : ""}"
                    data-page="${pageNumber}"
                >
                    ${pageNumber}
                </button>
            `);
        }

        paginationWrap.innerHTML = `
            ${result.has_prev ? `<button type="button" class="pagination-btn pagination-nav" data-page="${result.current_page - 1}">이전</button>` : ""}
            <div class="pagination-list">
                ${pages.join("")}
            </div>
            ${result.has_next ? `<button type="button" class="pagination-btn pagination-nav" data-page="${result.current_page + 1}">다음</button>` : ""}
        `;
    }

    // =========================
    // 메뉴 상세 조회
    // - 수정 확인창에서 "네"를 누르면 실행
    // - 선택한 메뉴 데이터를 폼에 채워 수정모드로 전환
    // =========================
    async function loadMenuDetail(menuId) {
        const response = await fetch(`${menuApi.detailBaseUrl}/${menuId}?restaurant_id=${state.selectedRestaurantId}`, {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "메뉴 상세 정보를 불러오지 못했습니다.");
        }

        state.editMenuId = result.menu_id;
        clientMenuIdInput.value = result.menu_id;
        clientRestaurantIdInput.value = result.restaurant_id || state.selectedRestaurantId || "";
        clientMenuNameInput.value = result.menu_name || "";
        clientPriceInput.value = result.price || "";
        clientMenuCategoryInput.value = result.menu_category_id || "";
        clientMenuImageInput.value = "";
        clientRemoveImageInput.checked = false;
        clientSoldoutInput.checked = result.status === "OFF";

        formTitle.textContent = "메뉴 수정";
        submitBtn.textContent = "수정완료";
        removeImageLabel.style.display = "inline-flex";

        const previewUrl = result.thumb_url
            ? `/static/${result.thumb_url}`
            : result.image_url
                ? `/static/${result.image_url}`
                : "";

        updatePreview(previewUrl, result.original_name || "");
        clearMessage();

        // 수정폼이 바로 보이도록 상단으로 이동
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // =========================
    // 메뉴 저장
    // - 등록/수정 공통 처리
    // - FormData로 이미지 포함 Ajax 전송
    // =========================
    async function saveMenu(event) {
        event.preventDefault();
        clearMessage();

        const formData = new FormData();
        formData.append("client_restaurant_id", clientRestaurantIdInput.value);
        formData.append("client_menu_id", clientMenuIdInput.value.trim());
        formData.append("client_menu_name", clientMenuNameInput.value.trim());
        formData.append("client_price", clientPriceInput.value.trim());
        formData.append("client_menu_category_id", clientMenuCategoryInput.value);
        formData.append("client_page", clientPageInput.value);
        formData.append("client_remove_image", clientRemoveImageInput.checked ? "Y" : "N");
        formData.append("client_soldout", clientSoldoutInput.checked ? "Y" : "N");

        const clientMenuImageFile = clientMenuImageInput.files[0];
        if (clientMenuImageFile) {
            formData.append("client_menu_image", clientMenuImageFile);
        }

        const response = await fetch(menuApi.saveUrl, {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            showMessage(result.message || "저장 중 오류가 발생했습니다.", "error");
            return;
        }

        state.currentPage = result.current_page;
        state.selectedRestaurantId = result.restaurant_id || state.selectedRestaurantId;
        clientPageInput.value = result.current_page;
        clientRestaurantIdInput.value = result.restaurant_id || state.selectedRestaurantId || "";

        // 저장 후 목록/페이지네이션 즉시 갱신
        renderMenuList(result);
        renderPagination(result);
        registeredMenuCount.textContent = `총 ${numberWithComma(result.total_menu_count)}개`;

        // 폼은 등록모드로 초기화
        resetForm();
        showMessage(result.message || "저장이 완료되었습니다.", "success");
    }

    // =========================
    // 메뉴 삭제
    // - 삭제 말풍선에서 "네" 클릭 시 실행
    // - 삭제 후 현재 페이지 기준으로 목록 다시 렌더링
    // =========================
    async function deleteMenu(menuId) {
        const formData = new FormData();
        formData.append("client_page", clientPageInput.value);
        formData.append("client_restaurant_id", clientRestaurantIdInput.value);

        const response = await fetch(`${menuApi.deleteBaseUrl}/${menuId}`, {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            showMessage(result.message || "삭제 중 오류가 발생했습니다.", "error");
            return;
        }

        state.currentPage = result.current_page;
        state.selectedRestaurantId = result.restaurant_id || state.selectedRestaurantId;
        clientPageInput.value = result.current_page;
        clientRestaurantIdInput.value = result.restaurant_id || state.selectedRestaurantId || "";

        renderMenuList(result);
        renderPagination(result);
        registeredMenuCount.textContent = `총 ${numberWithComma(result.total_menu_count)}개`;
        showMessage(result.message || "삭제가 완료되었습니다.", "success");

        // 현재 수정중인 메뉴를 삭제한 경우 폼도 초기화
        if (state.editMenuId && Number(state.editMenuId) === Number(menuId)) {
            resetForm();
        }
    }

    // =========================
    // 모든 말풍선 닫기
    // - 한 번에 하나만 열리게 하기 위해 사용
    // =========================
    function closeAllBubbles() {
        document.querySelectorAll(".confirm-bubble").forEach((bubble) => bubble.remove());
    }

    // =========================
    // 수정/삭제 확인 말풍선 열기
    // - alert/confirm 대신 카드 옆에 직접 출력
    // - 네/아니오 버튼 결과를 받아 실제 동작 수행
    // =========================
    function openConfirmBubble(button, action, menuId) {
        closeAllBubbles();

        const bubbleWrap = button.closest(".action-bubble-wrap");
        if (!bubbleWrap) {
            return;
        }

        const bubble = document.createElement("div");
        bubble.className = "confirm-bubble";

        const questionText = action === "edit"
            ? "이 메뉴를 수정하시겠습니까?"
            : "이 메뉴를 삭제하시겠습니까?";

        bubble.innerHTML = `
            <p class="confirm-bubble__text">${questionText}</p>
            <div class="confirm-bubble__actions">
                <button type="button" class="confirm-bubble__btn yes-btn">네</button>
                <button type="button" class="confirm-bubble__btn no-btn">아니오</button>
            </div>
        `;

        bubbleWrap.appendChild(bubble);

        const yesBtn = bubble.querySelector(".yes-btn");
        const noBtn = bubble.querySelector(".no-btn");

        yesBtn.addEventListener("click", async function () {
            closeAllBubbles();

            if (action === "edit") {
                await loadMenuDetail(menuId);
            }

            if (action === "delete") {
                await deleteMenu(menuId);
            }
        });

        noBtn.addEventListener("click", function () {
            closeAllBubbles();
        });
    }

    // =========================
    // 파일 선택 시 이미지 미리보기
    // - 업로드 전 로컬 미리보기 표시
    // =========================
    if (clientMenuImageInput) {
        clientMenuImageInput.addEventListener("change", function (event) {
            const selectedFile = event.target.files && event.target.files[0];

            if (!selectedFile) {
                updatePreview("", "");
                return;
            }

            const objectUrl = URL.createObjectURL(selectedFile);
            updatePreview(objectUrl, selectedFile.name);
        });
    }

    // =========================
    // 메뉴 저장 submit 처리
    // =========================
    if (menuForm) {
        menuForm.addEventListener("submit", saveMenu);
    }

    // =========================
    // 수정 취소 버튼
    // =========================
    if (cancelEditBtn) {
        cancelEditBtn.addEventListener("click", function () {
            resetForm();
        });
    }

    // =========================
    // 가게 선택 토글 변경 처리
    // - 선택한 restaurant_id 기준으로 메뉴 목록만 Ajax 재조회
    // =========================
    if (restaurantToggleGroup) {
        restaurantToggleGroup.addEventListener("change", async function (event) {
            const selectedRadio = event.target.closest('input[type="radio"]');

            if (!selectedRadio) {
                return;
            }

            state.selectedRestaurantId = Number(selectedRadio.value);
            clientRestaurantIdInput.value = selectedRadio.value;
            clientPageInput.value = 1;

            resetForm();
            await fetchMenuList(1);
        });
    }

    // =========================
    // 페이지네이션 클릭 처리
    // - data-page 값을 읽어 Ajax로 목록만 교체
    // =========================
    if (paginationWrap) {
        paginationWrap.addEventListener("click", async function (event) {
            const pageButton = event.target.closest("[data-page]");
            if (!pageButton) {
                return;
            }

            const nextPage = Number(pageButton.dataset.page);
            if (!nextPage || nextPage === state.currentPage) {
                return;
            }

            await fetchMenuList(nextPage);
        });
    }

    // =========================
    // 메뉴 목록 내 수정/삭제 버튼 클릭 처리
    // - 이벤트 위임 방식 사용
    // =========================
    if (registeredMenuList) {
        registeredMenuList.addEventListener("click", async function (event) {
            const confirmButton = event.target.closest(".js-open-confirm");

            if (!confirmButton) {
                return;
            }

            const action = confirmButton.dataset.action;
            const menuId = Number(confirmButton.dataset.menuId);

            if (!action || !menuId) {
                return;
            }

            openConfirmBubble(confirmButton, action, menuId);
        });
    }

    // 목록 바깥 클릭 시 열려있는 말풍선 닫기
    document.addEventListener("click", function (event) {
        if (!event.target.closest(".action-bubble-wrap")) {
            closeAllBubbles();
        }
    });

    // =========================
    // 최초 화면 렌더링
    // - 서버가 내려준 initialData로 첫 목록 출력
    // - 이후부터는 Ajax로만 갱신
    // =========================
    (function init() {
        state.currentPage = state.initialData.current_page || 1;
        clientPageInput.value = state.currentPage;
        clientRestaurantIdInput.value = state.selectedRestaurantId || "";
        renderMenuList(state.initialData);
        renderPagination(state.initialData);
        registeredMenuCount.textContent = `총 ${numberWithComma(state.initialData.total_menu_count)}개`;
        resetForm();
    })();
});