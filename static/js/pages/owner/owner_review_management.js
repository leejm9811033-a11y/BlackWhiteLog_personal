// static/js/owner/owner_review_management.js

document.addEventListener("DOMContentLoaded", () => {
    // 영역: 페이지 상태
    const pageRoot = document.getElementById("ownerReviewPage");
    if (!pageRoot) {
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const initialFocusReviewId = Number(urlParams.get("focus_review_id") || 0);

    const state = {
        restaurantId: Number(urlParams.get("restaurant_id") || pageRoot.dataset.restaurantId || 0),
        tab: urlParams.get("tab") || pageRoot.dataset.tab || "all",
        sort: urlParams.get("sort") || pageRoot.dataset.sort || "latest",
        page: Number(urlParams.get("page") || pageRoot.dataset.page || 1),
        keyword: urlParams.get("keyword") || "",
        selectedReviewId: initialFocusReviewId || null
    };

    // 영역: DOM 참조
    const reviewRestaurantSelect = document.getElementById("reviewRestaurantSelect");
    const reviewSummaryGrid = document.getElementById("reviewSummaryGrid");
    const reviewTabGroup = document.getElementById("reviewTabGroup");
    const reviewSortGroup = document.getElementById("reviewSortGroup");
    const reviewSearchInput = document.getElementById("reviewSearchInput");
    const reviewSearchBtn = document.getElementById("reviewSearchBtn");
    const reviewTableBody = document.getElementById("reviewTableBody");
    const reviewPagination = document.getElementById("reviewPagination");
    const reviewDetailCard = document.getElementById("reviewDetailCard");

    // 영역: 공통 유틸
    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function buildStars(rating) {
        const safeRating = Number(rating || 0);
        return "★".repeat(safeRating) + "☆".repeat(5 - safeRating);
    }

    function getStatusBadgeHtml(review) {
        if (Number(review.is_visible) === 0) {
            return '<span class="state-badge hidden">숨김</span>';
        }

        if (Number(review.is_active) === 1) {
            return '<span class="state-badge done">답변완료</span>';
        }

        return '<span class="state-badge pending">미답변</span>';
    }

    function getStatusText(review) {
        if (Number(review.is_visible) === 0) {
            return "숨김";
        }

        if (Number(review.is_active) === 1) {
            return "답변완료";
        }

        return "미답변";
    }

    function buildQueryString(params) {
        const query = new URLSearchParams();

        Object.entries(params).forEach(([key, value]) => {
            if (value === undefined || value === null || String(value).trim() === "") {
                return;
            }
            query.append(key, value);
        });

        return query.toString();
    }

    async function fetchJson(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                ...(options.headers || {})
            }
        });

        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            const text = await response.text();
            console.error("JSON 아님:", text);
            throw new Error("서버 응답이 JSON 형식이 아닙니다. 라우트 또는 경로를 확인해주세요.");
        }

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.message || "요청 처리 중 오류가 발생했습니다.");
        }

        return data;
    }

    function syncPageDataset() {
        pageRoot.dataset.restaurantId = String(state.restaurantId || 0);
        pageRoot.dataset.tab = state.tab;
        pageRoot.dataset.sort = state.sort;
        pageRoot.dataset.page = String(state.page || 1);
    }

    function setActiveButton(groupElement, selector, datasetKey, activeValue) {
        if (!groupElement) {
            return;
        }

        groupElement.querySelectorAll(selector).forEach((button) => {
            button.classList.toggle("active", button.dataset[datasetKey] === activeValue);
        });
    }

    function showAlert(message) {
        window.alert(message);
    }

    // - 추가: 특정 행 포커스 표시
    function focusReviewRow(reviewId) {
        if (!reviewTableBody || !reviewId) {
            return;
        }

        const targetRow = reviewTableBody.querySelector(`tr[data-review-id="${reviewId}"]`);
        if (!targetRow) {
            return;
        }

        targetRow.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });

        targetRow.classList.add("is-selected");
        targetRow.style.outline = "3px solid #9caf7f";
        targetRow.style.boxShadow = "0 0 0 6px rgba(156, 175, 127, 0.18)";

        window.setTimeout(() => {
            targetRow.style.outline = "";
            targetRow.style.boxShadow = "";
        }, 2200);
    }

    function renderSummary(summaryData) {
        if (!reviewSummaryGrid || !summaryData) {
            return;
        }

        reviewSummaryGrid.innerHTML = `
            <article class="summary-card card active">
                <span class="summary-label">전체 리뷰</span>
                <strong class="summary-value">${Number(summaryData.total_review_count || 0)}건</strong>
            </article>

            <article class="summary-card card">
                <span class="summary-label">미답변</span>
                <strong class="summary-value">${Number(summaryData.pending_review_count || 0)}건</strong>
            </article>

            <article class="summary-card card">
                <span class="summary-label">답변완료</span>
                <strong class="summary-value">${Number(summaryData.done_review_count || 0)}건</strong>
            </article>

            <article class="summary-card card warning">
                <span class="summary-label">숨김리뷰</span>
                <strong class="summary-value">${Number(summaryData.hidden_review_count || 0)}건</strong>
            </article>
        `;
    }

    function renderReviewTable(reviewList, selectedReviewId) {
        if (!reviewTableBody) {
            return;
        }

        if (!Array.isArray(reviewList) || reviewList.length === 0) {
            reviewTableBody.innerHTML = `
                <tr>
                    <td colspan="5">조회된 리뷰가 없습니다.</td>
                </tr>
            `;
            return;
        }

        reviewTableBody.innerHTML = reviewList.map((review) => {
            const isSelected = Number(review.review_id) === Number(selectedReviewId);

            return `
                <tr class="${isSelected ? "is-selected" : ""}" data-review-id="${review.review_id}">
                    <td>${escapeHtml(review.updated_at || "")}</td>
                    <td>${escapeHtml(review.nickname || "")}</td>
                    <td class="review-content-cell" title="${escapeHtml(review.content || "")}">
                        ${escapeHtml(review.content_preview || "")}
                    </td>
                    <td>${escapeHtml(review.rating_text || buildStars(review.rating))}</td>
                    <td>${getStatusBadgeHtml(review)}</td>
                </tr>
            `;
        }).join("");
    }

    function renderPagination(currentPage, totalPages) {
        if (!reviewPagination) {
            return;
        }

        const safeCurrentPage = Number(currentPage || 1);
        const safeTotalPages = Number(totalPages || 1);

        if (safeTotalPages <= 1) {
            reviewPagination.innerHTML = "";
            return;
        }

        let html = "";

        if (safeCurrentPage > 1) {
            html += `<button type="button" data-page="${safeCurrentPage - 1}">&lt;</button>`;
        }

        for (let page = 1; page <= safeTotalPages; page += 1) {
            html += `
                <button type="button" data-page="${page}" class="${page === safeCurrentPage ? "active" : ""}">
                    ${page}
                </button>
            `;
        }

        if (safeCurrentPage < safeTotalPages) {
            html += `<button type="button" data-page="${safeCurrentPage + 1}">&gt;</button>`;
        }

        reviewPagination.innerHTML = html;
    }

    function renderDetail(detailReview) {
        if (!reviewDetailCard) {
            return;
        }

        if (!detailReview) {
            reviewDetailCard.innerHTML = `
                <div class="detail-content">
                    <div class="detail-row">
                        <strong>리뷰 상세</strong>
                        <p>선택된 리뷰가 없습니다.</p>
                    </div>
                </div>
            `;
            return;
        }

        reviewDetailCard.innerHTML = `
            <div class="detail-meta">
                <span><strong>작성자</strong> : ${escapeHtml(detailReview.nickname || "")}</span>
                <span><strong>별점</strong> : ${escapeHtml(detailReview.rating_text || buildStars(detailReview.rating))}</span>
                <span><strong>작성일</strong> : ${escapeHtml(detailReview.created_at || "")}</span>
                <span><strong>상태</strong> : ${escapeHtml(detailReview.review_status_text || getStatusText(detailReview))}</span>
            </div>

            <div class="detail-content">
                <div class="detail-row">
                    <strong>리뷰 내용</strong>
                    <p>${escapeHtml(detailReview.content || "")}</p>
                </div>

                <div class="detail-row answer-row">
                    <strong>사장님 답변</strong>
                    <textarea
                        id="reviewReplyTextarea"
                        placeholder="고객에게 남길 답변을 입력해주세요."
                        data-review-id="${detailReview.review_id}"
                    >${escapeHtml(detailReview.reply_content || "")}</textarea>
                </div>
            </div>

            <div class="detail-actions">
                <button class="fill-btn" type="button" id="replySaveBtn">답변 등록</button>
                <button class="ghost-btn" type="button" id="replyUpdateBtn">답변 수정</button>
                <button class="ghost-btn" type="button" id="replyDeleteBtn">답변 삭제</button>
                <button class="ghost-btn warning" type="button" id="replyHideBtn">숨김 처리</button>
            </div>
        `;
    }

    function updateSelectedRow(reviewId) {
        if (!reviewTableBody) {
            return;
        }

        reviewTableBody.querySelectorAll("tr[data-review-id]").forEach((row) => {
            row.classList.toggle("is-selected", Number(row.dataset.reviewId) === Number(reviewId));
        });
    }

    async function loadReviewDetail(reviewId) {
        if (!reviewId) {
            renderDetail(null);
            return;
        }

        const queryString = buildQueryString({
            restaurant_id: state.restaurantId
        });

        const data = await fetchJson(`/owner/review_management/api/detail/${reviewId}?${queryString}`);

        state.selectedReviewId = Number(reviewId);
        renderDetail(data.detail_review);
        updateSelectedRow(reviewId);
        focusReviewRow(reviewId);
    }

    async function loadReviewList({ keepSelected = true } = {}) {
        syncPageDataset();

        const queryString = buildQueryString({
            restaurant_id: state.restaurantId,
            tab: state.tab,
            sort: state.sort,
            keyword: state.keyword,
            page: state.page
        });

        const data = await fetchJson(`/owner/review_management/api/list?${queryString}`);

        renderSummary(data.summary_data);
        setActiveButton(reviewTabGroup, ".tab-btn", "tab", state.tab);
        setActiveButton(reviewSortGroup, ".filter-chip", "sort", state.sort);

        let nextSelectedReviewId = data.selected_review_id;

        if (keepSelected && state.selectedReviewId) {
            const exists = Array.isArray(data.review_list)
                && data.review_list.some((review) => Number(review.review_id) === Number(state.selectedReviewId));

            if (exists) {
                nextSelectedReviewId = state.selectedReviewId;
            }
        }

        state.selectedReviewId = nextSelectedReviewId ? Number(nextSelectedReviewId) : null;

        renderReviewTable(data.review_list || [], state.selectedReviewId);
        renderPagination(data.current_page || 1, data.total_pages || 1);

        if (state.selectedReviewId) {
            await loadReviewDetail(state.selectedReviewId);
        } else {
            renderDetail(null);
        }
    }

    function getCurrentReplyInfo() {
        const textarea = document.getElementById("reviewReplyTextarea");

        if (!textarea) {
            return {
                reviewId: null,
                replyContent: ""
            };
        }

        return {
            reviewId: Number(textarea.dataset.reviewId || 0),
            replyContent: textarea.value.trim()
        };
    }

    async function submitReplyAction(actionType) {
        const { reviewId, replyContent } = getCurrentReplyInfo();

        if (!reviewId) {
            showAlert("선택된 리뷰가 없습니다.");
            return;
        }

        if ((actionType === "save" || actionType === "update") && !replyContent) {
            showAlert("답변 내용을 입력해주세요.");
            return;
        }

        let endpoint = "";
        let confirmMessage = "";

        if (actionType === "save") {
            endpoint = "/owner/review_management/api/reply/save";
            confirmMessage = "답변을 등록하시겠습니까?";
        } else if (actionType === "update") {
            endpoint = "/owner/review_management/api/reply/update";
            confirmMessage = "답변을 수정하시겠습니까?";
        } else if (actionType === "delete") {
            endpoint = "/owner/review_management/api/reply/delete";
            confirmMessage = "답변을 삭제하시겠습니까?";
        } else if (actionType === "hide") {
            endpoint = "/owner/review_management/api/reply/hide";
            confirmMessage = "이 리뷰를 숨김 처리하시겠습니까?";
        }

        if (!endpoint) {
            return;
        }

        if (!window.confirm(confirmMessage)) {
            return;
        }

        const formData = new FormData();
        formData.append("client_restaurant_id", String(state.restaurantId || ""));
        formData.append("client_review_id", String(reviewId));

        if (actionType === "save" || actionType === "update") {
            formData.append("client_reply_content", replyContent);
        }

        const data = await fetchJson(endpoint, {
            method: "POST",
            body: formData
        });

        renderSummary(data.summary_data);
        renderDetail(data.detail_review);
        state.selectedReviewId = Number(reviewId);
        await loadReviewList({ keepSelected: true });
        showAlert(data.message || "처리가 완료되었습니다.");
    }

    if (reviewRestaurantSelect) {
        reviewRestaurantSelect.addEventListener("change", async (event) => {
            state.restaurantId = Number(event.target.value || 0);
            state.page = 1;
            state.tab = "all";
            state.sort = "latest";
            state.keyword = "";
            state.selectedReviewId = null;

            if (reviewSearchInput) {
                reviewSearchInput.value = "";
            }

            try {
                await loadReviewList({ keepSelected: false });
            } catch (error) {
                showAlert(error.message);
            }
        });
    }

    if (reviewTabGroup) {
        reviewTabGroup.addEventListener("click", async (event) => {
            const button = event.target.closest(".tab-btn");
            if (!button) {
                return;
            }

            const nextTab = button.dataset.tab;
            if (!nextTab) {
                return;
            }

            state.tab = nextTab;
            state.page = 1;
            state.selectedReviewId = null;

            try {
                await loadReviewList({ keepSelected: false });
            } catch (error) {
                showAlert(error.message);
            }
        });
    }

    if (reviewSortGroup) {
        reviewSortGroup.addEventListener("click", async (event) => {
            const button = event.target.closest(".filter-chip");
            if (!button) {
                return;
            }

            const nextSort = button.dataset.sort;
            if (!nextSort) {
                return;
            }

            state.sort = nextSort;
            state.page = 1;

            try {
                await loadReviewList({ keepSelected: true });
            } catch (error) {
                showAlert(error.message);
            }
        });
    }

    async function handleSearch() {
        state.keyword = (reviewSearchInput?.value || "").trim();
        state.page = 1;
        state.selectedReviewId = null;

        try {
            await loadReviewList({ keepSelected: false });
        } catch (error) {
            showAlert(error.message);
        }
    }

    if (reviewSearchBtn) {
        reviewSearchBtn.addEventListener("click", handleSearch);
    }

    if (reviewSearchInput) {
        reviewSearchInput.addEventListener("keydown", async (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                await handleSearch();
            }
        });
    }

    if (reviewTableBody) {
        reviewTableBody.addEventListener("click", async (event) => {
            const row = event.target.closest("tr[data-review-id]");
            if (!row) {
                return;
            }

            const reviewId = Number(row.dataset.reviewId || 0);
            if (!reviewId) {
                return;
            }

            try {
                await loadReviewDetail(reviewId);
            } catch (error) {
                showAlert(error.message);
            }
        });
    }

    if (reviewPagination) {
        reviewPagination.addEventListener("click", async (event) => {
            const button = event.target.closest("button[data-page]");
            if (!button) {
                return;
            }

            const nextPage = Number(button.dataset.page || 1);
            if (!nextPage || nextPage === state.page) {
                return;
            }

            state.page = nextPage;
            state.selectedReviewId = null;

            try {
                await loadReviewList({ keepSelected: false });
            } catch (error) {
                showAlert(error.message);
            }
        });
    }

    if (reviewDetailCard) {
        reviewDetailCard.addEventListener("click", async (event) => {
            const saveBtn = event.target.closest("#replySaveBtn");
            const updateBtn = event.target.closest("#replyUpdateBtn");
            const deleteBtn = event.target.closest("#replyDeleteBtn");
            const hideBtn = event.target.closest("#replyHideBtn");

            try {
                if (saveBtn) {
                    await submitReplyAction("save");
                    return;
                }

                if (updateBtn) {
                    await submitReplyAction("update");
                    return;
                }

                if (deleteBtn) {
                    await submitReplyAction("delete");
                    return;
                }

                if (hideBtn) {
                    await submitReplyAction("hide");
                }
            } catch (error) {
                showAlert(error.message);
            }
        });
    }

    if (reviewSearchInput) {
        reviewSearchInput.value = state.keyword;
    }

    const initialSelectedRow = reviewTableBody?.querySelector("tr.is-selected[data-review-id]");
    if (initialSelectedRow && !state.selectedReviewId) {
        state.selectedReviewId = Number(initialSelectedRow.dataset.reviewId || 0);
    }

    // - 추가: 보드에서 focus_review_id로 넘어온 경우 첫 진입 즉시 포커스
    if (state.selectedReviewId) {
        focusReviewRow(state.selectedReviewId);
        loadReviewDetail(state.selectedReviewId).catch((error) => {
            showAlert(error.message);
        });
    }
});