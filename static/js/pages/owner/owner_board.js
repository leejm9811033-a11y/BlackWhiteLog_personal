document.addEventListener("DOMContentLoaded", () => {
    // ==================================================================================
    // 오너보드 공지사항 SPA 요약
    // ----------------------------------------------------------------------------------
    // 1. 오너가 여러 가게를 가진 경우 select 토글로 restaurant_id를 선택한다.
    // 2. 선택된 restaurant_id 기준으로 현재 고정 공지 1건 + 일반 공지 3건을 AJAX로 다시 조회한다.
    // 3. 현재 공지 카드는 is_pinned = 1 중 updated_at 최신 1건만 표시한다.
    // 4. 이전 공지 카드는 is_pinned = 0 중 updated_at 최신순 3건만 표시한다.
    // 5. 카드를 클릭하면 공지사항 관리 페이지로 이동하고, 해당 noticeList 카드 위치로 포커스한다.
    // ==================================================================================

    const sidebarNoticeRestaurantSelect = document.getElementById("sidebarNoticeRestaurantSelect");
    const sidebarNoticeCurrent = document.getElementById("sidebarNoticeCurrent");
    const sidebarNoticeHistoryList = document.getElementById("sidebarNoticeHistoryList");

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function buildNoticeManagementUrl(restaurantId, noticeId) {
        const url = new URL("/owner/notice_management", window.location.origin);
        url.searchParams.set("restaurant_id", restaurantId);

        if (noticeId) {
            url.searchParams.set("focus_notice_id", noticeId);
        }

        return url.toString();
    }

    function moveToNoticeManagement(restaurantId, noticeId) {
        window.location.href = buildNoticeManagementUrl(restaurantId, noticeId);
    }

    function renderCurrentNotice(currentNotice, restaurantId) {
        if (!currentNotice) {
            sidebarNoticeCurrent.className = "sidebar-notice-current";
            sidebarNoticeCurrent.removeAttribute("data-notice-id");
            sidebarNoticeCurrent.setAttribute("data-restaurant-id", restaurantId || "");
            sidebarNoticeCurrent.removeAttribute("tabindex");
            sidebarNoticeCurrent.removeAttribute("role");
            sidebarNoticeCurrent.removeAttribute("aria-label");

            sidebarNoticeCurrent.innerHTML = `
                <span class="notice-badge empty">현재</span>
                <strong class="notice-title">고정된 공지사항이 없습니다.</strong>
                <p class="notice-content">상단 고정된 공지사항을 등록하면 이 영역에 가장 최근 공지가 표시됩니다.</p>
                <span class="notice-date">-</span>
            `;
            return;
        }

        sidebarNoticeCurrent.className = "sidebar-notice-current is-clickable";
        sidebarNoticeCurrent.dataset.noticeId = currentNotice.notice_id;
        sidebarNoticeCurrent.dataset.restaurantId = currentNotice.restaurant_id;
        sidebarNoticeCurrent.setAttribute("tabindex", "0");
        sidebarNoticeCurrent.setAttribute("role", "button");
        sidebarNoticeCurrent.setAttribute("aria-label", "현재 공지사항 상세 보기");

        sidebarNoticeCurrent.innerHTML = `
            <span class="notice-badge">현재</span>
            <strong class="notice-title">${escapeHtml(currentNotice.notice_title)}</strong>
            <p class="notice-content">${escapeHtml(currentNotice.notice_content)}</p>
            <span class="notice-date">${escapeHtml(currentNotice.updated_at)}</span>
        `;
    }

    function renderHistoryNoticeList(historyNoticeList) {
        if (!historyNoticeList || historyNoticeList.length === 0) {
            sidebarNoticeHistoryList.innerHTML = `
                <li class="notice-history-item">
                    <div class="notice-history-card empty-card">
                        <strong class="notice-title">이전 공지가 없습니다.</strong>
                        <p class="notice-content">최근 일반 공지가 등록되면 이 영역에 최대 3개까지 표시됩니다.</p>
                        <span class="notice-date">-</span>
                    </div>
                </li>
            `;
            return;
        }

        sidebarNoticeHistoryList.innerHTML = historyNoticeList.map((db_notice) => {
            return `
                <li class="notice-history-item">
                    <div
                        class="notice-history-card is-clickable"
                        data-notice-id="${db_notice.notice_id}"
                        data-restaurant-id="${db_notice.restaurant_id}"
                        tabindex="0"
                        role="button"
                        aria-label="공지사항 상세 보기"
                    >
                        <strong class="notice-title">${escapeHtml(db_notice.notice_title)}</strong>
                        <p class="notice-content">${escapeHtml(db_notice.notice_content)}</p>
                        <span class="notice-date">${escapeHtml(db_notice.updated_at)}</span>
                    </div>
                </li>
            `;
        }).join("");
    }

    async function loadSidebarNoticeSummary(restaurantId) {
        const response = await fetch(`/owner/board/api/notice_summary?restaurant_id=${encodeURIComponent(restaurantId)}`);
        const result = await response.json();

        if (!result.success) {
            alert(result.message || "공지사항을 불러오지 못했습니다.");
            return;
        }

        renderCurrentNotice(result.current_notice, result.restaurant_id);
        renderHistoryNoticeList(result.history_notice_list || []);
    }

    sidebarNoticeRestaurantSelect.addEventListener("change", async (event) => {
        const client_restaurant_id = event.target.value;
        await loadSidebarNoticeSummary(client_restaurant_id);
    });

    sidebarNoticeCurrent.addEventListener("click", (event) => {
        const card = event.currentTarget;
        const restaurantId = card.dataset.restaurantId;
        const noticeId = card.dataset.noticeId;

        if (!restaurantId || !noticeId) {
            return;
        }

        moveToNoticeManagement(restaurantId, noticeId);
    });

    sidebarNoticeCurrent.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        event.preventDefault();

        const card = event.currentTarget;
        const restaurantId = card.dataset.restaurantId;
        const noticeId = card.dataset.noticeId;

        if (!restaurantId || !noticeId) {
            return;
        }

        moveToNoticeManagement(restaurantId, noticeId);
    });

    sidebarNoticeHistoryList.addEventListener("click", (event) => {
        const noticeCard = event.target.closest(".notice-history-card.is-clickable");

        if (!noticeCard) {
            return;
        }

        const restaurantId = noticeCard.dataset.restaurantId;
        const noticeId = noticeCard.dataset.noticeId;

        if (!restaurantId || !noticeId) {
            return;
        }

        moveToNoticeManagement(restaurantId, noticeId);
    });

    sidebarNoticeHistoryList.addEventListener("keydown", (event) => {
        const noticeCard = event.target.closest(".notice-history-card.is-clickable");

        if (!noticeCard) {
            return;
        }

        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }

        event.preventDefault();

        const restaurantId = noticeCard.dataset.restaurantId;
        const noticeId = noticeCard.dataset.noticeId;

        if (!restaurantId || !noticeId) {
            return;
        }

        moveToNoticeManagement(restaurantId, noticeId);
    });
});

let visitChartInstance = null;

async function loadVisitChart(restaurantId) {
    const response = await fetch(`/owner/board/api/visit_chart?restaurant_id=${restaurantId}`);
    const data = await response.json();

    if (!data.success) return;

    const labels = data.chart_data.map(item => `${item.label}(${item.weekday})`);
    const values = data.chart_data.map(item => item.visit_count);

    const canvas = document.getElementById("visitChart");
    if (!canvas) return;

    if (visitChartInstance) {
        visitChartInstance.destroy();
    }

    visitChartInstance = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [{
                label: "방문자 수",
                data: values,
                borderColor: "#2f6fed",
                backgroundColor: "rgba(47,111,237,0.12)",
                fill: true,
                tension: 0.35,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        stepSize: 1
                    }
                },
                x: {
                    ticks: {
                        autoSkip: false,
                        maxRotation: 0,
                        minRotation: 0
                    }
                }
            }
        }
    });
}