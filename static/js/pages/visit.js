const visitStampBtn = document.getElementById("visitStampBtn");
const visitReceiptModal = document.getElementById("visitReceiptModal");
const visitReceiptBackdrop = document.getElementById("visitReceiptBackdrop");
const visitReceiptCloseBtn = document.getElementById("visitReceiptCloseBtn");
const visitReceiptCancelBtn = document.getElementById("visitReceiptCancelBtn");
const visitReceiptForm = document.getElementById("visitReceiptForm");
const receiptImageInput = document.getElementById("receiptImageInput");
const visitPreviewArea = document.getElementById("visitPreviewArea");
const visitPreviewImage = document.getElementById("visitPreviewImage");
const visitFileName = document.getElementById("visitFileName");
const visitLoadingArea = document.getElementById("visitLoadingArea");
const visitReceiptMessage = document.getElementById("visitReceiptMessage");
const visitReceiptSubmitBtn = document.getElementById("visitReceiptSubmitBtn");

function openVisitReceiptModal() {
    if (!visitReceiptModal) return;
    visitReceiptModal.hidden = false;
    document.body.classList.add("visit-modal-open");
}

function closeVisitReceiptModal() {
    if (!visitReceiptModal) return;
    visitReceiptModal.hidden = true;
    document.body.classList.remove("visit-modal-open");
    resetVisitReceiptForm();
}

function resetVisitReceiptForm() {
    if (visitReceiptForm) {
        visitReceiptForm.reset();
    }

    if (visitPreviewArea) {
        visitPreviewArea.hidden = true;
    }

    if (visitPreviewImage) {
        visitPreviewImage.removeAttribute("src");
    }

    if (visitFileName) {
        visitFileName.textContent = "";
    }

    if (visitLoadingArea) {
        visitLoadingArea.hidden = true;
    }

    if (visitReceiptSubmitBtn) {
        visitReceiptSubmitBtn.disabled = false;
    }

    hideVisitMessage();
}

function showVisitMessage(message, type = "error") {
    if (!visitReceiptMessage) return;

    visitReceiptMessage.hidden = false;
    visitReceiptMessage.textContent = message;
    visitReceiptMessage.className = `visit-modal__message is-${type}`;
}

function hideVisitMessage() {
    if (!visitReceiptMessage) return;

    visitReceiptMessage.hidden = true;
    visitReceiptMessage.textContent = "";
    visitReceiptMessage.className = "visit-modal__message";
}

function showVisitLoading() {
    if (visitLoadingArea) {
        visitLoadingArea.hidden = false;
    }

    if (visitReceiptSubmitBtn) {
        visitReceiptSubmitBtn.disabled = true;
    }

    if (receiptImageInput) {
        receiptImageInput.disabled = true;
    }
}

function hideVisitLoading() {
    if (visitLoadingArea) {
        visitLoadingArea.hidden = true;
    }

    if (visitReceiptSubmitBtn) {
        visitReceiptSubmitBtn.disabled = false;
    }

    if (receiptImageInput) {
        receiptImageInput.disabled = false;
    }
}

function refreshRestaurantDataAfterVisit() {
    const activeSortChip = document.querySelector(".sort-chip.active");

    if (
        activeSortChip &&
        activeSortChip.dataset.sort === "latest" &&
        typeof window.fetchFavoriteRestaurants === "function"
    ) {
        return window.fetchFavoriteRestaurants();
    }

    if (typeof window.fetchRestaurants === "function") {
        return window.fetchRestaurants();
    }

    return Promise.resolve();
}

function handleReceiptImagePreview(event) {
    const file = event.target.files?.[0];

    hideVisitMessage();

    if (!file) {
        if (visitPreviewArea) {
            visitPreviewArea.hidden = true;
        }

        if (visitPreviewImage) {
            visitPreviewImage.removeAttribute("src");
        }

        if (visitFileName) {
            visitFileName.textContent = "";
        }

        return;
    }

    if (visitFileName) {
        visitFileName.textContent = file.name;
    }

    const reader = new FileReader();
    reader.onload = (loadEvent) => {
        if (visitPreviewImage) {
            visitPreviewImage.src = loadEvent.target.result;
        }

        if (visitPreviewArea) {
            visitPreviewArea.hidden = false;
        }
    };

    reader.readAsDataURL(file);
}

async function handleVisitReceiptSubmit(event) {
    event.preventDefault();

    const file = receiptImageInput?.files?.[0];
    if (!file) {
        showVisitMessage("영수증 사진을 먼저 선택해 주세요.");
        return;
    }

    const formData = new FormData();
    formData.append("receipt_image", file);

    hideVisitMessage();
    showVisitLoading();

    try {
        const response = await fetch(window.__INITIAL_STATE__.visitReceiptApiUrl, {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (response.status === 401) {
            showVisitMessage(result.message || "로그인 후 이용해 주세요.");

            setTimeout(() => {
                window.location.href = window.__INITIAL_STATE__.loginUrl;
            }, 800);

            return;
        }

        if (!response.ok || !result.success) {
            showVisitMessage(result.message || "영수증을 다시 찍어주세요!");
            return;
        }

        showVisitMessage(result.message || "등록완료!", "success");

        // 영수증 등록 성공 시 랭킹 & 요약 데이터 백그라운드 갱신 
        if (typeof loadRankingData === 'function') loadRankingData();
        if (typeof loadRankingSummary === 'function') loadRankingSummary();

        // 화면 전체를 새로고침하던 await refreshRestaurantDataAfterVisit(); 를 지우고,
        // 왼쪽 리스트에서 방금 도장 찍은 식당의 '방문' 숫자만 +1 올려줍니다.
        const card = document.querySelector(`.restaurant-card[data-id="${result.restaurant_id}"]`);
        if (card) {
            card.querySelectorAll('.stat-pill').forEach(pill => {
                if (pill.innerText.includes('방문')) {
                    const count = parseInt(pill.innerText.replace(/[^0-9]/g, '')) || 0;
                    pill.innerText = `방문 ${count + 1}`;
                }
            });
        }

        setTimeout(() => {
            closeVisitReceiptModal();
        }, 500);

    } catch (error) {
        console.error(error);
        showVisitMessage("영수증 등록 중 오류가 발생했습니다.");
    } finally {
        hideVisitLoading();
    }
}

if (visitStampBtn) {
    visitStampBtn.addEventListener("click", openVisitReceiptModal);
}

if (visitReceiptBackdrop) {
    visitReceiptBackdrop.addEventListener("click", closeVisitReceiptModal);
}

if (visitReceiptCloseBtn) {
    visitReceiptCloseBtn.addEventListener("click", closeVisitReceiptModal);
}

if (visitReceiptCancelBtn) {
    visitReceiptCancelBtn.addEventListener("click", closeVisitReceiptModal);
}

if (receiptImageInput) {
    receiptImageInput.addEventListener("change", handleReceiptImagePreview);
}

if (visitReceiptForm) {
    visitReceiptForm.addEventListener("submit", handleVisitReceiptSubmit);
}

window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && visitReceiptModal && !visitReceiptModal.hidden) {
        closeVisitReceiptModal();
    }
});