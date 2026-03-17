document.addEventListener("DOMContentLoaded", () => {
    // ==================================================================================
    // 공지사항 관리 JS 요약
    // ----------------------------------------------------------------------------------
    // 1. 식당 선택 시 해당 restaurant_id 기준으로 목록을 다시 조회한다.
    // 2. 공지 등록/수정 시 FormData 로 제목/내용/이미지/상단고정을 전송한다.
    // 3. 이미지 미리보기는 기본 공백 상태이고, 파일 선택 시에만 표시된다.
    // 4. 수정 클릭 시 상세 조회 후 폼에 값을 다시 채운다.
    // 5. 삭제 클릭 시 DB 삭제 후 목록을 다시 렌더링한다.
    // 6. 오너보드 공지 카드를 클릭해 이동한 경우 query string 의 restaurant_id, focus_notice_id 를 읽어
    //    해당 페이지의 noticeList 내부 카드 위치로 스크롤하고 시각적으로 포커스한다.
    // 7. 초기 진입 시 query string 의 restaurant_id 가 있으면 해당 가게 목록을 다시 조회한 뒤 포커스를 시도한다.
    // ==================================================================================

    const noticeForm = document.getElementById("noticeForm");
    const restaurantSelect = document.getElementById("restaurant-id");
    const noticeIdInput = document.getElementById("notice-id");
    const noticeTitleInput = document.getElementById("notice-title");
    const noticeContentInput = document.getElementById("notice-content");
    const noticePinInput = document.getElementById("notice-pin");
    const noticeFileInput = document.getElementById("notice-file");
    const currentPageInput = document.getElementById("current-page");
    const removeImageInput = document.getElementById("remove-image");

    const noticeList = document.getElementById("noticeList");
    const totalNoticeCount = document.getElementById("totalNoticeCount");
    const pageStatus = document.getElementById("pageStatus");
    const prevPageBtn = document.getElementById("prevPageBtn");
    const nextPageBtn = document.getElementById("nextPageBtn");

    const resetFormBtn = document.getElementById("resetFormBtn");
    const removeImageBtn = document.getElementById("removeImageBtn");
    const noticeImagePreview = document.getElementById("noticeImagePreview");

    let currentPage = Number(window.ownerNoticeInitialData?.initial_payload?.current_page || 1);
    let totalPages = Number(window.ownerNoticeInitialData?.initial_payload?.total_pages || 1);

    const urlSearchParams = new URLSearchParams(window.location.search);
    const focusNoticeId = urlSearchParams.get("focus_notice_id");
    const queryRestaurantId = urlSearchParams.get("restaurant_id");

    function setImagePreview(src) {
        if (src) {
            noticeImagePreview.src = src;
            noticeImagePreview.hidden = false;
        } else {
            noticeImagePreview.src = "";
            noticeImagePreview.hidden = true;
        }
    }

    function resetForm() {
        const selectedRestaurantId = restaurantSelect.value;

        noticeForm.reset();
        restaurantSelect.value = selectedRestaurantId;
        noticeIdInput.value = "";
        removeImageInput.value = "N";
        currentPageInput.value = String(currentPage);
        setImagePreview("");
    }

    function renderPagination(payload) {
        currentPage = Number(payload.current_page || 1);
        totalPages = Number(payload.total_pages || 1);

        currentPageInput.value = String(currentPage);
        pageStatus.textContent = `${currentPage} / ${totalPages}`;

        prevPageBtn.disabled = !payload.has_prev;
        nextPageBtn.disabled = !payload.has_next;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function focusNoticeCard(noticeId) {
        if (!noticeId) {
            return;
        }

        const targetCard = noticeList.querySelector(`[data-notice-id="${noticeId}"]`);

        if (!targetCard) {
            return;
        }

        targetCard.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

        targetCard.setAttribute("tabindex", "-1");
        targetCard.focus({ preventScroll: true });

        targetCard.style.outline = "3px solid #9caf7f";
        targetCard.style.boxShadow = "0 0 0 6px rgba(156, 175, 127, 0.18)";

        window.setTimeout(() => {
            targetCard.style.outline = "";
            targetCard.style.boxShadow = "";
        }, 2200);
    }

    function renderNoticeList(payload) {
        totalNoticeCount.textContent = payload.total_notice_count || 0;

        if (!payload.notice_list || payload.notice_list.length === 0) {
            noticeList.innerHTML = `
                <article class="notice-item empty-state">
                    <div class="empty-icon">📢</div>
                    <strong>등록된 공지사항이 없습니다.</strong>
                    <p>이벤트, 휴무, 운영시간 변경 등 중요한 내용을 작성해보세요.</p>
                </article>
            `;
            renderPagination(payload);
            return;
        }

        noticeList.innerHTML = payload.notice_list.map((notice) => {
            const pinnedHtml = Number(notice.is_pinned) === 1
                ? `<strong class="notice-badge">고정</strong>`
                : "";

            const thumbHtml = notice.thumb_url
                ? `
                    <div class="notice-thumb-wrap">
                        <img src="/static/${notice.thumb_url}" alt="공지 썸네일" class="notice-thumb" />
                    </div>
                  `
                : "";

            return `
                <article class="notice-item" data-notice-id="${notice.notice_id}">
                    <div class="notice-item-top">
                        <div class="notice-top-left">
                            ${pinnedHtml}
                            <span class="notice-date">${escapeHtml(notice.created_at)}</span>
                        </div>
                    </div>

                    <div class="notice-item-body">
                        <div class="notice-item-text">
                            <h3>${escapeHtml(notice.notice_title)}</h3>
                            <p>${escapeHtml(notice.notice_content)}</p>
                        </div>
                        ${thumbHtml}
                    </div>

                    <div class="notice-item-actions">
                        <button type="button" class="text-btn notice-edit-btn" data-notice-id="${notice.notice_id}">수정</button>
                        <button type="button" class="text-btn danger notice-delete-btn" data-notice-id="${notice.notice_id}">삭제</button>
                    </div>
                </article>
            `;
        }).join("");

        renderPagination(payload);

        if (focusNoticeId) {
            focusNoticeCard(focusNoticeId);
        }
    }

    async function loadNoticeList(page = 1) {
        const restaurantId = restaurantSelect.value;

        const response = await fetch(`/owner/notice_management/api/list?restaurant_id=${encodeURIComponent(restaurantId)}&page=${encodeURIComponent(page)}`);

        if (!response.ok) {
            const errorText = await response.text();
            console.error("notice list response error =", errorText);
            alert("공지사항 목록을 불러오지 못했습니다.");
            return;
        }

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 목록을 불러오지 못했습니다.");
            return;
        }

        renderNoticeList(result);
    }

    async function loadNoticeDetail(noticeId) {
        const restaurantId = restaurantSelect.value;

        const response = await fetch(`/owner/notice_management/api/detail/${noticeId}?restaurant_id=${encodeURIComponent(restaurantId)}`);

        if (!response.ok) {
            const errorText = await response.text();
            console.error("notice detail response error =", errorText);
            alert("공지사항 상세 정보를 불러오지 못했습니다.");
            return;
        }

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 상세 정보를 불러오지 못했습니다.");
            return;
        }

        noticeIdInput.value = result.notice_id || "";
        noticeTitleInput.value = result.notice_title || "";
        noticeContentInput.value = result.notice_content || "";
        noticePinInput.checked = Number(result.is_pinned) === 1;
        removeImageInput.value = "N";

        if (result.notice_url) {
            setImagePreview(`/static/${result.notice_url}`);
        } else {
            setImagePreview("");
        }

        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    async function saveNotice(event) {
        event.preventDefault();

        const formData = new FormData();
        formData.append("client_notice_id", noticeIdInput.value.trim());
        formData.append("client_restaurant_id", restaurantSelect.value);
        formData.append("client_notice_title", noticeTitleInput.value.trim());
        formData.append("client_notice_content", noticeContentInput.value.trim());
        formData.append("client_is_pinned", noticePinInput.checked ? "Y" : "N");
        formData.append("client_remove_image", removeImageInput.value);
        formData.append("client_page", currentPageInput.value || "1");

        if (noticeFileInput.files[0]) {
            formData.append("client_notice_image", noticeFileInput.files[0]);
        }

        const response = await fetch("/owner/notice_management/api/save", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("notice save response error =", errorText);
            alert("공지사항 저장에 실패했습니다.");
            return;
        }

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 저장에 실패했습니다.");
            return;
        }

        alert(result.message || "저장되었습니다.");
        renderNoticeList(result);
        resetForm();
    }

    async function deleteNotice(noticeId) {
        const formData = new FormData();
        formData.append("client_restaurant_id", restaurantSelect.value);
        formData.append("client_page", currentPageInput.value || "1");

        const response = await fetch(`/owner/notice_management/api/delete/${noticeId}`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("notice delete response error =", errorText);
            alert("공지사항 삭제에 실패했습니다.");
            return;
        }

        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항 삭제에 실패했습니다.");
            return;
        }

        alert(result.message || "삭제되었습니다.");
        renderNoticeList(result);
        resetForm();
    }

    restaurantSelect.addEventListener("change", async () => {
        currentPage = 1;
        currentPageInput.value = "1";
        resetForm();
        await loadNoticeList(1);
    });

    noticeFileInput.addEventListener("change", () => {
        const file = noticeFileInput.files[0];

        if (!file) {
            setImagePreview("");
            return;
        }

        const previewUrl = URL.createObjectURL(file);
        setImagePreview(previewUrl);
        removeImageInput.value = "N";
    });

    removeImageBtn.addEventListener("click", () => {
        noticeFileInput.value = "";
        removeImageInput.value = "Y";
        setImagePreview("");
    });

    resetFormBtn.addEventListener("click", () => {
        resetForm();
    });

    prevPageBtn.addEventListener("click", async () => {
        if (currentPage > 1) {
            await loadNoticeList(currentPage - 1);
        }
    });

    nextPageBtn.addEventListener("click", async () => {
        if (currentPage < totalPages) {
            await loadNoticeList(currentPage + 1);
        }
    });

    noticeList.addEventListener("click", async (event) => {
        const editBtn = event.target.closest(".notice-edit-btn");
        const deleteBtn = event.target.closest(".notice-delete-btn");

        if (editBtn) {
            const noticeId = editBtn.dataset.noticeId;
            await loadNoticeDetail(noticeId);
            return;
        }

        if (deleteBtn) {
            const noticeId = deleteBtn.dataset.noticeId;
            const isConfirmed = window.confirm("해당 공지사항을 삭제하시겠습니까?");

            if (isConfirmed) {
                await deleteNotice(noticeId);
            }
        }
    });

    noticeForm.addEventListener("submit", saveNotice);

    if (queryRestaurantId && restaurantSelect) {
        restaurantSelect.value = queryRestaurantId;
    }

    renderPagination(window.ownerNoticeInitialData?.initial_payload || {
        current_page: 1,
        total_pages: 1,
        has_prev: false,
        has_next: false
    });

    window.setTimeout(async () => {
        if (queryRestaurantId) {
            await loadNoticeList(1);
        }

        if (focusNoticeId) {
            focusNoticeCard(focusNoticeId);
        }
    }, 0);
});